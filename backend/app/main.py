from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import httpx
from fastapi import BackgroundTasks
from fastapi import HTTPException
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jwt import InvalidTokenError
from pydantic import BaseModel, ConfigDict, Field

from .auth import AuthenticatedUser, SupabaseTokenVerifier
from .config import Settings, get_settings
from .dev_tools import clear_plan_override, read_plan_override, write_plan_override
from .rate_limit import InMemoryRateLimiter

FRONTEND_DIR = Path(__file__).resolve().parents[2]


class UsageSummaryCache:
    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = Lock()

    def get(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._entries.get(user_id)
            if entry is None:
                return None
            ts, data = entry
            if time.time() - ts > self._ttl:
                del self._entries[user_id]
                return None
            return data.copy()

    def put(self, user_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._entries[user_id] = (time.time(), data.copy())

    def increment_used(self, user_id: str) -> None:
        with self._lock:
            entry = self._entries.get(user_id)
            if entry is None:
                return
            ts, data = entry
            data["monthly_requests_used"] = data.get("monthly_requests_used", 0) + 1
            limit = data.get("monthly_request_limit")
            if limit is not None:
                data["monthly_requests_remaining"] = max(0, limit - data["monthly_requests_used"])
            self._entries[user_id] = (ts, data)


logger = logging.getLogger("mnemorized.proxy")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


class MessagePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(min_length=1)
    max_tokens: int = Field(gt=0, le=64000)
    messages: list[dict[str, Any]] = Field(min_length=1)


class DevPlanOverridePayload(BaseModel):
    plan_code: str = Field(pattern="^(free|pro|team|enterprise|unlimited)$")
    clear: bool = False


class ImageGenerationPayload(BaseModel):
    prompts: list[str] = Field(min_length=1, max_length=2)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _client_id(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
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
    bearer_token: str,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    base_headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
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


async def _get_subscription_and_usage_summary(
    *,
    request: Request,
    settings: Settings,
    bearer_token: str | None,
    user: AuthenticatedUser | None,
    use_cache: bool = False,
) -> dict[str, Any]:
    if not (settings.supabase_auth_configured and bearer_token and user):
        return {
            "plan_code": "free",
            "subscription_status": "inactive",
            "monthly_request_limit": settings.request_limit_for_plan("free"),
            "monthly_requests_used": 0,
            "monthly_requests_remaining": settings.request_limit_for_plan("free"),
            "period_started_at": _iso_month_start(),
            "period_ends_at": _iso_next_month_start(),
            "is_dev_override": False,
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
            "limit": "1",
        },
    )
    if subscription_response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not load your subscription state from Supabase: "
                f"{subscription_response.text[:300]}"
            ),
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
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not load your usage summary from Supabase: "
                f"{usage_response.text[:300]}"
            ),
        )

    used = _parse_content_range_total(usage_response.headers.get("content-range"))
    remaining = None if monthly_limit is None else max(0, monthly_limit - used)

    result = {
        "plan_code": plan_code or "free",
        "subscription_status": subscription_status,
        "monthly_request_limit": monthly_limit,
        "monthly_requests_used": used,
        "monthly_requests_remaining": remaining,
        "period_started_at": _iso_month_start(),
        "period_ends_at": _iso_next_month_start(),
        "is_dev_override": bool(override),
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
    allow_origins=list(settings.cors_origins) or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "X-Request-ID", "X-Anthropic-Request-ID"],
)


@app.get("/")
async def landing():
    path = FRONTEND_DIR / "mnemorized-landing.html"
    if path.exists():
        return FileResponse(path, media_type="text/html")
    return JSONResponse({"service": "mnemorized-backend", "status": "ok"})


@app.get("/forge")
async def forge():
    return FileResponse(FRONTEND_DIR / "memory-palace-forge-v5.html", media_type="text/html")


@app.get("/library")
async def library():
    return FileResponse(FRONTEND_DIR / "library.html", media_type="text/html")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    active_settings = get_settings()
    return {
        "status": "ok",
        "service": "mnemorized-backend",
        "anthropic_configured": active_settings.anthropic_configured,
        "gemini_configured": active_settings.gemini_configured,
        "supabase_auth_configured": active_settings.supabase_auth_configured,
        "rate_limit": {
            "requests": active_settings.rate_limit_requests,
            "window_seconds": active_settings.rate_limit_window_seconds,
        },
        "next_foundations": {
            "auth": "supabase-ready" if active_settings.supabase_auth_configured else "planned",
            "persistence": "supabase-ready" if active_settings.supabase_auth_configured else "planned",
            "billing": "planned",
        },
    }


