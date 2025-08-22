#!/usr/bin/env python3
import argparse, socket, sys, time
from typing import Optional

DEFAULT_PORT = 6001
DEFAULT_TIMEOUT = 3.0
IDLE_MS = 200

# ---------- framing ----------
def checksum(length_byte: int, payload: bytes) -> int:
    s = (length_byte + sum(payload)) & 0xFF
    return (-s) & 0xFF

def build_frame(payload: bytes) -> bytes:
    ln = len(payload)
    return bytes([0x02, ln]) + payload + bytes([checksum(ln, payload)])

def b2h(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)

def hexstr_to_bytes(s: str) -> bytes:
    s = s.replace(',', ' ').replace(':', ' ').replace('-', ' ')
    parts = s.split()
    if len(parts) == 1 and all(c in "0123456789abcdefABCDEF" for c in s) and len(s) % 2 == 0:
        return bytes.fromhex(s)
    return bytes(int(p, 16) for p in parts)

# ---------- io ----------
def recv_burst(sock: socket.socket, total_timeout: float) -> bytes:
    sock.settimeout(total_timeout)
    data = bytearray()
    t_end = time.time() + total_timeout
    while time.time() < t_end:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
            t_idle = time.time() + IDLE_MS / 1000.0
            while time.time() < t_idle:
                sock.settimeout(max(0.01, t_idle - time.time()))
                try:
                    more = sock.recv(4096)
                    if not more:
                        break
                    data.extend(more)
                    t_idle = time.time() + IDLE_MS / 1000.0
                except socket.timeout:
                    break
            break
        except socket.timeout:
            break
    return bytes(data)

def send_tcp(host: str, port: int, payload: bytes, timeout: float, preamble_fe: bool, linger: bool) -> bytes:
    fr = build_frame(payload)
    with socket.create_connection((host, port), timeout=timeout) as s:
        if preamble_fe:
            try:
                s.sendall(bytes([0xFE]))  # wake/keepalive for some ES units
                time.sleep(0.05)
            except OSError:
                pass
        s.sendall(fr)
        if linger:
            return recv_burst(s, timeout)
        s.settimeout(0.2)
        try:
            return s.recv(1024)
        except socket.timeout:
            return b""

def open_and_hold(host: str, port: int, timeout: float, seconds: float, send_keepalive_fe: bool=True) -> bytes:
    collected = bytearray()
    with socket.create_connection((host, port), timeout=timeout) as s:
        t_end = time.time() + seconds
        s.settimeout(0.2)
        while time.time() < t_end:
            if send_keepalive_fe:
                try: s.sendall(bytes([0xFE]))
                except OSError: pass
            try:
                chunk = s.recv(4096)
                if chunk:
                    collected.extend(chunk)
            except socket.timeout:
                pass
            time.sleep(0.2)
    return bytes(collected)

# ---------- reply parsing ----------
def checksum_ok(frame: bytes) -> bool:
    if len(frame) < 4 or frame[0] != 0x02:
        return False
    ln = frame[1]
    if 2 + ln >= len(frame):
        return False
    payload = frame[2:2+ln]
    chk = frame[2+ln]
    return checksum(ln, payload) == chk

def decode_a8_status(payload: bytes) -> str:
    # Light helper for A8 82 … notifications (model-specific; we just print fields).
    if len(payload) >= 2 and payload[0] == 0xA8 and payload[1] == 0x82:
        fields = payload[2:]
        tail = f" flags=0x{fields[-1]:02X}" if fields else ""
        return f"A8 82 status fields: {b2h(fields)}{tail}"
    return ""

