from __future__ import annotations

import argparse
import atexit
import shutil
import sys
import tempfile
from pathlib import Path

import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the backend over HTTPS using a PFX certificate.")
    parser.add_argument("--pfx-path", required=True, help="Path to the .pfx certificate bundle.")
    parser.add_argument("--pfx-password", default="detect-report-dev", help="Passphrase for the .pfx bundle.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    parser.add_argument("--app", default="backend.main:app", help="ASGI app import path.")
    return parser.parse_args()


def write_pem_files_from_pfx(*, pfx_path: Path, password: str) -> tuple[Path, Path, Path]:
    pfx_bytes = pfx_path.read_bytes()
    private_key, certificate, extra_certificates = pkcs12.load_key_and_certificates(
        pfx_bytes,
        password.encode("utf-8") if password else None,
    )
    if private_key is None or certificate is None:
        raise RuntimeError(f"Failed to extract private key and certificate from {pfx_path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="https-backend-", dir=ROOT_DIR / ".runtime"))
    cert_path = temp_dir / "server-cert.pem"
    key_path = temp_dir / "server-key.pem"

    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    if extra_certificates:
        for item in extra_certificates:
            cert_pem += item.public_bytes(serialization.Encoding.PEM)
    cert_path.write_bytes(cert_pem)

    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path.write_bytes(key_pem)
    return temp_dir, cert_path, key_path


def main() -> int:
    args = parse_args()
    pfx_path = Path(args.pfx_path).expanduser().resolve()
    if not pfx_path.exists():
        raise FileNotFoundError(f"PFX certificate not found: {pfx_path}")

    runtime_root = ROOT_DIR / ".runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    temp_dir, cert_path, key_path = write_pem_files_from_pfx(pfx_path=pfx_path, password=args.pfx_password)
    atexit.register(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

    uvicorn.run(
        args.app,
        host=args.host,
        port=args.port,
        ssl_certfile=str(cert_path),
        ssl_keyfile=str(key_path),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
