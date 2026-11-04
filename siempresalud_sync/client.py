from __future__ import annotations

import base64
import hashlib
import json
import random
import secrets
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature


MCP_ENDPOINT = "https://siemsalud.myshopify.com/api/ucp/mcp"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_HTTP_OPENER = urllib.request.build_opener(_NoRedirect)


class SourceError(RuntimeError):
    pass


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _quote_sf_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


class UcpCatalogClient:
    def __init__(
        self,
        private_key_path: Path,
        private_key_password: str | None,
        agent_profile_url: str,
        signature_agent_url: str,
        timeout: int = 30,
        max_attempts: int = 3,
    ) -> None:
        password = private_key_password.encode() if private_key_password else None
        try:
            self.private_key = serialization.load_pem_private_key(
                private_key_path.read_bytes(),
                password=password,
            )
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Unable to load UCP private key: {exc}") from exc
        if not isinstance(self.private_key, ec.EllipticCurvePrivateKey) or not isinstance(
            self.private_key.curve, ec.SECP256R1
        ):
            raise RuntimeError("UCP/WBA signing requires an ECDSA P-256 private key.")

        for value, name in (
            (agent_profile_url, "agent profile URL"),
            (signature_agent_url, "signature-agent URL"),
        ):
            if urlparse(value).scheme != "https":
                raise RuntimeError(f"The {name} must use HTTPS.")

        public_numbers = self.private_key.public_key().public_numbers()
        self.x = _b64url(public_numbers.x.to_bytes(32, "big"))
        self.y = _b64url(public_numbers.y.to_bytes(32, "big"))
        thumbprint_input = json.dumps(
            {"crv": "P-256", "kty": "EC", "x": self.x, "y": self.y},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        self.key_id = _b64url(hashlib.sha256(thumbprint_input).digest())
        self.agent_profile_url = agent_profile_url
        self.signature_agent_url = signature_agent_url
        self.timeout = timeout
        self.max_attempts = max_attempts
        self._request_id = 0

    def _signed_headers(self, body: bytes, idempotency_key: str) -> dict[str, str]:
        parsed = urlparse(MCP_ENDPOINT)
        digest_header = "sha-256=:" + base64.b64encode(hashlib.sha256(body).digest()).decode() + ":"
        ucp_agent = "profile=" + _quote_sf_string(self.agent_profile_url)
        signature_agent = (
            'sig1=' + _quote_sf_string(self.signature_agent_url) + ";type=jwks_uri"
        )
        created = int(time.time())
        expires = created + 300
        nonce = _b64url(secrets.token_bytes(64))
        components = (
            '("@method" "@authority" "@path" "ucp-agent" '
            '"signature-agent";key="sig1" "idempotency-key" "content-digest" "content-type")'
        )
        signature_params = (
            f"{components};keyid={_quote_sf_string(self.key_id)};created={created};"
            f"expires={expires};nonce={_quote_sf_string(nonce)};tag=\"web-bot-auth\""
        )
        signature_base = "\n".join(
            (
                '"@method": POST',
                f'"@authority": {parsed.netloc}',
                f'"@path": {parsed.path}',
                f'"ucp-agent": {ucp_agent}',
                f'"signature-agent";key="sig1": {signature_agent}',
                f'"idempotency-key": {idempotency_key}',
                f'"content-digest": {digest_header}',
                '"content-type": application/json',
                '"@signature-params": ' + signature_params,
            )
        ).encode("utf-8")
        der_signature = self.private_key.sign(signature_base, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der_signature)
        raw_signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        return {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "UCP-Agent": ucp_agent,
            "Signature-Agent": signature_agent,
            "Idempotency-Key": idempotency_key,
            "Content-Digest": digest_header,
            "Signature-Input": f"sig1={signature_params}",
            "Signature": "sig1=:" + base64.b64encode(raw_signature).decode() + ":",
        }

    def _post(self, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        arguments = payload.get("params", {}).get("arguments", {})
        meta = arguments.get("meta", {})
        idempotency_key = meta.get("idempotency-key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise SourceError("A UCP idempotency key is required for every POST request.")
        last_error: Exception | None = None

        for attempt in range(self.max_attempts):
            request = urllib.request.Request(
                MCP_ENDPOINT,
                data=body,
                headers=self._signed_headers(body, idempotency_key),
                method="POST",
            )
            try:
                with _HTTP_OPENER.open(request, timeout=self.timeout) as response:
                    response_body = response.read()
                try:
                    message = json.loads(response_body)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    message = None
                    for line in response_body.decode("utf-8", errors="replace").splitlines():
                        if line.startswith("data:"):
                            try:
                                candidate = json.loads(line[5:].strip())
                            except json.JSONDecodeError:
                                continue
                            if (
                                isinstance(candidate, dict)
                                and ("result" in candidate or "error" in candidate)
                            ):
                                message = candidate
                    if message is None:
                        raise SourceError("The UCP endpoint returned invalid JSON or MCP events.") from exc
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    raise SourceError("The UCP endpoint returned an invalid JSON-RPC response.")
                if message.get("id") != payload.get("id"):
                    raise SourceError("The UCP response ID did not match the request.")
                if "error" in message:
                    raise SourceError(
                        f"UCP error {message['error'].get('code')}: "
                        f"{message['error'].get('message', 'unknown error')}"
                    )
                if not isinstance(message.get("result"), dict):
                    raise SourceError("The UCP response did not contain a result object.")
                return message["result"]
            except urllib.error.HTTPError as exc:
                last_error = exc
                retry_after = _retry_after_seconds(exc.headers.get("Retry-After"))
                retryable = exc.code == 429 or 500 <= exc.code <= 599
                if not retryable or attempt + 1 == self.max_attempts:
                    raise SourceError(f"UCP request failed with HTTP {exc.code}.") from exc
                if exc.code == 429 and retry_after is None:
                    raise SourceError(
                        "UCP returned HTTP 429 without a usable Retry-After header."
                    ) from exc
                delay = retry_after if exc.code == 429 else min(60.0, 2**attempt + random.random())
                if delay is not None:
                    time.sleep(delay)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt + 1 == self.max_attempts:
                    raise SourceError(f"Unable to reach the UCP endpoint: {exc}") from exc
                time.sleep(min(60.0, 2**attempt + random.random()))

        raise SourceError(f"UCP request failed: {last_error}")

    def _tool_call(self, name: str, arguments: dict) -> dict:
        self._request_id += 1
        meta = {
            "ucp-agent": {"profile": self.agent_profile_url},
            "idempotency-key": str(uuid.uuid4()),
        }
        result = self._post(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": self._request_id,
                "params": {
                    "name": name,
                    "arguments": {"meta": meta, **arguments},
                },
            }
        )
        if result.get("isError"):
            text = "; ".join(
                item.get("text", "")
                for item in result.get("content", [])
                if isinstance(item, dict)
            )
            raise SourceError(f"UCP tool {name} failed: {text or 'unspecified tool error'}")
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        for item in result.get("content", []):
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                try:
                    decoded = json.loads(item["text"])
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict):
                    return decoded
        raise SourceError(f"UCP tool {name} returned no structured catalog data.")

    def _list_tools(self) -> set[str]:
        self._request_id += 1
        result = self._post(
            {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": self._request_id,
                "params": {
                    "arguments": {
                        "meta": {
                            "ucp-agent": {"profile": self.agent_profile_url},
                            "idempotency-key": str(uuid.uuid4()),
                        }
                    }
                },
            }
        )
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise SourceError("UCP tools/list did not return a tool list.")
        return {tool["name"] for tool in tools if isinstance(tool, dict) and "name" in tool}

    def fetch_catalog(self) -> tuple[list[dict], bool]:
        tools = self._list_tools()
        if "search_catalog" not in tools:
            raise SourceError("The merchant did not advertise the UCP search_catalog tool.")

        products: dict[str, dict] = {}
        cursor: str | None = None
        seen_cursors: set[str] = set()
        complete = False

        for _ in range(1000):
            pagination = {"limit": 250}
            if cursor:
                pagination["cursor"] = cursor
            page = self._tool_call("search_catalog", {"catalog": {"pagination": pagination}})
            items = page.get("products")
            if not isinstance(items, list):
                raise SourceError("UCP search_catalog returned no products array.")
            for item in items:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    raise SourceError("UCP search_catalog returned a product without an ID.")
                product_id = item["id"]
                if product_id in products:
                    existing = products[product_id]
                    variants = {
                        variant.get("id"): variant
                        for variant in existing.get("variants", [])
                        if isinstance(variant, dict)
                    }
                    for variant in item.get("variants", []):
                        if isinstance(variant, dict) and variant.get("id"):
                            variants[variant["id"]] = variant
                    existing["variants"] = list(variants.values())
                else:
                    products[product_id] = item

            pagination_result = page.get("pagination")
            if not isinstance(pagination_result, dict):
                break
            if pagination_result.get("has_next_page") is not True:
                complete = True
                break
            next_cursor = pagination_result.get("cursor")
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                raise SourceError("UCP returned an invalid or repeated pagination cursor.")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        else:
            raise SourceError("UCP catalog exceeded the 1,000-page safety limit.")

        return list(products.values()), complete
