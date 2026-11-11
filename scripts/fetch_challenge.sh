#!/usr/bin/env bash
# Fetch challenge files (parquet only, plus tract-id csvs) with portable byte-size verification.
# Cross-platform: works on Linux, macOS, and Windows (Git Bash / WSL) without GNU stat or temp files.
set -euo pipefail

DEST="data/raw/challenge"
mkdir -p "$DEST"

if [ -d "$DEST/reference" ] && [ -d "$DEST/strata" ]; then
  echo "Notice: $DEST/reference and $DEST/strata already exist; verifying missing/incomplete files only."
fi

PY=$(command -v python3 || command -v python)
"$PY" - "$DEST" <<'PY'
import os, re, shutil, subprocess, sys, time, urllib.request

dest = sys.argv[1]
base = "https://data.source.coop/humane-intelligence"
url = f"{base}?list-type=2&prefix=bias-bounty-mapping-equity-challenge/&max-keys=1000"

with urllib.request.urlopen(url, timeout=60) as resp:
    xml = resp.read().decode("utf-8")

items = []
for k, s in re.findall(r"<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>", xml):
    if any(t in k for t in ("bulk-downloads", "roads", "rail", "infrastructure")):
        continue
    if k.endswith(".csv") and "geoids" not in k and "sample-submission" not in k:
        continue
    if "/strata/national/" in k and not any(
        t in k for t in ("strata-tract-table.parquet", "census-tract-table.parquet", "svi-tract", "tribal-tract-table", "ruca")
    ):
        continue
    items.append((k, int(s)))

curl = shutil.which("curl")
for k, size in items:
    rel = k.removeprefix("bias-bounty-mapping-equity-challenge/")
    out = os.path.join(dest, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out) == size:
        continue
    ok = False
    for attempt in range(4):
        try:
            if curl:
                subprocess.run([curl, "-sSfL", "-C", "-", "-o", out, f"{base}/{k}"], check=True)
            else:
                urllib.request.urlretrieve(f"{base}/{k}", out)
            if os.path.getsize(out) == size:
                ok = True
                break
        except Exception as exc:
            print(f"retry {attempt + 1} for {rel}: {exc}", file=sys.stderr)
        time.sleep(2 ** (attempt + 1))
    if not ok:
        raise SystemExit(f"SIZE MISMATCH or download failure: {rel} (expected {size} bytes)")

print(f"DONE ({len(items)} challenge files verified)")
PY
