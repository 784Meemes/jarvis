#!/usr/bin/env python3
"""Serve viewer/ and answer questions about the notes.

GET  /...       Static files from viewer/ only. config.json and everything
                else in the project root is outside this directory and
                unreachable.
POST /chat      {"question": str, "session_id": str|null} -> answers the
                question by finding the most relevant notes and calling the
                Anthropic Messages API. Conversation history is kept
                server-side, per session_id, so follow-up questions have
                context.
POST /remember  {"text": str} -> text starting with "remember that..." gets
                written as a new Markdown note under notes/captures/, added
                live to viewer/graph-data.js (appended, so every existing
                node keeps its id), and linked to whichever existing notes
                it mentions or is most related to. Returns the new node, the
                id of its closest relative (for the viewer to spawn it at
                that node's position), and a one-line spoken confirmation.
POST /upload    multipart/form-data, field "file" (+ optional "session_id")
                -> reads a plain-text document (.txt/.md/.csv/.json/etc,
                nothing binary) and attaches it to that chat session only -
                not written to the notes vault. Every /chat call in that
                session includes it as reference material the model can
                draw on, alongside (not instead of) the usual notes/web
                search/writing behavior. In-memory only, per session, capped
                per session and per file - never persisted to disk.

The API key and model come from config.json in the project root (never
served to the browser - it sits outside viewer/ and is read directly off
disk by this process only), or from the ANTHROPIC_API_KEY / CLAUDE_MODEL
environment variables as a fallback for hosted deployments where
config.json isn't present (it's deliberately excluded from git).
"""
import datetime
import http.server
import json
import os
import re
import secrets
import threading
import urllib.error
import urllib.request
from pathlib import Path

import build

PORT = int(os.environ.get("PORT", 4700))
ROOT_DIR = Path(__file__).resolve().parent
VIEWER_DIR = ROOT_DIR / "viewer"
NOTES_DIR = ROOT_DIR / "notes"
CAPTURES_DIR = NOTES_DIR / "captures"
CONFIG_PATH = ROOT_DIR / "config.json"
GRAPH_DATA_PATH = VIEWER_DIR / "graph-data.js"

REMEMBER_PREFIX_RE = re.compile(r"^\s*remember\s+that\b[:,]?\s*", re.IGNORECASE)
TITLE_WORD_COUNT = 8

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
MAX_TOKENS = 4096  # generous enough for a full essay, not just a one-line answer
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}
REQUEST_TIMEOUT_SECONDS = 300  # a researched essay (web search + thinking) can take minutes

TOP_N = 6
MAX_HISTORY_MESSAGES = 20  # 10 question/answer turns

MAX_DOCS_PER_SESSION = 5
MAX_DOC_CHARS = 8000
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2MB per file
MAX_UPLOAD_BODY_BYTES = 3 * 1024 * 1024  # multipart overhead headroom

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
GRAPH_LOCK = threading.Lock()  # guards read-modify-write of graph-data.js

SESSION_DOCS = {}  # session_id -> list of {"filename": ..., "content": ...} dicts
SESSION_DOCS_LOCK = threading.Lock()


class ChatError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def load_config():
    # config.json is deliberately not committed to git (it can hold a real
    # API key locally), so a fresh clone or hosted deploy legitimately won't
    # have one - that's fine, load_api_key/load_model fall back to env vars.
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise ChatError(500, "config.json is not valid JSON")


def load_api_key(config):
    api_key = config.get("api_key")
    if api_key and api_key != "PUT-YOUR-KEY-HERE":
        return api_key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return api_key
    raise ChatError(
        400,
        "No API key configured. Paste your Anthropic API key into the "
        "\"api_key\" field of config.json for local use, or set the "
        "ANTHROPIC_API_KEY environment variable for a hosted deployment, "
        "and restart the server.",
    )


def load_model(config):
    return config.get("model") or os.environ.get("CLAUDE_MODEL") or DEFAULT_MODEL


GRAPH_JS_PREFIX = "window.GRAPH = "


