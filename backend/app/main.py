from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Annotated, Any
from urllib.parse import unquote
from uuid import UUID, uuid4

import httpx
from fastapi import BackgroundTasks
from fastapi import HTTPException
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jwt import InvalidTokenError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .auth import AuthenticatedUser, SupabaseTokenVerifier
from .config import Settings, get_settings
from .dev_tools import clear_plan_override, read_plan_override, write_plan_override
from .rate_limit import InMemoryRateLimiter
from .replay import (
    clear_cassette,
    get_replay_meta,
    get_replay_mode,
    list_cassettes,
    load_cassette,
    save_cassette,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
PAGES_DIR = FRONTEND_DIR / "pages"
CATALOG_SEED_DIR = REPO_ROOT / "backend" / "catalog_seed"
CATALOG_SEED_TAG_PREFIX = "seed:"


class UsageSummaryCache:
    _CLEANUP_INTERVAL = 300

    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _purge_stale(self, now: float) -> None:
        stale = [k for k, (ts, _) in self._entries.items() if now - ts > self._ttl]
        for k in stale:
            del self._entries[k]

    def get(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            now = time.time()
            if now - self._last_cleanup > self._CLEANUP_INTERVAL:
                self._purge_stale(now)
                self._last_cleanup = now

            entry = self._entries.get(user_id)
            if entry is None:
                return None
            ts, data = entry
            if now - ts > self._ttl:
                del self._entries[user_id]
                return None
            return data.copy()

    def put(self, user_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._entries[user_id] = (time.time(), data.copy())

    def reserve_request(self, user_id: str, summary: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        with self._lock:
            now = time.time()
            entry = self._entries.get(user_id)
            if entry is None or now - entry[0] > self._ttl:
                data = summary.copy()
                ts = now
            else:
                ts, data = entry
                data = data.copy()

            used = int(data.get("monthly_requests_used") or 0)
            limit = data.get("monthly_request_limit")
            if limit is not None and used >= int(limit):
                self._entries[user_id] = (ts, data)
                return False, data.copy()

            data["monthly_requests_used"] = used + 1
            if limit is not None:
                data["monthly_requests_remaining"] = max(0, int(limit) - data["monthly_requests_used"])
            self._entries[user_id] = (ts, data)
            return True, data.copy()

    def release_request(self, user_id: str) -> None:
        with self._lock:
            entry = self._entries.get(user_id)
            if entry is None:
                return
            ts, data = entry
            data = data.copy()
            used = int(data.get("monthly_requests_used") or 0)
            if used > 0:
                data["monthly_requests_used"] = used - 1
            limit = data.get("monthly_request_limit")
            if limit is not None:
                data["monthly_requests_remaining"] = max(0, int(limit) - data["monthly_requests_used"])
            self._entries[user_id] = (ts, data)


logger = logging.getLogger("mnemorized.proxy")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


class MessagePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    max_tokens: int = Field(gt=0, le=64000)
    messages: list[dict[str, Any]] = Field(min_length=1)
    system: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=1)
    top_p: float | None = Field(default=None, ge=0, le=1)
    tools: list[dict[str, Any]] | None = None
    betas: list[str] | None = None


class DevPlanOverridePayload(BaseModel):
    plan_code: str = Field(pattern="^(free|pro|team|enterprise|unlimited)$")
    clear: bool = False


class PalaceSnapshotPayload(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    topic: str = Field(min_length=1, max_length=20000)
    source_name: str | None = Field(default=None, max_length=240)
    scene_title: str | None = Field(default=None, max_length=240)
    status: str = Field(default="generated", max_length=40)
    generation_inputs: dict[str, Any] = Field(default_factory=dict)
    generation_outputs: dict[str, Any] = Field(default_factory=dict)


class PalaceSavePayload(BaseModel):
    palace_id: str | None = None
    snapshot: PalaceSnapshotPayload


class PalaceRenamePayload(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class CatalogPublishPayload(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    topic: str = Field(min_length=1, max_length=20000)
    source_name: str | None = Field(default=None, max_length=240)
    scene_title: str | None = Field(default=None, max_length=240)
    tags: list[str] = Field(default_factory=list)
    generation_inputs: dict[str, Any] = Field(default_factory=dict)
    generation_outputs: dict[str, Any] = Field(default_factory=dict)


class CatalogSeedPublishPayload(BaseModel):
    slug: str = Field(min_length=1, max_length=80, pattern="^[a-z0-9][a-z0-9-]*$")


ImagePrompt = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=8000),
]


class ImageGenerationPayload(BaseModel):
    prompts: list[ImagePrompt] = Field(min_length=1, max_length=2)


class GeminiPromptAnchorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int = Field(ge=1, le=50)
    hook: str | None = Field(default=None, max_length=1000)
    visual: str = Field(min_length=1, max_length=4000)
    anchor: str | None = Field(default=None, max_length=4000)
    zone: str | None = Field(default=None, max_length=80)


class GeminiPromptDirectorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1, max_length=20000)
    scene_title: str | None = Field(default=None, max_length=240)
    opening: str | None = Field(default=None, max_length=8000)
    anchors: list[GeminiPromptAnchorPayload] = Field(min_length=1, max_length=20)
    mode: str = Field(default="initial", pattern="^(initial|repair)$")


class MedicalContextPayload(BaseModel):
    topic: str = Field(min_length=1, max_length=20000)
    max_chunks: int = Field(default=8, ge=1, le=12)


class MedicalQualityGatePayload(BaseModel):
    topic: str = Field(min_length=1, max_length=20000)
    generation_outputs: dict[str, Any] = Field(default_factory=dict)
    required_concepts: list[str] = Field(default_factory=list, max_length=40)
    max_evidence_chunks: int = Field(default=8, ge=1, le=12)


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
MEDICAL_EXCERPT_CHARS = 420
GEMINI_CONSTITUTION_PATH = REPO_ROOT / "docs" / "gemini-constitution.txt"


def _client_id(request: Request) -> str:
    settings = _get_runtime_settings(request)
    forwarded_for = request.headers.get("x-forwarded-for")
    if settings.trust_proxy_headers and forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_runtime_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", get_settings())


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "").strip()
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    return token or None


def _get_rate_limiter(request: Request, settings: Settings) -> InMemoryRateLimiter:
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = InMemoryRateLimiter(
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
        request.app.state.rate_limiter = limiter
    return limiter


def _request_size(request: Request) -> int:
    content_length = request.headers.get("content-length")
    try:
        return int(content_length) if content_length else 0
    except ValueError:
        return 0


def _rate_limit_subject(request: Request, user: AuthenticatedUser | None = None) -> str:
    if user:
        return f"user:{user.user_id}"
    return f"ip:{_client_id(request)}"


def _rate_limit_response(request_id: str, retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={
            "Retry-After": str(retry_after),
            "X-Request-ID": request_id,
        },
        content={
            "error": {
                "type": "rate_limit_error",
                "message": "Too many requests. Slow down and try again in a moment.",
            }
        },
    )


def _request_too_large_response(settings: Settings, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=413,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "type": "request_too_large",
                "message": f"Request exceeds MAX_REQUEST_BYTES={settings.max_request_bytes}.",
            }
        },
    )


def _auth_not_configured_response(request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "type": "auth_not_configured",
                "message": (
                    "Provider calls require Supabase auth in production, but Supabase "
                    "is not configured on the backend."
                ),
            }
        },
    )


def _auth_required_response(request_id: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "type": "authentication_required",
                "message": message,
            }
        },
    )


def _billing_context(settings: Settings) -> dict[str, Any]:
    return {
        "billing_mode": settings.billing_mode,
        "beta_mode": settings.billing_mode == "beta",
        "billing_enabled": settings.billing_upgrade_path_enabled,
        "upgrade_enabled": settings.billing_upgrade_path_enabled,
        "upgrade_path_enabled": settings.billing_upgrade_path_enabled,
        "billing_message": settings.billing_message,
        "upgrade_url": None,
        "quota_unit_label": "AI requests",
        "quota_reset_policy": "monthly",
    }


def _plan_display_name(plan_code: str | None, settings: Settings) -> str:
    plan = (plan_code or "free").strip().lower()
    if settings.billing_mode == "beta" and plan == "free":
        return "Free Beta"
    if plan == "pro":
        return "Pro"
    if plan == "team":
        return "Team"
    if plan == "enterprise":
        return "Enterprise"
    if plan == "unlimited":
        return "Unlimited"
    return "Free"


def _quota_exceeded_response(request_id: str, summary: dict[str, Any]) -> JSONResponse:
    monthly_limit = summary["monthly_request_limit"]
    monthly_used = summary["monthly_requests_used"]
    upgrade_path_enabled = bool(summary.get("upgrade_path_enabled"))
    billing_mode = summary.get("billing_mode") or "beta"
    billing_message = summary.get(
        "billing_message",
        "Billing is not active yet; account request limits are fixed by the backend.",
    )
    if upgrade_path_enabled:
        message = (
            f"You have used {monthly_used} of {monthly_limit} monthly requests "
            "for your current plan. Upgrade or wait for the next billing period."
        )
    else:
        message = (
            f"You have used {monthly_used} of {monthly_limit} monthly requests "
            "for your current plan. Billing is not active yet; wait for the next "
            "billing period or contact the app admin."
        )
    return JSONResponse(
        status_code=402,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "type": "quota_exceeded",
                "message": message,
            },
            "plan": {
                "code": summary["plan_code"],
                "display_name": summary.get("plan_display_name") or summary["plan_code"],
                "status": summary["subscription_status"],
            },
            "billing": {
                "mode": billing_mode,
                "upgrade_path_enabled": upgrade_path_enabled,
                "message": billing_message,
            },
            "usage": {
                "used": monthly_used,
                "limit": monthly_limit,
                "remaining": summary["monthly_requests_remaining"],
                "period_ends_at": summary["period_ends_at"],
            },
        },
    )


