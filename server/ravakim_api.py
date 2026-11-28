#!/usr/bin/env python3
"""Storage API for the רווקים לכולם Streamlit calendar.

Listens on 127.0.0.1 only; nginx exposes it at https://confessions.party/ravakim-api/.
Every request must carry `Authorization: Bearer <RAVAKIM_API_TOKEN>` — only the
Streamlit app has that token, so nobody else can read or write.

  GET    /people          -> {"people": {id: {name, color, marks}}}
  PUT    /people/<id>     body {name, color, marks}  (create or replace)
  DELETE /people/<id>
"""
import hmac
import json
import os
import re
import sqlite3
import threading
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("RAVAKIM_API_TOKEN", "")
DB_PATH = os.environ.get("RAVAKIM_DB", "ravakim.db")
PORT = int(os.environ.get("RAVAKIM_PORT", "5020"))

FIRST, LAST = date(2027, 1, 1), date(2027, 5, 31)
ID_RE = re.compile(r"p[0-9a-f]{10}")
COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")
MAX_PEOPLE, MAX_BODY = 200, 64 * 1024

LOCK = threading.Lock()


def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS people (id TEXT PRIMARY KEY, name TEXT NOT NULL,"
                " color TEXT NOT NULL, marks TEXT NOT NULL, updated TEXT NOT NULL)")
    return con


def clean_person(body):
    if not isinstance(body, dict):
        raise ValueError("body must be an object")
    name = str(body.get("name", "")).strip()
    if not 1 <= len(name) <= 24:
        raise ValueError("name must be 1-24 characters")
    color = body.get("color")
    if not isinstance(color, str) or not COLOR_RE.fullmatch(color):
        raise ValueError("color must be #rrggbb")
    marks = body.get("marks", {})
    if not isinstance(marks, dict):
        raise ValueError("marks must be an object")
    out = {}
    for k, v in marks.items():
        d = date.fromisoformat(k)  # ValueError on junk
        if not FIRST <= d <= LAST:
            raise ValueError(f"date out of range: {k}")
        if not isinstance(v, str) or len(v) > 60:
            raise ValueError("note must be text up to 60 characters")
        out[d.isoformat()] = v.strip()
    return name, color, out


class Handler(BaseHTTPRequestHandler):
    server_version = "ravakim-api"
    sys_version = ""

    def log_message(self, fmt, *args):  # keep journal quiet except errors
        pass

    def reply(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authed(self):
        got = self.headers.get("Authorization", "")
        if hmac.compare_digest(got.encode(), f"Bearer {TOKEN}".encode()):
            return True
        self.reply(401, {"error": "unauthorized"})
        return False

    def person_id(self):
        m = re.fullmatch(r"/people/([^/]+)", self.path)
        if not m or not ID_RE.fullmatch(m.group(1)):
            self.reply(404, {"error": "not found"})
            return None
        return m.group(1)

    def do_GET(self):
        if not self.authed():
            return
        if self.path != "/people":
            return self.reply(404, {"error": "not found"})
        with LOCK, db() as con:
            rows = con.execute("SELECT id, name, color, marks FROM people").fetchall()
        self.reply(200, {"people": {i: {"name": n, "color": c, "marks": json.loads(m)} for i, n, c, m in rows}})

    def do_PUT(self):
        if not self.authed():
            return
        pid = self.person_id()
        if not pid:
            return
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            return self.reply(413, {"error": "body too large or empty"})
        try:
            name, color, marks = clean_person(json.loads(self.rfile.read(length)))
        except (ValueError, TypeError) as e:
            return self.reply(400, {"error": str(e)})
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with LOCK, db() as con:
            exists = con.execute("SELECT 1 FROM people WHERE id=?", (pid,)).fetchone()
            if not exists and con.execute("SELECT COUNT(*) FROM people").fetchone()[0] >= MAX_PEOPLE:
                return self.reply(409, {"error": "calendar is full"})
            con.execute("INSERT INTO people (id, name, color, marks, updated) VALUES (?,?,?,?,?) "
                        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, color=excluded.color, "
                        "marks=excluded.marks, updated=excluded.updated",
                        (pid, name, color, json.dumps(marks, ensure_ascii=False), now))
        self.reply(200, {"ok": True})

    def do_DELETE(self):
        if not self.authed():
            return
        pid = self.person_id()
        if not pid:
            return
        with LOCK, db() as con:
            con.execute("DELETE FROM people WHERE id=?", (pid,))
        self.reply(200, {"ok": True})

    def do_POST(self):
        self.reply(405, {"error": "method not allowed"})


def main():
    if len(TOKEN) < 32:
        raise SystemExit("RAVAKIM_API_TOKEN must be set (32+ chars)")
    db().close()
    print(f"ravakim-api on 127.0.0.1:{PORT}, db={DB_PATH}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