def load_graph():
    if not GRAPH_DATA_PATH.exists():
        raise ChatError(500, "viewer/graph-data.js not found - run build.py first")
    raw = GRAPH_DATA_PATH.read_text(encoding="utf-8")
    if not raw.startswith(GRAPH_JS_PREFIX):
        raise ChatError(500, "viewer/graph-data.js is not in the expected format")
    return json.loads(raw[len(GRAPH_JS_PREFIX):].rstrip().rstrip(";"))


def write_graph(graph):
    GRAPH_DATA_PATH.write_text(
        GRAPH_JS_PREFIX + json.dumps(graph, indent=2) + ";\n", encoding="utf-8"
    )


def load_notes():
    return load_graph().get("nodes", [])


def parse_multipart_form(body, content_type):
    """Minimal multipart/form-data parser (stdlib only - no cgi, which is
    removed in Python 3.13). Handles the single-boundary case a plain
    browser FormData/fetch upload produces; not a general MIME parser.
    """
    m = re.search(r'boundary="?([^";]+)"?', content_type)
    if not m:
        raise ChatError(400, "Missing multipart boundary")
    boundary = b"--" + m.group(1).encode()

    fields = {}
    files = []
    raw_parts = body.split(boundary)
    for raw in raw_parts[1:-1]:  # skip the preamble and the closing "--\r\n"
        if raw.startswith(b"\r\n"):
            raw = raw[2:]
        if raw.endswith(b"\r\n"):
            raw = raw[:-2]
        header_blob, sep, content = raw.partition(b"\r\n\r\n")
        if not sep:
            continue
        headers = {}
        for line in header_blob.split(b"\r\n"):
            if b":" in line:
                k, v = line.split(b":", 1)
                headers[k.strip().lower().decode("latin-1")] = v.strip().decode("latin-1")
        disp = headers.get("content-disposition", "")
        name_m = re.search(r'name="([^"]*)"', disp)
        filename_m = re.search(r'filename="([^"]*)"', disp)
        field_name = name_m.group(1) if name_m else None
        if filename_m and filename_m.group(1):
            files.append({"field": field_name, "filename": filename_m.group(1), "content": content})
        elif field_name:
            fields[field_name] = content.decode("utf-8", errors="replace")
    return fields, files


def handle_upload(body, content_type):
    fields, files = parse_multipart_form(body, content_type)
    if not files:
        raise ChatError(400, "No file received")

    session_id = fields.get("session_id") or secrets.token_hex(16)
    uploaded = []

    with SESSION_DOCS_LOCK:
        docs = SESSION_DOCS.setdefault(session_id, [])
        for f in files:
            if len(f["content"]) > MAX_UPLOAD_BYTES:
                raise ChatError(400, f"\"{f['filename']}\" is too large - 2MB max per file.")
            try:
                text = f["content"].decode("utf-8")
            except UnicodeDecodeError:
                raise ChatError(
                    400,
                    f"Could not read \"{f['filename']}\" as text. Only plain-text "
                    "documents are supported right now (.txt, .md, .csv, .json, "
                    "and similar) - PDFs and Word docs aren't parsed yet, so "
                    "paste the text directly instead.",
                )
            excerpt = text[:MAX_DOC_CHARS]
            docs.append({"filename": f["filename"], "content": excerpt})
            uploaded.append({"filename": f["filename"], "chars": len(excerpt)})
        del docs[:-MAX_DOCS_PER_SESSION]

    return {"session_id": session_id, "uploaded": uploaded}


def tokenize(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1 and w not in STOPWORDS]


WRITE_VERBS = {"write", "writes", "compose", "composes", "draft", "drafts", "pen"}
WRITE_NOUNS = {
    "essay", "essays", "letter", "letters", "poem", "poems", "story", "stories",
    "article", "articles", "summary", "summaries", "report", "reports", "speech",
    "speeches", "paragraph", "paragraphs", "piece", "pieces", "blurb", "blurbs",
    "post", "posts", "paper", "papers", "script", "scripts",
}


def is_write_request(text):
    """A writing/composition request (both a write-verb and a document-noun
    present) always bypasses notes-only mode, even if the topic happens to
    match a note by keyword - "write an essay about stoicism" is a request
    to write an essay, not a request to summarize the Stoicism note, and
    needs the full internet (web search), not the vault's excerpt alone.
    """
    words = set(tokenize(text))
    return bool(words & WRITE_VERBS) and bool(words & WRITE_NOUNS)


