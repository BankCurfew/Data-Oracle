#!/usr/bin/env python3
"""
Embed kb_chunks rows that have NULL embeddings directly from Supabase.
Reads chunk_text from DB, generates BGE-M3 embeddings, updates in place.

Usage:
    python scripts/embed-missing.py              # embed all missing
    python scripts/embed-missing.py --dry-run    # preview only
"""

import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# BGE-M3 config
MODEL_NAME = "BAAI/bge-m3"
BATCH_SIZE = 8
MAX_LENGTH = 512

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def supabase_get(path):
    """GET request to Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    req = Request(url, headers=headers)
    with urlopen(req) as resp:
        return json.loads(resp.read())


def supabase_patch(path, data):
    """PATCH request to Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    body = json.dumps(data).encode()
    req = Request(url, data=body, headers=headers, method="PATCH")
    with urlopen(req) as resp:
        return resp.status


def main():
    dry_run = "--dry-run" in sys.argv

    # Fetch chunks missing embeddings
    print("Fetching chunks with missing embeddings...")
    rows = supabase_get("kb_chunks?embedding=is.null&select=id,source,document_name,chunk_index,chunk_text&order=id")
    print(f"Found {len(rows)} chunks missing embeddings")

    if not rows:
        print("Nothing to embed!")
        return

    # Group by source for reporting
    by_source = {}
    for r in rows:
        by_source.setdefault(r["source"], []).append(r)
    for src, chunks in by_source.items():
        print(f"  {src}: {len(chunks)} chunks")

    if dry_run:
        print("\n[DRY RUN] Would embed the above chunks. Exiting.")
        return

    # Load model
    print(f"\nLoading {MODEL_NAME} (CPU mode)...")
    start = time.time()
    from FlagEmbedding import BGEM3FlagModel
    model = BGEM3FlagModel(MODEL_NAME, use_fp16=False, device="cpu")
    print(f"Model loaded in {time.time() - start:.1f}s")

    # Embed and update each chunk
    total = len(rows)
    errors = 0
    for i, row in enumerate(rows):
        text = row["chunk_text"]
        chunk_id = row["id"]

        # Generate embedding
        output = model.encode(
            [text],
            batch_size=1,
            max_length=MAX_LENGTH,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense = output["dense_vecs"][0].tolist()
        sparse = {str(k): float(v) for k, v in output["lexical_weights"][0].items()}

        # Update row
        try:
            supabase_patch(
                f"kb_chunks?id=eq.{chunk_id}",
                {"embedding": dense, "sparse_embedding": sparse},
            )
            print(f"[{i+1}/{total}] {row['source']}/{row['document_name']} → embedded")
        except HTTPError as e:
            print(f"[{i+1}/{total}] {row['source']}/{row['document_name']} → ERROR: {e.code}")
            errors += 1

    elapsed = time.time() - start
    print(f"\nDone: {total - errors}/{total} embedded, {errors} errors, {elapsed:.1f}s")


if __name__ == "__main__":
    main()
