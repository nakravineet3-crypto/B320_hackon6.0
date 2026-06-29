"""
Download Amazon Product Metadata 2023 (McAuley Lab, UCSD)

Run:
    python scripts/download_amazon_data.py

Output:
    backend/app/data/amazon_raw/  — 6 .jsonl.gz files

Total uncompressed size estimate: ~8-12 GB across all 6 files.
Runtime estimate: 20-60 minutes depending on connection.
"""

import os
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/meta_categories/"

FILES = [
    "meta_Health_and_Personal_Care.jsonl.gz",
    "meta_Grocery_and_Gourmet_Food.jsonl.gz",
    "meta_Pet_Supplies.jsonl.gz",
    "meta_Home_and_Kitchen.jsonl.gz",
    "meta_Toys_and_Games.jsonl.gz",
    "meta_Office_Products.jsonl.gz",
]

# Script lives in backend/scripts/, data lives in backend/app/data/
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR.parent / "app" / "data" / "amazon_raw"

CHUNK_SIZE = 1024 * 1024  # 1 MB chunks
TIMEOUT_SECONDS = 300
MIN_FILE_SIZE_BYTES = 1024 * 1024  # 1 MB minimum to pass corruption check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _format_speed(bps: float) -> str:
    return _format_bytes(int(bps)) + "/s"


def _eta_str(remaining_bytes: int, bps: float) -> str:
    if bps <= 0:
        return "??:??"
    secs = remaining_bytes / bps
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m"
    return f"{m:02d}m {s:02d}s"


def download_file(url: str, dest_path: Path) -> bool:
    """
    Stream-download url to dest_path with HTTP Range resume support.
    If a .tmp file already exists it sends Range: bytes=<size>- and appends.
    Returns True on success.
    """
    tmp_path = dest_path.with_suffix(".tmp")

    # Check for a partial download to resume
    existing_size = tmp_path.stat().st_size if tmp_path.exists() else 0
    headers: dict = {}
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"
        print(f"  Resuming from {_format_bytes(existing_size)}")

    try:
        response = requests.get(
            url, stream=True, timeout=TIMEOUT_SECONDS, headers=headers
        )
        # 416 = Range Not Satisfiable — file is already fully downloaded
        if response.status_code == 416:
            print(f"  Server says range not satisfiable — assuming file is complete.")
            tmp_path.rename(dest_path)
            return True
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        print(f"  HTTP error: {exc}")
        return False
    except requests.exceptions.ConnectionError as exc:
        print(f"  Connection error: {exc}")
        return False
    except requests.exceptions.Timeout:
        print(f"  Timed out after {TIMEOUT_SECONDS}s")
        return False

    # When the server honours the Range request it returns 206 and
    # Content-Length is the *remaining* bytes.  Reconstruct total_size.
    partial = response.status_code == 206
    content_length = int(response.headers.get("content-length", 0))
    total_size = (existing_size + content_length) if partial else content_length

    # If server ignored Range and sent 200, restart from scratch
    if existing_size > 0 and not partial:
        print("  Server ignored Range header — restarting from 0.")
        existing_size = 0

    downloaded = existing_size
    start_time = time.monotonic()
    last_print = start_time

    # Append to the .tmp file if resuming, otherwise overwrite
    open_mode = "ab" if existing_size > 0 else "wb"
    try:
        with open(tmp_path, open_mode) as fh:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    fh.write(chunk)
                    downloaded += len(chunk)

                    now = time.monotonic()
                    if now - last_print >= 2.0:  # print every 2 seconds
                        elapsed = now - start_time
                        bps = downloaded / elapsed if elapsed > 0 else 0
                        remaining = total_size - downloaded if total_size else 0
                        pct = f"{downloaded / total_size * 100:.1f}%" if total_size else "?%"
                        print(
                            f"  {pct}  {_format_bytes(downloaded)} / {_format_bytes(total_size)}"
                            f"  {_format_speed(bps)}  ETA {_eta_str(remaining, bps)}",
                            end="\r",
                            flush=True,
                        )
                        last_print = now

    except KeyboardInterrupt:
        # Do NOT delete the .tmp — keep it so the next run can resume
        print("\n  Interrupted — partial file kept for resume.")
        return False
    except OSError as exc:
        print(f"\n  Write error: {exc}")
        return False

    print()  # newline after progress line

    # Verify minimum size
    file_size = tmp_path.stat().st_size
    if file_size < MIN_FILE_SIZE_BYTES:
        print(f"  ERROR: file too small ({_format_bytes(file_size)}) — likely corrupt. Removing.")
        tmp_path.unlink(missing_ok=True)
        return False

    tmp_path.rename(dest_path)
    elapsed = time.monotonic() - start_time
    print(f"  Done: {_format_bytes(file_size)} in {elapsed:.0f}s")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}\n")

    total_start = time.monotonic()
    downloaded_count = 0
    skipped_count = 0
    failed_files: list[str] = []

    for filename in FILES:
        dest = OUTPUT_DIR / filename
        url = BASE_URL + filename

        print(f"[{FILES.index(filename) + 1}/{len(FILES)}] {filename}")

        # Idempotent: skip if already present and large enough
        if dest.exists() and dest.stat().st_size >= MIN_FILE_SIZE_BYTES:
            print(f"  Skipping — already downloaded ({_format_bytes(dest.stat().st_size)})")
            skipped_count += 1
            continue

        print(f"  Downloading from {url}")
        success = download_file(url, dest)
        if success:
            downloaded_count += 1
        else:
            failed_files.append(filename)

        print()

    total_elapsed = time.monotonic() - total_start
    print("=" * 60)
    print(f"Finished in {total_elapsed:.0f}s")
    print(f"  Downloaded : {downloaded_count}")
    print(f"  Skipped    : {skipped_count}")
    print(f"  Failed     : {len(failed_files)}")
    if failed_files:
        print("  Failed files:")
        for f in failed_files:
            print(f"    - {f}")
        sys.exit(1)
    else:
        print("\nAll files ready. Run next:")
        print("  python scripts/build_amazon_catalog.py")


if __name__ == "__main__":
    # Dependency check — give a helpful message before crashing
    try:
        import requests  # noqa: F401
    except ImportError:
        print("ERROR: 'requests' is not installed. Run:  pip install requests")
        sys.exit(1)

    main()
