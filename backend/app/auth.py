from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt import InvalidTokenError


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None
    claims: dict[str, Any]


class SupabaseTokenVerifier:
    def __init__(
        self,
        *,
        jwks_url: str,
        issuer: str | None,
        audience: str | None,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self.cache_ttl_seconds = cache_ttl_seconds
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_fetched_at = 0.0

    async def _get_jwks(self, http_client: httpx.AsyncClient) -> dict[str, Any]:
        now = time.time()
        if self._jwks_cache and now - self._jwks_fetched_at < self.cache_ttl_seconds:
            return self._jwks_cache

        response = await http_client.get(self.jwks_url)
        response.raise_for_status()
        self._jwks_cache = response.json()
        self._jwks_fetched_at = now
        return self._jwks_cache

    async def verify_token(
        self,
        token: str,
        http_client: httpx.AsyncClient,
    ) -> AuthenticatedUser:
        jwks = await self._get_jwks(http_client)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise InvalidTokenError("Missing token key id.")

        key_data = next(
            (item for item in jwks.get("keys", []) if item.get("kid") == kid),
            None,
        )
        if key_data is None:
            raise InvalidTokenError("Signing key not found for token.")

        jwk = jwt.PyJWK.from_dict(
            key_data,
            algorithm=header.get("alg") or key_data.get("alg"),
        )
        decode_options = {"verify_aud": self.audience is not None}
        claims = jwt.decode(
            token,
            key=jwk.key,
            algorithms=[key_data.get("alg", "RS256")],
            audience=self.audience,
            issuer=self.issuer,
            options=decode_options,
        )

        return AuthenticatedUser(
            user_id=str(claims["sub"]),
            email=claims.get("email"),
            claims=claims,
        )