def _reserve_quota_if_needed(
    request: Request,
    user: AuthenticatedUser | None,
    summary: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    if user is None:
        return True, summary

    usage_cache: UsageSummaryCache | None = getattr(request.app.state, "usage_cache", None)
    if usage_cache is None:
        monthly_limit = summary["monthly_request_limit"]
        monthly_used = summary["monthly_requests_used"]
        return monthly_limit is None or monthly_used < monthly_limit, summary

    return usage_cache.reserve_request(user.user_id, summary)


def _release_quota_reservation(
    request: Request,
    user: AuthenticatedUser | None,
) -> None:
    if user is None:
        return
    usage_cache: UsageSummaryCache | None = getattr(request.app.state, "usage_cache", None)
    if usage_cache is not None:
        usage_cache.release_request(user.user_id)


def _load_gemini_constitution() -> str:
    try:
        constitution = GEMINI_CONSTITUTION_PATH.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("Gemini constitution could not be read: %s", exc)
        return ""
    return constitution[:60000]


def _gemini_text_from_response(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates", [])
    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return "".join(text_parts).strip()


def _extract_gemini_interaction_images(payload: dict[str, Any]) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            content_type = str(value.get("type") or "").lower()
            mime_type = (
                value.get("mime_type")
                or value.get("mimeType")
                or value.get("media_type")
                or value.get("mediaType")
                or "image/png"
            )
            data = value.get("data")
            if content_type == "image" and isinstance(data, str) and data:
                images.append({"mime_type": mime_type, "data": data})
                return

            inline_data = value.get("inlineData") or value.get("inline_data")
            if isinstance(inline_data, dict) and inline_data.get("data"):
                images.append({
                    "mime_type": inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png",
                    "data": inline_data["data"],
                })
                return

            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return images


def _gemini_prompt_director_system_prompt() -> str:
    constitution = _load_gemini_constitution()
    constitution_block = (
        "CURRENT MNEMORIZED GEMINI CONSTITUTION:\n"
        f"{constitution}\n\n"
        if constitution else
        "CURRENT MNEMORIZED GEMINI CONSTITUTION: unavailable; follow the built-in rules below.\n\n"
    )
    return (
        "You are Mnemorized's Gemini Constitution Director. Your job is to transform a "
        "validated memory-palace script into two image-generation prompts that maximize "
        "anchor legibility, exact medical text, and coherent spatial layout. "
        "Output strict JSON only. Do not include markdown, commentary, or extra keys.\n\n"
        f"{constitution_block}"
        "GLOBAL RULES:\n"
        "- Do not copy proprietary visual mnemonic products, recurring named characters, or brand-specific symbols.\n"
        "- Preserve all supplied anchors; do not invent new medical facts.\n"
        "- Prompt 1 is the empty room foundation only: no people, characters, props, labels, signs, or anchor objects.\n"
        "- Prompt 2 is the full single-scene mnemonic image with every supplied anchor present.\n"
        "- Keep the image in 16:9, hand-drawn 2D educational poster style, flat marker color, no 3D, no photorealism.\n"
        "- Use silhouette-first anchor language. Text is secondary and physically attached to mnemonic devices.\n"
        "- For precision text, prefer engraved, etched, chiseled, stamped, painted, or sticker-like physical text devices.\n"
        "- Avoid descriptive-noun label leakage: never ask for words like 'pharmacy label' or 'warning sign' to render.\n"
        "- Avoid adjacent duplicate characters on glowing or digital screen text; use physical text devices instead.\n"
        "- Keep visible labels sparse, exact, and large enough to read.\n\n"
        "JSON SCHEMA:\n"
        "{"
        "\"scene_description\":\"40-70 word empty-room description\","
        "\"prompt1\":\"complete Prompt 1 string\","
        "\"prompt2\":\"complete Prompt 2 string\","
        "\"notes\":\"one short implementation note\""
        "}"
    )


def _gemini_prompt_director_user_prompt(payload: GeminiPromptDirectorPayload) -> str:
    anchors = []
    for anchor in payload.anchors:
        zone = f" ({anchor.zone})" if anchor.zone else ""
        hook = f"\n  Hook: {anchor.hook}" if anchor.hook else ""
        encoded = f"\n  Encodes: {anchor.anchor}" if anchor.anchor else ""
        anchors.append(
            f"Anchor {anchor.n}{zone}:{hook}\n  Visual: {anchor.visual}{encoded}"
        )

    return (
        f"MODE: {payload.mode}\n"
        f"MEDICAL TOPIC:\n{payload.topic}\n\n"
        f"SCENE TITLE: {payload.scene_title or 'Untitled memory palace'}\n"
        f"OPENING / ATMOSPHERE:\n{payload.opening or ''}\n\n"
        f"ANCHORS TO PRESERVE ({len(payload.anchors)}):\n"
        + "\n\n".join(anchors)
        + "\n\nBuild Prompt 1 and Prompt 2 for direct submission to Gemini image generation. "
        "Prompt 2 must include all anchors, their zones, their exact medically essential labels or numbers, "
        "and the anti-meta-text boundary. Prompt 1 must contain only the empty spatial foundation."
    )


def _validated_prompt_director_payload(raw: dict[str, Any]) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError("Gemini prompt director did not return a JSON object.")

    result: dict[str, str] = {}
    for key in ("scene_description", "prompt1", "prompt2"):
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Gemini prompt director response is missing {key}.")
        result[key] = value.strip()

    notes = raw.get("notes")
    result["notes"] = notes.strip() if isinstance(notes, str) else ""
    return result


def _parse_json_object_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        parsed = json.loads(cleaned[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object.")
    return parsed


def _ensure_log_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _iso_month_start() -> str:
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_start.isoformat()


def _iso_next_month_start() -> str:
    now = datetime.now(UTC)
    if now.month == 12:
        next_month = now.replace(
            year=now.year + 1,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    else:
        next_month = now.replace(
            month=now.month + 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    return next_month.isoformat()


def _parse_content_range_total(header_value: str | None) -> int:
    if not header_value or "/" not in header_value:
        return 0
    total = header_value.rsplit("/", 1)[-1]
    if total == "*":
        return 0
    try:
        return int(total)
    except ValueError:
        return 0


def _parse_optional_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"expected ISO timestamp string, got {type(value).__name__}")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _get_http_client(request: Request) -> tuple[httpx.AsyncClient, bool]:
    http_client = getattr(request.app.state, "http_client", None)
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        return http_client, True
    return http_client, False


async def _resolve_authenticated_user(
    request: Request,
    settings: Settings,
) -> AuthenticatedUser | None:
    token = _extract_bearer_token(request)
    if not token:
        return None

    if not settings.supabase_auth_configured:
        raise HTTPException(
            status_code=503,
            detail="Supabase auth is not configured on the backend.",
        )

    verifier = getattr(request.app.state, "supabase_verifier", None)
    if verifier is None:
        verifier = SupabaseTokenVerifier(
            jwks_url=settings.supabase_jwks_url,
            issuer=settings.supabase_issuer,
            audience=settings.supabase_jwt_audience,
        )
        request.app.state.supabase_verifier = verifier

    http_client, owns_http_client = _get_http_client(request)
    try:
        return await verifier.verify_token(token, http_client)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid auth token: {exc}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not validate auth token against Supabase: {exc}",
        ) from exc
    finally:
        if owns_http_client:
            await http_client.aclose()


async def _supabase_rest_request(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str | None,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    use_service_role: bool = False,
) -> httpx.Response:
    api_key = (
        settings.supabase_service_role_key
        if use_service_role and settings.supabase_service_role_key
        else settings.supabase_anon_key
    )
    base_headers: dict[str, str] = {
        "apikey": api_key,
        "Content-Type": "application/json",
    }
    if use_service_role:
        base_headers["Authorization"] = f"Bearer {api_key}"
    elif bearer_token:
        base_headers["Authorization"] = f"Bearer {bearer_token}"
    if headers:
        base_headers.update(headers)

    http_client, owns_http_client = _get_http_client(request)
    try:
        response = await http_client.request(
            method,
            settings.supabase_url.rstrip("/") + path,
            headers=base_headers,
            params=params,
            json=json_body,
        )
        return response
    finally:
        if owns_http_client:
            await http_client.aclose()


PALACE_SELECT = "id,title,topic,scene_title,status,latest_version_number,updated_at,source_name"
PALACE_VERSION_SELECT = "version_number,generation_inputs,generation_outputs,created_at"
CATALOG_SELECT = (
    "id,title,topic,source_name,scene_title,tags,"
    "generation_inputs,generation_outputs,published_by,published_at"
)
ADMIN_USAGE_SELECT = (
    "id,user_id,provider,model,request_id,input_tokens,output_tokens,status_code,created_at"
)
ADMIN_PALACE_SELECT = (
    "id,user_id,title,topic,scene_title,status,latest_version_number,source_name,updated_at"
)
ADMIN_CATALOG_SELECT = "id,title,topic,scene_title,tags,published_by,published_at"
ADMIN_CATALOG_SEED_SELECT = (
    "id,title,topic,scene_title,tags,published_by,published_at,generation_inputs"
)


def _is_admin(user: AuthenticatedUser, settings: Settings) -> bool:
    if not user.email:
        return False
    return user.email.lower() in {e.lower() for e in settings.admin_emails}


async def _require_admin_context(
    request: Request,
    settings: Settings,
) -> tuple[str, AuthenticatedUser]:
    bearer_token, user = await _require_persistence_context(request, settings)
    if not _is_admin(user, settings):
        raise HTTPException(status_code=403, detail="Admin access is required.")
    return bearer_token, user


def _truncate_text(value: Any, limit: int = 180) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _sanitize_usage_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": record.get("timestamp") or record.get("created_at"),
        "request_id": record.get("request_id"),
        "user_id": record.get("user_id"),
        "user_email": record.get("user_email"),
        "provider": record.get("provider") or ("anthropic" if record.get("model") else None),
        "model": record.get("model"),
        "status_code": record.get("status_code"),
        "duration_ms": record.get("duration_ms"),
        "input_tokens": record.get("input_tokens"),
        "output_tokens": record.get("output_tokens"),
    }


def _read_recent_usage_log(settings: Settings, *, limit: int = 50) -> tuple[list[dict[str, Any]], str | None]:
    if not settings.usage_log_path.exists():
        return [], None

    try:
        lines = settings.usage_log_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], f"Could not read local usage log: {exc}"

    records: list[dict[str, Any]] = []
    for line in reversed(lines[-500:]):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except ValueError:
            continue
        if isinstance(raw, dict):
            records.append(_sanitize_usage_record(raw))
        if len(records) >= limit:
            break
    return records, None


async def _admin_supabase_rows(
    *,
    request: Request,
    settings: Settings,
    path: str,
    params: dict[str, Any],
    label: str,
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = await _supabase_rest_request(
            request=request,
            settings=settings,
            bearer_token=None,
            method="GET",
            path=path,
            params=params,
            use_service_role=True,
        )
        return _parse_supabase_rows(response, label), None
    except HTTPException as exc:
        return [], str(exc.detail)
    except httpx.HTTPError as exc:
        return [], f"Could not {label}: {exc}"


def _safe_status_code(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _usage_failure_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if (status := _safe_status_code(row.get("status_code"))) is not None and status >= 400
    ]


def _sanitize_palace_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "title": row.get("title"),
        "topic_preview": _truncate_text(row.get("topic"), 160),
        "scene_title": row.get("scene_title"),
        "status": row.get("status"),
        "latest_version_number": row.get("latest_version_number"),
        "source_name": row.get("source_name"),
        "updated_at": row.get("updated_at"),
    }


def _sanitize_catalog_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "topic_preview": _truncate_text(row.get("topic"), 160),
        "scene_title": row.get("scene_title"),
        "tags": row.get("tags") or [],
        "published_by": row.get("published_by"),
        "published_at": row.get("published_at"),
    }


def _catalog_seed_tag(slug: str) -> str:
    return f"{CATALOG_SEED_TAG_PREFIX}{slug}"


def _catalog_seed_version_tag(version: int) -> str:
    return f"seed-version:{version}"


def _clean_catalog_tags(tags: list[str]) -> list[str]:
    clean_tags: list[str] = []
    seen: set[str] = set()
    for raw_tag in tags:
        tag = str(raw_tag).strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        clean_tags.append(tag[:40])
    return clean_tags


def _validate_catalog_seed_payload(payload: Any, source_name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{source_name} must contain a JSON object.")

    required = ("slug", "version", "title", "topic", "scene_title", "tags", "generation_inputs", "generation_outputs")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"{source_name} is missing required field(s): {', '.join(missing)}.")

    slug = str(payload["slug"]).strip().lower()
    try:
        CatalogSeedPublishPayload(slug=slug)
    except Exception as exc:
        raise ValueError(f"{source_name} has invalid slug {slug!r}.") from exc

    tags = _clean_catalog_tags(list(payload.get("tags") or []))
    version = int(payload.get("version") or 1)
    seed_tag = _catalog_seed_tag(slug)
    if seed_tag not in tags:
        tags.append(seed_tag)
    version_tag = _catalog_seed_version_tag(version)
    if version_tag not in tags:
        tags.append(version_tag)

    generation_inputs = payload.get("generation_inputs") or {}
    if not isinstance(generation_inputs, dict):
        raise ValueError(f"{source_name} field generation_inputs must be an object.")
    generation_inputs = {
        **generation_inputs,
        "seed": {
            "source": "catalog_seed",
            "slug": slug,
            "version": version,
        },
    }

    return {
        "slug": slug,
        "version": version,
        "title": str(payload["title"]).strip()[:160],
        "topic": str(payload["topic"]).strip()[:20000],
        "source_name": str(payload.get("source_name") or "Mnemorized seed catalog").strip()[:240],
        "scene_title": str(payload.get("scene_title") or "").strip()[:240],
        "tags": tags,
        "generation_inputs": generation_inputs,
        "generation_outputs": payload.get("generation_outputs") or {},
        "summary": str(payload.get("summary") or "").strip()[:240],
    }


def _load_catalog_seed_payloads() -> tuple[list[dict[str, Any]], list[str]]:
    if not CATALOG_SEED_DIR.exists():
        return [], [f"Catalog seed directory not found: {CATALOG_SEED_DIR}"]

    seeds: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_slugs: set[str] = set()
    for path in sorted(CATALOG_SEED_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            seed = _validate_catalog_seed_payload(payload, path.name)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue

        if seed["slug"] in seen_slugs:
            errors.append(f"Duplicate catalog seed slug: {seed['slug']}.")
            continue
        seen_slugs.add(seed["slug"])
        seeds.append(seed)
    return seeds, errors


def _catalog_seed_public_view(seed: dict[str, Any], published_entry: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "slug": seed["slug"],
        "version": seed["version"],
        "title": seed["title"],
        "topic_preview": _truncate_text(seed["topic"], 160),
        "scene_title": seed.get("scene_title"),
        "tags": [
            tag for tag in seed.get("tags", [])
            if not tag.startswith(CATALOG_SEED_TAG_PREFIX) and not tag.startswith("seed-version:")
        ],
        "summary": seed.get("summary") or "",
        "published": bool(published_entry),
        "catalog_id": published_entry.get("id") if published_entry else None,
        "published_at": published_entry.get("published_at") if published_entry else None,
        "published_version": (
            (published_entry.get("generation_inputs") or {}).get("seed", {}).get("version")
            if published_entry else None
        ),
    }


async def _find_catalog_entry_by_seed_slug(
    *,
    request: Request,
    settings: Settings,
    slug: str,
) -> dict[str, Any] | None:
    response = await _supabase_rest_request(
        request=request,
        settings=settings,
        bearer_token=None,
        method="GET",
        path="/rest/v1/catalog_palaces",
        params={
            "select": ADMIN_CATALOG_SEED_SELECT,
            "tags": f"cs.{{{_catalog_seed_tag(slug)}}}",
            "limit": "1",
        },
        use_service_role=True,
    )
    rows = _parse_supabase_rows(response, "find catalog seed entry")
    return rows[0] if rows else None


def _validate_palace_id(palace_id: str) -> str:
    try:
        return str(UUID(palace_id))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid palace ID format.") from exc


async def _require_persistence_context(
    request: Request,
    settings: Settings,
) -> tuple[str, AuthenticatedUser]:
    bearer_token = _extract_bearer_token(request)
    if not bearer_token:
        raise HTTPException(status_code=401, detail="Sign in to access saved palaces.")
    if not settings.supabase_auth_configured:
        raise HTTPException(
            status_code=503,
            detail="Supabase persistence is not configured on the backend.",
        )

    user = await _resolve_authenticated_user(request, settings)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to access saved palaces.")

    return bearer_token, user


def _parse_supabase_rows(response: httpx.Response, label: str) -> list[dict[str, Any]]:
    if response.status_code >= 400:
        logger.error("Supabase error during %s: HTTP %s — %s", label, response.status_code, response.text[:500])
        raise HTTPException(
            status_code=502,
            detail=f"Could not {label} — the database returned an error. Please try again.",
        )
    try:
        rows = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Supabase returned non-JSON while trying to {label}.",
        ) from exc
    if not isinstance(rows, list):
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected Supabase payload while trying to {label}.",
        )
    return rows


