"""Download GDC files from a manifest without requiring gdc-client."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GDC_DATA_URL = "https://api.gdc.cancer.gov/data/{file_id}"


def download_file(file_id: str, filename: str, expected_size: int, outdir: Path, retries: int) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    destination = outdir / filename
    partial = destination.with_suffix(destination.suffix + ".part")

    if destination.exists() and expected_size and destination.stat().st_size == expected_size:
        print(f"SKIP complete {destination.name}")
        return

    if partial.exists():
        print(f"Removing partial file from previous attempt: {partial.name}")
        partial.unlink()

    url = GDC_DATA_URL.format(file_id=file_id)
    for attempt in range(1, retries + 1):
        try:
            print(f"DOWNLOAD {filename} attempt {attempt}/{retries}")
            request = Request(url, headers={"User-Agent": "pathology310-gdc-downloader"})
            with urlopen(request, timeout=180) as response, partial.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            if expected_size and partial.stat().st_size != expected_size:
                raise IOError(
                    f"Size mismatch for {filename}: got {partial.stat().st_size}, expected {expected_size}"
                )
            partial.replace(destination)
            print(f"DONE {destination.name}")
            return
        except (HTTPError, URLError, TimeoutError, IOError) as exc:
            print(f"ERROR {filename}: {exc}")
            if partial.exists():
                partial.unlink()
            if attempt == retries:
                raise
            time.sleep(30 * attempt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--retries", type=int, default=5)
    args = parser.parse_args()

    manifest = Path(args.manifest)
    outdir = Path(args.outdir)
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    total = sum(int(row.get("size") or 0) for row in rows)
    print(f"Files: {len(rows)}")
    print(f"Expected total GB: {total / 1024**3:.2f}")
    print(f"Output: {outdir}")

    for index, row in enumerate(rows, start=1):
        print(f"[{index}/{len(rows)}]")
        download_file(
            file_id=row["id"],
            filename=row["filename"],
            expected_size=int(row.get("size") or 0),
            outdir=outdir,
            retries=args.retries,
        )


if __name__ == "__main__":
    main()
