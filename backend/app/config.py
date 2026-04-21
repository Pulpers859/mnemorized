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
        os.environ.setdefault(key, value)


def _split_csv(raw: str) -> tuple[str, ...]:
    values = [item.strip() for item in raw.split(",")]
    return tuple(item for item in values if item)


@dataclass(frozen=True)
class Settings:
    app_env: str
    host: str
    port: int
    app_base_url: str
    anthropic_api_key: str
    anthropic_api_url: str
    cors_origins: tuple[str, ...]
    rate_limit_requests: int
    rate_limit_window_seconds: int
    max_request_bytes: int
    usage_log_path: Path
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_audience: str | None
    free_monthly_requests: int
    pro_monthly_requests: int
    team_monthly_requests: int
    gemini_api_key: str
    gemini_model: str
    plan_override_path: Path

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def supabase_auth_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

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
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_api_url=os.getenv(
            "ANTHROPIC_API_URL",
            "https://api.anthropic.com/v1/messages",
        ).strip(),
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS", "*")),
        rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "20")),
        rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
        max_request_bytes=int(os.getenv("MAX_REQUEST_BYTES", "12000000")),
        usage_log_path=Path(os.getenv("USAGE_LOG_PATH", str(default_log_path))),
        supabase_url=os.getenv("SUPABASE_URL", "").strip(),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", "").strip(),
        supabase_jwt_audience=os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated").strip()
        or None,
        free_monthly_requests=int(os.getenv("FREE_MONTHLY_REQUESTS", "40")),
        pro_monthly_requests=int(os.getenv("PRO_MONTHLY_REQUESTS", "400")),
        team_monthly_requests=int(os.getenv("TEAM_MONTHLY_REQUESTS", "4000")),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp").strip(),
        plan_override_path=Path(os.getenv("PLAN_OVERRIDE_PATH", str(default_override_path))),
    )
