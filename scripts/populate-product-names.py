#!/usr/bin/env python3
"""
P0 FIX: Populate product_name and aliases in kb_files and kb_chunks.
Uses AIA product master list + aliases to map filenames → canonical product names.

Usage:
    python scripts/populate-product-names.py --dry-run    # preview changes
    python scripts/populate-product-names.py              # apply changes
    python scripts/populate-product-names.py --check      # check current state
"""

import argparse
import json
import os
import sys
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# AIA data paths
AIA_ORACLE = os.path.expanduser("~/repos/github.com/BankCurfew/AIA-Oracle")
MASTER_LIST = f"{AIA_ORACLE}/ψ/active/knowledge-base/aia-products-master-list.json"
ALIASES_FILE = f"{AIA_ORACLE}/ψ/active/knowledge-base/aia-product-aliases.json"


def supabase_request(method, path, data=None):
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
            content = resp.read()
            return json.loads(content) if content else None
    except HTTPError as e:
        error_body = e.read().decode()
        print(f"  Error {e.code}: {error_body[:200]}")
        raise


def supabase_get(path):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    req = Request(url, headers=headers)
    with urlopen(req) as resp:
        return json.loads(resp.read())


def supabase_patch(table, filter_str, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filter_str}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    body = json.dumps(data).encode()
    req = Request(url, data=body, headers=headers, method="PATCH")
    try:
        with urlopen(req) as resp:
            return True
    except HTTPError as e:
        print(f"  PATCH error: {e.code} — {e.read().decode()[:200]}")
        return False


def build_filename_to_product_map():
    """Build a map from filename patterns to canonical product names."""
    # Load master list
    with open(MASTER_LIST) as f:
        master = json.load(f)

    # Load aliases
    with open(ALIASES_FILE) as f:
        aliases_data = json.load(f)

    # Build product lookup: id → product info
    products = {}
    for cat_key, cat_data in master["categories"].items():
        for prod in cat_data["products"]:
            products[prod["id"]] = {
                "name_en": prod["name_en"],
                "name_th": prod["name_th"],
                "category": prod.get("category", cat_key),
                "aliases_en": prod.get("aliases", []),
            }

    # Build alias → product map
    alias_map = {}
    for entry in aliases_data["aliases"]:
        pid = entry["id"]
        canonical = entry["canonical"]
        # Collect all aliases
        all_aliases = entry.get("aliases_en", []) + entry.get("aliases_th", [])
        all_aliases.append(canonical)
        for alias in all_aliases:
            alias_map[alias.lower()] = {
                "id": pid,
                "canonical": canonical,
                "name_en": products.get(pid.split("-")[0] + "-" + pid.split("-")[1] if "-" in pid else pid, {}).get("name_en", canonical),
            }

    # Build filename pattern matchers
    # These are tuples of (pattern, product_name_en, product_name_th)
    matchers = []

    for pid, prod in products.items():
        name_en = prod["name_en"]
        name_th = prod["name_th"]
        aliases = prod["aliases_en"]

        # Create regex patterns from product name and aliases
        patterns = [name_en] + aliases
        for pattern in patterns:
            # Convert to filename-safe regex: spaces → various separators
            # "AIA Pay Life Plus" → matches "AIA_Pay_Life_Plus", "AIA+Pay+Life+Plus", "AIAPayLifePlus"
            words = pattern.split()
            if len(words) > 1:
                # Match with various separators between words
                regex = r"[_+\s-]?".join(re.escape(w) for w in words)
                matchers.append((regex, name_en, name_th))
            else:
                matchers.append((re.escape(pattern), name_en, name_th))

    return matchers, products, aliases_data


def match_filename(filename, matchers):
    """Try to match a filename to a product."""
    fn_clean = filename.replace(".pdf", "").replace(".PDF", "")

    best_match = None
    best_len = 0

    for pattern, name_en, name_th in matchers:
        if re.search(pattern, fn_clean, re.IGNORECASE):
            # Prefer longer matches (more specific)
            if len(pattern) > best_len:
                best_match = (name_en, name_th)
                best_len = len(pattern)

    return best_match


def cmd_check(args):
    """Check current state of product_name in both tables."""
    print("=== kb_chunks ===")
    rows = supabase_get("kb_chunks?select=id,product_name&limit=5")
    print(f"  product_name column exists. Sample: {rows[:3]}")
    null_rows = supabase_get("kb_chunks?select=id&product_name=is.null")
    print(f"  Rows with NULL product_name: {len(null_rows)}")

    print("\n=== kb_files ===")
    # kb_files uses display_name_en / display_name_th instead of product_name
    rows = supabase_get("kb_files?select=id,display_name_en,display_name_th&limit=5")
    print(f"  display_name columns exist. Sample: {rows[:3]}")
    null_rows = supabase_get("kb_files?select=id&display_name_en=is.null")
    print(f"  Rows with NULL display_name_en: {len(null_rows)}")


