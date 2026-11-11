"""Re-download the four data.gov.sg datasets (needs internet; not used by tests or CI).

Writes data/raw/<name>.csv and data/raw/manifest.json. Data: Singapore Open Data Licence v1.0.
"""
import datetime as dt
import hashlib
import json
import time
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
DATASETS = {
    "va_per_worker_chained_annual": "d_43c4c89b056bc3b3959e4cf6771c2898",
    "va_per_hour_chained_annual": "d_c1fa91e0dd1a1960d5086a28ede16eea",
    "contracts_progress_annual": "d_cfda05718261fe933db5e14c2ca2d432",
    "cmp_work_permit": "d_4fb775d3cc311989261fae4ad22dde09",
}
HDR = {"User-Agent": "Mozilla/5.0 (open-data research script)"}


def get(url):
    for attempt in range(6):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(15)
    raise RuntimeError("rate limited: " + url)


def main():
    manifest = {"licence": "Singapore Open Data Licence v1.0, https://data.gov.sg/open-data-licence",
                "retrieved": dt.date.today().isoformat(), "datasets": {}}
    for name, did in DATASETS.items():
        meta = json.loads(get(f"https://api-production.data.gov.sg/v2/public/api/datasets/{did}/metadata"))["data"]
        for _ in range(6):
            url = json.loads(get(f"https://api-open.data.gov.sg/v1/public/api/datasets/{did}/poll-download"))["data"].get("url")
            if url:
                break
            time.sleep(8)
        body = get(url)
        (RAW / f"{name}.csv").write_bytes(body)
        manifest["datasets"][name] = {"datasetId": did, "name": meta["name"], "managedBy": meta.get("managedBy"),
                                      "lastUpdatedAt": meta.get("lastUpdatedAt"),
                                      "page": f"https://data.gov.sg/datasets/{did}/view",
                                      "sha256": hashlib.sha256(body).hexdigest()}
        time.sleep(5)
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
