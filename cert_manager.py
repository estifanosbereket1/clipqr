import subprocess
from pathlib import Path


def get_cert_dir() -> Path:
    """Where generated certs live, separate from the project source folder."""
    from settings_store import get_settings_path

    cert_dir = get_settings_path().parent / "certs"
    cert_dir.mkdir(exist_ok=True)
    return cert_dir


def ensure_ca_installed() -> None:
    """
    Runs `mkcert -install` once per user to trust the local CA. Has to run
    as the real desktop user (not root), since it writes into that user's
    CA/NSS/browser trust stores -- this is why the .deb's postinst doesn't
    do it and it happens here at app startup instead.
    """
    marker = get_cert_dir() / ".ca-installed"
    if marker.exists():
        return

    result = subprocess.run(["mkcert", "-install"], capture_output=True, text=True)
    if result.returncode == 0:
        marker.touch()
    else:
        print(f"mkcert -install failed: {result.stderr}")


def regenerate_cert_for_ip(ip: str) -> tuple[str, str] | None:
    """
    Runs `mkcert <ip> localhost 127.0.0.1` to produce a fresh cert signed by
    the already-trusted local CA. Returns (cert_path, key_path) as strings,
    or None if mkcert failed (e.g. not installed, or mkcert -install never run).
    """
    cert_dir = get_cert_dir()

    result = subprocess.run(
        [
            "mkcert",
            "-cert-file",
            "cert.pem",
            "-key-file",
            "key.pem",
            ip,
            "localhost",
            "127.0.0.1",
        ],
        cwd=cert_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"mkcert failed: {result.stderr}")
        return None

    cert_path = str(cert_dir / "cert.pem")
    key_path = str(cert_dir / "key.pem")
    return cert_path, key_path


def _standalone_test():
    from settings_store import get_current_lan_ip

    ip = get_current_lan_ip()
    print(f"Regenerating cert for {ip}...")
    result = regenerate_cert_for_ip(ip)
    print(result)


if __name__ == "__main__":
    _standalone_test()