def _single_row(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not rows:
        raise HTTPException(status_code=404, detail=f"Saved palace not found while trying to {label}.")
    row = rows[0]
    if not isinstance(row, dict):
        raise HTTPException(status_code=502, detail=f"Unexpected row payload while trying to {label}.")
    return row


def _serialize_vector(values: list[float]) -> str:
    return json.dumps([round(float(value), 8) for value in values], separators=(",", ":"))


def _capped_excerpt(text: str, max_chars: int = MEDICAL_EXCERPT_CHARS) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _medical_citation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_key": row.get("source_key"),
        "source_title": row.get("title"),
        "page_start": row.get("page_start"),
        "page_end": row.get("page_end"),
        "section_title": row.get("section_title"),
        "similarity": row.get("similarity"),
        "keyword_rank": row.get("keyword_rank"),
    }


def _public_medical_context_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **_medical_citation(row),
        "excerpt": _capped_excerpt(str(row.get("chunk_text") or "")),
    }


def _flatten_generation_text(value: Any, *, max_chars: int = 20000) -> str:
    parts: list[str] = []

    def visit(current: Any) -> None:
        if sum(len(part) for part in parts) >= max_chars:
            return
        if isinstance(current, str):
            parts.append(current)
            return
        if isinstance(current, dict):
            for child in current.values():
                visit(child)
            return
        if isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return " ".join(" ".join(parts).split())[:max_chars]


async def _create_openai_embedding(
    *,
    request: Request,
    settings: Settings,
    text: str,
) -> tuple[list[float], dict[str, Any]]:
    if not settings.openai_embeddings_configured:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured for medical knowledge embeddings.",
        )

    body: dict[str, Any] = {
        "model": settings.openai_embedding_model,
        "input": text[:20000],
    }
    if settings.openai_embedding_dimensions > 0:
        body["dimensions"] = settings.openai_embedding_dimensions

    http_client, owns_http_client = _get_http_client(request)
    try:
        response = await http_client.post(
            OPENAI_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="OpenAI embeddings timed out.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach OpenAI embeddings: {exc}") from exc
    finally:
        if owns_http_client:
            await http_client.aclose()

    if response.status_code >= 400:
        logger.error("OpenAI embeddings error: HTTP %s — %s", response.status_code, response.text[:500])
        raise HTTPException(
            status_code=502,
            detail="OpenAI embeddings request failed. Please try again.",
        )

    try:
        payload = response.json()
        data = payload.get("data")
        embedding = data[0].get("embedding") if isinstance(data, list) and data else None
        if not isinstance(embedding, list) or not embedding:
            raise ValueError("missing embedding data")
        return [float(value) for value in embedding], payload.get("usage", {})
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail="OpenAI embeddings returned an unexpected payload.") from exc


async def _retrieve_medical_context(
    *,
    request: Request,
    settings: Settings,
    query_text: str,
    max_chunks: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not settings.medical_knowledge_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Medical knowledge is not configured. Set SUPABASE_SERVICE_ROLE_KEY "
                "and OPENAI_API_KEY on the backend."
            ),
        )

    embedding, usage = await _create_openai_embedding(
        request=request,
        settings=settings,
        text=query_text,
    )
    response = await _supabase_rest_request(
        request=request,
        settings=settings,
        bearer_token=None,
        method="POST",
        path="/rest/v1/rpc/match_medical_knowledge_chunks",
        json_body={
            "p_query_embedding": _serialize_vector(embedding),
            "p_query_text": query_text,
            "p_match_count": max(1, min(max_chunks, 12)),
            "p_min_similarity": 0.12,
        },
        use_service_role=True,
    )
    rows = _parse_supabase_rows(response, "retrieve private medical context")
    return rows, usage


async def _reserve_provider_quota_for_user(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str,
    user: AuthenticatedUser,
    request_id: str,
) -> JSONResponse | None:
    rate_limiter = _get_rate_limiter(request, settings)
    allowed, retry_after = rate_limiter.allow(_rate_limit_subject(request, user))
    if not allowed:
        return _rate_limit_response(request_id, retry_after)

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=settings,
        bearer_token=bearer_token,
        user=user,
        use_cache=True,
    )
    quota_allowed, quota_summary = _reserve_quota_if_needed(request, user, summary)
    if not quota_allowed:
        return _quota_exceeded_response(request_id, quota_summary)
    return None


def _profile_display_name(user: AuthenticatedUser) -> str | None:
    metadata = user.claims.get("user_metadata")
    if isinstance(metadata, dict):
        display_name = metadata.get("display_name") or metadata.get("full_name") or metadata.get("name")
        if isinstance(display_name, str) and display_name.strip():
            return display_name.strip()

    if user.email and "@" in user.email:
        return user.email.split("@", 1)[0] or None
    return None


async def _load_palace_row(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str,
    user: AuthenticatedUser,
    palace_id: str,
) -> dict[str, Any]:
    response = await _supabase_rest_request(
        request=request,
        settings=settings,
        bearer_token=bearer_token,
        method="GET",
        path="/rest/v1/palaces",
        params={
            "select": PALACE_SELECT,
            "id": f"eq.{palace_id}",
            "user_id": f"eq.{user.user_id}",
            "limit": "1",
        },
    )
    return _single_row(_parse_supabase_rows(response, "load palace"), "load palace")


async def _delete_empty_palace_best_effort(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str,
    palace_id: str | None,
    user_id: str,
) -> None:
    if not palace_id:
        return
    try:
        response = await _supabase_rest_request(
            request=request,
            settings=settings,
            bearer_token=bearer_token,
            method="DELETE",
            path="/rest/v1/palaces",
            params={"id": f"eq.{palace_id}", "user_id": f"eq.{user_id}"},
            headers={"Prefer": "return=minimal"},
        )
        if response.status_code >= 400:
            logger.warning("Cleanup delete failed for empty palace %s: %s", palace_id, response.text[:300])
    except httpx.HTTPError as exc:
        logger.warning("Cleanup delete errored for empty palace %s: %s", palace_id, exc)


async def _get_subscription_and_usage_summary(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str | None,
    user: AuthenticatedUser | None,
    use_cache: bool = False,
) -> dict[str, Any]:
    if not (settings.supabase_auth_configured and bearer_token and user):
        plan_code = "free"
        return {
            "plan_code": plan_code,
            "plan_display_name": _plan_display_name(plan_code, settings),
            "subscription_status": "inactive",
            "monthly_request_limit": settings.request_limit_for_plan("free"),
            "monthly_requests_used": 0,
            "monthly_requests_remaining": settings.request_limit_for_plan("free"),
            "period_started_at": _iso_month_start(),
            "period_ends_at": _iso_next_month_start(),
            "is_dev_override": False,
            **_billing_context(settings),
        }

    if use_cache:
        cache: UsageSummaryCache | None = getattr(request.app.state, "usage_cache", None)
        if cache is not None:
            cached = cache.get(user.user_id)
            if cached is not None:
                return cached

    override = read_plan_override(settings.plan_override_path, user.user_id)
    subscription_response = await _supabase_rest_request(
        request=request,
        settings=settings,
        bearer_token=bearer_token,
        method="GET",
        path="/rest/v1/subscriptions",
        params={
            "select": "plan_code,status,current_period_end",
            "user_id": f"eq.{user.user_id}",
            "status": "in.(active,trialing)",
            "order": "current_period_end.desc.nullslast",
            "limit": "1",
        },
    )
    if subscription_response.status_code >= 400:
        logger.error("Subscription lookup error: HTTP %s — %s", subscription_response.status_code, subscription_response.text[:500])
        raise HTTPException(
            status_code=502,
            detail="Could not load your subscription state. Please try again.",
        )

    try:
        subscription_rows = subscription_response.json()
        if not isinstance(subscription_rows, list):
            raise ValueError(f"expected list, got {type(subscription_rows).__name__}")
        subscription = subscription_rows[0] if subscription_rows else None
        if subscription is not None and not isinstance(subscription, dict):
            raise ValueError(f"expected object, got {type(subscription).__name__}")
        current_period_end = subscription.get("current_period_end") if subscription else None
        parsed_period_end = _parse_optional_timestamp(current_period_end)
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected subscription payload from Supabase: {exc}",
        ) from exc

    subscription_active = bool(
        subscription
        and subscription.get("status") in {"active", "trialing"}
        and (
            parsed_period_end is None
            or parsed_period_end > datetime.now(UTC)
        )
    )
    plan_code = subscription.get("plan_code") if subscription_active else "free"
    subscription_status = subscription.get("status") if subscription_active else "inactive"
    if override:
        plan_code = override.plan_code
        subscription_status = override.status
    monthly_limit = settings.request_limit_for_plan(plan_code)

    usage_response = await _supabase_rest_request(
        request=request,
        settings=settings,
        bearer_token=bearer_token,
        method="GET",
        path="/rest/v1/usage_events",
        params={
            "select": "id",
            "user_id": f"eq.{user.user_id}",
            "created_at": f"gte.{_iso_month_start()}",
            "limit": "1",
        },
        headers={"Prefer": "count=exact"},
    )
    if usage_response.status_code >= 400:
        logger.error("Usage summary lookup error: HTTP %s — %s", usage_response.status_code, usage_response.text[:500])
        raise HTTPException(
            status_code=502,
            detail="Could not load your usage summary. Please try again.",
        )

    used = _parse_content_range_total(usage_response.headers.get("content-range"))
    remaining = None if monthly_limit is None else max(0, monthly_limit - used)

    result = {
        "plan_code": plan_code or "free",
        "plan_display_name": _plan_display_name(plan_code, settings),
        "subscription_status": subscription_status,
        "monthly_request_limit": monthly_limit,
        "monthly_requests_used": used,
        "monthly_requests_remaining": remaining,
        "period_started_at": _iso_month_start(),
        "period_ends_at": _iso_next_month_start(),
        "is_dev_override": bool(override),
        **_billing_context(settings),
    }

    cache_store: UsageSummaryCache | None = getattr(request.app.state, "usage_cache", None)
    if cache_store is not None and user:
        cache_store.put(user.user_id, result)

    return result


async def _persist_usage_event_to_supabase(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str | None,
    user: AuthenticatedUser | None,
    request_id: str,
    request_body: dict[str, Any],
    response_payload: dict[str, Any] | None,
    status_code: int,
) -> None:
    if not (settings.supabase_auth_configured and bearer_token and user):
        return

    usage = response_payload.get("usage", {}) if response_payload else {}
    payload = {
        "user_id": user.user_id,
        "provider": request_body.get("provider") or "anthropic",
        "model": request_body.get("model"),
        "request_id": request_id,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "status_code": status_code,
    }

    try:
        response = await _supabase_rest_request(
            request=request,
            settings=settings,
            bearer_token=bearer_token,
            method="POST",
            path="/rest/v1/usage_events",
            json_body=payload,
            headers={"Prefer": "return=minimal"},
        )
        if response.status_code >= 400:
            logger.warning(
                "Supabase usage event insert failed for request %s: %s %s",
                request_id,
                response.status_code,
                response.text[:300],
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "Supabase usage event insert errored for request %s: %s",
            request_id,
            exc,
        )


async def _persist_usage_event_background(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str | None,
    user: AuthenticatedUser | None,
    request_id: str,
    request_body: dict[str, Any],
    response_payload: dict[str, Any] | None,
    status_code: int,
) -> None:
    try:
        await _persist_usage_event_to_supabase(
            request=request,
            settings=settings,
            bearer_token=bearer_token,
            user=user,
            request_id=request_id,
            request_body=request_body,
            response_payload=response_payload,
            status_code=status_code,
        )
    except Exception:
        logger.exception("Failed to persist Supabase usage event for request %s", request_id)


def _schedule_usage_event(
    *,
    background_tasks: BackgroundTasks,
    request: Request,
    settings: Settings,
    bearer_token: str | None,
    user: AuthenticatedUser | None,
    request_id: str,
    request_body: dict[str, Any],
    response_payload: dict[str, Any] | None,
    status_code: int,
) -> None:
    try:
        background_tasks.add_task(
            _persist_usage_event_background,
            request=request,
            settings=settings,
            bearer_token=bearer_token,
            user=user,
            request_id=request_id,
            request_body=request_body,
            response_payload=response_payload,
            status_code=status_code,
        )
    except Exception:
        logger.exception("Failed to schedule usage event persistence for request %s", request_id)


