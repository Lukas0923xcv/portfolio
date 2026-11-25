#!/usr/bin/env python3
"""Writes status.json into the web root, read by the site to show live lab data.

    python3 write_status.py /etc/portfolio-status.json

Only uses the standard library. The config is a JSON file, see example-config.json.
Everything is optional: leave a key out and that line simply doesn't show on the site.
Nothing in the output names internal hosts or addresses.
"""
import datetime as dt
import json
import os
import socket
import struct
import sys
import tempfile
import urllib.request


def iso(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds")


def check_url(url, timeout=6):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "portfolio-status"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status < 500
    except urllib.error.HTTPError as e:
        return e.code < 500          # 401/403 from the login in front still means "up"
    except Exception:
        return False


def varint(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def read_varint(sock):
    n = shift = 0
    while True:
        b = sock.recv(1)[0]
        n |= (b & 0x7F) << shift
        if not b & 0x80:
            return n
        shift += 7


def minecraft(host, port=25565, timeout=4):
    """Server list ping (Java edition). Returns online, players, max."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            h = host.encode()
            hs = varint(0) + varint(767) + varint(len(h)) + h + struct.pack(">H", port) + varint(1)
            s.sendall(varint(len(hs)) + hs + varint(1) + varint(0))
            read_varint(s)
            read_varint(s)
            size = read_varint(s)
            data = b""
            while len(data) < size:
                chunk = s.recv(size - len(data))
                if not chunk:
                    break
                data += chunk
            info = json.loads(data)
            return {"online": True, "players": info["players"]["online"], "max": info["players"]["max"]}
    except Exception:
        return {"online": False, "players": 0, "max": 0}


def main():
    cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "/etc/portfolio-status.json"))
    out = {"updated": iso(dt.datetime.now().timestamp())}
    urls = cfg.get("service_urls", [])
    if urls:
        out["services"] = {"up": sum(check_url(u) for u in urls), "total": len(urls)}
    for key, path in (("backup_offsite", cfg.get("backup_stamp_file")), ("updates_last_run", cfg.get("updates_stamp_file"))):
        if path and os.path.exists(path):
            out[key] = iso(os.path.getmtime(path))
    if cfg.get("minecraft_host"):
        out["minecraft"] = minecraft(cfg["minecraft_host"], cfg.get("minecraft_port", 25565))
    target = cfg.get("output", "/var/www/portfolio/status.json")
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target))
    with os.fdopen(fd, "w") as f:
        json.dump(out, f)
    os.chmod(tmp, 0o644)
    os.replace(tmp, target)


if __name__ == "__main__":
    main()