def score_notes(question, nodes):
    """Rank notes by keyword overlap with the question; title hits count 3x.

    A single overlapping *body* word is discarded (score < 2) - one common
    word (e.g. "like", "way") shared with an excerpt is noise, not evidence
    the vault covers the question, and treating it as a match wrongly routes
    genuine outside-the-vault questions into the notes-only branch, which
    silently disables web search for them. A single *title* word is always
    enough on its own (weighted 3x, well past the threshold), so a real
    one-word match on a note's subject still works.

    Notes below the threshold are dropped rather than falling back to an
    arbitrary top-N - an empty result means "not a notes question" (small
    talk, banter, or a genuine outside question), which the caller uses to
    skip the notes context and offer web search instead, and which the
    viewer uses to leave the camera alone.
    """
    q_words = set(tokenize(question))
    if not q_words or not nodes:
        return []
    scored = []
    for node in nodes:
        title_words = set(tokenize(node.get("label", "")))
        body_words = set(tokenize(node.get("excerpt", "")))
        score = 3 * len(q_words & title_words) + len(q_words & body_words)
        if score > 1:
            scored.append((score, node))
    scored.sort(key=lambda pair: (-pair[0], pair[1].get("id", 0)))
    return [node for _, node in scored[:TOP_N]]


BUTLER_PERSONA = (
    "You are a dry, impeccably polite English butler with a razor wit, in "
    "service to the owner of this personal notes vault. Always address the "
    "owner as \"sir\" at least once somewhere in every single reply, without "
    "exception - but only once or twice, not in every sentence, so it reads "
    "as natural address rather than a verbal tic. One genuinely funny line "
    "beats three bland ones, so exercise restraint elsewhere: wit should "
    "feel earned, not forced into every reply."
)


def build_docs_block(docs):
    if not docs:
        return ""
    joined = "\n\n".join(f"### {d.get('filename', 'document')}\n{d.get('content', '')}" for d in docs)
    return (
        "\n\nThe owner has also attached the following document(s) to this "
        "conversation (not part of the permanent notes vault - just working "
        "material for this chat). Unlike web search results, these were "
        "handed to you directly, so drawing on them closely - summarizing, "
        "quoting, analyzing - is exactly the point; consult them whenever "
        "they're relevant to what's being asked, alongside anything else in "
        "play.\n\nATTACHED DOCUMENTS:\n" + joined
    )


def build_system_prompt(notes, docs=None):
    docs_block = build_docs_block(docs)
    if notes:
        notes_block = "\n\n".join(
            f"### {n.get('label', 'Untitled')}  [{n.get('group', '')}]\n{n.get('excerpt', '')}"
            for n in notes
        )
        return (
            BUTLER_PERSONA + "\n\n"
            "The owner has asked something about their notes. Answer using "
            "ONLY the notes below - never rely on outside knowledge, even if "
            "you know more about the topic. Reply with exactly one witty "
            "sentence, followed by the actual facts the owner needs, in your "
            "own words - never recite or quote a note back verbatim, since it "
            "is already open on screen right beside you. If the notes plainly "
            "don't cover the question, say so plainly (and wittily) rather "
            "than guessing.\n\nNOTES:\n" + notes_block + docs_block
        )
    return (
        BUTLER_PERSONA + "\n\n"
        "This is not a question about the notes vault. Three cases:\n"
        "1. Small talk or banter: stay in character and reply briefly, in "
        "1-3 sentences - do not invent facts about the notes and do not "
        "pretend to consult one.\n"
        "2. A genuine factual question the vault has nothing to do with "
        "(current events, general knowledge, anything outside these notes): "
        "you have a web search tool - use it when it would actually help, "
        "then answer briefly in your own words, still in character.\n"
        "3. A request to write, compose, or draft something - an essay, "
        "letter, poem, story, summary, or similar: the topic can be "
        "absolutely anything, not just what's in the notes vault - use "
        "your web search tool first if the topic needs current facts or "
        "details you're not certain of, then write the complete piece as "
        "asked, well-crafted and not artificially shortened, even if it "
        "runs to several paragraphs. Everything you write must be an "
        "ORIGINAL composition in your own words and sentence structure - "
        "research is for gathering facts and forming your own "
        "understanding, never for lifting or lightly rewording someone "
        "else's phrasing. (This originality rule is about outside sources "
        "like web search - it does not apply to the owner's own attached "
        "documents, if any are below: drawing on those closely is exactly "
        "what they're for.) If you quote a web source directly, keep it "
        "brief (well under twenty words), put it in quotation marks, and "
        "say where it's from - the piece as a whole must be your own "
        "prose. Never reproduce an existing published work (a real poem, "
        "article, speech, etc.) as if you wrote it - write a fresh piece "
        "in your own voice even when asked for something in the style of "
        "an existing work. A brief one-line introduction in character is "
        "welcome, but the requested piece itself is the point - do not "
        "summarize it away or cut it short."
        + docs_block
    )


