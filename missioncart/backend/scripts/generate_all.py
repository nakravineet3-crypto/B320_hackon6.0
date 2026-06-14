"""Run every MissionCart simulated dataset generator in dependency order."""

import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "generate_users.py",
    "generate_purchases.py",
    "generate_dataset.py",
    "generate_occasions.py",
    "generate_prices.py",
    "generate_depletion.py",
]


def main() -> None:
    print("=== MISSIONCART DATASET GENERATION ===\n")
    for script_name in SCRIPTS:
        relative_name = f"scripts/{script_name}"
        print(f"Running {relative_name}...")
        result = subprocess.run(
            [sys.executable, str(BACKEND_DIR / "scripts" / script_name)],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print("  FAILED")
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip())
            raise SystemExit(result.returncode)

        print("  DONE")
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                print(f"  {line}")
        print()

    print("=== DATASET GENERATION COMPLETE ===")


if __name__ == "__main__":
    main()
