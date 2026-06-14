import urllib.request
import json
import sys
import time


def check_backend(url="http://localhost:8000"):
    try:
        req = urllib.request.urlopen(
            f"{url}/health", timeout=5
        )
        data = json.loads(req.read())
        if data.get("data", {}).get("status") == "ok":
            print(f"  Backend: OK ({url})")
            return True
    except Exception as e:
        print(f"  Backend: NOT READY ({e})")
        return False


def wait_for_backend(url="http://localhost:8000", max_wait=30):
    print(f"Waiting for backend at {url}...")
    for i in range(max_wait):
        if check_backend(url):
            return True
        time.sleep(1)
        sys.stdout.write(f"\r  Waiting... {i+1}s")
        sys.stdout.flush()
    print("\nBackend did not start in time")
    return False


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    success = wait_for_backend(url)
    sys.exit(0 if success else 1)
