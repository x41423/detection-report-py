from __future__ import annotations

import argparse
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reissue the HTTPS dev server certificate from an existing root CA PFX."
    )
    parser.add_argument("--root-pfx", required=True, help="Path to the root CA PFX.")
    parser.add_argument("--root-password", default="detect-report-dev", help="Password for the root PFX.")
    parser.add_argument("--server-pfx", required=True, help="Output path for the server PFX.")
    parser.add_argument("--server-password", default="detect-report-dev", help="Password for the server PFX.")
    parser.add_argument(
        "--ip",
        action="append",
        dest="ips",
        default=[],
        help="IPv4 address to include in SAN. Can be repeated.",
    )
    parser.add_argument(
        "--root-cer",
        help="Optional path to export the root CA certificate as CER/PEM-compatible DER.",
    )
    return parser.parse_args()


def unique_ipv4_addresses(values: list[str]) -> list[ipaddress.IPv4Address]:
    seen: set[str] = set()
    resolved: list[ipaddress.IPv4Address] = []
    for value in ["127.0.0.1", *values]:
        parsed = ipaddress.ip_address(value)
        if not isinstance(parsed, ipaddress.IPv4Address):
            raise ValueError(f"Only IPv4 addresses are supported here: {value}")
        key = str(parsed)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(parsed)
    return resolved


def main() -> int:
    args = parse_args()

    root_pfx_path = Path(args.root_pfx).expanduser().resolve()
    server_pfx_path = Path(args.server_pfx).expanduser().resolve()
    root_cer_path = Path(args.root_cer).expanduser().resolve() if args.root_cer else None

    root_key, root_cert, root_chain = pkcs12.load_key_and_certificates(
        root_pfx_path.read_bytes(),
        args.root_password.encode("utf-8") if args.root_password else None,
    )
    if root_key is None or root_cert is None:
        raise RuntimeError(f"Unable to load root CA keypair from {root_pfx_path}")

    ips = unique_ipv4_addresses(args.ips)
    primary_ip = str(next((ip for ip in ips if str(ip) != "127.0.0.1"), ips[0]))

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, primary_ip)])

    san_values: list[x509.GeneralName] = [x509.DNSName("localhost")]
    san_values.extend(x509.IPAddress(ip) for ip in ips)

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(root_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=730))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(san_values), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
    )
    server_cert = builder.sign(private_key=root_key, algorithm=hashes.SHA256())

    server_pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=f"DetectionReport Dev HTTPS ({primary_ip})".encode("utf-8"),
        key=server_key,
        cert=server_cert,
        cas=[root_cert, *(root_chain or [])],
        encryption_algorithm=serialization.BestAvailableEncryption(args.server_password.encode("utf-8")),
    )
    server_pfx_path.parent.mkdir(parents=True, exist_ok=True)
    server_pfx_path.write_bytes(server_pfx_bytes)

    if root_cer_path is not None:
        root_cer_path.parent.mkdir(parents=True, exist_ok=True)
        root_cer_path.write_bytes(root_cert.public_bytes(serialization.Encoding.DER))

    print(f"server_pfx={server_pfx_path}")
    print("sans=localhost," + ",".join(str(ip) for ip in ips))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