@app.get("/api/config/public")
async def public_config() -> dict[str, Any]:
    active_settings = get_settings()
    return {
        "auth_enabled": active_settings.supabase_auth_configured,
        "supabase_url": active_settings.supabase_url or None,
        "supabase_anon_key": active_settings.supabase_anon_key or None,
        "app_base_url": active_settings.app_base_url,
        "dev_mode": active_settings.dev_mode,
    }


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

    content_length = request.headers.get("content-length")
    try:
        request_size = int(content_length) if content_length else 0
    except ValueError:
        request_size = 0

    if request_size > active_settings.max_request_bytes:
        return JSONResponse(
            status_code=413,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "request_too_large",
                    "message": (
                        f"Request exceeds MAX_REQUEST_BYTES={active_settings.max_request_bytes}."
                    ),
                }
            },
        )

    client_id = _client_id(request)
    rate_limiter = _get_rate_limiter(request, active_settings)
    allowed, retry_after = rate_limiter.allow(client_id)
    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={
                "Retry-After": str(retry_after),
                "X-Request-ID": request_id,
            },
            content={
                "error": {
                    "type": "rate_limit_error",
                    "message": (
                        "Too many requests. Slow down and try again in a moment."
                    ),
                }
            },
        )

    user: AuthenticatedUser | None = await _resolve_authenticated_user(
        request,
        active_settings,
    )
    bearer_token = _extract_bearer_token(request)

    if active_settings.supabase_auth_configured and user is None:
        return JSONResponse(
            status_code=401,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "authentication_required",
                    "message": "Sign in to use the API proxy.",
                }
            },
        )

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        use_cache=True,
    )
    monthly_limit = summary["monthly_request_limit"]
    monthly_used = summary["monthly_requests_used"]
    if monthly_limit is not None and monthly_used >= monthly_limit:
        return JSONResponse(
            status_code=402,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "quota_exceeded",
                    "message": (
                        f"You have used {monthly_used} of {monthly_limit} monthly requests "
                        "for your current plan. Upgrade or wait for the next billing period."
                    ),
                },
                "plan": {
                    "code": summary["plan_code"],
                    "status": summary["subscription_status"],
                },
                "usage": {
                    "used": monthly_used,
                    "limit": monthly_limit,
                    "remaining": summary["monthly_requests_remaining"],
                    "period_ends_at": summary["period_ends_at"],
                },
            },
        )

    body = payload.model_dump(exclude_none=True)
    upstream_headers = {
        "content-type": "application/json",
        "x-api-key": active_settings.anthropic_api_key,
        "anthropic-version": request.headers.get("anthropic-version", "2023-06-01"),
    }
    if request.headers.get("anthropic-beta"):
        upstream_headers["anthropic-beta"] = request.headers["anthropic-beta"]

    started = time.perf_counter()
    http_client, owns_http_client = _get_http_client(request)

    try:
        upstream_response = await http_client.post(
            active_settings.anthropic_api_url,
            headers=upstream_headers,
            json=body,
            timeout=httpx.Timeout(active_settings.anthropic_timeout_seconds, connect=10.0),
        )
    except httpx.TimeoutException:
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

    background_tasks.add_task(
        _persist_usage_event_background,
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        request_id=request_id,
        request_body=body,
        response_payload=response_payload,
        status_code=upstream_response.status_code,
    )

    if user:
        usage_cache = getattr(request.app.state, "usage_cache", None)
        if usage_cache is not None:
            usage_cache.increment_used(user.user_id)

    passthrough_headers = {"X-Request-ID": request_id}
    anthropic_request_id = upstream_response.headers.get("request-id")
    if anthropic_request_id:
        passthrough_headers["X-Anthropic-Request-ID"] = anthropic_request_id

    if response_payload is None:
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

    return JSONResponse(
        status_code=upstream_response.status_code,
        headers=passthrough_headers,
        content=response_payload,
        background=background_tasks,
    )