def _write_usage_log(
    *,
    settings: Settings,
    request_id: str,
    client_id: str,
    user_id: str | None,
    user_email: str | None,
    duration_ms: float,
    request_body: dict[str, Any],
    response_payload: dict[str, Any] | None,
    status_code: int,
) -> None:
    _ensure_log_path(settings.usage_log_path)
    usage = response_payload.get("usage", {}) if response_payload else {}
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "client_id": client_id,
        "user_id": user_id,
        "user_email": user_email,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "model": request_body.get("model"),
        "max_tokens": request_body.get("max_tokens"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "stop_reason": response_payload.get("stop_reason") if response_payload else None,
    }
    with settings.usage_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.rate_limiter = InMemoryRateLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    if settings.supabase_auth_configured:
        app.state.supabase_verifier = SupabaseTokenVerifier(
            jwks_url=settings.supabase_jwks_url,
            issuer=settings.supabase_issuer,
            audience=settings.supabase_jwt_audience,
        )
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0),
    )
    app.state.usage_cache = UsageSummaryCache(ttl_seconds=60)
    yield
    await app.state.http_client.aclose()


settings = get_settings()
app = FastAPI(
    title="Mnemorized Backend",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "X-Request-ID", "X-Anthropic-Request-ID"],
)


@app.middleware("http")
async def reject_oversized_api_requests(request: Request, call_next):
    active_settings = _get_runtime_settings(request)
    if (
        request.url.path.startswith("/api/")
        and request.method in {"POST", "PUT", "PATCH"}
        and _request_size(request) > active_settings.max_request_bytes
    ):
        return _request_too_large_response(active_settings, str(uuid4()))
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id = str(uuid4())
    issues = []
    for error in exc.errors():
        issues.append({
            "type": error.get("type", "validation_error"),
            "loc": [str(part) for part in error.get("loc", [])],
            "message": error.get("msg", "Invalid request field."),
        })

    return JSONResponse(
        status_code=422,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "type": "validation_error",
                "message": "Request validation failed.",
                "issues": issues,
            }
        },
    )


@app.get("/")
async def landing():
    path = PAGES_DIR / "landing.html"
    if path.exists():
        return FileResponse(path, media_type="text/html")
    return JSONResponse({"service": "mnemorized-backend", "status": "ok"})


@app.get("/forge")
async def forge():
    return FileResponse(PAGES_DIR / "forge.html", media_type="text/html")


@app.get("/library")
async def library():
    return FileResponse(PAGES_DIR / "library.html", media_type="text/html")


@app.get("/admin")
async def admin_dashboard():
    return FileResponse(PAGES_DIR / "admin.html", media_type="text/html")


