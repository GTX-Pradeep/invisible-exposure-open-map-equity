"""DuckDB connection configured for cloud parquet (httpfs + spatial), proxy-aware."""
import os
import urllib.parse
from pathlib import Path

import duckdb

EXT_DIR = Path(os.environ.get("DUCKDB_EXT_DIR", Path.home() / ".duckext"))


def connect(threads: int | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for ext in ("httpfs", "spatial"):
        local = EXT_DIR / f"{ext}.duckdb_extension"
        try:
            con.sql(f"LOAD {ext}")
        except Exception:
            con.sql(f"INSTALL '{local}'" if local.exists() else f"INSTALL {ext}")
            con.sql(f"LOAD {ext}")
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        p = urllib.parse.urlparse(proxy)
        con.sql(f"SET http_proxy='{p.hostname}:{p.port}'")
    ca = os.environ.get("DUCKDB_CA_CERT", "/root/.ccr/ca-bundle.crt")
    if Path(ca).exists():
        con.sql(f"SET ca_cert_file='{ca}'")
    # public buckets: force anonymous S3 access (ignore any injected AWS creds)
    con.sql("CREATE OR REPLACE SECRET anon_s3 (TYPE s3, KEY_ID '', SECRET '', REGION 'us-west-2')")
    con.sql("SET http_retries=8; SET http_timeout=120000")
    if threads:
        con.sql(f"SET threads={threads}")
    return con


def source_coop_files(account: str, prefix: str, suffix: str = ".parquet") -> list[str]:
    """List files on Source Cooperative (S3-compatible proxy) as explicit https URLs."""
    import re
    import requests

    urls, token = [], None
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        x = requests.get(f"https://data.source.coop/{account}", params=params, timeout=60).text
        urls += [f"https://data.source.coop/{account}/{k}" for k in re.findall(r"<Key>([^<]+)</Key>", x) if k.endswith(suffix)]
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", x)
        if not m:
            return urls
        token = m.group(1)


def sql_list(urls: list[str]) -> str:
    return "[" + ",".join(f"'{u}'" for u in urls) + "]"
