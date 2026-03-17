#!/usr/bin/env python3
"""
Embed iagencyaia.com scrape data into kb_chunks.
Source: Researcher-Oracle verified scrape (85 records)

Usage:
    python scripts/embed-iagency-scrape.py
    python scripts/embed-iagency-scrape.py --dry-run
"""

import json
import os
import sys
import time
import hashlib
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://heciyiepgxqtbphepalf.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
EMBED_URL = os.environ.get("EMBED_URL", "http://localhost:8100/embed")

INPUT_FILE = "/home/mbank/repos/github.com/BankCurfew/Researcher-Oracle/ψ/writing/research/iagencyaia-scrape-2026-03-18.json"
SOURCE_TAG = "iagencyaia-scrape-2026-03-18"
BATCH_SIZE = 32  # embedding service max 64, use 32 for safety


def supabase_request(path, method="GET", data=None, headers_extra=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if headers_extra:
        headers.update(headers_extra)
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode()) if resp.status != 201 else []
    except HTTPError as e:
        err = e.read().decode()
        print(f"  ERROR {e.code}: {err[:200]}")
        return None


def get_embeddings(texts):
    """Get dense + sparse embeddings from embedding-service."""
    data = json.dumps({"texts": texts, "return_dense": True, "return_sparse": True}).encode()
    req = Request(EMBED_URL, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            dense = result.get("dense", result.get("embeddings", []))
            sparse = result.get("sparse", [])
            return dense, sparse
    except Exception as e:
        print(f"  Embedding error: {e}")
        return None, None


def check_existing():
    """Check which records already exist (by source tag)."""
    path = f"kb_chunks?select=id,storage_path&source=eq.{SOURCE_TAG}"
    result = supabase_request(path)
    if result:
        return {r.get("storage_path") for r in result}
    return set()


def main():
    dry_run = "--dry-run" in sys.argv

    if not SUPABASE_KEY:
        print("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Load data
    with open(INPUT_FILE) as f:
        records = json.load(f)
    print(f"Loaded {len(records)} records from {INPUT_FILE}")

    # Check existing
    existing = check_existing()
    print(f"Already in DB: {len(existing)} records with source={SOURCE_TAG}")

    # Prepare chunks
    chunks = []
    for r in records:
        # Build rich text for embedding: title + content
        text = f"{r['title']}\n\n{r['content']}"
        url = r.get("url", "")
        chunk_id = hashlib.sha256(f"{SOURCE_TAG}:{url}".encode()).hexdigest()[:16]

        if url in existing:
            continue

        chunks.append({
            "text": text,
            "record": r,
            "chunk_id": chunk_id,
        })

    print(f"New chunks to embed: {len(chunks)}")
    if not chunks:
        print("Nothing to do!")
        return

    if dry_run:
        print("\n=== DRY RUN — would embed these: ===")
        for c in chunks:
            r = c["record"]
            print(f"  [{r['category']}] {r['product_name']}: {r['title'][:60]}")
        return

    # Embed in batches
    success = 0
    failed = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        print(f"\nBatch {i // BATCH_SIZE + 1}: embedding {len(batch)} texts...")

        dense, sparse = get_embeddings(texts)
        if not dense or len(dense) != len(batch):
            print(f"  ERROR: got {len(dense) if dense else 0} embeddings for {len(batch)} texts")
            failed += len(batch)
            continue

        # Upload to kb_chunks (matching actual schema)
        rows = []
        for j, c in enumerate(batch):
            r = c["record"]
            row = {
                "document_name": r.get("title", "")[:255],
                "chunk_text": c["text"],
                "chunk_tokens": len(c["text"].split()),
                "embedding": dense[j],
                "product_name": r.get("product_name"),
                "category": r.get("category", "general"),
                "source": SOURCE_TAG,
                "storage_path": r.get("url", ""),
                "chunk_index": 0,
                "pdf_url": r.get("url", ""),
                "metadata": {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "type": r.get("type"),
                    "scraped_date": "2026-03-18",
                    "pipeline": "embed-iagency-scrape-v1",
                },
            }
            if sparse and j < len(sparse):
                row["sparse_embedding"] = sparse[j]
            rows.append(row)

        result = supabase_request(
            "kb_chunks",
            method="POST",
            data=rows,
            headers_extra={"Prefer": "return=minimal"},
        )
        if result is not None:
            success += len(batch)
            print(f"  Uploaded {len(batch)} chunks")
        else:
            failed += len(batch)

        # Rate limit
        if i + BATCH_SIZE < len(chunks):
            time.sleep(1)

    print(f"\n=== DONE ===")
    print(f"Success: {success}")
    print(f"Failed:  {failed}")
    print(f"Total in KB: {len(existing) + success}")


if __name__ == "__main__":
    main()
