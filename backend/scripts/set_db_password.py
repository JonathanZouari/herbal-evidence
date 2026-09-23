"""Set a (reset) Supabase DB password everywhere this machine needs it, without it ever being printed.

Run it YOURSELF in a terminal (it prompts with hidden input):

    cd backend
    uv run python scripts/set_db_password.py            # updates backend/.env + supabase/.env, tests the connection
    uv run python scripts/set_db_password.py --railway  # ...and sets DATABASE_URL on Railway staging/backend

Get the password from: Supabase Dashboard -> Project Settings -> Database -> Reset database password.
"""

import argparse
import getpass
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV = ROOT / "backend" / ".env"
SUPABASE_ENV = ROOT / "supabase" / ".env"
POOLER_FILE = ROOT / "supabase" / ".temp" / "pooler-url"


def set_key(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out, done = [], False
    for line in lines:
        if re.match(rf"^\s*{re.escape(key)}\s*=", line):
            out.append(f"{key}={value}")
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


def current_url() -> str:
    for line in BACKEND_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].split(" #")[0].strip()
    return POOLER_FILE.read_text(encoding="utf-8").strip()


def with_password(url: str, password: str) -> str:
    p = urlsplit(url)
    host = p.hostname + (f":{p.port}" if p.port else "")
    return urlunsplit((p.scheme, f"{p.username}:{quote(password, safe='')}@{host}", p.path, p.query, p.fragment))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--railway", action="store_true", help="also set DATABASE_URL on Railway (staging, backend)")
    args = ap.parse_args()

    password = getpass.getpass("New Supabase DB password (hidden): ").strip()
    if not password:
        print("no password given; nothing changed")
        return 1
    url = with_password(current_url(), password)

    import psycopg
    try:
        with psycopg.connect(url, connect_timeout=15) as c:
            c.execute("select 1")
    except Exception as e:  # message never contains the password
        print(f"connection FAILED ({type(e).__name__}); nothing changed. Check the password and try again.")
        return 1
    print("connection OK")

    set_key(BACKEND_ENV, "DATABASE_URL", url)
    set_key(SUPABASE_ENV, "SUPABASE_DB_PASSWORD", password)
    print(f"updated {BACKEND_ENV.relative_to(ROOT)} (DATABASE_URL) and {SUPABASE_ENV.relative_to(ROOT)} (SUPABASE_DB_PASSWORD)")

    if args.railway:
        # value passed as an argument to the local railway CLI only (not echoed)
        exe = shutil.which("railway")
        if not exe:
            print("railway CLI not found; set DATABASE_URL on Railway manually")
            return 0
        r = subprocess.run([exe, "variables", "-e", "staging", "-s", "backend", "--set", f"DATABASE_URL={url}"],
                           capture_output=True, text=True, cwd=ROOT)
        print("railway staging DATABASE_URL:", "set" if r.returncode == 0 else f"FAILED ({r.stderr.strip()[:200]})")
    print("done. Remember to update the other machine's .env files too.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
