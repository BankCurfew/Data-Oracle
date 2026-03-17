#!/usr/bin/env python3
"""
Auto-Embed Watcher — detect new/modified .md/.pdf files and embed into kb_chunks.

Watches AIA-Knowledge repo (and other configured paths) for changes.
Uses embedding-service at localhost:8100 instead of loading BGE-M3 locally.

Usage:
    python scripts/auto-embed-watcher.py                # scan once
    python scripts/auto-embed-watcher.py --watch        # continuous (cron-style, 5min interval)
    python scripts/auto-embed-watcher.py --file path.md # embed specific file
    python scripts/auto-embed-watcher.py --dry-run      # preview without embedding

Designed for cron:
    */5 * * * * cd /home/mbank/repos/.../Data-Oracle && python scripts/auto-embed-watcher.py >> /tmp/auto-embed.log 2>&1
"""

import argparse
import json
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
EMBED_SERVICE = os.environ.get("EMBED_SERVICE_URL", "http://localhost:8100")
EMBED_BATCH_SIZE = 64  # max per request

# Watch paths: (path, source, default_category)
WATCH_PATHS = [
    (Path.home() / "repos/github.com/BankCurfew/AIA-Knowledge", "research", ""),
    (Path.home() / "repos/github.com/BankCurfew/Researcher-Oracle/knowledge-base", "research", ""),
]

# State file to track what's been embedded
STATE_FILE = Path.home() / ".oracle/auto-embed-state.json"

# Chunking config
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"embedded_files": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def file_hash(path):
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def embed_texts(texts):
    """Call embedding-service to get dense embeddings."""
    url = f"{EMBED_SERVICE}/embed"
    data = json.dumps({"texts": texts, "return_sparse": True}).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("dense", []), result.get("sparse", [])
    except Exception as e:
        print(f"  Embed service error: {e}")
        return None, None


def supabase_post(path, data):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    body = json.dumps(data).encode()
    req = Request(url, data=body, headers=headers, method="POST")
    with urlopen(req) as resp:
        return True


def supabase_delete(path):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "return=minimal",
    }
    req = Request(url, headers=headers, method="DELETE")
    with urlopen(req) as resp:
        return True


