#!/usr/bin/env python3
"""
check_network.py — Quick network sanity check before using local resources.

Returns exit code 0 if on home network, 1 if on guest/wrong network.
"""

import subprocess
import sys

GUEST_NETWORKS = ["Gäste-WLAN", "Gaeste-WLAN", "Guest"]
HOME_RESOURCES = {
    "Steve": "192.168.2.49",
    "Qdrant": "192.168.2.191",
    "Watercooler": "192.168.2.55",
}


def get_current_wifi() -> str | None:
    """Get current WiFi SSID on Windows. Returns None if unavailable (needs admin/location)."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Check for permission error
        if "error 5" in result.stderr.lower() or "location" in result.stderr.lower():
            return None  # Can't read SSID, fall back to ping check
        for line in result.stdout.splitlines():
            if "SSID" in line and "BSSID" not in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
    except Exception:
        pass
    return None


def ping_host(ip: str, timeout_ms: int = 1000) -> bool:
    """Quick ping check."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout_ms), ip],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


def main() -> int:
    ssid = get_current_wifi()

    if ssid:
        print(f"Current WiFi: {ssid}")
        if any(guest in ssid for guest in GUEST_NETWORKS):
            print(f"\n[!] You're on guest WiFi ({ssid})")
            print("    No access to: Steve, Qdrant, Watercooler")
            print("    Switch to home network for full functionality")
            return 1
    else:
        print("Current WiFi: (needs admin to read SSID, checking by ping)")

    print("\nHome resources:")
    all_ok = True
    for name, ip in HOME_RESOURCES.items():
        ok = ping_host(ip)
        status = "[OK]" if ok else "[--]"
        print(f"  {status} {name} ({ip})")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nAll resources reachable")
        return 0
    else:
        print("\nSome resources unreachable (might be powered off)")
        return 0  # Still return 0 if on right network, just resources down


if __name__ == "__main__":
    sys.exit(main())
