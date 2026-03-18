#!/usr/bin/env python3
"""
Deduplicate kb_chunks in Supabase.
For each (source, chunk_text) group with duplicates, keeps the row with
the lowest id and deletes the rest.

Usage:
    python scripts/dedup-kb-chunks.py              # execute dedup
    python scripts/dedup-kb-chunks.py --dry-run    # preview only
"""

import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BATCH_SIZE = 50  # delete in batches


def supabase_request(method, path, data=None, headers_extra=None):
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
    with urlopen(req) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def main():
    dry_run = "--dry-run" in sys.argv

    # Find all duplicate groups using Supabase RPC or REST
    # We'll fetch all chunks ordered by source, chunk_text, id
    # and detect duplicates client-side (REST API doesn't support GROUP BY)
    print("Fetching all chunk ids + hashes for dedup analysis...")
    print("(This may take a moment for large datasets)")

    # Use postgres function via SQL if available, otherwise fetch all
    # Strategy: fetch id, source, md5(chunk_text) ordered, detect dupes
    offset = 0
    page_size = 1000
    all_rows = []

    while True:
        rows = supabase_request(
            "GET",
            f"kb_chunks?select=id,source,chunk_text&order=source,chunk_text,id&offset={offset}&limit={page_size}",
        )
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
        print(f"  Fetched {len(all_rows)} rows...")

    print(f"Total rows fetched: {len(all_rows)}")

    # Find duplicates: group by (source, chunk_text), keep lowest id
    seen = {}  # (source, chunk_text) -> lowest_id
    to_delete = []

    for row in all_rows:
        key = (row["source"], row["chunk_text"])
        if key in seen:
            to_delete.append(row["id"])
        else:
            seen[key] = row["id"]

    print(f"Unique chunks: {len(seen)}")
    print(f"Duplicate rows to delete: {len(to_delete)}")

    if not to_delete:
        print("No duplicates found!")
        return

    # Show breakdown by source
    source_counts = {}
    for row in all_rows:
        if row["id"] in set(to_delete):
            source_counts[row["source"]] = source_counts.get(row["source"], 0) + 1
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {src}: {cnt} duplicates to remove")

    if dry_run:
        print(f"\n[DRY RUN] Would delete {len(to_delete)} duplicate rows. Exiting.")
        return

    # Delete in batches
    deleted = 0
    errors = 0
    for i in range(0, len(to_delete), BATCH_SIZE):
        batch = to_delete[i : i + BATCH_SIZE]
        ids_csv = ",".join(str(x) for x in batch)
        try:
            supabase_request(
                "DELETE",
                f"kb_chunks?id=in.({ids_csv})",
                headers_extra={"Prefer": "return=minimal"},
            )
            deleted += len(batch)
            print(f"  Deleted {deleted}/{len(to_delete)}")
        except HTTPError as e:
            print(f"  ERROR deleting batch: {e.code}")
            errors += len(batch)

    print(f"\nDone: {deleted} deleted, {errors} errors")
    print(f"KB now has {len(seen)} unique chunks")


if __name__ == "__main__":
    main()
