#!/usr/bin/env python3
"""
Embedding Service Output-Based Health Check

Tests that the embedding service actually produces valid vectors,
not just returns HTTP 200. Catches the NaN bug from 2026-03-18.

Usage:
    python scripts/embed-health-check.py          # check and exit
    python scripts/embed-health-check.py --json    # machine-readable output
    python scripts/embed-health-check.py --fix     # restart service if unhealthy

Exit codes: 0 = healthy, 1 = unhealthy, 2 = unreachable
"""

import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

EMBED_URL = os.environ.get("EMBED_URL", "http://localhost:8100/embed")
HEALTH_URL = EMBED_URL.rsplit("/", 1)[0] + "/health"

TEST_SENTENCES = [
    "AIA Health Happy is a health insurance product with OPD coverage.",
    "ประกันสุขภาพแบบเหมาจ่าย คุ้มครองค่ารักษาพยาบาล",
]

EXPECTED_DIM = 1024
TIMEOUT = 30


def check_health_endpoint():
    """Check if /health endpoint responds."""
    try:
        req = Request(HEALTH_URL, method="GET")
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read())
            return {"reachable": True, "status": data.get("status", "unknown")}
    except (HTTPError, URLError, Exception) as e:
        return {"reachable": False, "error": str(e)}


def check_embedding_output():
    """Embed test sentences and validate output quality."""
    try:
        payload = json.dumps({
            "texts": TEST_SENTENCES,
            "return_dense": True,
            "return_sparse": True,
        }).encode()
        req = Request(EMBED_URL, data=payload, method="POST", headers={
            "Content-Type": "application/json",
        })

        start = time.time()
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read())
        latency_ms = int((time.time() - start) * 1000)

        # Extract dense embeddings
        dense = data.get("dense") or data.get("embeddings") or []
        if not dense:
            return {"valid": False, "error": "No dense embeddings in response", "latency_ms": latency_ms}

        issues = []
        for i, vec in enumerate(dense):
            if len(vec) != EXPECTED_DIM:
                issues.append(f"sentence[{i}]: dim={len(vec)}, expected={EXPECTED_DIM}")

            nan_count = sum(1 for v in vec if v != v)  # NaN check
            if nan_count > 0:
                issues.append(f"sentence[{i}]: {nan_count}/{len(vec)} NaN values")

            zero_count = sum(1 for v in vec if v == 0.0)
            if zero_count == len(vec):
                issues.append(f"sentence[{i}]: all zeros")

            # Check magnitude (should be roughly unit-normalized for BGE-M3)
            magnitude = sum(v * v for v in vec) ** 0.5
            if magnitude < 0.1 or magnitude > 10.0:
                issues.append(f"sentence[{i}]: unusual magnitude={magnitude:.4f}")

        # Check that different sentences produce different embeddings
        if len(dense) >= 2:
            dot = sum(a * b for a, b in zip(dense[0], dense[1]))
            if dot > 0.9999:
                issues.append("sentences produced identical embeddings")

        sparse = data.get("sparse", [])

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "latency_ms": latency_ms,
            "dim": len(dense[0]) if dense else 0,
            "vectors": len(dense),
            "sparse_count": len(sparse),
        }

    except (HTTPError, URLError, Exception) as e:
        return {"valid": False, "error": str(e)}


def main():
    json_mode = "--json" in sys.argv

    health = check_health_endpoint()
    embed = check_embedding_output()

    healthy = health.get("reachable", False) and embed.get("valid", False)

    if json_mode:
        result = {
            "healthy": healthy,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "health_endpoint": health,
            "embedding_output": embed,
        }
        print(json.dumps(result, indent=2))
    else:
        print("=== Embedding Service Health Check ===\n")

        # Health endpoint
        if health.get("reachable"):
            print(f"  /health endpoint: OK (status={health.get('status')})")
        else:
            print(f"  /health endpoint: UNREACHABLE ({health.get('error')})")

        # Embedding output
        if embed.get("valid"):
            print(f"  Embedding output: VALID")
            print(f"    dim={embed['dim']}, vectors={embed['vectors']}, latency={embed['latency_ms']}ms")
        elif "error" in embed:
            print(f"  Embedding output: ERROR — {embed['error']}")
        else:
            print(f"  Embedding output: INVALID")
            for issue in embed.get("issues", []):
                print(f"    - {issue}")

        print(f"\n  Result: {'HEALTHY' if healthy else 'UNHEALTHY'}")

    sys.exit(0 if healthy else (2 if not health.get("reachable") else 1))


if __name__ == "__main__":
    main()