@app.post("/api/generate-image")
async def generate_image(
    payload: ImageGenerationPayload,
    request: Request,
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

    user: AuthenticatedUser | None = await _resolve_authenticated_user(
        request,
        active_settings,
    )
    bearer_token = _extract_bearer_token(request)

    if active_settings.supabase_auth_configured and user is None:
        return JSONResponse(
            status_code=401,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "authentication_required",
                    "message": "Sign in to generate images.",
                }
            },
        )

    summary = await _get_subscription_and_usage_summary(
        request=request,
        settings=active_settings,
        bearer_token=bearer_token,
        user=user,
        use_cache=True,
    )
    monthly_limit = summary["monthly_request_limit"]
    monthly_used = summary["monthly_requests_used"]
    if monthly_limit is not None and monthly_used >= monthly_limit:
        return JSONResponse(
            status_code=402,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "type": "quota_exceeded",
                    "message": (
                        f"You have used {monthly_used} of {monthly_limit} monthly requests "
                        "for your current plan. Upgrade or wait for the next billing period."
                    ),
                },
                "usage": {
                    "used": monthly_used,
                    "limit": monthly_limit,
                    "remaining": summary["monthly_requests_remaining"],
                    "period_ends_at": summary["period_ends_at"],
                },
            },
        )

    model = active_settings.gemini_model
    api_url = f"{GEMINI_API_BASE}/{model}:generateContent"
    http_client, owns_http_client = _get_http_client(request)
    images: list[dict[str, Any]] = []
    conversation: list[dict[str, Any]] = []

    try:
        for idx, prompt_text in enumerate(payload.prompts):
            conversation.append({"role": "user", "parts": [{"text": prompt_text}]})

            gemini_body: dict[str, Any] = {
                "contents": conversation.copy(),
                "generationConfig": {
                    "responseModalities": ["IMAGE"],
                },
            }

            try:
                resp = await http_client.post(
                    api_url,
                    params={"key": active_settings.gemini_api_key},
                    json=gemini_body,
                    timeout=httpx.Timeout(120.0, connect=10.0),
                )
            except httpx.TimeoutException:
                return JSONResponse(
                    status_code=504,
                    headers={"X-Request-ID": request_id},
                    content={
                        "error": {
                            "type": "upstream_timeout",
                            "message": f"Gemini did not respond in time for prompt {idx + 1}.",
                        }
                    },
                )
            except httpx.HTTPError as exc:
                return JSONResponse(
                    status_code=502,
                    headers={"X-Request-ID": request_id},
                    content={
                        "error": {
                            "type": "upstream_connection_error",
                            "message": f"Could not reach Gemini: {exc}",
                        }
                    },
                )

            if resp.status_code != 200:
                error_detail = resp.text[:500]
                logger.warning(
                    "Gemini API error for request %s prompt %d: %s %s",
                    request_id, idx + 1, resp.status_code, error_detail,
                )
                return JSONResponse(
                    status_code=502,
                    headers={"X-Request-ID": request_id},
                    content={
                        "error": {
                            "type": "upstream_error",
                            "message": (
                                f"Gemini returned {resp.status_code} for prompt {idx + 1} "
                                f"using model {model}."
                            ),
                            "detail": error_detail,
                        }
                    },
                )

            resp_json = resp.json()
            candidates = resp_json.get("candidates", [])
            if not candidates:
                return JSONResponse(
                    status_code=502,
                    headers={"X-Request-ID": request_id},
                    content={
                        "error": {
                            "type": "upstream_empty",
                            "message": f"Gemini returned no candidates for prompt {idx + 1}.",
                        }
                    },
                )

            model_parts = candidates[0].get("content", {}).get("parts", [])
            image_part = None
            for part in model_parts:
                if "inlineData" in part:
                    image_part = part["inlineData"]
                    break

            if image_part is None:
                return JSONResponse(
                    status_code=502,
                    headers={"X-Request-ID": request_id},
                    content={
                        "error": {
                            "type": "no_image_in_response",
                            "message": f"Gemini did not return an image for prompt {idx + 1}.",
                        }
                    },
                )

            images.append({
                "prompt_index": idx,
                "mime_type": image_part.get("mimeType", "image/png"),
                "data": image_part["data"],
            })

            conversation.append({
                "role": "model",
                "parts": [{"inlineData": image_part}],
            })

    finally:
        if owns_http_client:
            await http_client.aclose()

    try:
        await _persist_usage_event_to_supabase(
            request=request,
            settings=active_settings,
            bearer_token=bearer_token,
            user=user,
            request_id=request_id,
            request_body={"provider": "gemini", "model": model, "prompts": len(payload.prompts)},
            response_payload={"usage": {}},
            status_code=200,
        )
    except Exception:
        logger.exception("Failed to persist Gemini usage event for request %s", request_id)

    if user:
        usage_cache = getattr(request.app.state, "usage_cache", None)
        if usage_cache is not None:
            usage_cache.increment_used(user.user_id)

    return JSONResponse(
        status_code=200,
        headers={"X-Request-ID": request_id},
        content={"images": images},
    )


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
