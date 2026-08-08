#!/usr/bin/env python3
"""Serve viewer/ and answer questions about the notes at http://localhost:4700/.

GET  /...   Static files from viewer/ only. config.json and everything else
            in the project root is outside this directory and unreachable.
POST /chat  {"question": str, "session_id": str|null} -> answers the question
            by finding the most relevant notes and shelling out to `claude -p`
            (your Claude Code subscription, not the Anthropic API - no key
            needed). Conversation history is kept server-side, per session_id,
            so follow-up questions have context.
"""
import http.server
import json
import re
import secrets
import subprocess
import threading
from pathlib import Path

PORT = 4700
ROOT_DIR = Path(__file__).resolve().parent
VIEWER_DIR = ROOT_DIR / "viewer"
CONFIG_PATH = ROOT_DIR / "config.json"
GRAPH_DATA_PATH = VIEWER_DIR / "graph-data.js"

TOP_N = 6
MAX_HISTORY_TURNS = 8
CLAUDE_TIMEOUT_SECONDS = 90

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "on", "at", "for", "with", "and", "or", "but", "if",
    "do", "does", "did", "what", "why", "how", "who", "which", "when",
    "where", "my", "me", "i", "you", "your", "it", "its", "this", "that",
    "these", "those", "about", "from", "as", "so", "can", "could", "should",
    "would", "will", "there", "their", "them", "than", "then", "tell",
}

SESSIONS = {}  # session_id -> list of (question, answer) tuples
SESSIONS_LOCK = threading.Lock()


class ChatError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def load_model():
    if not CONFIG_PATH.exists():
        raise ChatError(500, "config.json not found in project root")
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise ChatError(500, "config.json is not valid JSON")
    return config.get("model") or None


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


def build_prompt(history, question):
    if not history:
        return question
    lines = []
    for q, a in history:
        lines.append(f"User: {q}")
        lines.append(f"Assistant: {a}")
    lines.append(f"User: {question}")
    return "\n".join(lines)


def call_claude(model, system_prompt, prompt):
    cmd = [
        "claude", "-p",
        "--system-prompt", system_prompt,
        "--tools", "",
        "--no-session-persistence",
        "--output-format", "json",
    ]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS, cwd=str(ROOT_DIR),
        )
    except FileNotFoundError:
        raise ChatError(500, "claude CLI not found - install Claude Code and run `claude auth login`")
    except subprocess.TimeoutExpired:
        raise ChatError(504, "claude CLI timed out")

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        detail = (proc.stderr or proc.stdout or "").strip()[:500]
        raise ChatError(502, f"claude CLI did not return JSON: {detail or 'no output'}")

    if result.get("is_error"):
        raise ChatError(502, result.get("result") or "claude CLI reported an error")

    return (result.get("result") or "").strip()


def handle_chat(question, session_id):
    model = load_model()
    nodes = load_notes()
    top_notes = score_notes(question, nodes)
    system_prompt = build_system_prompt(top_notes)

    with SESSIONS_LOCK:
        history = list(SESSIONS.setdefault(session_id, []))

    prompt = build_prompt(history, question)
    answer = call_claude(model, system_prompt, prompt)

    with SESSIONS_LOCK:
        h = SESSIONS.setdefault(session_id, [])
        h.append((question, answer))
        del h[:-MAX_HISTORY_TURNS]

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
        print(f"Serving {VIEWER_DIR} at http://localhost:{PORT}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
