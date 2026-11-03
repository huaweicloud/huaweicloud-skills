"""Transport server template — WSS communication loop with no inference
logic.

This is the full reference implementation for SKILL.md "Step 3: Create the
Transport Server". Copy this file into the project's deployment directory
and adjust it per the target protocol's communication details.

Responsibilities (only moves bytes, no inference):
1. Send metadata as the first frame after connect (handshake)
2. recv -> adapter.infer() -> send loop
3. Attach per-connection server_timing
4. On error, send a traceback string and close with INTERNAL_ERROR

Wire contract (see SKILL.md "Fixed Protocol Contract"):
- Transport: WSS (WebSocket over TLS)
- Serialization: msgpack (+ numpy extension)
"""

import datetime
import logging
import os
import ssl
import tempfile
import time
import traceback

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from websockets.exceptions import ConnectionClosed

INTERNAL_ERROR = 1011


class TransportServer:
    def __init__(self, adapter, host="0.0.0.0", port=8000,
                 idle_timeout=-1, metadata=None):
        self._adapter = adapter
        self._host = host
        self._port = port
        self._idle_timeout = idle_timeout
        self._metadata = metadata or getattr(adapter, "metadata", {})
        self._ssl_context = self._create_ssl_context()

    def generate_self_signed_cert(self):
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=3072,
        )
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Huawei"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3600))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName("localhost")]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pem") as f_key:
            f_key.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
            key_path = f_key.name

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pem") as f_cert:
            f_cert.write(cert.public_bytes(serialization.Encoding.PEM))
            cert_path = f_cert.name

        return cert_path, key_path

    def _create_ssl_context(self):
        cert_file, key_file = self.generate_self_signed_cert()
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)

        for path in (cert_file, key_file):
            if path and os.path.exists(path):
                os.unlink(path)

        ssl_context.set_ciphers(
            "ECDHE-ECDSA-AES256-GCM-SHA384:"
            "ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-CHACHA20-POLY1305:"
        )
        return ssl_context

    async def _handler(self, websocket):
        packer = create_serializer()  # msgpack + numpy extension

        # 1. Handshake: send metadata as the first frame
        await websocket.send(packer.pack(self._metadata))

        prev_total_time = 0.0  # per-connection timing state

        while True:
            try:
                t_start = time.time()

                # 2. Receive observation (no envelope, no routing)
                obs = unpack(await websocket.recv())

                # 3. Infer
                infer_start = time.time()
                action = self._adapter.infer(obs)
                infer_ms = (time.time() - infer_start) * 1000

                # 4. Attach timing (per-connection, not per-inference)
                action["server_timing"] = {
                    "infer_ms": float(infer_ms),
                    "prev_total_ms": float(prev_total_time * 1000),
                }
                prev_total_time = time.time() - t_start

                # 5. Send response (no wrapper, no envelope)
                await websocket.send(packer.pack(action))

            except ConnectionClosed:
                break
            except Exception:
                # Error contract: send the traceback string, close with
                # INTERNAL_ERROR
                logging.exception("Handler error")
                await websocket.send(traceback.format_exc())
                await websocket.close(code=INTERNAL_ERROR)
                raise

    def serve_forever(self):
        """Start the WSS server (TLS provided by _ssl_context)."""
        import asyncio

        import websockets.asyncio.server

        async def _run():
            async with websockets.asyncio.server.serve(
                self._handler,
                self._host,
                self._port,
                ssl=self._ssl_context,
                compression=None,
                max_size=None,
            ) as server:
                await server.serve_forever()

        asyncio.run(_run())


# --- Serialization helpers (adjust per the actually used protocol) -------
#
# Serialization format: plain msgpack + numpy extension (same as the
# reference test_openpi.py).
# - np.ndarray -> {"__ndarray__": True, "data": bytes, "dtype": str, "shape": tuple}
# - np.generic -> {"__npgeneric__": True, "data": scalar, "dtype": str}
# Both ends (server/client) MUST use the same pack_array/unpack_array.

import functools

import msgpack
import numpy as np


def pack_array(obj):
    """msgpack.Packer default: turn numpy objects into serializable dicts."""
    if (isinstance(obj, (np.ndarray, np.generic))) and obj.dtype.kind in ("V", "O", "c"):
        raise ValueError(f"Unsupported dtype: {obj.dtype}")

    if isinstance(obj, np.ndarray):
        return {
            b"__ndarray__": True,
            b"data": obj.tobytes(),
            b"dtype": obj.dtype.str,
            b"shape": obj.shape,
        }

    if isinstance(obj, np.generic):
        return {
            b"__npgeneric__": True,
            b"data": obj.item(),
            b"dtype": obj.dtype.str,
        }

    return obj


def unpack_array(obj):
    """msgpack object_hook: restore __ndarray__/__npgeneric__ dicts."""
    if b"__ndarray__" in obj:
        return np.ndarray(buffer=obj[b"data"], dtype=np.dtype(obj[b"dtype"]), shape=obj[b"shape"])

    if b"__npgeneric__" in obj:
        return np.dtype(obj[b"dtype"]).type(obj[b"data"])

    return obj


Packer = functools.partial(msgpack.Packer, default=pack_array)
unpackb = functools.partial(msgpack.unpackb, object_hook=unpack_array)


def create_serializer():
    """Create a msgpack + numpy extension packer."""
    return Packer()


def unpack(data: bytes):
    """Deserialize received data."""
    return unpackb(data)