def cmd_populate(args):
    """Populate product_name for all rows."""
    dry_run = args.dry_run

    print("Loading AIA product data...")
    matchers, products, aliases_data = build_filename_to_product_map()
    print(f"  {len(matchers)} filename matchers loaded")

    # Get all kb_files
    print("\nFetching kb_files...")
    files = supabase_get("kb_files?source=eq.products&select=id,filename,category,display_name_en&order=filename")
    print(f"  {len(files)} product files")

    # Match each file
    matched = 0
    unmatched = []
    updates = []

    for f in files:
        result = match_filename(f["filename"], matchers)
        if result:
            name_en, name_th = result
            updates.append({
                "id": f["id"],
                "filename": f["filename"],
                "product_name": name_en,
                "product_name_th": name_th,
            })
            matched += 1
        else:
            unmatched.append(f["filename"])

    print(f"\n  Matched: {matched}/{len(files)}")
    print(f"  Unmatched: {len(unmatched)}")

    if unmatched and len(unmatched) <= 30:
        print("\n  Unmatched files:")
        for fn in unmatched:
            print(f"    {fn}")

    if dry_run:
        print("\n[DRY RUN] Sample updates:")
        for u in updates[:20]:
            print(f"  {u['filename'][:60]} → {u['product_name']}")
        print(f"\n  Total: {len(updates)} files would be updated")
        return

    # Apply updates to kb_files (display_name_en + display_name_th)
    print(f"\nUpdating kb_files ({len(updates)} rows)...")
    ok = 0
    for u in updates:
        success = supabase_patch(
            "kb_files",
            f"id=eq.{u['id']}",
            {"display_name_en": u["product_name"], "display_name_th": u["product_name_th"]}
        )
        if success:
            ok += 1
        if ok % 50 == 0 and ok > 0:
            print(f"  Updated {ok}/{len(updates)} kb_files...")

    print(f"  Done: {ok}/{len(updates)} kb_files updated")

    # Now update kb_chunks with same mapping
    print(f"\nFetching kb_chunks...")
    chunks = supabase_get("kb_chunks?source=eq.products&select=id,document_name,product_name&order=document_name")
    print(f"  {len(chunks)} product chunks")

    chunk_updates = 0
    for chunk in chunks:
        result = match_filename(chunk["document_name"], matchers)
        if result:
            name_en, name_th = result
            success = supabase_patch(
                "kb_chunks",
                f"id=eq.{chunk['id']}",
                {"product_name": name_en}
            )
            if success:
                chunk_updates += 1
            if chunk_updates % 100 == 0 and chunk_updates > 0:
                print(f"  Updated {chunk_updates} kb_chunks...")

    print(f"  Done: {chunk_updates} kb_chunks updated")

    # Also update bot_summary and faq chunks
    print(f"\nUpdating bot_summary chunks...")
    bot_chunks = supabase_get("kb_chunks?source=eq.bot_summary&select=id,document_name")
    bot_updates = 0
    for chunk in bot_chunks:
        # bot_summary docs are like "bot_summary_health_happy"
        doc = chunk["document_name"]
        result = match_filename(doc.replace("bot_summary_", "").replace("_", " "), matchers)
        if result:
            success = supabase_patch("kb_chunks", f"id=eq.{chunk['id']}", {"product_name": result[0]})
            if success:
                bot_updates += 1
    print(f"  Done: {bot_updates} bot_summary chunks updated")

    # Store aliases as JSON in a new table or as metadata
    print(f"\nStoring aliases data...")
    store_aliases(aliases_data)

    print(f"\n{'='*60}")
    print(f"TOTAL: {ok} kb_files + {chunk_updates} kb_chunks + {bot_updates} bot_summary")


def store_aliases(aliases_data):
    """Store product aliases for search matching."""
    # Create/update a kb_product_aliases record per product
    for entry in aliases_data["aliases"]:
        canonical = entry["canonical"]
        all_aliases = entry.get("aliases_en", []) + entry.get("aliases_th", [])

        row = {
            "product_id": entry["id"],
            "canonical_name": canonical,
            "category": entry.get("category", ""),
            "aliases": all_aliases,
        }

        # Try upsert — if table doesn't exist, just log
        try:
            supabase_request("POST", "kb_product_aliases", row)
        except Exception as e:
            if "relation" in str(e).lower() or "42P01" in str(e):
                print("  kb_product_aliases table doesn't exist — aliases stored in kb_chunks metadata only")
                return
            # For other errors, continue
            pass

    # Also store generic category aliases
    for mapping in aliases_data.get("generic_category_aliases", {}).get("mappings", []):
        row = {
            "product_id": f"CAT-{mapping['map_to_category']}",
            "canonical_name": f"Category: {mapping['map_to_category']}",
            "category": mapping["map_to_category"],
            "aliases": mapping["query_patterns"],
        }
        try:
            supabase_request("POST", "kb_product_aliases", row)
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description="Populate product_name in KB tables")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    parser.add_argument("--check", action="store_true", help="Check current state")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        sys.exit(1)

    if args.check:
        cmd_check(args)
    else:
        cmd_populate(args)


if __name__ == "__main__":
    main()
