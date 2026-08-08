#!/usr/bin/env python3
"""Serve viewer/ and answer questions about the notes.

GET  /...   Static files from viewer/ only. config.json and everything else
            in the project root is outside this directory and unreachable.
POST /chat  {"question": str, "session_id": str|null} -> answers the question
            by finding the most relevant notes and calling the Anthropic
            Messages API. Conversation history is kept server-side, per
            session_id, so follow-up questions have context.

The API key and model both come from config.json in the project root, which
sits outside viewer/ and is therefore never served to the browser - it is
read directly off disk by this process only. Paste your key into the
"api_key" field of config.json before starting the server.
"""
import http.server
import json
import os
import re
import secrets
import threading
import urllib.error
import urllib.request
from pathlib import Path

PORT = int(os.environ.get("PORT", 4700))
ROOT_DIR = Path(__file__).resolve().parent
VIEWER_DIR = ROOT_DIR / "viewer"
CONFIG_PATH = ROOT_DIR / "config.json"
GRAPH_DATA_PATH = VIEWER_DIR / "graph-data.js"

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
MAX_TOKENS = 500
REQUEST_TIMEOUT_SECONDS = 60

TOP_N = 6
MAX_HISTORY_MESSAGES = 20  # 10 question/answer turns

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "on", "at", "for", "with", "and", "or", "but", "if",
    "do", "does", "did", "what", "why", "how", "who", "which", "when",
    "where", "my", "me", "i", "you", "your", "it", "its", "this", "that",
    "these", "those", "about", "from", "as", "so", "can", "could", "should",
    "would", "will", "there", "their", "them", "than", "then", "tell",
}

SESSIONS = {}  # session_id -> list of {"role": ..., "content": ...} dicts
SESSIONS_LOCK = threading.Lock()


class ChatError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def load_config():
    if not CONFIG_PATH.exists():
        raise ChatError(500, "config.json not found in the project root")
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise ChatError(500, "config.json is not valid JSON")


def load_api_key(config):
    api_key = config.get("api_key")
    if not api_key or api_key == "PUT-YOUR-KEY-HERE":
        raise ChatError(
            400,
            "No API key configured. Paste your Anthropic API key into the "
            "\"api_key\" field of config.json (project root) and restart "
            "the server.",
        )
    return api_key


def load_model(config):
    return config.get("model") or DEFAULT_MODEL


def load_notes():
    if not GRAPH_DATA_PATH.exists():
        raise ChatError(500, "viewer/graph-data.js not found - run build.py first")
    raw = GRAPH_DATA_PATH.read_text(encoding="utf-8")
    prefix = "window.GRAPH = "
    if not raw.startswith(prefix):
        raise ChatError(500, "viewer/graph-data.js is not in the expected format")
    data = json.loads(raw[len(prefix):].rstrip().rstrip(";"))
    return data.get("nodes", [])


def tokenize(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1 and w not in STOPWORDS]


def score_notes(question, nodes):
    """Rank notes by keyword overlap with the question; title hits count 3x."""
    q_words = set(tokenize(question))
    if not q_words or not nodes:
        return nodes[:TOP_N]
    scored = []
    for node in nodes:
        title_words = set(tokenize(node.get("label", "")))
        body_words = set(tokenize(node.get("excerpt", "")))
        score = 3 * len(q_words & title_words) + len(q_words & body_words)
        scored.append((score, node))
    scored.sort(key=lambda pair: (-pair[0], pair[1].get("id", 0)))
    return [node for _, node in scored[:TOP_N]]


def build_system_prompt(notes):
    if notes:
        notes_block = "\n\n".join(
            f"### {n.get('label', 'Untitled')}  [{n.get('group', '')}]\n{n.get('excerpt', '')}"
            for n in notes
        )
    else:
        notes_block = "(no notes available)"
    return (
        "You are the voice of a personal notes vault, answering questions about "
        "its contents. Answer ONLY using the notes provided below - never rely "
        "on outside knowledge, even if you know more about the topic. Answer in "
        "2-3 sentences. If the notes don't cover the question, say so plainly "
        "instead of guessing.\n\nNOTES:\n" + notes_block
    )


def call_anthropic(api_key, model, system_prompt, messages):
    body = json.dumps({
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system_prompt,
        "messages": messages,
    }).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(detail).get("error", {}).get("message", detail)
        except json.JSONDecodeError:
            msg = detail
        raise ChatError(502, f"Anthropic API error: {msg}")
    except urllib.error.URLError as e:
        raise ChatError(502, f"Could not reach the Anthropic API: {e.reason}")

    text_parts = [b.get("text", "") for b in result.get("content", []) if b.get("type") == "text"]
    return "".join(text_parts).strip()


def handle_chat(question, session_id):
    config = load_config()
    api_key = load_api_key(config)
    model = load_model(config)
    nodes = load_notes()
    top_notes = score_notes(question, nodes)
    system_prompt = build_system_prompt(top_notes)

    with SESSIONS_LOCK:
        history = list(SESSIONS.setdefault(session_id, []))

    messages = history + [{"role": "user", "content": question}]
    answer = call_anthropic(api_key, model, system_prompt, messages)

    with SESSIONS_LOCK:
        h = SESSIONS.setdefault(session_id, [])
        h.append({"role": "user", "content": question})
        h.append({"role": "assistant", "content": answer})
        del h[:-MAX_HISTORY_MESSAGES]

    return {
        "answer": answer,
        "nodes": [n.get("id") for n in top_notes],
        "session_id": session_id,
    }


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(VIEWER_DIR), **kwargs)

    def do_POST(self):
        if self.path != "/chat":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return

        question = (payload.get("question") or "").strip()
        session_id = payload.get("session_id") or secrets.token_hex(16)
        if not question:
            self._send_json(400, {"error": "question is required"})
            return

        try:
            result = handle_chat(question, session_id)
        except ChatError as e:
            self._send_json(e.status, {"error": str(e)})
            return
        except Exception as e:
            self._send_json(500, {"error": f"unexpected server error: {e}"})
            return

        self._send_json(200, result)

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    with http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving {VIEWER_DIR} on port {PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