def call_anthropic(api_key, model, system_prompt, messages, tools=None):
    def one_request(msgs):
        payload = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": system_prompt,
            "messages": msgs,
        }
        if tools:
            payload["tools"] = tools
        req = urllib.request.Request(
            ANTHROPIC_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            try:
                msg = json.loads(detail).get("error", {}).get("message", detail)
            except json.JSONDecodeError:
                msg = detail
            raise ChatError(502, f"Anthropic API error: {msg}")
        except urllib.error.URLError as e:
            raise ChatError(502, f"Could not reach the Anthropic API: {e.reason}")
        except TimeoutError:
            # A plain read timeout (e.g. a long essay + web search taking a
            # while to generate) raises bare TimeoutError, not URLError -
            # urllib only wraps connection-stage failures, not a stalled
            # read on an already-open connection - so it needs its own
            # handler or it leaks as a raw Python error to the user.
            raise ChatError(
                504,
                "That took too long to generate and timed out - try asking "
                "again, or for something a bit shorter.",
            )

    result = one_request(messages)
    if result.get("stop_reason") == "pause_turn":
        # A server-side tool (web search) hit its per-turn iteration cap;
        # resending the paused assistant turn lets the API pick back up
        # where it left off, per Anthropic's documented pause_turn handling.
        result = one_request(messages + [{"role": "assistant", "content": result.get("content", [])}])

    text_parts = [b.get("text", "") for b in result.get("content", []) if b.get("type") == "text"]
    return "".join(text_parts).strip()


def handle_chat(question, session_id):
    config = load_config()
    api_key = load_api_key(config)
    model = load_model(config)
    nodes = load_notes()
    top_notes = [] if is_write_request(question) else score_notes(question, nodes)
    with SESSION_DOCS_LOCK:
        session_docs = list(SESSION_DOCS.get(session_id, []))
    system_prompt = build_system_prompt(top_notes, session_docs)

    with SESSIONS_LOCK:
        history = list(SESSIONS.setdefault(session_id, []))

    messages = history + [{"role": "user", "content": question}]
    # Web search is only offered when nothing in the vault is relevant, so a
    # notes question can never be answered (or the source node picked) from
    # anything other than the notes actually shown to the model.
    tools = None if top_notes else [WEB_SEARCH_TOOL]
    answer = call_anthropic(api_key, model, system_prompt, messages, tools=tools)

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


def slugify(text, max_len=60):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "note"


def make_title(remainder):
    words = remainder.split()[:TITLE_WORD_COUNT]
    title = " ".join(words).strip(" .,!?;:")
    if not title:
        return "Captured Note"
    return title[0].upper() + title[1:]


def unique_capture_path(slug):
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    candidate = CAPTURES_DIR / f"{slug}.md"
    n = 2
    while candidate.exists():
        candidate = CAPTURES_DIR / f"{slug}-{n}.md"
        n += 1
    return candidate


def find_links_and_anchor(raw_text, nodes):
    """Figure out which existing notes a freshly captured note relates to.

    Exact [[wikilinks]] and title mentions (the same signals build.py's full
    rebuild uses) come first; if the dictated text doesn't literally name
    any note, fall back to keyword overlap so there's still a sensible
    "closest relative" for the viewer to spawn the new node next to.
    """
    title_index = {}
    for n in nodes:
        stem = Path(n["path"]).stem if n.get("path") else ""
        for key in (build.normalize(n["label"]), build.normalize(stem)):
            if key and key not in title_index:
                title_index[key] = n["id"]

    link_ids = set()
    for m in build.WIKILINK_RE.finditer(raw_text):
        target = m.group(1).partition("|")[0]
        j = title_index.get(build.normalize(target))
        if j is not None:
            link_ids.add(j)

    for n in nodes:
        label = n["label"]
        if len(label) < 3:
            continue
        if re.search(r"\b" + re.escape(label) + r"\b", raw_text, re.IGNORECASE):
            link_ids.add(n["id"])

    if link_ids:
        candidates = [n for n in nodes if n["id"] in link_ids]
        ranked = score_notes(raw_text, candidates)
        anchor_id = ranked[0]["id"] if ranked else next(iter(link_ids))
    else:
        ranked = score_notes(raw_text, nodes)
        anchor_id = ranked[0]["id"] if ranked else None
        if anchor_id is not None:
            link_ids.add(anchor_id)

    return link_ids, anchor_id


def build_remember_prompt(title):
    return (
        BUTLER_PERSONA + "\n\n"
        "The owner just dictated a note that has been filed away under the "
        f"title \"{title}\". Confirm this out loud in EXACTLY one witty "
        "sentence - do not repeat the note's contents back, do not add "
        "caveats, just acknowledge in character that it has been filed."
    )


def handle_remember(text):
    remainder = REMEMBER_PREFIX_RE.sub("", text, count=1).strip()
    if not remainder:
        raise ChatError(400, "Nothing to remember - say or type what comes after \"remember that\".")

    title = make_title(remainder)
    body = remainder[0].upper() + remainder[1:]
    if not body.endswith((".", "!", "?")):
        body += "."
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    note_text = f"# {title}\n\n{body}\n\n*Captured by voice on {timestamp}.*\n"

    config = load_config()
    api_key = load_api_key(config)
    model = load_model(config)

    with GRAPH_LOCK:
        path = unique_capture_path(slugify(title))
        path.write_text(note_text, encoding="utf-8")

        graph = load_graph()
        nodes = graph.get("nodes", [])
        new_id = len(nodes)
        new_node = {
            "id": new_id,
            "label": title,
            "group": path.resolve().parent.relative_to(ROOT_DIR).name,
            "excerpt": build.clean_excerpt(note_text),
            "path": path.resolve().relative_to(ROOT_DIR).as_posix(),
        }

        link_ids, anchor_id = find_links_and_anchor(remainder, nodes)

        graph["nodes"] = nodes + [new_node]
        graph["links"] = graph.get("links", []) + [
            {"source": new_id, "target": tid} for tid in sorted(link_ids)
        ]
        write_graph(graph)

    reply = call_anthropic(
        api_key, model, build_remember_prompt(title),
        [{"role": "user", "content": "Confirm the capture."}],
    )

    return {
        "node": new_node,
        "anchor_id": anchor_id,
        "links": sorted(link_ids),
        "reply": reply,
    }


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(VIEWER_DIR), **kwargs)

    def do_POST(self):
        if self.path == "/chat":
            self._handle_chat_request()
        elif self.path == "/remember":
            self._handle_remember_request()
        elif self.path == "/upload":
            self._handle_upload_request()
        else:
            self.send_error(404)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw or b"{}")

    def _handle_chat_request(self):
        try:
            payload = self._read_json_body()
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

    def _handle_remember_request(self):
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return

        text = (payload.get("text") or "").strip()
        if not text:
            self._send_json(400, {"error": "text is required"})
            return

        try:
            result = handle_remember(text)
        except ChatError as e:
            self._send_json(e.status, {"error": str(e)})
            return
        except Exception as e:
            self._send_json(500, {"error": f"unexpected server error: {e}"})
            return

        self._send_json(200, result)

    def _handle_upload_request(self):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json(400, {"error": "expected multipart/form-data"})
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > MAX_UPLOAD_BODY_BYTES:
            self._send_json(400, {"error": "invalid or too-large upload (2MB max per file)"})
            return
        body = self.rfile.read(length)

        try:
            result = handle_upload(body, content_type)
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
