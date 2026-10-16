"""Native Kontoanmeldung; Agentenausführung bleibt ausschließlich im SDK."""

import hmac
import http.client
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time
from contextlib import closing
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

PROVIDERS = {
    "codex": {
        "login": ("codex", "login", "--device-auth"),
        "status": ("codex", "login", "status"),
        "mode": "device",
    },
    "claude-code": {
        "login": ("claude", "auth", "login", "--claudeai"),
        "status": ("claude", "auth", "status", "--json"),
        "mode": "code",
    },
    "opencode": {
        "login": ("opencode", "console", "login", "--pure"),
        "mode": "device",
    },
    "kiro": {
        "login": ("kiro-cli", "login"),
        "status": ("kiro-cli", "whoami", "--format", "json"),
        "mode": "callback",
    },
}
HOSTS = {
    "codex": {"auth.openai.com"},
    "opencode": {"opencode.ai"},
    "claude-code": {
        "claude.ai",
        "claude.com",
        "platform.claude.com",
        "console.anthropic.com",
    },
    "kiro": {"app.kiro.dev"},
}
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
LOGIN_TIMEOUT = 900


def login_challenge(provider, output):
    text = ANSI.sub("", output)
    urls = re.findall(r"https://[^\s<>\x1b]+", text)
    url = next(
        (value for value in urls if urlsplit(value).hostname in HOSTS[provider]), None
    )
    code_text = re.sub(r"https://[^\s<>\x1b]+", "", text)
    code = (
        None
        if provider in ("claude-code", "kiro")
        else re.search(
            r"(?<![\w/-])[A-Za-z0-9]{4}-[A-Za-z0-9]{4,6}(?![\w/-])", code_text
        )
    )
    return {"url": url, "user_code": code.group() if code else None}


