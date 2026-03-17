#!/usr/bin/env python3
"""
Extract + Embed pipeline for PDFs in Supabase Storage.
Downloads PDFs that exist in kb_files but NOT in kb_chunks, extracts text,
chunks, generates BGE-M3 embeddings, and uploads to kb_chunks.

Usage:
    # Embed priority products (Pay Life, 20PayLink, Wealth Max, CI Plus)
    python scripts/embed-from-storage.py --priority

    # Embed all missing products
    python scripts/embed-from-storage.py --source products

    # Embed specific category
    python scripts/embed-from-storage.py --source products --category savings

    # Dry run (extract + chunk but don't embed/upload)
    python scripts/embed-from-storage.py --source products --dry-run

    # Embed a specific file
    python scripts/embed-from-storage.py --file "AIA_PayLife_Plus_Brochure.pdf"

Requires:
    pip install pymupdf FlagEmbedding
    Environment: SUPABASE_URL, SUPABASE_SERVICE_KEY
"""

import argparse
import json
import os
import sys
import time
import tempfile
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = "aia-knowledge-base"

# BGE-M3 config
MODEL_NAME = "BAAI/bge-m3"
BATCH_SIZE = 8
MAX_LENGTH = 512
EMBEDDING_DIM = 1024

# Chunking config
CHUNK_SIZE = 1200       # chars per chunk (~300 tokens)
CHUNK_OVERLAP = 200     # overlap between chunks


def supabase_rest(method, path, data=None, headers_extra=None):
    """Make authenticated request to Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    if headers_extra:
        headers.update(headers_extra)
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            content = resp.read()
            return json.loads(content) if content else None
    except HTTPError as e:
        error_body = e.read().decode()
        print(f"  REST error {e.code}: {error_body[:200]}")
        raise


def get_missing_files(source, category=None, skip_placeholders=True):
    """Get files in kb_files that have NO chunks in kb_chunks."""
    # Get all filenames from kb_files
    url = f"kb_files?source=eq.{source}&select=filename,storage_path,category,display_name_en"
    if category:
        url += f"&category=eq.{category}"
    files = supabase_rest("GET", url) or []

    # Get all document_names from kb_chunks for this source
    chunks_url = f"kb_chunks?source=eq.{source}&select=document_name"
    chunks = supabase_rest("GET", chunks_url) or []
    embedded_names = set(c["document_name"] for c in chunks)

    # Files that have no chunks
    missing = [f for f in files if f["filename"] not in embedded_names]

    # Optionally filter out known placeholders (files < 5KB from pre-scan)
    if skip_placeholders:
        try:
            import json as _json
            with open("/tmp/real_missing_products.json") as fp:
                real_names = {r["filename"] for r in _json.load(fp)}
            before = len(missing)
            missing = [f for f in missing if f["filename"] in real_names]
            skipped = before - len(missing)
            if skipped:
                print(f"  Skipped {skipped} placeholder files (<5KB)")
        except FileNotFoundError:
            pass  # No pre-scan data, process all

    return missing


def download_pdf(storage_path):
    """Download PDF from Supabase Storage. Returns bytes."""
    url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_path}"
    # URL-encode the path properly
    from urllib.parse import quote
    parts = storage_path.split("/")
    encoded_path = "/".join(quote(p, safe="") for p in parts)
    url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{encoded_path}"

    req = Request(url)
    try:
        with urlopen(req) as resp:
            return resp.read()
    except HTTPError as e:
        print(f"  Download error {e.code} for {storage_path}")
        return None


def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF bytes using pymupdf."""
    import pymupdf
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text.strip())
    doc.close()
    return pages


