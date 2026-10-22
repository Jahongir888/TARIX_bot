"""
Cloudflare Tunnel (cloudflared) orqali lokal 8080-portni ochiq URL ga chiqaradi.
Ro'yxatdan o'tish va token talab qilinmaydi.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import threading
from typing import Optional

LOCAL_URL = "http://127.0.0.1:8080"
ADMIN_TOKEN = "admin123"
TRYCLOUDFLARE_RE = re.compile(
    r"https://[a-z0-9-]+\.trycloudflare\.com",
    re.IGNORECASE,
)


def build_command() -> list[str]:
    """Tizimdagi cloudflared yoki npx orqali cloudflared buyrug'ini tanlaydi."""
    cloudflared = shutil.which("cloudflared")
    if cloudflared:
        return [cloudflared, "tunnel", "--url", LOCAL_URL]

    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "cloudflared", "tunnel", "--url", LOCAL_URL]

    print(
        "Xatolik: 'cloudflared' yoki 'npx' topilmadi.\n"
        "cloudflared o'rnating yoki Node.js (npx) ni ishga tushiring."
    )
    sys.exit(1)


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
        # Ctrl+C asosiy skriptga tushsin; tunnelni o'zimiz yopamiz
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