@app.get("/api/health")
async def health(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    return {
        "status": "ok",
        "service": "mnemorized-backend",
        "anthropic_configured": active_settings.anthropic_configured,
        "gemini_configured": active_settings.gemini_configured,
        "openai_embeddings_configured": active_settings.openai_embeddings_configured,
        "supabase_auth_configured": active_settings.supabase_auth_configured,
        "supabase_admin_configured": active_settings.supabase_admin_configured,
        "medical_knowledge_configured": active_settings.medical_knowledge_configured,
        "billing_mode": active_settings.billing_mode,
        "upgrade_path_enabled": active_settings.billing_upgrade_path_enabled,
        "demo_auth_bypass_enabled": active_settings.dev_mode and active_settings.demo_auth_bypass,
        "provider_auth_required": active_settings.provider_auth_required,
        "provider_auth_ready": (
            not active_settings.provider_auth_required
            or active_settings.supabase_auth_configured
        ),
        "rate_limit": {
            "requests": active_settings.rate_limit_requests,
            "window_seconds": active_settings.rate_limit_window_seconds,
        },
        "next_foundations": {
            "auth": "supabase-ready" if active_settings.supabase_auth_configured else "planned",
            "persistence": "supabase-ready" if active_settings.supabase_auth_configured else "planned",
            "billing": active_settings.billing_foundation_status,
        },
    }


@app.get("/api/diagnose-gemini")
async def diagnose_gemini(request: Request) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    if not active_settings.dev_mode:
        await _require_admin_context(request, active_settings)

    if not active_settings.gemini_api_key:
        return JSONResponse(content={
            "status": "no_key",
            "message": "GEMINI_API_KEY is not set in backend environment.",
        })

    model = active_settings.gemini_text_model
    api_url = f"{GEMINI_API_BASE}/{model}:generateContent"
    test_body = {
        "contents": [{"role": "user", "parts": [{"text": "Say OK"}]}],
        "generationConfig": {"maxOutputTokens": 5},
    }
    key = active_settings.gemini_api_key
    results: dict[str, Any] = {
        "text_model": model,
        "image_model": active_settings.gemini_image_model,
        "key_prefix": key[:8] + "...",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        # Method 1: ?key= query parameter (classic API keys starting with AIza)
        try:
            resp1 = await client.post(api_url, params={"key": key}, json=test_body)
            body1 = resp1.json() if resp1.headers.get("content-type", "").startswith("application/json") else {"raw": resp1.text[:300]}
            results["query_param"] = {"status": resp1.status_code, "response": body1}
        except httpx.HTTPError as exc:
            results["query_param"] = {"status": "unreachable", "error": str(exc)}

        # Method 2: Authorization: Bearer header (newer keys)
        try:
            resp2 = await client.post(
                api_url,
                headers={"Authorization": f"Bearer {key}"},
                json=test_body,
            )
            body2 = resp2.json() if resp2.headers.get("content-type", "").startswith("application/json") else {"raw": resp2.text[:300]}
            results["bearer_header"] = {"status": resp2.status_code, "response": body2}
        except httpx.HTTPError as exc:
            results["bearer_header"] = {"status": "unreachable", "error": str(exc)}

        # Method 3: x-goog-api-key header
        try:
            resp3 = await client.post(
                api_url,
                headers={"x-goog-api-key": key},
                json=test_body,
            )
            body3 = resp3.json() if resp3.headers.get("content-type", "").startswith("application/json") else {"raw": resp3.text[:300]}
            results["x_goog_api_key"] = {"status": resp3.status_code, "response": body3}
        except httpx.HTTPError as exc:
            results["x_goog_api_key"] = {"status": "unreachable", "error": str(exc)}

    working = []
    for method in ("query_param", "bearer_header", "x_goog_api_key"):
        if results.get(method, {}).get("status") == 200:
            working.append(method)

    if working:
        results["status"] = "ok"
        results["working_methods"] = working
        results["message"] = f"Gemini key works via: {', '.join(working)}"
        return JSONResponse(content=results)

    results["status"] = "all_failed"
    results["message"] = "Key failed with all three auth methods. See responses for details."
    return JSONResponse(status_code=401, content=results)


@app.get("/api/config/public")
async def public_config(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    return {
        "auth_enabled": active_settings.supabase_auth_configured,
        "supabase_url": active_settings.supabase_url or None,
        "supabase_anon_key": active_settings.supabase_anon_key or None,
        "app_base_url": active_settings.app_base_url,
        "dev_mode": active_settings.dev_mode,
        "demo_auth_bypass_enabled": active_settings.dev_mode and active_settings.demo_auth_bypass,
        "medical_knowledge_enabled": active_settings.medical_knowledge_configured,
        **_billing_context(active_settings),
    }


@app.get("/api/admin/diagnostics")
async def admin_diagnostics(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    _bearer_token, user = await _require_admin_context(request, active_settings)

    if not active_settings.supabase_admin_configured:
        raise HTTPException(
            status_code=503,
            detail="SUPABASE_SERVICE_ROLE_KEY is required for admin diagnostics.",
        )

    errors: dict[str, str] = {}
    usage_rows, usage_error = await _admin_supabase_rows(
        request=request,
        settings=active_settings,
        path="/rest/v1/usage_events",
        params={
            "select": ADMIN_USAGE_SELECT,
            "order": "created_at.desc",
            "limit": "50",
        },
        label="load admin usage events",
    )
    if usage_error:
        errors["usage_events"] = usage_error

    palace_rows, palace_error = await _admin_supabase_rows(
        request=request,
        settings=active_settings,
        path="/rest/v1/palaces",
        params={
            "select": ADMIN_PALACE_SELECT,
            "order": "updated_at.desc",
            "limit": "25",
        },
        label="load recent palaces",
    )
    if palace_error:
        errors["palaces"] = palace_error

    catalog_rows, catalog_error = await _admin_supabase_rows(
        request=request,
        settings=active_settings,
        path="/rest/v1/catalog_palaces",
        params={
            "select": ADMIN_CATALOG_SELECT,
            "order": "published_at.desc",
            "limit": "25",
        },
        label="load catalog publish history",
    )
    if catalog_error:
        errors["catalog"] = catalog_error

    local_usage, local_error = _read_recent_usage_log(active_settings, limit=75)
    if local_error:
        errors["local_usage_log"] = local_error

    local_failures = [
        row for row in local_usage
        if (status := _safe_status_code(row.get("status_code"))) is not None and status >= 400
    ]
    supabase_failures = _usage_failure_rows(usage_rows)
    recent_failures = sorted(
        [*local_failures[:20], *supabase_failures[:20]],
        key=lambda row: str(row.get("timestamp") or row.get("created_at") or ""),
        reverse=True,
    )[:20]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "admin": {
            "email": user.email,
            "user_id": user.user_id,
        },
        "config": {
            "environment": active_settings.app_env,
            "anthropic_configured": active_settings.anthropic_configured,
            "gemini_configured": active_settings.gemini_configured,
            "openai_embeddings_configured": active_settings.openai_embeddings_configured,
            "supabase_auth_configured": active_settings.supabase_auth_configured,
            "supabase_admin_configured": active_settings.supabase_admin_configured,
            "medical_knowledge_configured": active_settings.medical_knowledge_configured,
            "provider_auth_required": active_settings.provider_auth_required,
            "rate_limit": {
                "requests": active_settings.rate_limit_requests,
                "window_seconds": active_settings.rate_limit_window_seconds,
            },
        },
        "summary": {
            "recent_usage_events": len(usage_rows),
            "recent_usage_failures": len(supabase_failures),
            "recent_local_provider_failures": len(local_failures),
            "recent_palaces": len(palace_rows),
            "recent_catalog_entries": len(catalog_rows),
            "sections_with_errors": sorted(errors.keys()),
        },
        "recent_usage_events": [_sanitize_usage_record(row) for row in usage_rows],
        "recent_provider_failures": [_sanitize_usage_record(row) for row in recent_failures],
        "recent_palaces": [_sanitize_palace_row(row) for row in palace_rows],
        "catalog_publish_history": [_sanitize_catalog_row(row) for row in catalog_rows],
        "errors": errors,
    }


@app.get("/api/admin/catalog-seeds")
async def list_catalog_seeds(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    _bearer_token, _user = await _require_admin_context(request, active_settings)

    if not active_settings.supabase_admin_configured:
        raise HTTPException(
            status_code=503,
            detail="SUPABASE_SERVICE_ROLE_KEY is required for catalog seed publishing.",
        )

    seeds, errors = _load_catalog_seed_payloads()
    seed_views: list[dict[str, Any]] = []
    for seed in seeds:
        published_entry = await _find_catalog_entry_by_seed_slug(
            request=request,
            settings=active_settings,
            slug=seed["slug"],
        )
        seed_views.append(_catalog_seed_public_view(seed, published_entry))

    return {
        "seeds": seed_views,
        "errors": errors,
    }


@app.post("/api/admin/catalog-seeds/publish")
async def publish_catalog_seed(
    payload: CatalogSeedPublishPayload,
    request: Request,
) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    _bearer_token, user = await _require_admin_context(request, active_settings)

    if not active_settings.supabase_admin_configured:
        raise HTTPException(
            status_code=503,
            detail="SUPABASE_SERVICE_ROLE_KEY is required for catalog seed publishing.",
        )

    seeds, errors = _load_catalog_seed_payloads()
    seed = next((item for item in seeds if item["slug"] == payload.slug), None)
    if seed is None:
        detail = f"Catalog seed not found: {payload.slug}."
        if errors:
            detail += " Seed load errors: " + "; ".join(errors[:3])
        raise HTTPException(status_code=404, detail=detail)

    existing = await _find_catalog_entry_by_seed_slug(
        request=request,
        settings=active_settings,
        slug=seed["slug"],
    )
    if existing:
        existing_seed = (existing.get("generation_inputs") or {}).get("seed", {})
        if existing_seed.get("version") != seed["version"]:
            update_response = await _supabase_rest_request(
                request=request,
                settings=active_settings,
                bearer_token=None,
                method="PATCH",
                path="/rest/v1/catalog_palaces",
                params={"id": f"eq.{existing['id']}"},
                json_body={
                    "title": seed["title"],
                    "topic": seed["topic"],
                    "source_name": seed["source_name"],
                    "scene_title": seed["scene_title"],
                    "tags": seed["tags"],
                    "generation_inputs": seed["generation_inputs"],
                    "generation_outputs": seed["generation_outputs"],
                    "published_by": user.user_id,
                },
                headers={"Prefer": "return=representation"},
                use_service_role=True,
            )
            row = _single_row(
                _parse_supabase_rows(update_response, "update catalog seed"),
                "update catalog seed",
            )
            return {
                "published": True,
                "updated": True,
                "entry": row,
                "seed": _catalog_seed_public_view(seed, row),
                "message": f"Updated catalog seed '{seed['slug']}' to version {seed['version']}.",
            }
        return {
            "published": False,
            "updated": False,
            "entry": existing,
            "seed": _catalog_seed_public_view(seed, existing),
            "message": f"Catalog seed '{seed['slug']}' is already published.",
        }

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=None,
        method="POST",
        path="/rest/v1/catalog_palaces",
        json_body={
            "title": seed["title"],
            "topic": seed["topic"],
            "source_name": seed["source_name"],
            "scene_title": seed["scene_title"],
            "tags": seed["tags"],
            "generation_inputs": seed["generation_inputs"],
            "generation_outputs": seed["generation_outputs"],
            "published_by": user.user_id,
        },
        headers={"Prefer": "return=representation"},
        use_service_role=True,
    )
    row = _single_row(_parse_supabase_rows(response, "publish catalog seed"), "publish catalog seed")
    return {
        "published": True,
        "updated": False,
        "entry": row,
        "seed": _catalog_seed_public_view(seed, row),
        "message": f"Published catalog seed '{seed['slug']}'.",
    }


@app.get("/api/medical-knowledge/coverage")
async def medical_knowledge_coverage(request: Request) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    if not active_settings.supabase_admin_configured:
        return JSONResponse(
            status_code=503,
            content={"error": {"message": "Medical knowledge is not configured."}},
        )

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=None,
        method="GET",
        path="/rest/v1/medical_sources",
        params={"select": "source_key,title,metadata"},
        headers={"Accept-Profile": "medical"},
        use_service_role=True,
    )
    rows = _parse_supabase_rows(response, "retrieve medical knowledge coverage")
    sources = []
    for row in rows:
        meta = row.get("metadata") or {}
        sources.append({
            "source_key": row.get("source_key"),
            "title": row.get("title"),
            "tags": meta.get("tags", []),
        })
    return JSONResponse(content={"sources": sources, "source_count": len(sources)})


@app.post("/api/medical-knowledge/context")
async def medical_knowledge_context(
    payload: MedicalContextPayload,
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())

    if _request_size(request) > active_settings.max_request_bytes:
        return _request_too_large_response(active_settings, request_id)

    bearer_token, user = await _require_persistence_context(request, active_settings)
    quota_response = await _reserve_provider_quota_for_user(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        request_id=request_id,
    )
    if quota_response is not None:
        return quota_response

    try:
        rows, usage = await _retrieve_medical_context(
            request=request,
            settings=active_settings,
            query_text=payload.topic,
            max_chunks=payload.max_chunks,
        )
    except HTTPException:
        _release_quota_reservation(request, user)
        raise

    _schedule_usage_event(
        background_tasks=background_tasks,
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        request_id=request_id,
        request_body={"provider": "openai", "model": active_settings.openai_embedding_model},
        response_payload={
            "usage": {
                "input_tokens": usage.get("prompt_tokens") or usage.get("total_tokens"),
                "output_tokens": 0,
            }
        },
        status_code=200,
    )
    return JSONResponse(
        headers={"X-Request-ID": request_id},
        content={
            "count": len(rows),
            "context": [_public_medical_context_row(row) for row in rows],
            "copyright_boundary": (
                "Private source material is retained server-side; browser responses include only "
                "short excerpts and citation metadata."
            ),
        },
        background=background_tasks,
    )


@app.post("/api/medical-knowledge/quality-check")
async def medical_knowledge_quality_check(
    payload: MedicalQualityGatePayload,
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())

    if _request_size(request) > active_settings.max_request_bytes:
        return _request_too_large_response(active_settings, request_id)

    bearer_token, user = await _require_persistence_context(request, active_settings)
    quota_response = await _reserve_provider_quota_for_user(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        request_id=request_id,
    )
    if quota_response is not None:
        return quota_response

    query_text = payload.topic
    required_concepts = [concept.strip() for concept in payload.required_concepts if concept.strip()]
    if required_concepts:
        query_text = f"{payload.topic}\n\nRequired concepts:\n" + "\n".join(required_concepts)

    try:
        rows, usage = await _retrieve_medical_context(
            request=request,
            settings=active_settings,
            query_text=query_text,
            max_chunks=payload.max_evidence_chunks,
        )
    except HTTPException:
        _release_quota_reservation(request, user)
        raise

    # Only show citations genuinely relevant to the queried topic. A lower cutoff
    # allowed unrelated high-level emergency terms to surface wrong source families.
    QUALITY_GATE_MIN_SIMILARITY = 0.58
    rows = [r for r in rows if (r.get("similarity") or 0) >= QUALITY_GATE_MIN_SIMILARITY]
    evidence_status = "matched" if rows else "no_relevant_source"

    output_text = _flatten_generation_text(payload.generation_outputs).lower()
    coverage = []
    for concept in required_concepts:
        needle = concept.lower()
        evidence_refs = [
            _medical_citation(row)
            for row in rows
            if needle and needle in str(row.get("chunk_text") or "").lower()
        ][:3]
        coverage.append(
            {
                "concept": concept,
                "present_in_generation": bool(needle and needle in output_text),
                "evidence_refs": evidence_refs,
            }
        )

    missing_or_weak = [
        item["concept"]
        for item in coverage
        if not item["present_in_generation"]
    ]
    verdict = "needs_repair" if missing_or_weak else "ready_for_review"

    _schedule_usage_event(
        background_tasks=background_tasks,
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        request_id=request_id,
        request_body={"provider": "openai", "model": active_settings.openai_embedding_model},
        response_payload={
            "usage": {
                "input_tokens": usage.get("prompt_tokens") or usage.get("total_tokens"),
                "output_tokens": 0,
            }
        },
        status_code=200,
    )
    return JSONResponse(
        headers={"X-Request-ID": request_id},
        content={
            "verdict": verdict,
            "evidence_status": evidence_status,
            "min_evidence_similarity": QUALITY_GATE_MIN_SIMILARITY,
            "evidence_count": len(rows),
            "evidence": [_medical_citation(row) for row in rows],
            "required_concept_coverage": coverage,
            "repair_focus": missing_or_weak,
            "limits": (
                "This deterministic gate checks retrieval coverage and required-concept presence. "
                "It is not a standalone clinical correctness guarantee."
            ),
        },
        background=background_tasks,
    )


@app.get("/api/account/summary")
async def account_summary(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    user = await _resolve_authenticated_user(request, active_settings)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view account summary.")

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=active_settings,
        bearer_token=_extract_bearer_token(request),
        user=user,
    )
    return {
        "user_id": user.user_id,
        "email": user.email,
        "dev_mode": active_settings.dev_mode,
        **summary,
    }


@app.post("/api/profile/ensure")
async def ensure_profile(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="POST",
        path="/rest/v1/profiles",
        params={"on_conflict": "id"},
        json_body={
            "id": user.user_id,
            "email": user.email,
            "display_name": _profile_display_name(user),
        },
        headers={"Prefer": "resolution=merge-duplicates,return=representation"},
    )
    row = _single_row(_parse_supabase_rows(response, "sync profile"), "sync profile")
    return {"profile": row}


@app.get("/api/palaces")
async def list_palaces(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="GET",
        path="/rest/v1/palaces",
        params={
            "select": PALACE_SELECT,
            "user_id": f"eq.{user.user_id}",
            "order": "updated_at.desc",
        },
    )
    rows = _parse_supabase_rows(response, "load saved palaces")
    return {"palaces": rows}


@app.get("/api/palaces/{palace_id}")
async def get_palace(palace_id: str, request: Request) -> dict[str, Any]:
    palace_id = _validate_palace_id(palace_id)
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    palace = await _load_palace_row(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        palace_id=palace_id,
    )
    version_response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="GET",
        path="/rest/v1/palace_versions",
        params={
            "select": PALACE_VERSION_SELECT,
            "palace_id": f"eq.{palace_id}",
            "order": "version_number.desc",
            "limit": "1",
        },
    )
    version = _single_row(_parse_supabase_rows(version_response, "load palace version"), "load palace version")
    return {"palace": palace, "version": version}


@app.post("/api/palaces/save")
async def save_palace(payload: PalaceSavePayload, request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    snapshot = payload.snapshot
    palace_id = payload.palace_id
    created_palace_id: str | None = None

    try:
        if palace_id:
            palace_row = await _load_palace_row(
                request=request,
                settings=active_settings,
                bearer_token=bearer_token,
                user=user,
                palace_id=palace_id,
            )
            next_version = int(palace_row.get("latest_version_number") or 0) + 1
        else:
            insert_response = await _supabase_rest_request(
                request=request,
                settings=active_settings,
                bearer_token=bearer_token,
                method="POST",
                path="/rest/v1/palaces",
                json_body={
                    "user_id": user.user_id,
                    "title": snapshot.title,
                    "topic": snapshot.topic,
                    "source_name": snapshot.source_name,
                    "scene_title": snapshot.scene_title,
                    "status": snapshot.status,
                    "latest_version_number": 1,
                },
                headers={"Prefer": "return=representation"},
            )
            palace_row = _single_row(_parse_supabase_rows(insert_response, "create palace"), "create palace")
            palace_id = palace_row.get("id")
            created_palace_id = palace_id
            next_version = 1

        version_response = await _supabase_rest_request(
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            method="POST",
            path="/rest/v1/palace_versions",
            json_body={
                "palace_id": palace_id,
                "version_number": next_version,
                "generation_inputs": snapshot.generation_inputs,
                "generation_outputs": snapshot.generation_outputs,
            },
            headers={"Prefer": "return=minimal"},
        )
        if version_response.status_code >= 400:
            logger.error("Palace version save error: HTTP %s — %s", version_response.status_code, version_response.text[:500])
            raise HTTPException(
                status_code=502,
                detail="Could not save palace version. Please try again.",
            )

        update_response = await _supabase_rest_request(
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            method="PATCH",
            path="/rest/v1/palaces",
            params={"id": f"eq.{palace_id}", "user_id": f"eq.{user.user_id}"},
            json_body={
                "title": snapshot.title,
                "topic": snapshot.topic,
                "source_name": snapshot.source_name,
                "scene_title": snapshot.scene_title,
                "status": snapshot.status,
                "latest_version_number": next_version,
            },
            headers={"Prefer": "return=representation"},
        )
        palace_row = _single_row(_parse_supabase_rows(update_response, "update palace metadata"), "update palace metadata")
    except HTTPException:
        if created_palace_id:
            await _delete_empty_palace_best_effort(
                request=request,
                settings=active_settings,
                bearer_token=bearer_token,
                palace_id=created_palace_id,
                user_id=user.user_id,
            )
        raise

    return {
        "palace": palace_row,
        "version_number": next_version,
    }


@app.patch("/api/palaces/{palace_id}")
async def rename_palace(
    palace_id: str,
    payload: PalaceRenamePayload,
    request: Request,
) -> dict[str, Any]:
    palace_id = _validate_palace_id(palace_id)
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="PATCH",
        path="/rest/v1/palaces",
        params={"id": f"eq.{palace_id}", "user_id": f"eq.{user.user_id}"},
        json_body={"title": payload.title},
        headers={"Prefer": "return=representation"},
    )
    row = _single_row(_parse_supabase_rows(response, "rename palace"), "rename palace")
    return {"palace": row}


@app.delete("/api/palaces/{palace_id}")
async def delete_palace(palace_id: str, request: Request) -> dict[str, Any]:
    palace_id = _validate_palace_id(palace_id)
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    await _load_palace_row(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        palace_id=palace_id,
    )
    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="DELETE",
        path="/rest/v1/palaces",
        params={"id": f"eq.{palace_id}", "user_id": f"eq.{user.user_id}"},
        headers={"Prefer": "return=minimal"},
    )
    if response.status_code >= 400:
        logger.error("Palace delete error: HTTP %s — %s", response.status_code, response.text[:500])
        raise HTTPException(
            status_code=502,
            detail="Could not delete palace. Please try again.",
        )
    return {"deleted": True, "palace_id": palace_id}


# ── Shared palace catalog ────────────────────────────────────────


@app.get("/api/catalog")
async def list_catalog(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    if not active_settings.supabase_auth_configured:
        return {"catalog": []}

    params: dict[str, str] = {
        "select": CATALOG_SELECT,
        "order": "published_at.desc",
    }

    tag = request.query_params.get("tag")
    if tag:
        clean_tag = tag[:100].strip().lower()
        for ch in ("(", ")", ",", ".", "*", "{", "}"):
            clean_tag = clean_tag.replace(ch, "")
        clean_tag = clean_tag.strip()
        if clean_tag:
            params["tags"] = f"cs.{{{clean_tag}}}"

    q = request.query_params.get("q")
    if q:
        safe_q = q[:200].replace("%", "").strip()
        for ch in ("(", ")", ",", ".", "*", "{", "}"):
            safe_q = safe_q.replace(ch, "")
        safe_q = safe_q.strip()
        if safe_q:
            params["or"] = f"(title.ilike.%{safe_q}%,topic.ilike.%{safe_q}%)"

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=None,
        method="GET",
        path="/rest/v1/catalog_palaces",
        params=params,
    )
    rows = _parse_supabase_rows(response, "load catalog")
    return {"catalog": rows}


