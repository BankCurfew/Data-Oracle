#!/usr/bin/env python3
"""Ingest iAgencyAIA KB chunks into Supabase aia_knowledge table with BGE-M3 embeddings."""

import json
import os
import sys
import argparse
import urllib.parse
import urllib.request
from pathlib import Path

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://heciyiepgxqtbphepalf.supabase.co")
SB_AUTH = os.environ.get("SUPABASE_SERVICE_KEY", "")
OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "bge-m3"
BATCH_SIZE = 10
CHUNKS_PATH = Path(__file__).parent.parent / "data" / "kb" / "iagencyaia-chunks.json"


def log(msg: str) -> None:
    print(f"[ingest] {msg}", flush=True)


def embed_batch(texts: list[str]) -> list[list[float]]:
    embeddings = []
    for text in texts:
        payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
        req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        embeddings.append(data["embedding"])
    return embeddings


def sb_request(method: str, path: str, body: dict | None = None) -> dict | list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SB_AUTH,
        "Authorization": f"Bearer {SB_AUTH}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def chunk_exists(source_url: str, title: str) -> bool:
    path = f"aia_knowledge?source_url=eq.{urllib.parse.quote(source_url)}&title=eq.{urllib.parse.quote(title)}&select=id&limit=1"
    try:
        result = sb_request("GET", path)
        return isinstance(result, list) and len(result) > 0
    except Exception:
        return False


def insert_chunk(chunk: dict, embedding: list[float]) -> None:
    row = {
        "title": chunk["title"],
        "content": chunk["content"],
        "category": chunk.get("category", ""),
        "source_url": chunk.get("source_url", ""),
        "source": "iagencyaia.com",
        "embedding": embedding,
        "metadata": chunk.get("metadata", {}),
    }
    sb_request("POST", "aia_knowledge", row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest iAgencyAIA KB into Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Print chunks without uploading")
    parser.add_argument("--file", default=str(CHUNKS_PATH), help="Path to chunks JSON file")
    args = parser.parse_args()

    if not args.dry_run and not SB_AUTH:
        log("ERROR: SUPABASE_SERVICE_KEY env var required")
        sys.exit(1)

    chunks_file = Path(args.file)
    if not chunks_file.exists():
        log(f"ERROR: chunks file not found: {chunks_file}")
        sys.exit(1)

    chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
    log(f"Loaded {len(chunks)} chunks from {chunks_file}")

    if args.dry_run:
        for i, chunk in enumerate(chunks):
            print(f"\n--- Chunk {i+1}/{len(chunks)} ---")
            print(f"  title:    {chunk.get('title', '')}")
            print(f"  category: {chunk.get('category', '')}")
            print(f"  source:   {chunk.get('source_url', '')}")
            print(f"  content:  {chunk.get('content', '')[:120]}...")
        log("Dry run complete — no data uploaded")
        return

    skipped = inserted = errors = 0

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]
        log(f"Processing batch {batch_start // BATCH_SIZE + 1} ({batch_start+1}–{batch_start+len(batch)}/{len(chunks)})")

        to_embed = []
        to_skip = []
        for chunk in batch:
            src = chunk.get("source_url", "")
            title = chunk.get("title", "")
            if chunk_exists(src, title):
                log(f"  SKIP (exists): {title[:60]}")
                to_skip.append(True)
                skipped += 1
            else:
                to_skip.append(False)
                to_embed.append(chunk)

        if not to_embed:
            continue

        try:
            log(f"  Embedding {len(to_embed)} chunks via Ollama …")
            texts = [f"{c['title']}\n{c['content']}" for c in to_embed]
            embeddings = embed_batch(texts)
        except Exception as e:
            log(f"  ERROR embedding batch: {e}")
            errors += len(to_embed)
            continue

        for chunk, emb in zip(to_embed, embeddings):
            try:
                insert_chunk(chunk, emb)
                log(f"  INSERT: {chunk.get('title', '')[:60]}")
                inserted += 1
            except Exception as e:
                log(f"  ERROR inserting '{chunk.get('title', '')}': {e}")
                errors += 1

    log(f"\nDone — inserted: {inserted}, skipped: {skipped}, errors: {errors}")


if __name__ == "__main__":
    main()
