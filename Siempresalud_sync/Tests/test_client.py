from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from Siempresalud_sync.client import UcpCatalogClient


class UcpSignatureTests(unittest.TestCase):
    def _client(self, directory: str) -> UcpCatalogClient:
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        path = Path(directory) / "key.pem"
        path.write_bytes(pem)
        return UcpCatalogClient(
            path,
            None,
            "https://nexor.example/.well-known/ucp",
            "https://nexor.example/.well-known/ucp",
        )

    def test_signed_headers_use_registered_profile_and_wba_fields(self) -> None:
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key.pem"
            path.write_bytes(pem)
            client = UcpCatalogClient(
                path,
                None,
                "https://nexor.example/.well-known/ucp",
                "https://nexor.example/.well-known/ucp",
            )
            body = b'{"jsonrpc":"2.0"}'
            headers = client._signed_headers(body, "123e4567-e89b-12d3-a456-426614174000")

        digest = base64.b64encode(hashlib.sha256(body).digest()).decode()
        signature = base64.b64decode(headers["Signature"].removeprefix("sig1=:").removesuffix(":"))
        self.assertEqual(headers["Content-Digest"], f"sha-256=:{digest}:")
        self.assertIn('tag="web-bot-auth"', headers["Signature-Input"])
        self.assertIn("signature-agent", headers["Signature-Input"])
        self.assertEqual(len(signature), 64)
        signature_params = headers["Signature-Input"].removeprefix("sig1=")
        signature_agent = headers["Signature-Agent"]
        ucp_agent = headers["UCP-Agent"]
        signature_base = "\n".join(
            (
                '"@method": POST',
                '"@authority": siemsalud.myshopify.com',
                '"@path": /api/ucp/mcp',
                f'"ucp-agent": {ucp_agent}',
                f'"signature-agent";key="sig1": {signature_agent}',
                f'"idempotency-key": {headers["Idempotency-Key"]}',
                f'"content-digest": {headers["Content-Digest"]}',
                '"content-type": application/json',
                '"@signature-params": ' + signature_params,
            )
        ).encode()
        r, s = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
        key.public_key().verify(
            encode_dss_signature(r, s),
            signature_base,
            ec.ECDSA(hashes.SHA256()),
        )
        public = key.public_key().public_numbers()
        thumbprint = json.dumps(
            {
                "crv": "P-256",
                "kty": "EC",
                "x": base64.urlsafe_b64encode(public.x.to_bytes(32, "big")).rstrip(b"=").decode(),
                "y": base64.urlsafe_b64encode(public.y.to_bytes(32, "big")).rstrip(b"=").decode(),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        expected_key_id = base64.urlsafe_b64encode(
            hashlib.sha256(thumbprint).digest()
        ).rstrip(b"=").decode()
        self.assertIn(f'keyid="{expected_key_id}"', headers["Signature-Input"])

    def test_catalog_client_uses_only_advertised_read_search_tool(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = self._client(directory)
            page = {
                "structuredContent": {
                    "products": [
                        {
                            "id": "gid://shopify/Product/40017",
                            "title": "Kit de repuesto Gris para fonendoscopio Littmann",
                            "variants": [{"id": "gid://shopify/ProductVariant/40017"}],
                        }
                    ],
                    "pagination": {"has_next_page": False, "total_count": 1},
                }
            }
            with patch.object(
                client,
                "_post",
                side_effect=[{"tools": [{"name": "search_catalog"}]}, page],
            ) as post:
                products, complete = client.fetch_catalog()

        self.assertTrue(complete)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["id"], "gid://shopify/Product/40017")
        call = post.call_args_list[1].args[0]
        self.assertEqual(call["params"]["name"], "search_catalog")
        self.assertEqual(call["params"]["arguments"]["catalog"]["pagination"]["limit"], 250)
        self.assertNotIn("query", call["params"]["arguments"]["catalog"])


if __name__ == "__main__":
    unittest.main()