def chunk_text(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split pages into overlapping chunks."""
    # Join all pages with page separator
    full_text = "\n\n".join(pages)

    if not full_text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(full_text)

    while start < text_len:
        end = start + chunk_size

        # Try to break at sentence/paragraph boundary
        if end < text_len:
            # Look for paragraph break
            break_pos = full_text.rfind("\n\n", start + chunk_size // 2, end + 100)
            if break_pos == -1:
                # Look for sentence break
                break_pos = full_text.rfind(".", start + chunk_size // 2, end + 100)
            if break_pos == -1:
                break_pos = full_text.rfind(" ", start + chunk_size // 2, end + 100)
            if break_pos > start:
                end = break_pos + 1

        chunk_text = full_text[start:end].strip()
        if chunk_text and len(chunk_text) > 30:  # skip tiny fragments
            chunks.append({
                "chunk_text": chunk_text,
                "chunk_index": len(chunks),
                "chunk_tokens": len(chunk_text) // 4,  # rough estimate
            })

        start = end - overlap
        if start >= text_len:
            break

    return chunks


def load_model():
    """Load BGE-M3 model."""
    print(f"Loading {MODEL_NAME} (CPU mode)...")
    start = time.time()
    from FlagEmbedding import BGEM3FlagModel
    model = BGEM3FlagModel(MODEL_NAME, use_fp16=False, device="cpu")
    print(f"Model loaded in {time.time() - start:.1f}s")
    return model


def embed_batch(model, texts):
    """Generate dense + sparse embeddings."""
    output = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        max_length=MAX_LENGTH,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )
    return output["dense_vecs"], output["lexical_weights"]


LOCAL_FILES_DIR = Path.home() / "repos/github.com/BankCurfew/Dev-Oracle/knowledge-base/files"


def process_file(file_info, model, source, dry_run=False):
    """Download PDF (local first, then storage), extract, chunk, embed, upload."""
    filename = file_info["filename"]
    storage_path = file_info.get("storage_path", f"{source}/{filename}")
    category = file_info.get("category", "")
    product_name = file_info.get("display_name_en", "")

    # Try local file first (much faster than download)
    local_path = LOCAL_FILES_DIR / source / filename
    pdf_bytes = None
    if local_path.exists():
        pdf_bytes = local_path.read_bytes()
        if len(pdf_bytes) < 5000:
            pdf_bytes = None  # Likely placeholder

    # Fallback to Supabase Storage download
    if not pdf_bytes:
        pdf_bytes = download_pdf(storage_path)

    if not pdf_bytes:
        return {"doc": filename, "status": "download_error", "count": 0}

    if len(pdf_bytes) < 5000:
        return {"doc": filename, "status": "placeholder", "count": 0}

    # Extract text
    try:
        pages = extract_text_from_pdf(pdf_bytes)
    except Exception as e:
        return {"doc": filename, "status": "extract_error", "count": 0, "error": str(e)}

    if not pages:
        return {"doc": filename, "status": "no_text", "count": 0}

    # Chunk
    chunks = chunk_text(pages)
    if not chunks:
        return {"doc": filename, "status": "no_chunks", "count": 0}

    if dry_run:
        print(f"  [DRY] {filename}: {len(pages)} pages → {len(chunks)} chunks")
        return {"doc": filename, "status": "dry_run", "count": len(chunks), "pages": len(pages)}

    # Embed
    texts = [c["chunk_text"] for c in chunks]
    try:
        dense, sparse = embed_batch(model, texts)
    except Exception as e:
        return {"doc": filename, "status": "embed_error", "count": 0, "error": str(e)}

    # Build rows for Supabase
    rows = []
    for i, chunk in enumerate(chunks):
        embedding_list = dense[i].tolist()
        sparse_dict = {str(k): float(v) for k, v in sparse[i].items()}

        row = {
            "document_name": filename,
            "source": source,
            "section": "",
            "chunk_index": chunk["chunk_index"],
            "chunk_text": chunk["chunk_text"],
            "chunk_tokens": chunk.get("chunk_tokens"),
            "embedding": embedding_list,
            "sparse_embedding": sparse_dict,
            "product_name": product_name or None,
            "metadata": {
                "extraction_method": "pymupdf",
                "page_count": len(pages),
                "category": category,
                "pipeline": "embed-from-storage-v1",
            },
        }
        rows.append(row)

    # Upload to Supabase in batches of 50 (avoid payload too large)
    uploaded = 0
    for batch_start in range(0, len(rows), 50):
        batch = rows[batch_start:batch_start + 50]
        try:
            supabase_rest("POST", "kb_chunks", batch)
            uploaded += len(batch)
        except Exception as e:
            return {"doc": filename, "status": "upload_error", "count": uploaded, "error": str(e)}

    return {"doc": filename, "status": "ok", "count": uploaded, "pages": len(pages)}


# Priority product patterns for --priority mode
PRIORITY_PATTERNS = [
    # AIA Pay Life variants
    "PayLife", "Pay+Life", "Pay Life",
    # 20PayLink
    "20PayLink", "20Pay+Link",
    # Wealth Max
    "WealthMax", "Wealth+Max", "Wealth Max",
    # CI Plus
    "CI_Plus", "CI+Plus", "CIPlus", "CI Plus",
    # CI ProCare
    "CI_ProCare", "CIProCare", "CI ProCare", "CI+ProCare",
    # CI SuperCare
    "CI_SuperCare", "CISuperCare", "CI SuperCare", "CI+SuperCare",
    # Health Happy
    "Health_Happy", "HealthHappy", "Health Happy", "Health+Happy",
    # Health Starter
    "Health_Starter", "HealthStarter", "Health Starter", "Health+Starter",
    # Infinite Care
    "Infinite_Care", "InfiniteCare", "Infinite Care", "Infinite+Care",
    # Elite Income
    "Elite_Income", "EliteIncome", "Elite Income", "Elite+Income",
    # Legacy Prestige
    "Legacy_Prestige", "LegacyPrestige", "Legacy Prestige", "Legacy+Prestige",
    # Multi Pay CI
    "Multi_Pay_CI", "MultiPayCI", "Multi Pay CI", "Multi-Pay+CI", "MPCI",
    # Smart Select
    "Smart_Select", "SmartSelect", "Smart Select", "Smart+Select",
    # Smart Wealth
    "Smart_Wealth", "SmartWealth", "Smart Wealth", "Smart+Wealth",
    # Issara
    "Issara",
    # Protection 65
    "Protection65", "Protection_65", "Protection 65",
    # Annuity Sure / Saving Sure
    "AnnuitySure", "Annuity_Sure", "SavingSure", "Saving_Sure", "Saving+Sure",
    # Care for Cancer
    "CareforCancer", "Care_for_Cancer", "Care for Cancer", "Care+for+Cancer",
    # TPD
    "TPD",
    # HB Extra
    "HBExtra", "HB_Extra", "HB Extra", "HB+Extra",
    # Exclusive Wealth
    "ExclusiveWealth", "Exclusive_Wealth", "Exclusive+Wealth",
    # Infinite Gift / Wealth
    "InfiniteGift", "Infinite_Gift", "Infinite+Gift",
    "InfiniteWealth", "Infinite_Wealth", "Infinite+Wealth",
    # Vitality
    "Vitality",
    # Health Saver
    "HealthSaver", "Health_Saver", "Health Saver", "Health+Saver",
]


def is_priority(filename):
    """Check if filename matches priority patterns."""
    fn_lower = filename.lower()
    for pattern in PRIORITY_PATTERNS:
        if pattern.lower() in fn_lower:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Extract + Embed from Supabase Storage")
    parser.add_argument("--source", default="products", help="Source in kb_files (default: products)")
    parser.add_argument("--category", help="Filter by category (savings, ci, health, etc.)")
    parser.add_argument("--priority", action="store_true", help="Priority products only")
    parser.add_argument("--file", help="Embed a specific filename")
    parser.add_argument("--dry-run", action="store_true", help="Extract only, don't embed/upload")
    parser.add_argument("--limit", type=int, default=0, help="Max files to process (0=all)")
    parser.add_argument("--batch-report", type=int, default=20, help="Report progress every N files")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        print("  source ~/.../Dev-Oracle/.env")
        sys.exit(1)

    # Get missing files
    print(f"Scanning kb_files vs kb_chunks for source={args.source}...")
    missing = get_missing_files(args.source, args.category)
    print(f"Found {len(missing)} files missing embeddings")

    if args.file:
        missing = [f for f in missing if f["filename"] == args.file]
        if not missing:
            print(f"File '{args.file}' not found in missing list (may already be embedded)")
            sys.exit(1)

    if args.priority:
        priority = [f for f in missing if is_priority(f["filename"])]
        non_priority = [f for f in missing if not is_priority(f["filename"])]
        print(f"Priority filter: {len(priority)} priority, {len(non_priority)} non-priority")
        missing = priority  # Do priority first

    if args.limit > 0:
        missing = missing[:args.limit]

    if not missing:
        print("No files to process!")
        return

    print(f"\nProcessing {len(missing)} files...")

    # Load model (skip for dry-run)
    model = None if args.dry_run else load_model()

    # Process
    results = []
    total_chunks = 0
    errors = []
    start_time = time.time()

    for i, file_info in enumerate(missing):
        fn = file_info["filename"]
        cat = file_info.get("category", "?")
        print(f"[{i+1}/{len(missing)}] [{cat}] {fn}", end=" ", flush=True)

        result = process_file(file_info, model, args.source, args.dry_run)
        results.append(result)

        status = result["status"]
        count = result["count"]
        total_chunks += count

        if status == "ok":
            print(f"→ ✅ {count} chunks ({result.get('pages', '?')}p)")
        elif status == "dry_run":
            print(f"→ [DRY] {count} chunks ({result.get('pages', '?')}p)")
        else:
            print(f"→ ❌ {status}: {result.get('error', '')[:80]}")
            errors.append(result)

        # Batch progress report
        if (i + 1) % args.batch_report == 0:
            elapsed = time.time() - start_time
            rate = total_chunks / elapsed if elapsed > 0 else 0
            ok_count = sum(1 for r in results if r["status"] in ("ok", "dry_run"))
            print(f"\n  === Batch {(i+1)//args.batch_report}: {ok_count}/{i+1} ok, "
                  f"{total_chunks} chunks, {rate:.1f} chunks/s, "
                  f"{elapsed:.0f}s elapsed ===\n")

    # Final summary
    elapsed = time.time() - start_time
    ok_results = [r for r in results if r["status"] in ("ok", "dry_run")]
    no_text = [r for r in results if r["status"] == "no_text"]

    print(f"\n{'='*60}")
    print(f"COMPLETE: {args.source}" + (f" ({args.category})" if args.category else ""))
    print(f"  Processed: {len(results)} files")
    print(f"  Success:   {len(ok_results)} files, {total_chunks} chunks")
    print(f"  No text:   {len(no_text)} (image-only PDFs)")
    print(f"  Errors:    {len(errors)}")
    print(f"  Time:      {elapsed:.0f}s ({total_chunks/elapsed:.1f} chunks/s)" if elapsed > 0 else "")

    if errors:
        print(f"\nErrors:")
        for e in errors:
            print(f"  {e['doc']}: {e['status']} — {e.get('error', '')[:100]}")

    if no_text:
        print(f"\nNo-text PDFs (image-only, need OCR):")
        for r in no_text[:10]:
            print(f"  {r['doc']}")
        if len(no_text) > 10:
            print(f"  ... and {len(no_text) - 10} more")


if __name__ == "__main__":
    main()
