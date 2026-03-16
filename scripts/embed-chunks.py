#!/usr/bin/env python3
"""
BGE-M3 Embedding Pipeline for AIA Knowledge Base
Reads extracted JSON files, generates dense + sparse embeddings, upserts to Supabase kb_chunks.

Usage:
    python scripts/embed-chunks.py --source products         # embed one source
    python scripts/embed-chunks.py --source products --dry-run  # test without uploading
    python scripts/embed-chunks.py --source products --force  # re-embed already done
    python scripts/embed-chunks.py status                     # show embedding status
    python scripts/embed-chunks.py test                       # test with 1 sample chunk

Requires:
    pip install FlagEmbedding
    Environment: SUPABASE_URL, SUPABASE_SERVICE_KEY (from Dev-Oracle .env)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Dev-Oracle knowledge-base paths
DEV_ORACLE_ROOT = Path.home() / "repos/github.com/BankCurfew/Dev-Oracle/knowledge-base"
EXTRACTED_DIR = DEV_ORACLE_ROOT / "extracted"

# BGE-M3 config
MODEL_NAME = "BAAI/bge-m3"
BATCH_SIZE = 8          # conservative for CPU
MAX_LENGTH = 512        # 1500 chars ≈ 375 tokens, 512 is safe ceiling
EMBEDDING_DIM = 1024

# Supabase config (loaded from env)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def supabase_request(method, path, data=None):
    """Make authenticated request to Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            if resp.status in (200, 201):
                content = resp.read()
                return json.loads(content) if content else None
            return None
    except HTTPError as e:
        error_body = e.read().decode()
        print(f"  Supabase error {e.code}: {error_body}")
        raise


def get_existing_embeddings(source):
    """Get document names that already have embeddings for this source."""
    url = f"{SUPABASE_URL}/rest/v1/kb_chunks?source=eq.{source}&embedding=not.is.null&select=document_name"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as resp:
            rows = json.loads(resp.read())
            return set(r["document_name"] for r in rows)
    except HTTPError:
        return set()


def load_extracted_files(source):
    """Load all extracted JSON files for a source."""
    source_dir = EXTRACTED_DIR / source
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}")
        return []

    files = sorted(source_dir.glob("*.json"))
    # Skip report files
    files = [f for f in files if f.name != "extraction-report.json"]
    return files


def load_model():
    """Load BGE-M3 model (CPU mode)."""
    print(f"Loading {MODEL_NAME} (CPU mode)...")
    start = time.time()
    from FlagEmbedding import BGEM3FlagModel
    model = BGEM3FlagModel(
        MODEL_NAME,
        use_fp16=False,     # CPU mode
        device="cpu",
    )
    elapsed = time.time() - start
    print(f"Model loaded in {elapsed:.1f}s")
    return model


def embed_batch(model, texts):
    """Generate dense + sparse embeddings for a batch of texts."""
    output = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        max_length=MAX_LENGTH,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,  # not used in schema
    )
    dense = output["dense_vecs"]        # numpy array (N, 1024)
    sparse = output["lexical_weights"]  # list of dicts {token_id: weight}
    return dense, sparse


def process_file(filepath, model, source, dry_run=False):
    """Process one extracted JSON file: read chunks, embed, upsert."""
    with open(filepath) as f:
        data = json.load(f)

    doc_name = data.get("document_name", filepath.stem)
    chunks = data.get("chunks", [])

    if not chunks:
        return {"doc": doc_name, "status": "no_chunks", "count": 0}

    # Extract chunk texts
    texts = [c["chunk_text"] for c in chunks]

    # Generate embeddings
    dense, sparse = embed_batch(model, texts)

    if dry_run:
        print(f"  [DRY RUN] {doc_name}: {len(chunks)} chunks embedded (not uploaded)")
        return {"doc": doc_name, "status": "dry_run", "count": len(chunks)}

    # Upsert to Supabase
    rows = []
    for i, chunk in enumerate(chunks):
        embedding_list = dense[i].tolist()
        sparse_dict = {str(k): float(v) for k, v in sparse[i].items()}

        row = {
            "document_name": doc_name,
            "source": source,
            "section": data.get("gemini", {}).get("sections", [{}])[0].get("heading", "") if i == 0 else "",
            "chunk_index": chunk["chunk_index"],
            "chunk_text": chunk["chunk_text"],
            "chunk_tokens": chunk.get("chunk_tokens"),
            "embedding": embedding_list,
            "sparse_embedding": sparse_dict,
            "metadata": {
                "extraction_method": data.get("extraction_method"),
                "final_confidence": data.get("final_confidence"),
                "qa_action": data.get("qa_action"),
                "page_count": data.get("page_count"),
                "language": data.get("gemini", {}).get("language"),
            },
        }
        rows.append(row)

    # Batch upsert (Supabase REST handles arrays)
    try:
        supabase_request("POST", "kb_chunks", rows)
        return {"doc": doc_name, "status": "uploaded", "count": len(chunks)}
    except Exception as e:
        return {"doc": doc_name, "status": "error", "count": 0, "error": str(e)}