@app.get("/api/catalog/{catalog_id}")
async def get_catalog_entry(catalog_id: str, request: Request) -> dict[str, Any]:
    catalog_id = _validate_palace_id(catalog_id)
    active_settings = _get_runtime_settings(request)
    if not active_settings.supabase_auth_configured:
        raise HTTPException(status_code=404, detail="Catalog is not available.")

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=None,
        method="GET",
        path="/rest/v1/catalog_palaces",
        params={
            "select": CATALOG_SELECT,
            "id": f"eq.{catalog_id}",
            "limit": "1",
        },
    )
    row = _single_row(
        _parse_supabase_rows(response, "load catalog entry"),
        "load catalog entry",
    )
    return {"entry": row}


@app.post("/api/catalog/{catalog_id}/clone")
async def clone_catalog_entry(catalog_id: str, request: Request) -> dict[str, Any]:
    catalog_id = _validate_palace_id(catalog_id)
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    catalog_response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=None,
        method="GET",
        path="/rest/v1/catalog_palaces",
        params={
            "select": CATALOG_SELECT,
            "id": f"eq.{catalog_id}",
            "limit": "1",
        },
    )
    entry = _single_row(
        _parse_supabase_rows(catalog_response, "load catalog entry for clone"),
        "load catalog entry for clone",
    )

    insert_response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="POST",
        path="/rest/v1/palaces",
        json_body={
            "user_id": user.user_id,
            "title": entry.get("title") or "Catalog palace",
            "topic": entry.get("topic") or "",
            "source_name": entry.get("source_name") or "Mnemorized catalog",
            "scene_title": entry.get("scene_title"),
            "status": "generated",
            "latest_version_number": 1,
        },
        headers={"Prefer": "return=representation"},
    )
    palace_row = _single_row(_parse_supabase_rows(insert_response, "clone catalog palace"), "clone catalog palace")
    palace_id = palace_row.get("id")

    generation_inputs = dict(entry.get("generation_inputs") or {})
    generation_inputs["catalog_clone"] = {
        "catalog_id": catalog_id,
        "published_at": entry.get("published_at"),
        "tags": entry.get("tags") or [],
    }

    try:
        version_response = await _supabase_rest_request(
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            method="POST",
            path="/rest/v1/palace_versions",
            json_body={
                "palace_id": palace_id,
                "version_number": 1,
                "generation_inputs": generation_inputs,
                "generation_outputs": entry.get("generation_outputs") or {},
            },
            headers={"Prefer": "return=minimal"},
        )
        if version_response.status_code >= 400:
            logger.error("Catalog clone version error: HTTP %s — %s", version_response.status_code, version_response.text[:500])
            raise HTTPException(
                status_code=502,
                detail="Could not clone catalog version. Please try again.",
            )
    except HTTPException:
        await _delete_empty_palace_best_effort(
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            palace_id=palace_id,
            user_id=user.user_id,
        )
        raise

    return {
        "palace": palace_row,
        "version_number": 1,
        "catalog_id": catalog_id,
    }


@app.post("/api/catalog/publish")
async def publish_to_catalog(
    payload: CatalogPublishPayload,
    request: Request,
) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    if not _is_admin(user, active_settings):
        raise HTTPException(
            status_code=403,
            detail="Only admins can publish to the catalog.",
        )
    if not active_settings.supabase_admin_configured:
        raise HTTPException(
            status_code=503,
            detail="Catalog publishing requires SUPABASE_SERVICE_ROLE_KEY on the backend.",
        )

    clean_tags = list(dict.fromkeys(
        t.strip().lower() for t in payload.tags if t.strip()
    ))

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=None,
        method="POST",
        path="/rest/v1/catalog_palaces",
        json_body={
            "title": payload.title,
            "topic": payload.topic,
            "source_name": payload.source_name,
            "scene_title": payload.scene_title,
            "tags": clean_tags,
            "generation_inputs": payload.generation_inputs,
            "generation_outputs": payload.generation_outputs,
            "published_by": user.user_id,
        },
        headers={"Prefer": "return=representation"},
        use_service_role=True,
    )
    row = _single_row(
        _parse_supabase_rows(response, "publish to catalog"),
        "publish to catalog",
    )
    return {"entry": row}


@app.delete("/api/catalog/{catalog_id}")
async def unpublish_from_catalog(
    catalog_id: str,
    request: Request,
) -> dict[str, Any]:
    catalog_id = _validate_palace_id(catalog_id)
    active_settings = _get_runtime_settings(request)
    bearer_token, user = await _require_persistence_context(request, active_settings)

    if not _is_admin(user, active_settings):
        raise HTTPException(
            status_code=403,
            detail="Only admins can unpublish from the catalog.",
        )
    if not active_settings.supabase_admin_configured:
        raise HTTPException(
            status_code=503,
            detail="Catalog unpublishing requires SUPABASE_SERVICE_ROLE_KEY on the backend.",
        )

    response = await _supabase_rest_request(
        request=request,
        settings=active_settings,
        bearer_token=None,
        method="DELETE",
        path="/rest/v1/catalog_palaces",
        params={"id": f"eq.{catalog_id}"},
        headers={"Prefer": "return=minimal"},
        use_service_role=True,
    )
    if response.status_code >= 400:
        logger.error("Catalog unpublish error: HTTP %s — %s", response.status_code, response.text[:500])
        raise HTTPException(
            status_code=502,
            detail="Could not unpublish catalog entry. Please try again.",
        )
    return {"deleted": True, "catalog_id": catalog_id}


@app.post("/api/dev/plan-override")
async def set_dev_plan_override(
    payload: DevPlanOverridePayload,
    request: Request,
) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    if not active_settings.dev_mode:
        raise HTTPException(status_code=403, detail="Dev plan overrides are disabled in production.")

    user = await _resolve_authenticated_user(request, active_settings)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to modify your dev plan override.")

    if payload.clear:
        clear_plan_override(active_settings.plan_override_path, user.user_id)
    else:
        write_plan_override(
            active_settings.plan_override_path,
            user.user_id,
            payload.plan_code,
            "active",
        )

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=active_settings,
        bearer_token=_extract_bearer_token(request),
        user=user,
    )
    return {
        "message": "Dev plan override updated.",
        "user_id": user.user_id,
        **summary,
    }


@app.post("/api/anthropic/messages")
async def proxy_anthropic_messages(
    payload: MessagePayload,
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())

    if not active_settings.anthropic_configured:
        return JSONResponse(
            status_code=503,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "configuration_error",
                    "message": "ANTHROPIC_API_KEY is not configured on the backend.",
                }
            },
        )

    if _request_size(request) > active_settings.max_request_bytes:
        return _request_too_large_response(active_settings, request_id)

    if payload.max_tokens > active_settings.anthropic_max_tokens:
        return JSONResponse(
            status_code=400,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "max_tokens_exceeded",
                    "message": (
                        f"max_tokens exceeds ANTHROPIC_MAX_TOKENS="
                        f"{active_settings.anthropic_max_tokens}."
                    ),
                }
            },
        )

    user: AuthenticatedUser | None = await _resolve_authenticated_user(
        request,
        active_settings,
    )
    bearer_token = _extract_bearer_token(request)

    if active_settings.provider_auth_required:
        if not active_settings.supabase_auth_configured:
            return _auth_not_configured_response(request_id)
        if user is None:
            return _auth_required_response(request_id, "Sign in to use the API proxy.")

    rate_limiter = _get_rate_limiter(request, active_settings)
    allowed, retry_after = rate_limiter.allow(_rate_limit_subject(request, user))
    if not allowed:
        return _rate_limit_response(request_id, retry_after)

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        use_cache=True,
    )
    quota_allowed, quota_summary = _reserve_quota_if_needed(request, user, summary)
    if not quota_allowed:
        return _quota_exceeded_response(request_id, quota_summary)

    # ── Evidence-first generation: inject source material into system prompt ──
    evidence_topic = unquote(request.headers.get("x-evidence-topic", "")).strip()
    if (
        request.headers.get("x-evidence-grounding") == "true"
        and evidence_topic
        and active_settings.medical_knowledge_configured
        and payload.system
    ):
        try:
            rows, _ev_usage = await _retrieve_medical_context(
                request=request,
                settings=active_settings,
                query_text=evidence_topic,
                max_chunks=6,
            )
            EVIDENCE_MIN_SIMILARITY = 0.45
            relevant = [r for r in rows if (r.get("similarity") or 0) >= EVIDENCE_MIN_SIMILARITY]
            if relevant:
                evidence_lines = []
                for i, row in enumerate(relevant, 1):
                    src = row.get("title") or row.get("source_key") or "Medical source"
                    ps = row.get("page_start") or "?"
                    pe = row.get("page_end") or ps
                    page_ref = f"p{ps}" if ps == pe else f"p{ps}-{pe}"
                    section = row.get("section_title") or ""
                    section_label = f" — {section}" if section else ""
                    chunk = str(row.get("chunk_text") or "")[:1500]
                    evidence_lines.append(
                        f"[{i}] {src} ({page_ref}{section_label}):\n{chunk}"
                    )
                evidence_block = (
                    "\n\nSOURCE EVIDENCE — The following excerpts are from the student's "
                    "verified medical reference material. Derive your core concepts "
                    "primarily from these facts. Use the same terminology, thresholds, "
                    "and clinical details that appear in the source. You may supplement "
                    "with critical safety facts from your training knowledge, but the "
                    "source material is the primary authority.\n\n"
                    + "\n\n".join(evidence_lines)
                )
                payload.system = payload.system + evidence_block
                logger.info(
                    "Evidence grounding: injected %d source excerpts for topic '%s' (request %s)",
                    len(relevant), evidence_topic[:60], request_id,
                )
        except Exception as exc:
            logger.warning("Evidence grounding retrieval failed (non-fatal): %s", exc)

    body = payload.model_dump(exclude_none=True)
    body_betas: list[str] = body.pop("betas", None) or []

    replay_mode = get_replay_mode(request.headers) if active_settings.dev_mode else None
    replay_topic, replay_stage = get_replay_meta(request.headers) if replay_mode else (None, None)
    if replay_mode == "replay" and replay_topic and replay_stage:
        cassette = load_cassette(replay_topic, replay_stage)
        if cassette is not None:
            return JSONResponse(
                status_code=200,
                headers={"X-Request-ID": request_id, "X-Replay": "hit"},
                content=cassette,
            )
        return JSONResponse(
            status_code=404,
            headers={"X-Request-ID": request_id, "X-Replay": "miss"},
            content={"error": {"type": "replay_miss", "message": f"No cassette for {replay_topic}/{replay_stage}. Switch to Record mode first."}},
        )

    upstream_headers = {
        "content-type": "application/json",
        "x-api-key": active_settings.anthropic_api_key,
        "anthropic-version": request.headers.get("anthropic-version", "2023-06-01"),
    }
    beta_parts: list[str] = list(body_betas)
    header_beta = request.headers.get("anthropic-beta", "")
    if header_beta:
        beta_parts.extend(b.strip() for b in header_beta.split(",") if b.strip())
    if beta_parts:
        upstream_headers["anthropic-beta"] = ",".join(dict.fromkeys(beta_parts))

    started = time.perf_counter()
    client_id = _client_id(request)
    http_client, owns_http_client = _get_http_client(request)

    try:
        upstream_response = await http_client.post(
            active_settings.anthropic_api_url,
            headers=upstream_headers,
            json=body,
            timeout=httpx.Timeout(active_settings.anthropic_timeout_seconds, connect=10.0),
        )
    except httpx.TimeoutException:
        _release_quota_reservation(request, user)
        return JSONResponse(
            status_code=504,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "upstream_timeout",
                    "message": "Anthropic did not respond before the timeout elapsed.",
                }
            },
        )
    except httpx.HTTPError as exc:
        _release_quota_reservation(request, user)
        return JSONResponse(
            status_code=502,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "upstream_connection_error",
                    "message": f"Could not reach Anthropic: {exc}",
                }
            },
        )
    finally:
        if owns_http_client:
            await http_client.aclose()

    duration_ms = (time.perf_counter() - started) * 1000

    response_payload: dict[str, Any] | None = None
    try:
        response_payload = upstream_response.json()
    except ValueError:
        logger.warning("Anthropic returned non-JSON content for request %s", request_id)

    upstream_ok = 200 <= upstream_response.status_code < 300
    if not upstream_ok:
        _release_quota_reservation(request, user)

    try:
        _write_usage_log(
            settings=active_settings,
            request_id=request_id,
            client_id=client_id,
            user_id=user.user_id if user else None,
            user_email=user.email if user else None,
            duration_ms=duration_ms,
            request_body=body,
            response_payload=response_payload,
            status_code=upstream_response.status_code,
        )
    except Exception:
        logger.exception("Failed to write local usage log for request %s", request_id)

    if upstream_ok:
        _schedule_usage_event(
            background_tasks=background_tasks,
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            user=user,
            request_id=request_id,
            request_body=body,
            response_payload=response_payload,
            status_code=upstream_response.status_code,
        )

    passthrough_headers = {"X-Request-ID": request_id}
    anthropic_request_id = upstream_response.headers.get("request-id")
    if anthropic_request_id:
        passthrough_headers["X-Anthropic-Request-ID"] = anthropic_request_id

    if response_payload is None:
        _release_quota_reservation(request, user)
        return JSONResponse(
            status_code=502,
            headers=passthrough_headers,
            content={
                "error": {
                    "type": "upstream_parse_error",
                    "message": "Anthropic returned a non-JSON response.",
                }
            },
        )

    if replay_mode == "record" and replay_topic and replay_stage and upstream_ok and response_payload:
        save_cassette(replay_topic, replay_stage, response_payload)
        passthrough_headers["X-Replay"] = "recorded"

    return JSONResponse(
        status_code=upstream_response.status_code,
        headers=passthrough_headers,
        content=response_payload,
        background=background_tasks,
    )


