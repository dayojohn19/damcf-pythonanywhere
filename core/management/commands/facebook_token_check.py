import os
from dataclasses import dataclass

import requests
from django.core.management.base import BaseCommand


GRAPH_VERSION = os.environ.get("FACEBOOK_GRAPH_VERSION", "v18.0").strip() or "v18.0"


@dataclass(frozen=True)
class TokenDebugInfo:
    token_type: str | None
    app_id: str | None
    user_id: str | None
    expires_at: int | None
    is_valid: bool | None
    scopes: list[str]
    granular_scopes: list[dict]


def _graph_url(path: str) -> str:
    path = path.lstrip("/")
    return f"https://graph.facebook.com/{GRAPH_VERSION}/{path}"


def _debug_token(user_or_page_token: str, app_id: str, app_secret: str) -> TokenDebugInfo:
    app_token = f"{app_id}|{app_secret}"
    resp = requests.get(
        _graph_url("debug_token"),
        params={"input_token": user_or_page_token, "access_token": app_token},
        timeout=20,
    )
    resp.raise_for_status()
    data = (resp.json() or {}).get("data") or {}

    scopes = data.get("scopes") or []
    granular_scopes = data.get("granular_scopes") or []

    return TokenDebugInfo(
        token_type=data.get("type"),
        app_id=data.get("app_id"),
        user_id=data.get("user_id"),
        expires_at=data.get("expires_at"),
        is_valid=data.get("is_valid"),
        scopes=list(scopes) if isinstance(scopes, list) else [],
        granular_scopes=list(granular_scopes) if isinstance(granular_scopes, list) else [],
    )


class Command(BaseCommand):
    help = "Validate Facebook Page token and posting permissions."

    def handle(self, *args, **options):
        page_id = (os.environ.get("FACEBOOK_PAGE_ID") or "").strip()
        page_token = (os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()

        if not page_id:
            self.stderr.write("Missing env var FACEBOOK_PAGE_ID")
            return
        if not page_token:
            self.stderr.write("Missing env var FACEBOOK_PAGE_ACCESS_TOKEN")
            return

        self.stdout.write(f"Graph API version: {GRAPH_VERSION}")
        self.stdout.write(f"Page ID: {page_id}")

        # 1) Basic page lookup
        try:
            r = requests.get(
                _graph_url(page_id),
                params={"fields": "id,name", "access_token": page_token},
                timeout=20,
            )
            self.stdout.write(f"GET /{page_id}?fields=id,name -> {r.status_code}")
            self.stdout.write(r.text)
        except Exception as e:
            self.stderr.write(f"Page lookup failed: {e}")

        # 2) Can we post?
        try:
            r = requests.post(
                _graph_url(f"{page_id}/feed"),
                data={"message": "(token check) Facebook auto-post is configured.", "access_token": page_token},
                timeout=20,
            )
            self.stdout.write(f"POST /{page_id}/feed -> {r.status_code}")
            self.stdout.write(r.text)
        except Exception as e:
            self.stderr.write(f"Posting test failed: {e}")

        # 3) Optional: token introspection (requires app id/secret)
        app_id = (os.environ.get("FACEBOOK_APP_ID") or "").strip()
        app_secret = (os.environ.get("FACEBOOK_APP_SECRET") or "").strip()
        if app_id and app_secret:
            try:
                info = _debug_token(page_token, app_id=app_id, app_secret=app_secret)
                self.stdout.write("debug_token:")
                self.stdout.write(f"  is_valid: {info.is_valid}")
                self.stdout.write(f"  type: {info.token_type}")
                self.stdout.write(f"  app_id: {info.app_id}")
                self.stdout.write(f"  user_id: {info.user_id}")
                self.stdout.write(f"  expires_at: {info.expires_at}")
                self.stdout.write(f"  scopes: {', '.join(info.scopes) if info.scopes else '(none)'}")
                if info.granular_scopes:
                    self.stdout.write("  granular_scopes:")
                    for gs in info.granular_scopes:
                        self.stdout.write(f"    - {gs}")
            except Exception as e:
                self.stderr.write(f"debug_token failed: {e}")
        else:
            self.stdout.write(
                "Skipping debug_token (set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET to enable introspection)."
            )
