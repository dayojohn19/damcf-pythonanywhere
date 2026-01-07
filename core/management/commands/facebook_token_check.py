import os
from dataclasses import dataclass

import requests
from django.core.management.base import BaseCommand


def _normalize_graph_version(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "v18.0"
    if raw.startswith("v"):
        return raw
    # Allow users to set 24.0 or 24 and treat it as v24.0 / v24
    if raw[0].isdigit():
        return f"v{raw}"
    return raw


GRAPH_VERSION = _normalize_graph_version(os.environ.get("FACEBOOK_GRAPH_VERSION", "v18.0"))


@dataclass(frozen=True)
class TokenDebugInfo:
    token_type: str | None
    app_id: str | None
    user_id: str | None
    expires_at: int | None
    is_valid: bool | None
    scopes: list[str]
    granular_scopes: list[dict]


def _graph_url(path: str, *, graph_version: str | None = None) -> str:
    path = path.lstrip("/")
    version = _normalize_graph_version(graph_version) if graph_version is not None else GRAPH_VERSION
    return f"https://graph.facebook.com/{version}/{path}"


def _debug_token(
    user_or_page_token: str,
    app_id: str,
    app_secret: str,
    *,
    graph_version: str | None = None,
    timeout: int = 20,
) -> TokenDebugInfo:
    app_token = f"{app_id}|{app_secret}"
    resp = requests.get(
        _graph_url("debug_token", graph_version=graph_version),
        params={"input_token": user_or_page_token, "access_token": app_token},
        timeout=timeout,
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

    def add_arguments(self, parser):
        parser.add_argument(
            "--page-id",
            dest="page_id",
            default=None,
            help="Facebook Page ID (defaults to env FACEBOOK_PAGE_ID).",
        )
        parser.add_argument(
            "--page-token",
            dest="page_token",
            default=None,
            help="Facebook Page access token (defaults to env FACEBOOK_PAGE_ACCESS_TOKEN).",
        )
        parser.add_argument(
            "--post",
            action="store_true",
            help="Actually attempt to POST to /{page_id}/feed. Off by default to avoid accidental posts.",
        )
        parser.add_argument(
            "--message",
            dest="message",
            default="(token check) Facebook auto-post is configured.",
            help="Message used for the posting test when --post is set.",
        )
        parser.add_argument(
            "--timeout",
            dest="timeout",
            type=int,
            default=20,
            help="HTTP timeout in seconds (default: 20).",
        )
        parser.add_argument(
            "--graph-version",
            dest="graph_version",
            default=None,
            help="Override Graph API version (defaults to env FACEBOOK_GRAPH_VERSION or v18.0).",
        )

    def handle(self, *args, **options):
        graph_version = _normalize_graph_version(
            options.get("graph_version") or os.environ.get("FACEBOOK_GRAPH_VERSION") or "v18.0"
        )
        page_id = (options.get("page_id") or os.environ.get("FACEBOOK_PAGE_ID") or "").strip()
        page_token = (options.get("page_token") or os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()
        timeout = int(options.get("timeout") or 20)
        do_post = bool(options.get("post"))
        post_message = (options.get("message") or "").strip() or "(token check) Facebook auto-post is configured."

        if not page_id:
            self.stderr.write("Missing env var FACEBOOK_PAGE_ID")
            return
        if not page_token:
            self.stderr.write("Missing env var FACEBOOK_PAGE_ACCESS_TOKEN")
            return

        self.stdout.write(f"Graph API version: {graph_version}")
        self.stdout.write(f"Page ID: {page_id}")

        def graph_url(path: str) -> str:
            return _graph_url(path, graph_version=graph_version)

        # 1) Basic page lookup
        try:
            r = requests.get(
                graph_url(page_id),
                params={"fields": "id,name", "access_token": page_token},
                timeout=timeout,
            )
            self.stdout.write(f"GET /{page_id}?fields=id,name -> {r.status_code}")
            self.stdout.write(r.text)
        except Exception as e:
            self.stderr.write(f"Page lookup failed: {e}")

        # 2) Can we post?
        if do_post:
            try:
                r = requests.post(
                    graph_url(f"{page_id}/feed"),
                    data={"message": post_message, "access_token": page_token},
                    timeout=timeout,
                )
                self.stdout.write(f"POST /{page_id}/feed -> {r.status_code}")
                self.stdout.write(r.text)
            except Exception as e:
                self.stderr.write(f"Posting test failed: {e}")
        else:
            self.stdout.write(f"Skipping posting test (use --post to attempt POST /{page_id}/feed).")

        # 3) Optional: token introspection (requires app id/secret)
        app_id = (os.environ.get("FACEBOOK_APP_ID") or "").strip()
        app_secret = (os.environ.get("FACEBOOK_APP_SECRET") or "").strip()
        if app_id and app_secret:
            try:
                info = _debug_token(
                    page_token,
                    app_id=app_id,
                    app_secret=app_secret,
                    graph_version=graph_version,
                    timeout=timeout,
                )
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
