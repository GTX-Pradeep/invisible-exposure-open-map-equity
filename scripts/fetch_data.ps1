<#
Download everything the pipeline needs, on Windows (PowerShell). Safe to rerun: existing files are skipped.

    cd "C:\Users\prajw\OneDrive\Documents\5 sem\ada\invisible-exposure-open-map-equity"
    powershell -ExecutionPolicy Bypass -File scripts\fetch_data.ps1            # steps 1-3 (local links + small downloads + ACS)
    powershell -ExecutionPolicy Bypass -File scripts\fetch_data.ps1 -Stream    # also steps 4-5 (cloud streaming, ~30-60 min)

Writes data/raw/MANIFEST.csv: every downloaded file with size, SHA-256 and the date it was fetched.
See docs/DATA_DOWNLOAD.md for what each dataset is.
#>
param([switch]$Stream)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"
function Step($n, $t) { Write-Host "`n=== $n. $t ===" -ForegroundColor Cyan }

# 0. Python environment
Step 0 "Python environment"
if (-not (Test-Path $py)) {
  py -3.11 -m venv .venv
  if (-not (Test-Path $py)) { py -m venv .venv }
  & $py -m pip install --upgrade pip
  & $py -m pip install -e ".[dev]" jupyter
}
$env:PYTHONPATH = "src"

# 1. Challenge data: link to the copy already in MapEquityChallenge (no 6 GB duplicate, no double OneDrive sync)
Step 1 "Challenge extracts and strata (local junctions)"
New-Item -ItemType Directory -Force data\raw\challenge | Out-Null
foreach ($d in "reference", "strata") {
  $dst = "data\raw\challenge\$d"; $src = (Resolve-Path "..\MapEquityChallenge\data\$d").Path
  if (Test-Path $dst) { Write-Host "  exists: $dst" } else { cmd /c mklink /J "$dst" "$src" | Out-Null; Write-Host "  linked: $dst -> $src" }
}
$need = @("reference\maricopa-az\maricopa-az-overture-buildings.parquet", "reference\maricopa-az\maricopa-az-overture-pois.parquet",
          "reference\maricopa-az\maricopa-az-sample-submission.csv", "strata\national\national-census-tract-table.parquet",
          "strata\national\national-strata-tract-table.parquet", "strata\maricopa-az\maricopa-az-census-tracts.parquet")
foreach ($f in $need) { if (-not (Test-Path "data\raw\challenge\$f")) { throw "missing challenge file: $f" } }

# 2. Small public downloads
Step 2 "LODES 2022, Business Patterns 2023, ZCTA-tract file"
New-Item -ItemType Directory -Force data\raw\lodes, data\raw\cbp | Out-Null
$files = @{}
foreach ($st in "az", "ca", "nm", "ok", "tx", "wa") {
  $files["data\raw\lodes\$($st)_wac_S000_JT00_2022.csv.gz"] = "https://lehd.ces.census.gov/data/lodes/LODES8/$st/wac/$($st)_wac_S000_JT00_2022.csv.gz"
}
$files["data\raw\cbp\zbp23totals.zip"] = "https://www2.census.gov/programs-surveys/cbp/datasets/2023/zbp23totals.zip"
$files["data\raw\cbp\cbp23co.zip"] = "https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip"
$files["data\raw\cbp\tab20_zcta520_tract20_natl.txt"] = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt"
foreach ($k in $files.Keys) {
  if ((Test-Path $k) -and ((Get-Item $k).Length -gt 0)) { Write-Host "  exists: $k"; continue }
  Write-Host "  downloading $k"
  curl.exe -sSfL --retry 3 -o $k $files[$k]
  if ($LASTEXITCODE) { throw "download failed: $($files[$k])" }
}
if (-not (Test-Path data\raw\cbp\zbp23totals.txt)) { Expand-Archive data\raw\cbp\zbp23totals.zip -DestinationPath data\raw\cbp -Force }
if (-not (Test-Path data\raw\cbp\cbp23co.txt))     { Expand-Archive data\raw\cbp\cbp23co.zip     -DestinationPath data\raw\cbp -Force }

# 3. ACS 2020-2024 (national .dat files, reduced to tract parquet by the script)
Step 3 "ACS 2020-2024 five-year tables"
& $py -c "from coverage_risk.features import fetch_acs; fetch_acs()"
if ($LASTEXITCODE) { throw "ACS download failed" }

# 4-5. Cloud streaming (needs internet; DuckDB installs httpfs + spatial on first use)
if ($Stream) {
  Step 4 "USA Structures (streamed) and Business Patterns reference"
  New-Item -ItemType Directory -Force data\processed | Out-Null
  & $py scripts\00b_usa_structures_counts.py; if ($LASTEXITCODE) { throw "00b failed" }
  & $py scripts\00c_poi_reference.py;         if ($LASTEXITCODE) { throw "00c failed" }
  Step 5 "Overture counts: 2026-08 (local), 2026-10 and 2023 (streamed)"
  & $py scripts\01_count_overture.py --release r2026a; if ($LASTEXITCODE) { throw "r2026a failed" }
  & $py scripts\01_count_overture.py --release r2026b; if ($LASTEXITCODE) { throw "r2026b failed (Overture deletes releases after ~60 days)" }
  & $py scripts\01_count_overture.py --release r2023 --layer buildings; if ($LASTEXITCODE) { throw "r2023 failed" }
} else {
  Write-Host "`nSkipped cloud streaming. Rerun with -Stream before late December 2026 (Overture 2026-10-21.0 will be deleted)." -ForegroundColor Yellow
}

# Manifest of everything downloaded (not the linked challenge data, which has its own byte checks)
Step 6 "Manifest"
$rows = Get-ChildItem data\raw\lodes, data\raw\cbp, data\raw\acs -File -ErrorAction SilentlyContinue | ForEach-Object {
  [pscustomobject]@{ file = (Resolve-Path -Relative $_.FullName); bytes = $_.Length; sha256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(); fetched = $_.LastWriteTime.ToString("s") } }
if ($Stream) { $rows += Get-ChildItem data\processed -File -Filter *.parquet | ForEach-Object {
  [pscustomobject]@{ file = (Resolve-Path -Relative $_.FullName); bytes = $_.Length; sha256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(); fetched = $_.LastWriteTime.ToString("s") } } }
$rows | Export-Csv data\raw\MANIFEST.csv -NoTypeInformation
$rows | Format-Table -AutoSize
Write-Host "Done. Manifest: data\raw\MANIFEST.csv" -ForegroundColor Green
