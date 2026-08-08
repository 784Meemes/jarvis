#!/usr/bin/env python3
"""Scan a folder of Markdown notes and build viewer/graph-data.js.

Usage:
    python3 build.py [root-dir]

root-dir defaults to the current directory. Every *.md file found beneath it
(recursively) becomes a graph node; the viewer/ directory itself, .git, and a
few common junk directories are skipped. The output always lands next to this
script, in viewer/graph-data.js, regardless of what root-dir you point at.
"""
import json
import os
import re
import sys
from pathlib import Path

EXCERPT_LEN = 700
EXCLUDE_DIRS = {".git", "viewer", "node_modules", "__pycache__", ".venv", "venv"}

HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
MD_PUNCT_RE = re.compile(r"[#*_`>~]")
WHITESPACE_RE = re.compile(r"\s+")
NORM_RE = re.compile(r"[^a-z0-9]+")


def find_markdown_files(root: Path):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.lower().endswith(".md"):
                files.append(Path(dirpath) / name)
    files.sort(key=lambda p: str(p).lower())
    return files


def get_title(path: Path, raw: str) -> str:
    m = HEADING_RE.search(raw)
    if m:
        return m.group(1).strip()
    return re.sub(r"[-_]+", " ", path.stem).strip()


def get_group(path: Path, root: Path) -> str:
    rel_parent = path.resolve().parent.relative_to(root.resolve())
    return rel_parent.name if rel_parent.parts else "general"


def clean_excerpt(raw: str) -> str:
    text = FRONTMATTER_RE.sub("", raw, count=1)
    text = HEADING_RE.sub("", text, count=1)  # drop the title heading itself

    def wikilink_repl(m):
        inner = m.group(1)
        target, _, alias = inner.partition("|")
        return (alias or target).strip()

    text = WIKILINK_RE.sub(wikilink_repl, text)
    text = MD_LINK_RE.sub(lambda m: m.group(1), text)
    text = MD_PUNCT_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > EXCERPT_LEN:
        text = text[:EXCERPT_LEN].rstrip() + "…"
    return text


def normalize(title: str) -> str:
    return NORM_RE.sub(" ", title.lower()).strip()


def build_graph(root: Path):
    files = find_markdown_files(root)
    nodes = []
    raw_texts = []
    for i, path in enumerate(files):
        raw = path.read_text(encoding="utf-8", errors="replace")
        raw_texts.append(raw)
        title = get_title(path, raw)
        nodes.append({
            "id": i,
            "label": title,
            "group": get_group(path, root),
            "excerpt": clean_excerpt(raw),
            "path": str(path.resolve().relative_to(root.resolve())),
        })

    # Map normalized title/filename -> node id, for resolving mentions and wikilinks.
    title_index = {}
    for node, path in zip(nodes, files):
        for key in (normalize(node["label"]), normalize(path.stem)):
            if key and key not in title_index:
                title_index[key] = node["id"]

    link_pairs = set()

    for i, raw in enumerate(raw_texts):
        # Explicit [[wikilinks]]
        for m in WIKILINK_RE.finditer(raw):
            target = m.group(1).partition("|")[0]
            j = title_index.get(normalize(target))
            if j is not None and j != i:
                link_pairs.add((min(i, j), max(i, j)))

        # Plain-text mentions of another note's title.
        for j, other in enumerate(nodes):
            if j == i or len(other["label"]) < 3:
                continue
            pattern = r"\b" + re.escape(other["label"]) + r"\b"
            if re.search(pattern, raw, re.IGNORECASE):
                link_pairs.add((min(i, j), max(i, j)))

    links = [{"source": a, "target": b} for a, b in sorted(link_pairs)]
    return {"nodes": nodes, "links": links}


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    root = root.resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    graph = build_graph(root)

    viewer_dir = Path(__file__).resolve().parent / "viewer"
    viewer_dir.mkdir(parents=True, exist_ok=True)
    out_path = viewer_dir / "graph-data.js"
    out_path.write_text("window.GRAPH = " + json.dumps(graph, indent=2) + ";\n", encoding="utf-8")

    print(f"Scanned {root}")
    print(f"Wrote {len(graph['nodes'])} nodes and {len(graph['links'])} links to {out_path}")


if __name__ == "__main__":
    main()