def chunk_markdown(text, filepath):
    """Chunk markdown by ## headings, fallback to size-based."""
    sections = re.split(r'\n(?=## )', text)
    chunks = []

    for section in sections:
        if not section.strip():
            continue

        # Extract heading
        lines = section.strip().split('\n')
        heading = lines[0].lstrip('#').strip() if lines[0].startswith('#') else ""
        body = '\n'.join(lines[1:]).strip() if heading else section.strip()

        if not body:
            continue

        # If section is small enough, keep as one chunk
        if len(body) <= CHUNK_SIZE * 1.5:
            chunks.append({
                "chunk_text": body,
                "chunk_index": len(chunks),
                "chunk_tokens": len(body) // 4,
                "section": heading,
            })
        else:
            # Split large sections
            start = 0
            while start < len(body):
                end = start + CHUNK_SIZE
                if end < len(body):
                    # Break at paragraph or sentence
                    for sep in ["\n\n", ".\n", ". ", "\n"]:
                        pos = body.rfind(sep, start + CHUNK_SIZE // 2, end + 100)
                        if pos > start:
                            end = pos + len(sep)
                            break

                chunk_text = body[start:end].strip()
                if chunk_text and len(chunk_text) > 30:
                    chunks.append({
                        "chunk_text": chunk_text,
                        "chunk_index": len(chunks),
                        "chunk_tokens": len(chunk_text) // 4,
                        "section": heading,
                    })
                start = end - CHUNK_OVERLAP

    return chunks


def chunk_pdf(filepath):
    """Extract and chunk PDF."""
    import pymupdf
    doc = pymupdf.open(str(filepath))
    pages = []
    for page in doc:
        text = page.get_text().strip()
        if text:
            pages.append(text)
    doc.close()

    if not pages:
        return []

    full_text = "\n\n".join(pages)
    chunks = []
    start = 0
    while start < len(full_text):
        end = start + CHUNK_SIZE
        if end < len(full_text):
            for sep in ["\n\n", ".\n", ". ", "\n", " "]:
                pos = full_text.rfind(sep, start + CHUNK_SIZE // 2, end + 100)
                if pos > start:
                    end = pos + len(sep)
                    break

        chunk_text = full_text[start:end].strip()
        if chunk_text and len(chunk_text) > 30:
            chunks.append({
                "chunk_text": chunk_text,
                "chunk_index": len(chunks),
                "chunk_tokens": len(chunk_text) // 4,
                "section": "",
            })
        start = end - CHUNK_OVERLAP

    return chunks


def process_file(filepath, source, category, dry_run=False, priority=None):
    """Process a single file: chunk → embed → upload."""
    ext = filepath.suffix.lower()
    filename = filepath.name

    # Chunk based on file type
    if ext == ".md":
        text = filepath.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_markdown(text, filepath)
    elif ext == ".pdf":
        chunks = chunk_pdf(filepath)
    else:
        return {"status": "skip", "reason": f"unsupported: {ext}"}

    if not chunks:
        return {"status": "no_chunks"}

    if dry_run:
        return {"status": "dry_run", "chunks": len(chunks)}

    # Delete existing chunks for this document (re-embed)
    from urllib.parse import quote
    try:
        supabase_delete(f"kb_chunks?document_name=eq.{quote(filename, safe='')}&source=eq.{source}")
    except:
        pass

    # Embed in batches
    all_rows = []
    texts = [c["chunk_text"] for c in chunks]

    for batch_start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch_texts = texts[batch_start:batch_start + EMBED_BATCH_SIZE]
        dense, sparse = embed_texts(batch_texts)

        if dense is None:
            return {"status": "embed_error", "chunks": len(chunks)}

        for i, chunk in enumerate(chunks[batch_start:batch_start + len(batch_texts)]):
            sparse_dict = {}
            if sparse and i < len(sparse):
                sparse_dict = {str(k): float(v) for k, v in sparse[i].items()} if isinstance(sparse[i], dict) else {}

            row = {
                "document_name": filename,
                "source": source,
                "section": chunk.get("section", ""),
                "chunk_index": chunk["chunk_index"],
                "chunk_text": chunk["chunk_text"],
                "chunk_tokens": chunk.get("chunk_tokens"),
                "embedding": dense[i],
                "sparse_embedding": sparse_dict,
                "metadata": {
                    "extraction_method": "auto-embed-watcher",
                    "category": category,
                    "pipeline": "auto-embed-v1",
                    "priority": priority,
                    "file_path": str(filepath),
                },
            }
            if category:
                row["category"] = category
            all_rows.append(row)

    # Upload in batches of 50
    uploaded = 0
    for batch_start in range(0, len(all_rows), 50):
        batch = all_rows[batch_start:batch_start + 50]
        try:
            supabase_post("kb_chunks", batch)
            uploaded += len(batch)
        except Exception as e:
            return {"status": "upload_error", "chunks": uploaded, "error": str(e)}

    return {"status": "ok", "chunks": uploaded}


def scan_paths(state, dry_run=False):
    """Scan watch paths for new/modified files."""
    embedded = state.get("embedded_files", {})
    to_process = []

    for watch_path, source, category in WATCH_PATHS:
        if not watch_path.exists():
            continue

        for ext in ["*.md", "*.pdf"]:
            for filepath in watch_path.rglob(ext):
                # Skip hidden/temp files
                if any(part.startswith('.') for part in filepath.parts):
                    continue

                key = str(filepath)
                current_hash = file_hash(filepath)

                if key in embedded and embedded[key] == current_hash:
                    continue  # Already embedded, unchanged

                # Detect category from path
                cat = category
                for part in filepath.parts:
                    if part in ("cfp", "unit-linked", "health", "ci", "savings"):
                        cat = part
                        break

                to_process.append({
                    "path": filepath,
                    "source": source,
                    "category": cat,
                    "hash": current_hash,
                    "is_update": key in embedded,
                })

    return to_process


def main():
    parser = argparse.ArgumentParser(description="Auto-embed watcher")
    parser.add_argument("--watch", action="store_true", help="Continuous mode (5min interval)")
    parser.add_argument("--file", help="Embed specific file")
    parser.add_argument("--source", default="research", help="Source for --file mode")
    parser.add_argument("--category", default="", help="Category for --file mode")
    parser.add_argument("--priority", help="Priority tag (e.g., 'correction')")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        sys.exit(1)

    # Single file mode
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)
        print(f"Processing: {filepath}")
        result = process_file(filepath, args.source, args.category, args.dry_run, args.priority)
        print(f"  Result: {result}")
        return

    # Scan mode
    state = load_state()

    while True:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        to_process = scan_paths(state, args.dry_run)

        if to_process:
            print(f"[{ts}] Found {len(to_process)} new/modified files")
            for item in to_process:
                action = "UPDATE" if item["is_update"] else "NEW"
                print(f"  [{action}] {item['path'].name} ({item['source']}/{item['category']})", end=" ")

                result = process_file(item["path"], item["source"], item["category"], args.dry_run, args.priority)
                print(f"→ {result['status']} ({result.get('chunks', 0)} chunks)")

                if result["status"] in ("ok", "dry_run"):
                    state["embedded_files"][str(item["path"])] = item["hash"]

            save_state(state)
            print(f"  State saved. Total tracked: {len(state['embedded_files'])} files")
        else:
            print(f"[{ts}] No new files")

        if not args.watch:
            break

        time.sleep(300)  # 5 minutes


if __name__ == "__main__":
    main()
