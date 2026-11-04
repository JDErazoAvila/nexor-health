from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    database_path: Path
    private_key_path: Path
    private_key_password: str | None
    agent_profile_url: str
    signature_agent_url: str
    admin_token: str
    host: str
    port: int
    sync_interval_seconds: int = 60
    request_timeout_seconds: int = 30
    max_request_attempts: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        profile_url = os.environ.get("NEXOR_UCP_PROFILE_URL", "").strip()
        key_path = os.environ.get("NEXOR_UCP_PRIVATE_KEY_PATH", "").strip()
        admin_token = os.environ.get("NEXOR_SYNC_ADMIN_TOKEN", "")

        if not profile_url:
            raise RuntimeError("NEXOR_UCP_PROFILE_URL is required.")
        if urlparse(profile_url).scheme != "https" or not urlparse(profile_url).netloc:
            raise RuntimeError("NEXOR_UCP_PROFILE_URL must use HTTPS.")
        if not key_path:
            raise RuntimeError("NEXOR_UCP_PRIVATE_KEY_PATH is required.")
        if not admin_token or len(admin_token) < 32:
            raise RuntimeError("NEXOR_SYNC_ADMIN_TOKEN must contain at least 32 characters.")

        database_path = Path(
            os.environ.get(
                "NEXOR_SYNC_DATABASE",
                str(ROOT / "data" / "siempresalud_sync.sqlite3"),
            )
        ).expanduser()
        signature_agent_url = os.environ.get(
            "NEXOR_UCP_SIGNATURE_AGENT_URL", profile_url
        ).strip()
        if urlparse(signature_agent_url).scheme != "https" or not urlparse(signature_agent_url).netloc:
            raise RuntimeError("NEXOR_UCP_SIGNATURE_AGENT_URL must use HTTPS.")
        return cls(
            database_path=database_path,
            private_key_path=Path(key_path).expanduser(),
            private_key_password=os.environ.get("NEXOR_UCP_PRIVATE_KEY_PASSWORD") or None,
            agent_profile_url=profile_url,
            signature_agent_url=signature_agent_url,
            admin_token=admin_token,
            host=os.environ.get("NEXOR_SYNC_HOST", "127.0.0.1"),
            port=int(os.environ.get("NEXOR_SYNC_PORT", "8765")),
        )
