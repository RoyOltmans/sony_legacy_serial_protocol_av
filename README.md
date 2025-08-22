# Sony STR-DA3600ES IP Control

Tiny Python CLI to control Sony ES receivers (tested on **STR-DA3600ES**) over TCP **port 6001** using the “Sony Binary Serial Protocol” (aka S-Control binary).  
It wraps raw payloads with the proper frame (`STX / LEN / PAYLOAD / CHECKSUM`) and adds niceties like **one-word input commands**, **best-effort query**, and a **monitor** mode.

> ✅ Confirmed working on STR-DA3600ES: Power, Volume ±, Source selection (CD/MD/TV/HDMI1-6/FM/AM/etc.)

---

## Features

- Power on/off (`A0 60 00 01/00`)
- Volume up/down (`A0 55/56 00`)
- One-word **source selection** (e.g., `cd`, `md`, `tv`, `hdmi1`, `fm`, …)
- Generic `input --name/--code` selector
- `query power` (best-effort; listens for A8xx notifications)
- `monitor` to passively print incoming frames
- `raw` to send any payload bytes you like
- **FE wake byte** and short **linger** reads enabled by default (can be disabled)

---

## Requirements

- Python **3.7+**
- Same LAN as the receiver
- Receiver’s IP control enabled (pre-2012 ES models typically use TCP **6001**)

---

## Install

```bash
git clone <your-repo-url> sony-es-ip
cd sony-es-ip
# drop the script in this folder as control.py if it's not already present
````

---

## Quick start

```bash
# Power
python control.py --host 192.168.2.31 power on
python control.py --host 192.168.2.31 power off

# Volume
python control.py --host 192.168.2.31 volume up
python control.py --host 192.168.2.31 volume down

# Inputs (one-word commands)
python control.py --host 192.168.2.31 cd
python control.py --host 192.168.2.31 md
python control.py --host 192.168.2.31 tv
python control.py --host 192.168.2.31 hdmi1

# Generic input selector
python control.py --host 192.168.2.31 input --name dvd
python control.py --host 192.168.2.31 input --code 21   # hex code (HDMI1)

# Best-effort power query (see notes below)
python control.py --host 192.168.2.31 query power --hold 3

# Monitor unsolicited notifications for 10s
python control.py --host 192.168.2.31 monitor --seconds 10
```

> By default the tool sends a **0xFE** wake/keepalive and **lingers** briefly to read replies. Disable with `--no-preamble-fe` / `--no-linger`.

---

## CLI Overview

```
usage: control.py --host HOST [--port 6001] [--timeout 3.0]
                  [--no-preamble-fe] [--no-linger]
                  {power,volume,raw,query,monitor,input, ...one-word sources...} ...

Core:
  power on|off                 # A0 60 00 01 / 00
  volume up|down               # A0 55 00 / A0 56 00
  raw "<hex payload>"          # send payload only; framing added for you
  input (--name NAME | --code HEX)
  query power|raw [--hold SECS] [--payload HEX]
  monitor [--seconds N] [--no-fe]

One-word source commands:
  cd, md, tv, dvd, bd, game, tuner, phono, fm, am, video1..video5,
  hdmi1..hdmi6, bluetooth, usb, network, server, sen, stb, ...
