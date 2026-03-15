import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "todos")
STATIC_DIR = Path(__file__).parent / "static"


class SupabaseClient:
    def __init__(self, url: str, anon_key: str, table: str):
        self.url = url
        self.anon_key = anon_key
        self.table = table

    @property
    def configured(self) -> bool:
        return bool(self.url and self.anon_key)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {self.anon_key}",
            "Content-Type": "application/json",
        }

    def list_rows(self) -> list[dict[str, Any]]:
        endpoint = f"{self.url}/rest/v1/{self.table}"
        response = httpx.get(endpoint, headers=self._headers(), params={"select": "*", "order": "id.desc"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Expected a list response from Supabase")
        return data

    def create_row(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self.url}/rest/v1/{self.table}"
        headers = self._headers() | {"Prefer": "return=representation"}
        response = httpx.post(endpoint, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            return data[0]
        raise ValueError("Unexpected insert response from Supabase")


SUPABASE = SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_TABLE)


class AppHandler(BaseHTTPRequestHandler):
    def _json_response(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path.startswith("/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
            return

        if self.path == "/api/health":
            self._json_response(
                {
                    "status": "ok",
                    "supabase_configured": SUPABASE.configured,
                    "table": SUPABASE.table,
                }
            )
            return

        if self.path == "/api/todos":
            if not SUPABASE.configured:
                self._json_response({"error": "SUPABASE_URL and SUPABASE_ANON_KEY are required."}, 500)
                return
            try:
                rows = SUPABASE.list_rows()
                self._json_response(rows)
            except Exception as exc:  # pragma: no cover
                self._json_response({"error": str(exc)}, 502)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/todos":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        if not SUPABASE.configured:
            self._json_response({"error": "SUPABASE_URL and SUPABASE_ANON_KEY are required."}, 500)
            return

        try:
            payload = self._read_json_body()
            title = str(payload.get("title", "")).strip()
            if not title:
                self._json_response({"error": "title is required"}, 400)
                return

            row = SUPABASE.create_row({"title": title, "is_done": False})
            self._json_response(row, 201)
        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON body"}, 400)
        except Exception as exc:  # pragma: no cover
            self._json_response({"error": str(exc)}, 502)

    def _serve_file(self, filename: str, content_type: str) -> None:
        file_path = STATIC_DIR / filename
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def run() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server started on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