class LoginService:
    def __init__(self, home: Path, on_complete=None):
        self.home = home
        self.on_complete = on_complete
        self.jobs = {}
        self.lock = threading.RLock()

    def environment(self):
        # Login must not silently select API billing or inherit the Mac account.
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            in (
                "PATH",
                "LANG",
                "LC_ALL",
                "SSL_CERT_FILE",
                "SSL_CERT_DIR",
                "HTTPS_PROXY",
                "HTTP_PROXY",
                "NO_PROXY",
            )
        }
        env.update(HOME=str(self.home), BROWSER="true", NO_COLOR="1", TERM="dumb")
        return env

    def provider(self, provider):
        if provider not in PROVIDERS:
            raise ValueError("Für diesen Agenten ist kein Browser-Login eingerichtet")
        return PROVIDERS[provider]

    def status(self, provider):
        spec = self.provider(provider)
        if provider == "opencode":
            available = (
                shutil.which(spec["login"][0], path=self.environment().get("PATH"))
                is not None
            )
            database = self.home / ".local/share/opencode/opencode.db"
            try:
                with closing(
                    sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
                ) as db:
                    connected = bool(
                        db.execute(
                            "SELECT 1 FROM account a JOIN account_state s "
                            "ON s.active_account_id = a.id WHERE s.id = 1 "
                            "AND a.url = 'https://opencode.ai/console' "
                            "AND length(a.refresh_token) > 0 LIMIT 1"
                        ).fetchone()
                    )
            except sqlite3.Error:
                connected = False
            return {"available": available, "connected": connected}
        try:
            result = subprocess.run(
                spec["status"], env=self.environment(), capture_output=True, timeout=15
            )
        except FileNotFoundError:
            return {"available": False, "connected": False}
        except (OSError, subprocess.TimeoutExpired):
            return {"available": True, "connected": False}
        output = (result.stdout + result.stderr).decode(errors="replace")
        connected = False
        if provider == "claude-code":
            try:
                connected = json.loads(result.stdout).get("loggedIn") is True
            except (ValueError, AttributeError):
                pass
        elif provider == "codex":
            connected = result.returncode == 0 and "chatgpt" in output.lower()
        else:
            connected = result.returncode == 0 and bool(result.stdout.strip())
        return {"available": True, "connected": connected}

    def current(self, provider):
        spec = self.provider(provider)
        with self.lock:
            job = self.jobs.get(provider)
            if not job:
                return {"state": "idle", "mode": spec["mode"]}
            if job["state"] == "pending" and job.get("browser_file"):
                try:
                    challenge = login_challenge(
                        provider, job["browser_file"].read_text()
                    )
                    if challenge["url"]:
                        job["challenge"].update(challenge)
                except OSError:
                    pass
            if (
                job["state"] == "pending"
                and not job["challenge"]["url"]
                and time.time() > job["expires_at"] - LOGIN_TIMEOUT + 60
            ):
                return self.cancel(provider, job["id"], "failed")
            return {
                "id": job["id"],
                "state": job["state"],
                "mode": spec["mode"],
                "expires_at": job["expires_at"],
                **job["challenge"],
            }

    def start(self, provider):
        spec = self.provider(provider)
        with self.lock:
            if self.jobs.get(provider, {}).get("state") == "pending":
                return self.current(provider)
            self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
            browser = None
            env = self.environment()
            if spec["mode"] == "callback":
                browser = tempfile.TemporaryDirectory(prefix="cliscade-login-")
                env["BROWSER"] = (
                    shutil.which("cliscade-login-browser") or "cliscade-login-browser"
                )
                env["CLISCADE_LOGIN_URL_FILE"] = str(Path(browser.name) / "url")
            try:
                process = subprocess.Popen(
                    spec["login"],
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            except OSError as error:
                if browser:
                    browser.cleanup()
                raise RuntimeError(
                    "Login-CLI fehlt oder kann nicht gestartet werden"
                ) from error
            job = {
                "id": str(uuid4()),
                "state": "pending",
                "process": process,
                "output": "",
                "browser": browser,
                "browser_file": Path(browser.name) / "url" if browser else None,
                "challenge": {"url": None, "user_code": None},
                "expires_at": time.time() + LOGIN_TIMEOUT,
            }
            self.jobs[provider] = job
            timer = threading.Timer(
                LOGIN_TIMEOUT, self.cancel, args=(provider, job["id"], "expired")
            )
            timer.daemon = True
            job["timer"] = timer
            timer.start()
            threading.Thread(
                target=self.read, args=(provider, job), daemon=True
            ).start()
            return self.current(provider)

    def read(self, provider, job):
        process = job["process"]
        try:
            while chunk := process.stdout.read1(4096):
                with self.lock:
                    if job["state"] == "pending":
                        job["output"] = (
                            job["output"] + chunk.decode(errors="replace")
                        )[-32768:]
                        for key, value in login_challenge(
                            provider, job["output"]
                        ).items():
                            if value:
                                job["challenge"][key] = value
            code = process.wait()
            connected = code == 0 and self.status(provider)["connected"]
            if connected and self.on_complete:
                try:
                    self.on_complete(provider, self.home)
                except (OSError, RuntimeError):
                    connected = False
            with self.lock:
                if job["state"] == "pending":
                    job["state"] = "completed" if connected else "failed"
                if connected:
                    directory = self.home / ".cliscade-accounts"
                    directory.mkdir(mode=0o700, exist_ok=True)
                    (directory / provider).touch(mode=0o600)
                job["output"] = ""
                job["challenge"] = {"url": None, "user_code": None}
        finally:
            job["timer"].cancel()
            process.stdout.close()
            process.stdin.close()
            if job.get("browser"):
                job["browser"].cleanup()

    def submit(self, provider, job_id, code):
        with self.lock:
            job = self.jobs.get(provider)
            if (
                not job
                or job["id"] != job_id
                or job["state"] != "pending"
                or self.provider(provider)["mode"] not in ("code", "callback")
            ):
                raise ValueError(
                    "Anmeldung fehlt, ist abgelaufen oder erwartet keinen Code"
                )
            if self.provider(provider)["mode"] == "callback":
                self.callback(job, code)
                return self.current(provider)
            if not re.fullmatch(r"[A-Za-z0-9_#./+=:-]{1,4096}", code):
                raise ValueError("Ungültiger Anmeldecode")
            try:
                job["process"].stdin.write((code + "\n").encode())
                job["process"].stdin.flush()
            except (OSError, ValueError) as error:
                raise ValueError(
                    "Anmeldung wurde beendet; bitte neu starten"
                ) from error
            return self.current(provider)

    def callback(self, job, value):
        portal = urlsplit(job["challenge"]["url"] or "")
        params = parse_qs(portal.query)
        expected = urlsplit(params.get("redirect_uri", [""])[0])
        actual = urlsplit(value)
        query = parse_qs(actual.query)
        if (
            expected.scheme != "http"
            or expected.hostname not in ("localhost", "127.0.0.1", "::1")
            or not expected.port
            or (actual.scheme, actual.netloc, actual.path.rstrip("/"))
            != (expected.scheme, expected.netloc, expected.path.rstrip("/"))
            or not query.get("code")
            or not params.get("state")
            or not hmac.compare_digest(query.get("state", [""])[0], params["state"][0])
        ):
            raise ValueError(
                "Rückleitungsadresse gehört nicht zu dieser Kiro-Anmeldung"
            )
        connection = http.client.HTTPConnection("127.0.0.1", expected.port, timeout=15)
        try:
            connection.request("GET", f"{expected.path or '/'}?{actual.query}")
            if connection.getresponse().status >= 400:
                raise ValueError("Kiro hat die Rückleitung abgewiesen")
        except (OSError, http.client.HTTPException) as error:
            raise ValueError(
                "Kiro hat die Rückleitung abgewiesen; Anmeldung neu starten"
            ) from error
        finally:
            connection.close()

    def cancel(self, provider, job_id, state="cancelled"):
        with self.lock:
            self.provider(provider)
            job = self.jobs.get(provider)
            if not job or job["id"] != job_id:
                raise ValueError("Anmeldung nicht gefunden")
            if job["state"] == "pending":
                job["state"] = state
                job["output"] = ""
                job["challenge"] = {"url": None, "user_code": None}
                try:
                    os.killpg(job["process"].pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    job["process"].wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(job["process"].pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    job["process"].wait(timeout=2)
                job["timer"].cancel()
            return self.current(provider)

    def close(self):
        for provider, job in list(self.jobs.items()):
            self.cancel(provider, job["id"])


def capture_browser():
    """Übergibt ausschließlich die native Portal-URL an den eigenen Login-Vorgang."""
    import sys

    target = Path(os.environ["CLISCADE_LOGIN_URL_FILE"])
    url = sys.argv[1]
    if urlsplit(url).scheme != "https" or urlsplit(url).hostname != "app.kiro.dev":
        raise SystemExit(1)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(url)
