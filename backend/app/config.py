from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def _split_csv(raw: str) -> tuple[str, ...]:
    values = [item.strip() for item in raw.split(",")]
    return tuple(item for item in values if item)


def _normalize_origin(raw: str) -> str:
    return raw.strip().rstrip("/")


def _clean_env_value(key: str, default: str = "") -> str:
    value = os.getenv(key, default).strip()
    lowered = value.lower()
    placeholder_fragments = (
        "replace-with",
        "your-project-ref",
        "your-public-anon-key",
        "your-server-only-service-role-key",
        "your-local",
    )
    if not value or any(fragment in lowered for fragment in placeholder_fragments):
        return ""
    return value


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_billing_mode(raw: str) -> str:
    mode = raw.strip().lower()
    if mode in {"beta", "stripe", "production", "disabled"}:
        return mode
    return "beta"


@dataclass(frozen=True)
class Settings:
    app_env: str
    host: str
    port: int
    app_base_url: str
    anthropic_api_key: str
    anthropic_api_url: str
    anthropic_max_tokens: int
    anthropic_timeout_seconds: float
    cors_origins: tuple[str, ...]
    trust_proxy_headers: bool
    rate_limit_requests: int
    rate_limit_window_seconds: int
    max_request_bytes: int
    usage_log_path: Path
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_audience: str | None
    free_monthly_requests: int
    pro_monthly_requests: int
    team_monthly_requests: int
    billing_mode: str
    demo_auth_bypass: bool
    gemini_api_key: str
    gemini_model: str
    gemini_text_model: str
    gemini_image_model: str
    openai_api_key: str
    openai_embedding_model: str
    openai_embedding_dimensions: int
    plan_override_path: Path
    admin_emails: tuple[str, ...]

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def openai_embeddings_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_embedding_model)

    @property
    def supabase_auth_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def supabase_admin_configured(self) -> bool:
        return bool(self.supabase_auth_configured and self.supabase_service_role_key)

    @property
    def medical_knowledge_configured(self) -> bool:
        return bool(self.supabase_admin_configured and self.openai_embeddings_configured)

    @property
    def supabase_jwks_url(self) -> str:
        if not self.supabase_url:
            return ""
        return self.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"

    @property
    def supabase_issuer(self) -> str | None:
        if not self.supabase_url:
            return None
        return self.supabase_url.rstrip("/") + "/auth/v1"

    @property
    def dev_mode(self) -> bool:
        return self.app_env.lower() != "production"

    @property
    def provider_auth_required(self) -> bool:
        if self.dev_mode and self.demo_auth_bypass:
            return False
        return self.supabase_auth_configured or not self.dev_mode

    @property
    def billing_upgrade_path_enabled(self) -> bool:
        return self.billing_mode in {"stripe", "production"}

    @property
    def billing_foundation_status(self) -> str:
        if self.billing_upgrade_path_enabled:
            return "active"
        if self.billing_mode == "disabled":
            return "disabled"
        return "beta"

    @property
    def billing_message(self) -> str:
        if self.billing_upgrade_path_enabled:
            return "Billing is active. Paid plan upgrades can change monthly request limits."
        if self.billing_mode == "disabled":
            return "Billing is disabled. Account request limits are fixed by the backend."
        return (
            "Mnemorized is in private beta. Billing is not active yet; beta accounts use "
            "fixed monthly request limits."
        )

    @property
    def cors_allowed_origins(self) -> tuple[str, ...]:
        origins = tuple(_normalize_origin(origin) for origin in self.cors_origins if origin.strip())
        if self.dev_mode:
            return origins or ("*",)

        explicit_origins = tuple(origin for origin in origins if origin != "*")
        if explicit_origins:
            return explicit_origins

        app_origin = _normalize_origin(self.app_base_url)
        return (app_origin,) if app_origin else ()

    def request_limit_for_plan(self, plan_code: str | None) -> int | None:
        plan = (plan_code or "free").strip().lower()
        if plan in {"enterprise", "unlimited"}:
            return None
        if plan == "team":
            return self.team_monthly_requests
        if plan in {"pro", "paid"}:
            return self.pro_monthly_requests
        return self.free_monthly_requests


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parents[1]
    _load_env_file(backend_dir / ".env")
    default_log_path = backend_dir / "logs" / "anthropic_usage.jsonl"
    default_override_path = backend_dir / "dev_data" / "plan_overrides.json"
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        app_base_url=os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").strip(),
        anthropic_api_key=_clean_env_value("ANTHROPIC_API_KEY"),
        anthropic_api_url=os.getenv(
            "ANTHROPIC_API_URL",
            "https://api.anthropic.com/v1/messages",
        ).strip(),
        anthropic_max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "8192")),
        anthropic_timeout_seconds=float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "180")),
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS", "*")),
        trust_proxy_headers=_env_bool("TRUST_PROXY_HEADERS", False),
        rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "20")),
        rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
        max_request_bytes=int(os.getenv("MAX_REQUEST_BYTES", "12000000")),
        usage_log_path=Path(os.getenv("USAGE_LOG_PATH", str(default_log_path))),
        supabase_url=_clean_env_value("SUPABASE_URL"),
        supabase_anon_key=_clean_env_value("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_clean_env_value("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_jwt_audience=os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated").strip()
        or None,
        free_monthly_requests=int(os.getenv("FREE_MONTHLY_REQUESTS", "40")),
        pro_monthly_requests=int(os.getenv("PRO_MONTHLY_REQUESTS", "400")),
        team_monthly_requests=int(os.getenv("TEAM_MONTHLY_REQUESTS", "4000")),
        billing_mode=_normalize_billing_mode(os.getenv("BILLING_MODE", "beta")),
        demo_auth_bypass=_env_bool("DEMO_AUTH_BYPASS", True),
        gemini_api_key=_clean_env_value("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3-pro-image").strip(),
        gemini_text_model=os.getenv("GEMINI_TEXT_MODEL", "gemini-3.1-pro-preview").strip(),
        gemini_image_model=os.getenv(
            "GEMINI_IMAGE_MODEL",
            os.getenv("GEMINI_MODEL", "gemini-3-pro-image"),
        ).strip(),
        openai_api_key=_clean_env_value("OPENAI_API_KEY"),
        openai_embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ).strip(),
        openai_embedding_dimensions=int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536")),
        plan_override_path=Path(os.getenv("PLAN_OVERRIDE_PATH", str(default_override_path))),
        admin_emails=_split_csv(os.getenv("ADMIN_EMAILS", "")),
    )
