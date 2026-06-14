import socket
import os


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def update_frontend_env(ip: str):
    env_path = os.path.join(
        os.path.dirname(__file__),
        "..", "frontend", ".env"
    )
    env_path = os.path.normpath(env_path)

    api_url = f"http://{ip}:8000"

    # Read existing .env if it exists
    existing = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for l in f:
                l = l.strip()
                if "=" in l and not l.startswith("#"):
                    k, v = l.split("=", 1)
                    existing[k.strip()] = v.strip()

    # Update the API URL
    existing["EXPO_PUBLIC_API_URL"] = api_url

    # Write back
    with open(env_path, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    print(f"Updated frontend/.env:")
    print(f"  EXPO_PUBLIC_API_URL={api_url}")
    return api_url


if __name__ == "__main__":
    ip = get_lan_ip()
    url = update_frontend_env(ip)
    print(f"LAN IP detected: {ip}")
    print(f"API URL set to: {url}")