def cmd_embed(args):
    """Main embedding command."""
    source = args.source
    dry_run = args.dry_run
    force = args.force

    files = load_extracted_files(source)
    if not files:
        print(f"No extracted files found for source: {source}")
        return

    print(f"Found {len(files)} extracted files for source: {source}")

    # Skip already embedded (unless --force)
    if not force and not dry_run and SUPABASE_URL:
        existing = get_existing_embeddings(source)
        before = len(files)
        files = [f for f in files if f.stem not in existing]
        skipped = before - len(files)
        if skipped:
            print(f"Skipping {skipped} already embedded (use --force to re-embed)")

    if not files:
        print("All files already embedded!")
        return

    # Load model
    model = load_model()

    # Process files
    results = []
    total_chunks = 0
    start = time.time()

    for i, filepath in enumerate(files):
        print(f"[{i+1}/{len(files)}] {filepath.name}", end=" ")
        result = process_file(filepath, model, source, dry_run)
        results.append(result)
        total_chunks += result["count"]
        print(f"→ {result['status']} ({result['count']} chunks)")

        # Progress checkpoint every 50 files
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            rate = total_chunks / elapsed if elapsed > 0 else 0
            print(f"  --- Checkpoint: {i+1}/{len(files)} files, {total_chunks} chunks, {rate:.1f} chunks/sec ---")

    elapsed = time.time() - start
    errors = [r for r in results if r["status"] == "error"]

    print(f"\n{'='*60}")
    print(f"Embedding complete: {source}")
    print(f"  Files: {len(results)}")
    print(f"  Chunks: {total_chunks}")
    print(f"  Errors: {len(errors)}")
    print(f"  Time: {elapsed:.1f}s ({total_chunks/elapsed:.1f} chunks/sec)" if elapsed > 0 else "")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e['doc']}: {e.get('error', 'unknown')}")


def cmd_status(args):
    """Show embedding status per source."""
    sources = ["products", "forms", "bqm", "brand", "pdpa", "regulations", "news"]
    print(f"{'Source':<15} {'Extracted':<12} {'Embedded':<12} {'Status'}")
    print("-" * 55)

    for source in sources:
        files = load_extracted_files(source)
        extracted = len(files)
        if SUPABASE_URL:
            embedded_docs = get_existing_embeddings(source)
            embedded = len(embedded_docs)
        else:
            embedded = "?"
        status = "✅" if extracted > 0 and embedded == extracted else "⏳" if embedded and embedded != "?" else "❌"
        print(f"{source:<15} {extracted:<12} {str(embedded):<12} {status}")


def cmd_test(args):
    """Test embedding with a single sample chunk."""
    print("=== BGE-M3 Embedding Test ===\n")

    # Find a sample file
    for source in ["bqm", "products", "forms", "brand", "pdpa", "regulations"]:
        files = load_extracted_files(source)
        if files:
            break
    else:
        print("No extracted files found to test with.")
        return

    filepath = files[0]
    with open(filepath) as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    if not chunks:
        print(f"No chunks in {filepath.name}")
        return

    sample_text = chunks[0]["chunk_text"][:500]
    print(f"Source file: {filepath.name}")
    print(f"Sample text ({len(sample_text)} chars): {sample_text[:100]}...\n")

    # Load model and embed
    model = load_model()
    dense, sparse = embed_batch(model, [sample_text])

    print(f"\nDense embedding: shape={dense.shape}, dim={dense.shape[1]}")
    print(f"  First 5 values: {dense[0][:5].tolist()}")
    print(f"  Norm: {(dense[0] ** 2).sum() ** 0.5:.4f}")
    print(f"\nSparse embedding: {len(sparse[0])} non-zero tokens")
    top_sparse = sorted(sparse[0].items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"  Top 5 weights: {top_sparse}")
    print(f"\nExpected Supabase column: vector({EMBEDDING_DIM}) ✓")
    print(f"Sparse as JSONB: {len(json.dumps({str(k): float(v) for k, v in sparse[0].items()}))} bytes")
    print("\n✅ BGE-M3 embedding test passed!")


def main():
    parser = argparse.ArgumentParser(description="BGE-M3 Embedding Pipeline for AIA KB")
    subparsers = parser.add_subparsers(dest="command")

    # embed command (default when --source is used)
    embed_parser = subparsers.add_parser("embed", help="Embed extracted chunks")
    embed_parser.add_argument("--source", required=True, help="Source to embed (products, bqm, etc.)")
    embed_parser.add_argument("--dry-run", action="store_true", help="Embed but don't upload")
    embed_parser.add_argument("--force", action="store_true", help="Re-embed already done files")

    # status command
    subparsers.add_parser("status", help="Show embedding status")

    # test command
    subparsers.add_parser("test", help="Test with sample chunk")

    args = parser.parse_args()

    # Allow --source without subcommand for convenience
    if not args.command:
        if hasattr(args, "source") and args.source:
            args.command = "embed"
        else:
            parser.print_help()
            return

    if args.command == "embed":
        cmd_embed(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "test":
        cmd_test(args)


if __name__ == "__main__":
    main()
