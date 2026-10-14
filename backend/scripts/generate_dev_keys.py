"""
Development Key Generation Utility for LabOS Sentinel.
Generates an isolated Ed25519 keypair for local development and testing.

SAFETY PRECAUTIONS:
1. Refuses to run if ENVIRONMENT is set to 'production'.
2. Refuses to overwrite existing key without explicit --force flag.
3. Sets restrictive 0600 file permissions on POSIX systems.
4. Outputs the public key in hex format for easy registration.
5. Never commits key material to version control (.keys/ is in .gitignore).

Usage:
    python scripts/generate_dev_keys.py [--force] [--key-id KEY_ID] [--out-file PATH]
"""

import argparse
import os
import stat
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cryptography.hazmat.primitives.asymmetric import ed25519
from app.core.config import settings


def generate_dev_key(force: bool = False, key_id: str = None, out_path: str = None) -> None:
    # 1. Enforce safety check against production environment
    if settings.ENVIRONMENT.lower() == "production":
        print(
            "ERROR: generate_dev_keys.py cannot be executed in a production environment!",
            file=sys.stderr,
        )
        print("Production keys must be managed through secure KMS/Vault infrastructure.", file=sys.stderr)
        sys.exit(1)

    effective_key_id = key_id or settings.CERTIFICATE_KEY_ID or "labos-sentinel-dev-2026"
    dest_path = out_path or os.path.join(".keys", "dev_ed25519_private.key")
    abs_dest = os.path.abspath(dest_path)

    # 2. Check for overwrite without --force
    if os.path.exists(abs_dest) and not force:
        print(f"Key file already exists at '{abs_dest}'.")
        print("Use --force to overwrite if you intentionally want to generate a new development key.")
        sys.exit(1)

    os.makedirs(os.path.dirname(abs_dest), exist_ok=True)

    # 3. Generate Ed25519 private key
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes_raw()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes_raw()

    # 4. Save private key with restrictive permissions
    with open(abs_dest, "w", encoding="utf-8") as f:
        f.write(private_bytes.hex())

    if os.name != "nt":
        try:
            os.chmod(abs_dest, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    pub_hex = public_bytes.hex()
    print("=" * 60)
    print("LabOS Sentinel - Development Ed25519 Key Generated Successfully")
    print("=" * 60)
    print(f"Key ID:             {effective_key_id}")
    print(f"Private Key Path:   {abs_dest}")
    print(f"Public Key (Hex):   {pub_hex}")
    print(f"Algorithm:          ED25519-SHA256")
    print("=" * 60)
    print("Add this public key to your .env or database to verify certificates:")
    print(f'CERTIFICATE_TRUSTED_PUBLIC_KEYS=\'{{"{effective_key_id}": "{pub_hex}"}}\'')
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Ed25519 development key for LabOS Sentinel")
    parser.add_argument("--force", action="store_true", help="Overwrite existing key file")
    parser.add_argument("--key-id", type=str, default=None, help="Custom key ID")
    parser.add_argument("--out-file", type=str, default=None, help="Output path for private key")
    args = parser.parse_args()

    generate_dev_key(force=args.force, key_id=args.key_id, out_path=args.out_file)