@app.post("/api/gemini/prompt-director")
async def gemini_prompt_director(
    payload: GeminiPromptDirectorPayload,
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())

    if not active_settings.gemini_configured:
        return JSONResponse(
            status_code=503,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "configuration_error",
                    "message": "GEMINI_API_KEY is not configured on the backend.",
                }
            },
        )

    if _request_size(request) > active_settings.max_request_bytes:
        return _request_too_large_response(active_settings, request_id)

    user: AuthenticatedUser | None = await _resolve_authenticated_user(
        request,
        active_settings,
    )
    bearer_token = _extract_bearer_token(request)

    if active_settings.provider_auth_required:
        if not active_settings.supabase_auth_configured:
            return _auth_not_configured_response(request_id)
        if user is None:
            return _auth_required_response(request_id, "Sign in to build Gemini image prompts.")

    rate_limiter = _get_rate_limiter(request, active_settings)
    allowed, retry_after = rate_limiter.allow(_rate_limit_subject(request, user))
    if not allowed:
        return _rate_limit_response(request_id, retry_after)

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        use_cache=True,
    )
    quota_allowed, quota_summary = _reserve_quota_if_needed(request, user, summary)
    if not quota_allowed:
        return _quota_exceeded_response(request_id, quota_summary)

    replay_mode = get_replay_mode(request.headers) if active_settings.dev_mode else None
    replay_topic, replay_stage = get_replay_meta(request.headers) if replay_mode else (None, None)
    if replay_mode == "replay" and replay_topic and replay_stage:
        cassette = load_cassette(replay_topic, replay_stage)
        if cassette is not None:
            return JSONResponse(
                status_code=200,
                headers={"X-Request-ID": request_id, "X-Replay": "hit"},
                content=cassette,
            )
        return JSONResponse(
            status_code=404,
            headers={"X-Request-ID": request_id, "X-Replay": "miss"},
            content={"error": {"type": "replay_miss", "message": f"No cassette for {replay_topic}/{replay_stage}. Switch to Record mode first."}},
        )

    model = active_settings.gemini_text_model
    api_url = f"{GEMINI_API_BASE}/{model}:generateContent"
    body = {
        "systemInstruction": {
            "parts": [{"text": _gemini_prompt_director_system_prompt()}],
        },
        "contents": [{
            "role": "user",
            "parts": [{"text": _gemini_prompt_director_user_prompt(payload)}],
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }
    usage_request_body = {
        "provider": "gemini",
        "model": model,
        "task": "prompt_director",
        "anchors": len(payload.anchors),
        "constitution": "docs/gemini-constitution.txt",
    }

    def schedule_director_usage(status_code: int, count_quota: bool = True) -> None:
        if not count_quota:
            _release_quota_reservation(request, user)
        _schedule_usage_event(
            background_tasks=background_tasks,
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            user=user,
            request_id=request_id,
            request_body=usage_request_body,
            response_payload={"usage": {}},
            status_code=status_code,
        )

    http_client, owns_http_client = _get_http_client(request)
    try:
        try:
            resp = await http_client.post(
                api_url,
                params={"key": active_settings.gemini_api_key},
                json=body,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        except httpx.TimeoutException:
            schedule_director_usage(504, count_quota=False)
            return JSONResponse(
                status_code=504,
                headers={"X-Request-ID": request_id},
                content={
                    "error": {
                        "type": "upstream_timeout",
                        "message": "Gemini prompt director did not respond before the timeout elapsed.",
                    }
                },
            )
        except httpx.HTTPError as exc:
            schedule_director_usage(502, count_quota=False)
            return JSONResponse(
                status_code=502,
                headers={"X-Request-ID": request_id},
                content={
                    "error": {
                        "type": "upstream_connection_error",
                        "message": f"Could not reach Gemini prompt director: {exc}",
                    }
                },
            )
    finally:
        if owns_http_client:
            await http_client.aclose()

    if resp.status_code != 200:
        upstream_error_message = None
        try:
            error_payload = resp.json()
            upstream_error_message = error_payload.get("error", {}).get("message")
        except ValueError:
            pass
        logger.warning(
            "Gemini prompt director error for request %s: %s %s",
            request_id, resp.status_code, resp.text[:500],
        )
        schedule_director_usage(resp.status_code, count_quota=False)
        return JSONResponse(
            status_code=502,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "upstream_error",
                    "message": upstream_error_message
                    or f"Gemini prompt director returned HTTP {resp.status_code} using model {model}.",
                }
            },
        )

    try:
        raw_response = resp.json()
        text = _gemini_text_from_response(raw_response)
        director_payload = _validated_prompt_director_payload(_parse_json_object_text(text))
    except (ValueError, json.JSONDecodeError, TypeError, IndexError) as exc:
        logger.warning("Gemini prompt director parse error for request %s: %s", request_id, exc)
        schedule_director_usage(502, count_quota=False)
        return JSONResponse(
            status_code=502,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "upstream_parse_error",
                    "message": "Gemini prompt director returned an invalid prompt contract.",
                }
            },
        )

    response_content: dict[str, Any] = {
        **director_payload,
        "model": model,
        "constitution_source": "docs/gemini-constitution.txt",
    }
    schedule_director_usage(200)

    response_headers: dict[str, str] = {"X-Request-ID": request_id}
    if replay_mode == "record" and replay_topic and replay_stage:
        save_cassette(replay_topic, replay_stage, response_content)
        response_headers["X-Replay"] = "recorded"

    return JSONResponse(
        status_code=200,
        headers=response_headers,
        content=response_content,
        background=background_tasks,
    )


@app.post("/api/generate-image")
async def generate_image(
    payload: ImageGenerationPayload,
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())

    if not active_settings.gemini_configured:
        return JSONResponse(
            status_code=503,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "configuration_error",
                    "message": "GEMINI_API_KEY is not configured on the backend.",
                }
            },
        )

    if _request_size(request) > active_settings.max_request_bytes:
        return _request_too_large_response(active_settings, request_id)

    user: AuthenticatedUser | None = await _resolve_authenticated_user(
        request,
        active_settings,
    )
    bearer_token = _extract_bearer_token(request)

    if active_settings.provider_auth_required:
        if not active_settings.supabase_auth_configured:
            return _auth_not_configured_response(request_id)
        if user is None:
            return _auth_required_response(request_id, "Sign in to generate images.")

    rate_limiter = _get_rate_limiter(request, active_settings)
    allowed, retry_after = rate_limiter.allow(_rate_limit_subject(request, user))
    if not allowed:
        return _rate_limit_response(request_id, retry_after)

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        use_cache=True,
    )
    quota_allowed, quota_summary = _reserve_quota_if_needed(request, user, summary)
    if not quota_allowed:
        return _quota_exceeded_response(request_id, quota_summary)

    replay_mode = get_replay_mode(request.headers) if active_settings.dev_mode else None
    replay_topic, replay_stage = get_replay_meta(request.headers) if replay_mode else (None, None)
    if replay_mode == "replay" and replay_topic and replay_stage:
        cassette = load_cassette(replay_topic, replay_stage)
        if cassette is not None:
            return JSONResponse(
                status_code=200,
                headers={"X-Request-ID": request_id, "X-Replay": "hit"},
                content=cassette,
            )
        return JSONResponse(
            status_code=404,
            headers={"X-Request-ID": request_id, "X-Replay": "miss"},
            content={"error": {"type": "replay_miss", "message": f"No cassette for {replay_topic}/{replay_stage}. Switch to Record mode first."}},
        )

    model = active_settings.gemini_image_model
    api_url = GEMINI_INTERACTIONS_URL
    http_client, owns_http_client = _get_http_client(request)
    images: list[dict[str, Any]] = []
    usage_request_body = {"provider": "gemini", "model": model, "prompts": len(payload.prompts)}

    def schedule_gemini_usage(status_code: int, count_quota: bool = True) -> None:
        if not count_quota:
            _release_quota_reservation(request, user)
        _schedule_usage_event(
            background_tasks=background_tasks,
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            user=user,
            request_id=request_id,
            request_body=usage_request_body,
            response_payload={"usage": {}},
            status_code=status_code,
        )

    GEMINI_RETRYABLE = {429, 500, 503}
    GEMINI_MAX_RETRIES = 2
    prompt_errors: list[dict[str, Any]] = []

    try:
        for idx, prompt_text in enumerate(payload.prompts):
            gemini_body: dict[str, Any] = {
                "model": model,
                "input": prompt_text,
                "response_format": {
                    "type": "image",
                    "mime_type": "image/jpeg",
                    "aspect_ratio": "16:9",
                    "image_size": "2K",
                },
            }

            resp = None
            last_error: str | None = None
            last_error_type: str | None = None

            for attempt in range(1 + GEMINI_MAX_RETRIES):
                try:
                    resp = await http_client.post(
                        api_url,
                        headers={"x-goog-api-key": active_settings.gemini_api_key},
                        json=gemini_body,
                        timeout=httpx.Timeout(120.0, connect=10.0),
                    )
                except httpx.TimeoutException:
                    last_error = f"Gemini did not respond in time for prompt {idx + 1}."
                    last_error_type = "upstream_timeout"
                    if attempt < GEMINI_MAX_RETRIES:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break
                except httpx.HTTPError as exc:
                    last_error = f"Could not reach Gemini: {exc}"
                    last_error_type = "upstream_connection_error"
                    if attempt < GEMINI_MAX_RETRIES:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break

                if resp.status_code in GEMINI_RETRYABLE and attempt < GEMINI_MAX_RETRIES:
                    logger.info(
                        "Gemini %d for request %s prompt %d, retry %d",
                        resp.status_code, request_id, idx + 1, attempt + 1,
                    )
                    await asyncio.sleep(2 ** attempt)
                    resp = None
                    continue
                break

            if resp is None:
                prompt_errors.append({
                    "prompt_index": idx,
                    "type": last_error_type or "upstream_connection_error",
                    "message": last_error or f"Gemini unreachable for prompt {idx + 1} after retries.",
                })
                continue

            if resp.status_code != 200:
                upstream_error_message = None
                error_type = "upstream_error"
                try:
                    error_payload = resp.json()
                    upstream_error_message = error_payload.get("error", {}).get("message")
                    if resp.status_code == 400 and "safety" in (upstream_error_message or "").lower():
                        error_type = "safety_block"
                except ValueError:
                    pass
                logger.warning(
                    "Gemini API error for request %s prompt %d: %s %s",
                    request_id, idx + 1, resp.status_code, resp.text[:500],
                )
                prompt_errors.append({
                    "prompt_index": idx,
                    "type": error_type,
                    "message": upstream_error_message
                    or f"Gemini returned {resp.status_code} for prompt {idx + 1} using model {model}.",
                })
                continue

            try:
                resp_json = resp.json()
            except ValueError:
                logger.warning(
                    "Gemini returned non-JSON content for request %s prompt %d",
                    request_id, idx + 1,
                )
                prompt_errors.append({
                    "prompt_index": idx,
                    "type": "upstream_parse_error",
                    "message": f"Gemini returned a non-JSON response for prompt {idx + 1}.",
                })
                continue

            response_images = _extract_gemini_interaction_images(resp_json)
            if not response_images:
                prompt_errors.append({
                    "prompt_index": idx,
                    "type": "no_image_in_response",
                    "message": f"Gemini did not return an image for prompt {idx + 1}.",
                })
                continue

            image_part = response_images[0]
            images.append({
                "prompt_index": idx,
                "mime_type": image_part.get("mime_type", "image/png"),
                "data": image_part["data"],
            })

    finally:
        if owns_http_client:
            await http_client.aclose()

    if not images and prompt_errors:
        schedule_gemini_usage(502, count_quota=False)
        first_err = prompt_errors[0]
        return JSONResponse(
            status_code=502,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": first_err["type"],
                    "message": first_err["message"],
                },
                "prompt_errors": prompt_errors,
            },
        )

    schedule_gemini_usage(200)

    response_content: dict[str, Any] = {"images": images}
    if prompt_errors:
        response_content["prompt_errors"] = prompt_errors
    response_headers: dict[str, str] = {"X-Request-ID": request_id}
    if replay_mode == "record" and replay_topic and replay_stage and images:
        save_cassette(replay_topic, replay_stage, response_content)
        response_headers["X-Replay"] = "recorded"

    return JSONResponse(
        status_code=200,
        headers=response_headers,
        content=response_content,
        background=background_tasks,
    )