```

---

## Command details & payloads

### Power

| Action      | Payload       | Full frame             |
| ----------- | ------------- | ---------------------- |
| `power on`  | `A0 60 00 01` | `02 04 A0 60 00 01 FB` |
| `power off` | `A0 60 00 00` | `02 04 A0 60 00 00 FC` |

### Volume

| Action        | Payload    | Full frame          |
| ------------- | ---------- | ------------------- |
| `volume up`   | `A0 55 00` | `02 03 A0 55 00 08` |
| `volume down` | `A0 56 00` | `02 03 A0 56 00 07` |

### Inputs (sources)

All source buttons use: **`A0 42 00 <code>`** (main zone).
You can invoke them via **one-word commands** (e.g., `cd`) or `input --name NAME`.

| Name (command)      | Code | Example full frame     |
| ------------------- | ---- | ---------------------- |
| `tuner`             | 00   | `02 04 A0 42 00 00 1A` |
| `phono`             | 01   | `02 04 A0 42 00 01 19` |
| `cd`                | 02   | `02 04 A0 42 00 02 18` |
| `dat`               | 03   | `02 04 A0 42 00 03 17` |
| `md`                | 04   | `02 04 A0 42 00 04 16` |
| `tape1`             | 05   | `02 04 A0 42 00 05 15` |
| `tape2`             | 06   | `02 04 A0 42 00 06 14` |
| `digital1`          | 07   | `02 04 A0 42 00 07 13` |
| `digital2`          | 08   | `02 04 A0 42 00 08 12` |
| `digital3`          | 09   | `02 04 A0 42 00 09 11` |
| `aux1`              | 0A   | `02 04 A0 42 00 0A 10` |
| `aux2`              | 0B   | `02 04 A0 42 00 0B 0F` |
| `md_wm`             | 0C   | `02 04 A0 42 00 0C 0E` |
| `md2`               | 0D   | `02 04 A0 42 00 0D 0D` |
| `ms`                | 0E   | `02 04 A0 42 00 0E 0C` |
| `source`            | 0F   | `02 04 A0 42 00 0F 0B` |
| `video1`            | 10   | `02 04 A0 42 00 10 0A` |
| `video2`            | 11   | `02 04 A0 42 00 11 09` |
| `video3`            | 12   | `02 04 A0 42 00 12 08` |
| `video4`            | 13   | `02 04 A0 42 00 13 07` |
| `video5`            | 14   | `02 04 A0 42 00 14 06` |
| `ld`                | 15   | `02 04 A0 42 00 15 05` |
| `sat_tv`            | 16   | `02 04 A0 42 00 16 04` |
| `dbs`               | 17   | `02 04 A0 42 00 17 03` |
| `vcd`               | 18   | `02 04 A0 42 00 18 02` |
| `dvd`               | 19   | `02 04 A0 42 00 19 01` |
| `tv`                | 1A   | `02 04 A0 42 00 1A 00` |
| `bd`                | 1B   | `02 04 A0 42 00 1B FF` |
| `game`              | 1C   | `02 04 A0 42 00 1C FE` |
| `multi_in`          | 20   | `02 04 A0 42 00 20 FA` |
| `hdmi1`             | 21   | `02 04 A0 42 00 21 F9` |
| `hdmi2`             | 22   | `02 04 A0 42 00 22 F8` |
| `hdmi3`             | 23   | `02 04 A0 42 00 23 F7` |
| `hdmi4`             | 24   | `02 04 A0 42 00 24 F6` |
| `hdmi5`             | 25   | `02 04 A0 42 00 25 F5` |
| `hdmi6`             | 26   | `02 04 A0 42 00 26 F4` |
| `xm_radio`          | 2A   | `02 04 A0 42 00 2A F0` |
| `dm_port1`          | 2B   | `02 04 A0 42 00 2B EF` |
| `dm_port2`          | 2C   | `02 04 A0 42 00 2C EE` |
| `sirius`            | 2D   | `02 04 A0 42 00 2D ED` |
| `fm`                | 2E   | `02 04 A0 42 00 2E EC` |
| `am`                | 2F   | `02 04 A0 42 00 2F EB` |
| `server`            | 30   | `02 04 A0 42 00 30 EA` |
| `rhapsody`          | 31   | `02 04 A0 42 00 31 E9` |
| `shoutcast`         | 32   | `02 04 A0 42 00 32 E8` |
| `bluetooth`         | 33   | `02 04 A0 42 00 33 E7` |
| `usb`               | 34   | `02 04 A0 42 00 34 E6` |
| `airplay`           | 35   | `02 04 A0 42 00 35 E5` |
| `music_media`       | 36   | `02 04 A0 42 00 36 E4` |
| `video_media`       | 37   | `02 04 A0 42 00 37 E3` |
| `photo_media`       | 38   | `02 04 A0 42 00 38 E2` |
| `internet_contents` | 39   | `02 04 A0 42 00 39 E1` |
| `internet_music`    | 3A   | `02 04 A0 42 00 3A E0` |
| `internet_video`    | 3B   | `02 04 A0 42 00 3B DF` |
| `internet_photo`    | 3C   | `02 04 A0 42 00 3C DE` |
| `network`           | 3D   | `02 04 A0 42 00 3D DD` |
| `sen`               | 3E   | `02 04 A0 42 00 3E DC` |
| `stb`               | 3F   | `02 04 A0 42 00 3F DB` |

> Not every code is guaranteed to be enabled on every unit; unsupported ones usually NAK with `FD`.

---

## Querying state (best-effort)

Older ES receivers often **don’t** respond to `A1 00` with a neat `A2…` status.
Instead, they may send **`A8 82 …`** notifications when the state changes.

Use:

```bash
# Send A1 00 then keep the socket open to catch A8xx frames
python control.py --host <IP> query power --hold 3

