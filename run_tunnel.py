"""
Cloudflare Tunnel (cloudflared) orqali lokal 8080-portni ochiq URL ga chiqaradi.
Ro'yxatdan o'tish va token talab qilinmaydi.

Agar tizimda cloudflared / npx bo'lmasa, skript o'zi
rasmiy cloudflared.exe ni loyiha papkasiga yuklab oladi.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Optional

LOCAL_URL = "http://127.0.0.1:8080"
ADMIN_TOKEN = "admin123"
SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_BIN = SCRIPT_DIR / ("cloudflared.exe" if os.name == "nt" else "cloudflared")

TRYCLOUDFLARE_RE = re.compile(
    r"https://[a-z0-9-]+\.trycloudflare\.com",
    re.IGNORECASE,
)

# Cloudflare rasmiy release (GitHub)
DOWNLOAD_URLS = {
    ("Windows", "AMD64"): (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-windows-amd64.exe"
    ),
    ("Windows", "ARM64"): (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-windows-arm64.exe"
    ),
    ("Linux", "x86_64"): (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-linux-amd64"
    ),
    ("Linux", "aarch64"): (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-linux-arm64"
    ),
    ("Darwin", "x86_64"): (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-darwin-amd64.tgz"
    ),
    ("Darwin", "arm64"): (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-darwin-arm64.tgz"
    ),
}


def download_cloudflared() -> Path:
    """Rasmiy cloudflared binarini loyiha papkasiga yuklab oladi."""
    system = platform.system()
    machine = platform.machine()
    # Windows ba'zan 'AMD64', ba'zan 'x86_64' deb qaytaradi
    if machine.lower() in {"x86_64", "amd64"}:
        machine = "AMD64" if system == "Windows" else "x86_64"
    elif machine.lower() in {"aarch64", "arm64"}:
        machine = "ARM64" if system == "Windows" else (
            "arm64" if system == "Darwin" else "aarch64"
        )

    url = DOWNLOAD_URLS.get((system, machine))
    if not url:
        print(
            f"Xatolik: bu platforma uchun avtomatik yuklash yo'q ({system}/{machine}).\n"
            "Qo'lda cloudflared o'rnating: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
        )
        sys.exit(1)

    if url.endswith(".tgz"):
        print(
            "macOS uchun .tgz arxivini qo'lda ochib cloudflared ni PATH ga qo'ying,\n"
            f"yoki shu URL dan yuklang:\n  {url}"
        )
        sys.exit(1)

    print("cloudflared topilmadi. Rasmiy binar yuklanmoqda...")
    print(f"  {url}")
    try:
        urllib.request.urlretrieve(url, LOCAL_BIN)
    except Exception as exc:
        print(f"Yuklab bo'lmadi: {exc}")
        sys.exit(1)

    if os.name != "nt":
        LOCAL_BIN.chmod(LOCAL_BIN.stat().st_mode | 0o111)

    print(f"Tayyor: {LOCAL_BIN}\n")
    return LOCAL_BIN


def resolve_cloudflared() -> str:
    """Ishga tushirish uchun cloudflared yo'lini topadi (yoki yuklab oladi)."""
    found = shutil.which("cloudflared")
    if found:
        return found

    if LOCAL_BIN.is_file():
        return str(LOCAL_BIN)

    npx = shutil.which("npx")
    if npx:
        return "__npx__"

    return str(download_cloudflared())


def build_command() -> list[str]:
    binary = resolve_cloudflared()
    if binary == "__npx__":
        return [shutil.which("npx") or "npx", "--yes", "cloudflared", "tunnel", "--url", LOCAL_URL]
    return [binary, "tunnel", "--url", LOCAL_URL]


def print_public_urls(base_url: str) -> None:
    base = base_url.rstrip("/")
    admin_url = f"{base}/admin?token={ADMIN_TOKEN}"
    print("\n" + "=" * 62)
    print("SIZNING TELEFON UCHUN MINI APP VA ADMIN HAVOLANGIZ:")
    print(admin_url)
    print("-" * 62)
    print(f"Mini App (asosiy): {base}")
    print("=" * 62)
    print("Tunnel ishlayapti. To'xtatish uchun Ctrl+C bosing.\n")


def stream_output(pipe, url_found: threading.Event) -> None:
    """cloudflared chiqishidan trycloudflare URL ni ajratib oladi."""
    try:
        for raw in iter(pipe.readline, b""):
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace")
            sys.stdout.write(line)
            sys.stdout.flush()

            if not url_found.is_set():
                match = TRYCLOUDFLARE_RE.search(line)
                if match:
                    url_found.set()
                    print_public_urls(match.group(0))
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def main() -> None:
    cmd = build_command()
    print(f"Tunnel ishga tushirilmoqda:\n  {' '.join(cmd)}\n")

    popen_kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "bufsize": 0,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    process: Optional[subprocess.Popen] = None
    url_found = threading.Event()

    try:
        process = subprocess.Popen(cmd, **popen_kwargs)
        reader = threading.Thread(
            target=stream_output,
            args=(process.stdout, url_found),
            daemon=True,
        )
        reader.start()

        while True:
            try:
                code = process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                continue

            if not url_found.is_set():
                print(
                    "\nTunnel URL topilmadi. cloudflared loglarini tekshiring "
                    "yoki lokal server 8080-portda ishlayotganini tasdiqlang."
                )
            sys.exit(code or 0)

    except KeyboardInterrupt:
        print("\nTunnel to'xtatilmoqda...")
    finally:
        if process is not None:
            stop_process(process)
        print("Tunnel yopildi.")


if __name__ == "__main__":
    main()