# ── ElevenLabs TTS endpoint ──────────────────────────────────────────


class ElevenLabsTTSPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Annotated[str, StringConstraints(min_length=1, max_length=10_000)]
    voice: str = ""
    model_id: str = "eleven_multilingual_v2"
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0)


class AudioUploadPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    palace_id: str = Field(min_length=1, max_length=80)
    audio_base64: str = Field(min_length=1)
    content_type: str = Field(default="audio/mpeg", max_length=80)
    filename: str = Field(default="narration.mp3", max_length=255)


ELEVENLABS_VOICES: dict[str, str] = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "adam": "pNInz6obpgDQGcFmaJgB",
    "callum": "N2lVS1w4EtoT3dr4eOWO",
    "charlie": "IKne3meq5aSn9XLyUdCD",
    "charlotte": "XB0fDUnXU5powFXDhCwa",
    "clyde": "2EiwWnXFnvU5JabPnv8n",
    "daniel": "onwK4e9ZLuTAKqWW03F9",
    "dave": "CYw3kZ02Hs0563khs1Fj",
    "dorothy": "ThT5KcBeYPX3keUQqHPh",
    "elli": "MF3mGyEYCl7XYWbV9V6O",
    "emily": "LcfcDJNUP1GQjkzn1xUU",
    "josh": "TxGEqnHWrfWFTfGW9XjX",
    "sam": "yoZ06aMxZJJ28mfd3POQ",
}


def _resolve_elevenlabs_voice_id(voice: str, default_voice: str) -> str:
    name = (voice or default_voice).strip().lower()
    return ELEVENLABS_VOICES.get(name, voice or ELEVENLABS_VOICES.get(default_voice.lower(), "21m00Tcm4TlvDq8ikWAM"))


def _write_elevenlabs_usage_log(
    *,
    settings: Settings,
    request_id: str,
    client_id: str,
    user_id: str | None,
    user_email: str | None,
    duration_ms: float,
    text_length: int,
    voice: str,
    model_id: str,
    status_code: int,
    audio_bytes: int | None,
) -> None:
    _ensure_log_path(settings.usage_log_path)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "provider": "elevenlabs",
        "client_id": client_id,
        "user_id": user_id,
        "user_email": user_email,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "text_length": text_length,
        "voice": voice,
        "model_id": model_id,
        "audio_bytes": audio_bytes,
    }
    with settings.usage_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


@app.post("/api/elevenlabs/tts")
async def elevenlabs_tts(
    payload: ElevenLabsTTSPayload,
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())

    if not active_settings.elevenlabs_configured:
        return JSONResponse(
            status_code=503,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "configuration_error",
                    "message": "ELEVENLABS_API_KEY is not configured on the backend.",
                }
            },
        )

    user: AuthenticatedUser | None = await _resolve_authenticated_user(
        request,
        active_settings,
    )
    bearer_token = _extract_bearer_token(request)

    if active_settings.provider_auth_required:
        if not active_settings.supabase_auth_configured:
            return _auth_not_configured_response(request_id)
        if user is None:
            return _auth_required_response(request_id, "Sign in to use ElevenLabs TTS.")

    rate_limiter = _get_rate_limiter(request, active_settings)
    allowed, retry_after = rate_limiter.allow(_rate_limit_subject(request, user))
    if not allowed:
        return _rate_limit_response(request_id, retry_after)

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        use_cache=True,
    )
    quota_allowed, quota_summary = _reserve_quota_if_needed(request, user, summary)
    if not quota_allowed:
        return _quota_exceeded_response(request_id, quota_summary)

    voice_id = _resolve_elevenlabs_voice_id(payload.voice, active_settings.elevenlabs_default_voice)

    started = time.perf_counter()
    client_id = _client_id(request)
    http_client, owns_http_client = _get_http_client(request)

    try:
        upstream_response = await http_client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": active_settings.elevenlabs_api_key,
                "content-type": "application/json",
                "accept": "audio/mpeg",
            },
            json={
                "text": payload.text,
                "model_id": payload.model_id,
                "voice_settings": {
                    "stability": payload.stability,
                    "similarity_boost": payload.similarity_boost,
                },
            },
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
    except httpx.TimeoutException:
        _release_quota_reservation(request, user)
        return JSONResponse(
            status_code=504,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "upstream_timeout",
                    "message": "ElevenLabs did not respond before the timeout elapsed.",
                }
            },
        )
    except httpx.HTTPError as exc:
        _release_quota_reservation(request, user)
        return JSONResponse(
            status_code=502,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "upstream_connection_error",
                    "message": f"Could not reach ElevenLabs: {exc}",
                }
            },
        )
    finally:
        if owns_http_client:
            await http_client.aclose()

    duration_ms = (time.perf_counter() - started) * 1000
    upstream_ok = 200 <= upstream_response.status_code < 300

    if not upstream_ok:
        _release_quota_reservation(request, user)
        error_body: dict[str, Any] = {}
        try:
            error_body = upstream_response.json()
        except ValueError:
            pass
        try:
            _write_elevenlabs_usage_log(
                settings=active_settings,
                request_id=request_id,
                client_id=client_id,
                user_id=user.user_id if user else None,
                user_email=user.email if user else None,
                duration_ms=duration_ms,
                text_length=len(payload.text),
                voice=voice_id,
                model_id=payload.model_id,
                status_code=upstream_response.status_code,
                audio_bytes=None,
            )
        except Exception:
            logger.exception("Failed to write ElevenLabs usage log for request %s", request_id)
        return JSONResponse(
            status_code=upstream_response.status_code,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "elevenlabs_error",
                    "message": error_body.get("detail", {}).get("message", "ElevenLabs returned an error."),
                    "status": upstream_response.status_code,
                }
            },
        )

    audio_data = upstream_response.content

    try:
        _write_elevenlabs_usage_log(
            settings=active_settings,
            request_id=request_id,
            client_id=client_id,
            user_id=user.user_id if user else None,
            user_email=user.email if user else None,
            duration_ms=duration_ms,
            text_length=len(payload.text),
            voice=voice_id,
            model_id=payload.model_id,
            status_code=upstream_response.status_code,
            audio_bytes=len(audio_data),
        )
    except Exception:
        logger.exception("Failed to write ElevenLabs usage log for request %s", request_id)

    if upstream_ok and user:
        _schedule_usage_event(
            background_tasks=background_tasks,
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            user=user,
            request_id=request_id,
            request_body={"provider": "elevenlabs", "text_length": len(payload.text), "voice": voice_id},
            response_payload={"usage": {"audio_bytes": len(audio_data)}},
            status_code=upstream_response.status_code,
        )

    return JSONResponse(
        status_code=200,
        headers={"X-Request-ID": request_id},
        content={
            "audio_base64": base64.b64encode(audio_data).decode("ascii"),
            "content_type": "audio/mpeg",
            "size_bytes": len(audio_data),
        },
        background=background_tasks,
    )


# ── Audio storage (Supabase Storage) ──────────────────────────────────

AUDIO_BUCKET = "palace-audio"
AUDIO_MAX_BYTES = 25 * 1024 * 1024  # 25 MB
AUDIO_ALLOWED_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/webm"}
_SAFE_FILENAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-.")


def _sanitize_audio_filename(raw: str) -> str:
    name = raw.strip().lower().replace(" ", "_")
    sanitized = "".join(c for c in name if c in _SAFE_FILENAME_CHARS)
    if not sanitized or sanitized.startswith("."):
        sanitized = "narration.mp3"
    if "." not in sanitized:
        sanitized += ".mp3"
    if len(sanitized) > 120:
        dot = sanitized.rfind(".")
        ext = sanitized[dot:] if dot >= 0 else ".mp3"
        sanitized = sanitized[: 120 - len(ext)] + ext
    return sanitized


async def _supabase_storage_request(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str,
    method: str,
    path: str,
    content: bytes | None = None,
    content_type: str = "application/octet-stream",
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    headers: dict[str, str] = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {bearer_token}",
    }
    if method in {"POST", "PUT"} and content is not None:
        headers["Content-Type"] = content_type

    http_client, owns = _get_http_client(request)
    try:
        return await http_client.request(
            method,
            settings.supabase_url.rstrip("/") + path,
            headers=headers,
            content=content,
            params=params,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
    finally:
        if owns:
            await http_client.aclose()


@app.post("/api/audio/upload")
async def upload_audio(payload: AudioUploadPayload, request: Request) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())
    bearer_token, user = await _require_persistence_context(request, active_settings)

    palace_id = _validate_palace_id(payload.palace_id)
    filename = _sanitize_audio_filename(payload.filename)

    if payload.content_type not in AUDIO_ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type: {payload.content_type}. Allowed: {', '.join(sorted(AUDIO_ALLOWED_TYPES))}",
        )

    try:
        audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio data: {exc}") from exc

    if len(audio_bytes) > AUDIO_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file exceeds {AUDIO_MAX_BYTES // (1024 * 1024)} MB limit.",
        )
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Audio data is empty.")

    storage_path = f"{user.user_id}/{palace_id}/{filename}"
    object_path = f"/storage/v1/object/{AUDIO_BUCKET}/{storage_path}"

    response = await _supabase_storage_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="POST",
        path=object_path,
        content=audio_bytes,
        content_type=payload.content_type,
    )

    if response.status_code == 400 and "already exists" in response.text.lower():
        response = await _supabase_storage_request(
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            method="PUT",
            path=object_path,
            content=audio_bytes,
            content_type=payload.content_type,
        )

    if response.status_code >= 400:
        logger.error(
            "Supabase Storage upload failed for %s: HTTP %s — %s",
            storage_path, response.status_code, response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail="Could not upload audio to storage. Please try again.",
        )

    logger.info(
        "Audio uploaded: %s (%d bytes) for palace %s [request %s]",
        filename, len(audio_bytes), palace_id, request_id,
    )

    return JSONResponse(
        status_code=200,
        headers={"X-Request-ID": request_id},
        content={
            "storage_path": storage_path,
            "filename": filename,
            "size_bytes": len(audio_bytes),
            "content_type": payload.content_type,
            "storage": "supabase",
        },
    )


@app.get("/api/audio/{palace_id}/{filename}")
async def download_audio(palace_id: str, filename: str, request: Request) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())
    bearer_token, user = await _require_persistence_context(request, active_settings)

    palace_id = _validate_palace_id(palace_id)
    filename = _sanitize_audio_filename(filename)
    storage_path = f"{user.user_id}/{palace_id}/{filename}"

    response = await _supabase_storage_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="GET",
        path=f"/storage/v1/object/{AUDIO_BUCKET}/{storage_path}",
    )

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Audio file not found in storage.")

    if response.status_code >= 400:
        logger.error(
            "Supabase Storage download failed for %s: HTTP %s — %s",
            storage_path, response.status_code, response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve audio from storage.",
        )

    audio_data = response.content
    content_type = response.headers.get("content-type", "audio/mpeg")

    return JSONResponse(
        status_code=200,
        headers={"X-Request-ID": request_id},
        content={
            "audio_base64": base64.b64encode(audio_data).decode("ascii"),
            "content_type": content_type,
            "size_bytes": len(audio_data),
            "filename": filename,
            "storage_path": storage_path,
        },
    )


@app.delete("/api/audio/{palace_id}/{filename}")
async def delete_audio(palace_id: str, filename: str, request: Request) -> JSONResponse:
    active_settings = _get_runtime_settings(request)
    request_id = str(uuid4())
    bearer_token, user = await _require_persistence_context(request, active_settings)

    palace_id = _validate_palace_id(palace_id)
    filename = _sanitize_audio_filename(filename)
    storage_path = f"{user.user_id}/{palace_id}/{filename}"

    response = await _supabase_storage_request(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        method="DELETE",
        path=f"/storage/v1/object/{AUDIO_BUCKET}/{storage_path}",
    )

    if response.status_code == 404:
        return JSONResponse(
            status_code=200,
            headers={"X-Request-ID": request_id},
            content={"deleted": False, "reason": "not_found"},
        )

    if response.status_code >= 400:
        logger.error(
            "Supabase Storage delete failed for %s: HTTP %s — %s",
            storage_path, response.status_code, response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail="Could not delete audio from storage.",
        )

    logger.info("Audio deleted: %s [request %s]", storage_path, request_id)

    return JSONResponse(
        status_code=200,
        headers={"X-Request-ID": request_id},
        content={"deleted": True, "storage_path": storage_path},
    )


@app.get("/api/dev/replay-cassettes")
async def list_replay_cassettes(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    if not active_settings.dev_mode:
        raise HTTPException(status_code=404, detail="Not found.")
    return {"cassettes": list_cassettes()}


@app.delete("/api/dev/replay-cassettes")
async def clear_replay_cassettes(request: Request) -> dict[str, Any]:
    active_settings = _get_runtime_settings(request)
    if not active_settings.dev_mode:
        raise HTTPException(status_code=404, detail="Not found.")
    topic = request.query_params.get("topic", "")
    stage = request.query_params.get("stage")
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required.")
    removed = clear_cassette(topic, stage)
    return {"removed": removed, "topic": topic, "stage": stage}


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