def parse_and_print(raw: bytes):
    if not raw:
        print("Reply: <no data>")
        return
    print(f"Raw ({len(raw)}): {b2h(raw)}")
    i = 0
    idx = 0
    while i < len(raw):
        if raw[i] == 0x02 and i + 1 < len(raw):
            ln = raw[i+1]
            end = i + 2 + ln
            chk_idx = end
            if chk_idx < len(raw):
                frame = raw[i:chk_idx+1]
                ok = "OK" if checksum_ok(frame) else "BAD"
                payload = frame[2:2+ln]
                extra = decode_a8_status(payload)
                if extra:
                    print(f"  Frame[{idx}]: {b2h(frame)}  ({ok}) | {extra}")
                else:
                    print(f"  Frame[{idx}]: {b2h(frame)}  ({ok}) | payload {b2h(payload)}")
                idx += 1
                i = chk_idx + 1
                continue
        print(f"  Byte: {raw[i]:02X}")
        i += 1

# ---------- DA3600ES commands ----------
def cmd_power(on: bool) -> bytes:                 # 02 04 A0 60 00 01 FB / ... 00 FC
    return bytes([0xA0, 0x60, 0x00, 0x01 if on else 0x00])

def cmd_input_value(v: int) -> bytes:             # 02 04 A0 42 00 <value> <chk>
    return bytes([0xA0, 0x42, 0x00, v & 0xFF])

def cmd_volume(up: bool) -> bytes:                # 02 03 A0 55 00 08 / 02 03 A0 56 00 07
    return bytes([0xA0, 0x55 if up else 0x56, 0x00])

def qry_power() -> bytes:                         # often ignored; notifications come as A8 82 …
    return bytes([0xA1, 0x00])