# Or just passively listen while you change things on the front panel
python control.py --host <IP> monitor --seconds 10
```

The script prints raw frames and a hint for `A8 82 …`.
If you capture two distinct `A8 82 …` payloads (ON vs STANDBY), you can hard-map them to “Power: ON/OFF”.

---

## Raw mode

Send any payload you want (the script adds the frame wrapper + checksum):

```bash
# HDMI1 (same as `hdmi1`)
python control.py --host <IP> raw "A0 42 00 21"

# Power ON
python control.py --host <IP> raw "A0 60 00 01"
```

Tip: you can pass hex with spaces, commas, or continuous.

---

## Flags & defaults

* **FE wake byte**: **enabled** by default. Disable with `--no-preamble-fe`.
* **Linger** (read a short burst after send): **enabled** by default. Disable with `--no-linger`.
* `--timeout` (socket): defaults to `3.0` seconds.
* `--port`: defaults to `6001`.

---

## Protocol notes (framing & checksum)

Frames look like:

```
02 | LEN |  payload bytes…  | CHK
STX        (A0/A1/…)          two’s complement of (LEN + sum(payload)) & 0xFF
```

Examples:

* Power ON payload `A0 60 00 01`
  `LEN=04`, `(04 + A0+60+00+01) & FF = 0x05` → CHK = `-0x05 & FF = FB`
  Full frame: `02 04 A0 60 00 01 FB`

* HDMI1 payload `A0 42 00 21`
  `LEN=04` → CHK = `F9`
  Full frame: `02 04 A0 42 00 21 F9`

* Volume up payload `A0 55 00`
  `LEN=03` → CHK = `08`
  Full frame: `02 03 A0 55 00 08`

**Common replies**

* `FE` — trivial ack/keepalive (not a status).
* `FD` — NAK (command recognized but rejected in current context).
* `02 … A8 82 …` — unsolicited notification/status (model-specific fields).

---

## Troubleshooting

* **Only seeing `FE`**: Normal on this family. Use `monitor` or `query power --hold N` and look for `A8 82 …`.
* **`FD` (NAK)**: The input/service may be disabled on your unit. Try another code (e.g., HDMI/TV/CD/FM).
* **No reaction**:

  * Ensure the receiver is on the same LAN and IP is correct.
  * Keep using the defaults (FE + linger). If needed, try adding `--no-preamble-fe` or increasing `--timeout`.
  * Some models won’t power-on via IP from deep standby unless “Control over IP / Installer mode” is enabled in setup.
* **Windows**: Use `py -3 control.py ...` or full `python` path if multiple Pythons are installed.

---

## Extending

* To add more one-word commands, edit `INPUT_MAP` in `control.py`.
  The script auto-creates a subcommand for each entry.
* To add non-source functions (e.g., mute), wire new payload builders like:

  * `A0 10` (mute on), `A0 11` (mute off) and expose as a `mute on|off` subcommand.

---

## Disclaimer

This tool is intended for local control of your own hardware.
It doesn’t authenticate or encrypt; keep your receiver on a trusted network.
