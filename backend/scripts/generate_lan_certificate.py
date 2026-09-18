from __future__ import annotations

import argparse
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate(hosts: list[str], output: Path) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    cert_path, key_path = output / "server.crt", output / "server.key"
    if cert_path.exists() or key_path.exists():
        raise FileExistsError("Certificate/key already exist; remove them explicitly to replace the trust pin")
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "GoldNest LAN")])
    names = []
    for host in hosts:
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            names.append(x509.DNSName(host))
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName(names), critical=False)
            .sign(key, hashes.SHA256()))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", action="append", required=True, help="LAN IPv4 address or hostname; repeat as needed")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "certs")
    args = parser.parse_args()
    crt, key = generate(args.host, args.output)
    print(f"Certificate: {crt}\nPrivate key: {key}")
    print(f"SHA-256 certificate fingerprint: {x509.load_pem_x509_certificate(crt.read_bytes()).fingerprint(hashes.SHA256()).hex()}")