# Source map (from RTI driver “Source Selections”; values are $xx)  :contentReference[oaicite:4]{index=4}
INPUT_MAP = {
    "tuner":0x00, "phono":0x01, "cd":0x02, "dat":0x03, "md":0x04,
    "tape1":0x05, "tape2":0x06, "digital1":0x07, "digital2":0x08, "digital3":0x09,
    "aux1":0x0A, "aux2":0x0B, "md_wm":0x0C, "md2":0x0D, "ms":0x0E, "source":0x0F,
    "video1":0x10, "video2":0x11, "video3":0x12, "video4":0x13, "video5":0x14,
    "ld":0x15, "sat_tv":0x16, "dbs":0x17, "vcd":0x18, "dvd":0x19, "tv":0x1A,
    "bd":0x1B, "game":0x1C, "multi_in":0x20,
    "hdmi1":0x21, "hdmi2":0x22, "hdmi3":0x23, "hdmi4":0x24, "hdmi5":0x25, "hdmi6":0x26,
    "xm_radio":0x2A, "dm_port1":0x2B, "dm_port2":0x2C, "sirius":0x2D,
    "fm":0x2E, "am":0x2F,
    "server":0x30, "rhapsody":0x31, "shoutcast":0x32, "bluetooth":0x33, "usb":0x34,
    "airplay":0x35, "music_media":0x36, "video_media":0x37, "photo_media":0x38,
    "internet_contents":0x39, "internet_music":0x3A, "internet_video":0x3B, "internet_photo":0x3C,
    "network":0x3D, "sen":0x3E, "stb":0x3F,  # STB appears in the RTI map as well  :contentReference[oaicite:5]{index=5}
}

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="Sony STR-DA3600ES IP control (power/volume/query + full source commands)")
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    # defaults: FE + linger enabled (disable if you want)
    ap.add_argument("--no-preamble-fe", action="store_true", help="Disable FE wake byte (default: enabled)")
    ap.add_argument("--no-linger", action="store_true", help="Disable linger read (default: enabled)")

    sub = ap.add_subparsers(dest="mode", required=True)

    # Core commands
    sp_pwr = sub.add_parser("power");   sp_pwr.add_argument("state", choices=["on","off"])
    sp_vol = sub.add_parser("volume");  sp_vol.add_argument("step", choices=["up","down"])
    sp_raw = sub.add_parser("raw");     sp_raw.add_argument("payload_hex", help="Hex payload, e.g. 'A0 42 00 21'")

    # Query + monitor
    sp_q = sub.add_parser("query", help="Best-effort queries (receiver often emits FE / A8xx)")
    sp_q.add_argument("what", choices=["power","raw"])
    sp_q.add_argument("--hold", type=float, default=3.0, help="Seconds to keep link open & listen (default 3s)")
    sp_q.add_argument("--payload", help="Hex for 'query raw' (e.g. 'A1 00')")

    sp_mon = sub.add_parser("monitor", help="Open and print all frames for N seconds")
    sp_mon.add_argument("--seconds", type=float, default=10.0)
    sp_mon.add_argument("--no-fe", action="store_true", help="Disable periodic FE keepalive while monitoring")

    # One-word source commands: add a subparser for every item in INPUT_MAP
    # Also keep an 'input' umbrella command for flexibility.
    sp_input = sub.add_parser("input", help="Generic input selection")
    g = sp_input.add_mutually_exclusive_group(required=True)
    g.add_argument("--name", choices=sorted(INPUT_MAP.keys()))
    g.add_argument("--code", help="Hex like '21' or '0x21'")

    # dynamically create subparsers like 'md', 'cd', 'tv', 'hdmi1', 'fm', ...
    simple_cmds = {}
    for name, code in INPUT_MAP.items():
        sp = sub.add_parser(name, help=f"Select {name.replace('_',' ').upper()}")
        simple_cmds[name] = code

    args = ap.parse_args()
    use_preamble = not args.no_preamble_fe
    use_linger   = not args.no_linger

    def run(payload: bytes, linger_override: Optional[bool] = None) -> bytes:
        fr = build_frame(payload)
        print(f"Send:   {b2h(fr)}  (payload {b2h(payload)})")
        try:
            rep = send_tcp(args.host, args.port, payload, args.timeout,
                           use_preamble, use_linger if linger_override is None else bool(linger_override))
        except OSError as e:
            print(f"Send error: {e}", file=sys.stderr); sys.exit(1)
        parse_and_print(rep)
        return rep

    # Core
    if args.mode == "power":
        run(cmd_power(args.state == "on")); sys.exit(0)

    if args.mode == "volume":
        run(cmd_volume(args.step == "up")); sys.exit(0)

    if args.mode == "raw":
        run(hexstr_to_bytes(args.payload_hex)); sys.exit(0)

    # Generic input
    if args.mode == "input":
        if args.name:
            code = INPUT_MAP[args.name]
        else:
            code = int(args.code, 16)
        run(cmd_input_value(code)); sys.exit(0)

    # One-word inputs
    if args.mode in simple_cmds:
        run(cmd_input_value(simple_cmds[args.mode])); sys.exit(0)

    # Query & monitor
    if args.mode == "query":
        if args.what == "power":
            print("Querying power (A1 00) and listening for A8xx…")
            run(qry_power(), linger_override=True)
            raw = open_and_hold(args.host, args.port, args.timeout, args.hold, send_keepalive_fe=True)
            parse_and_print(raw); sys.exit(0)
        elif args.what == "raw":
            if not args.payload:
                print("Provide --payload for 'query raw' (e.g. --payload 'A1 00')", file=sys.stderr)
                sys.exit(2)
            run(hexstr_to_bytes(args.payload), linger_override=True)
            raw = open_and_hold(args.host, args.port, args.timeout, args.hold, send_keepalive_fe=True)
            parse_and_print(raw); sys.exit(0)

    if args.mode == "monitor":
        secs = args.seconds
        print(f"Monitoring {args.host}:{args.port} for {secs:.1f}s… (FE keepalive: {'off' if args.no_fe else 'on'})")
        raw = open_and_hold(args.host, args.port, args.timeout, secs, send_keepalive_fe=(not args.no_fe))
        parse_and_print(raw); sys.exit(0)

if __name__ == "__main__":
    main()
