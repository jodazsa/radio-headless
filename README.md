# radio-headless

A headless Raspberry Pi radio stack built around **MPD**, a **rotary hardware interface**, optional **web controls**, and unattended **station auto-updates**.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [System Requirements](#system-requirements)
3. [Quick Start (Fresh Pi)](#quick-start-fresh-pi)
4. [Day-2 Operations](#day-2-operations)
5. [How the System Works](#how-the-system-works)
6. [Repository Layout](#repository-layout)
7. [Configuration Reference](#configuration-reference)
8. [Services and Timers](#services-and-timers)
9. [Web Control](#web-control)
10. [Rotary Hardware Variant Notes](#rotary-hardware-variant-notes)
11. [Auto-Update Stations](#auto-update-stations)
12. [Local Music / Offline Content](#local-music--offline-content)
13. [Troubleshooting and Diagnostics](#troubleshooting-and-diagnostics)
14. [Extended Documentation](#extended-documentation)

---

## What This Project Does

This repository provisions and runs a Raspberry Pi as a radio appliance with:

- MPD playback engine
- Rotary hardware station/bank control
- I2C-based volume encoder support
- Systemd-managed runtime services
- Optional browser-based remote control UI/backend
- Daily (and boot-time) station list refresh from a configured source

---

## System Requirements

- Raspberry Pi running a Debian-based OS
  - **Recommended:** Raspberry Pi OS Lite 64-bit (Bookworm)
  - **Also acceptable:** Debian/RPi variants where install dependencies are available
- `apt`, `systemd`, `raspi-config`, and GPIO/I2C tooling
- Audio hat/DAC configuration compatible with Raspberry Pi boot config

---

## Quick Start (Fresh Pi)

### 1) Prepare OS image

Using Raspberry Pi Imager advanced settings, configure:

- Hostname
- Username/password
- Wi-Fi (optional at imaging time)
- SSH enabled

### 2) Clone repository and install

```bash
sudo apt-get update
sudo apt-get install -y git

cd ~
git clone https://github.com/jodazsa/radio-headless.git
cd radio-headless

chmod +x install-rotary.sh
./install-rotary.sh

sudo reboot
```

### 3) Verify after reboot

```bash
sudo systemctl status rotary-controller
sudo systemctl status mpd
systemctl status radio-update-stations.timer

i2cdetect -y 1
aplay -l

tail -f /home/radio/logs/rotary.log
tail -f /home/radio/logs/update-stations.log
```

---

## Day-2 Operations

### Update an existing installation

```bash
cd ~/radio-headless
./deploy-rotary.sh
```

### Pull latest code and redeploy

```bash
cd ~/radio-headless
git fetch origin
git pull --ff-only origin main
./deploy-rotary.sh
```

### Check service health

```bash
sudo systemctl is-active rotary-controller.service
sudo systemctl is-active mpd.service
sudo systemctl is-active radio-web-backend.service
systemctl is-active radio-update-stations.timer
```

### Follow logs

```bash
tail -f /home/radio/logs/rotary.log
sudo journalctl -u rotary-controller.service -f
sudo journalctl -u radio-update-stations.service -f
sudo journalctl -u radio-web-backend.service -f
```

---

## How the System Works

1. The install script provisions dependencies, runtime files, and systemd units.
2. `rotary-controller` reads hardware inputs and maps them to station/bank actions.
3. `radio-play` executes playback behavior via MPD.
4. `update-stations` refreshes `stations.yaml` from configured remote source.
5. Optional `pi_backend.py` exposes local HTTP endpoints/UI for network control.

---

## Repository Layout

### Root

- `README.md` – this consolidated guide
- `install-rotary.sh` – first-time provisioning script
- `deploy-rotary.sh` – update/redeploy script for already-installed systems

### Runtime scripts (`bin/`)

- `bin/rotary-controller` – main rotary hardware control loop
- `bin/radio-play` – playback command wrapper/dispatcher
- `bin/update-stations` – station auto-update logic + validation/backups
- `bin/radio_lib.py` – shared Python support code
- `bin/smoke-test-config` – quick config validation helper
- `bin/apply-network-config` – privileged network/hostname apply helper (provisioning flow)

### Configuration (`config/`)

- `config/stations.yaml` – station definitions and bank organization
- `config/hardware-rotary.yaml` – hardware mapping and behavior settings (including auto-update source)

### Service units (`systemd/`)

- `systemd/rotary-controller.service`
- `systemd/radio-update-stations.service`
- `systemd/radio-update-stations.timer`
- `systemd/radio-web-backend.service`

### Web UI/backend (`web/`)

- `web/radio.html` – web control UI
- `web/pi-music-controller.html` – music control UI variant
- `web/setup.html` – setup/provisioning UI
- `web/pi_backend.py` – Pi-hosted backend for control/setup endpoints

### System config templates (`etc/`)

- `etc/mpd.conf` – MPD config template/deployment source
- `etc/mpd` – supplemental MPD defaults
- `etc/sudoers.d/radio-provisioning` – restricted sudo permissions for provisioning helper

### Project docs (`docs/`)

- `docs/ROTARY-README.md`
- `docs/WEB-CONTROL.md`
- `docs/AUTO-UPDATE.md`
- `docs/MUSIC-TRANSFER.md`
- `docs/WIFI-PROVISIONING-DESIGN.md`
- `docs/REMOTE-RECOVERY-WIFI-LOSS.md`

---

## Configuration Reference

### `stations.yaml`

Defines station banks and station entries.

Station types used by this project include:

- `stream` (uses URL)
- `mp3_loop_random_start` (uses local `file`)
- `mp3_dir_random_start_then_in_order` (uses local `dir`)

### `hardware-rotary.yaml`

Defines hardware behavior and update source settings. Important section:

```yaml
auto_update:
  enabled: true
  github_url: "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/config/stations.yaml"
  local_path: "/home/radio/stations.yaml"
```

---

## Services and Timers

### Main services

- `rotary-controller.service` – hardware -> playback control loop
- `mpd.service` – playback daemon
- `radio-web-backend.service` – optional HTTP backend for browser control

### Update automation

- `radio-update-stations.service` – on-demand stations refresh task
- `radio-update-stations.timer` – schedule trigger (daily + shortly after boot)

Useful commands:

```bash
systemctl status radio-update-stations.timer
systemctl list-timers radio-update-stations.timer
sudo systemctl start radio-update-stations.service
```

---

## Web Control

The web control flow is:

**Browser -> `pi_backend.py` on Pi -> local radio commands/services**

Primary files:

- `web/radio.html`
- `web/pi_backend.py`
- `systemd/radio-web-backend.service`

See complete setup and troubleshooting in `docs/WEB-CONTROL.md`.

---

## Rotary Hardware Variant Notes

For wiring details, behavior, and variant-specific installation notes, read:

- `docs/ROTARY-README.md`

This includes BCD switch wiring, I2C encoder expectations (e.g. `0x36`), and operational behavior differences from encoder/OLED versions.

---

## Auto-Update Stations

The station updater can periodically fetch and validate a remote `stations.yaml`.

Core behavior:

- Download from configured URL
- Compare checksum with current file
- Validate structure before install
- Backup previous file (rolling history)
- Log to `/home/radio/logs/update-stations.log`

Details and recovery procedures are in `docs/AUTO-UPDATE.md`.

---

## Local Music / Offline Content

Local files are expected under:

- `/home/radio/audio`

Any `file:` or `dir:` entries in `stations.yaml` are resolved relative to that root.

See complete transfer examples (`scp`, `rsync`), permissions, and MPD refresh in:

- `docs/MUSIC-TRANSFER.md`

---

## Troubleshooting and Diagnostics

### Core checks

```bash
sudo systemctl status rotary-controller --no-pager
sudo journalctl -u rotary-controller.service -n 100 --no-pager
sudo journalctl -u radio-update-stations.service -n 100 --no-pager
```

### Hardware checks

```bash
i2cdetect -y 1
aplay -l
```

### Station update checks

```bash
tail -n 80 /home/radio/logs/update-stations.log
curl -I "<your stations yaml raw URL>"
```

### If local edits block `git pull`

```bash
git stash push -u -m "pi-local-changes"
git pull --ff-only origin main
./deploy-rotary.sh
```

---

## Extended Documentation

- Rotary details: `docs/ROTARY-README.md`
- Web control: `docs/WEB-CONTROL.md`
- Auto-updates: `docs/AUTO-UPDATE.md`
- Local music transfer: `docs/MUSIC-TRANSFER.md`
- Wi-Fi/hostname provisioning design: `docs/WIFI-PROVISIONING-DESIGN.md`
- Wi-Fi outage + no physical access recovery guide: `docs/REMOTE-RECOVERY-WIFI-LOSS.md`

If you are new to this project, read in this order:

1. This `README.md`
2. `docs/ROTARY-README.md`
3. `docs/AUTO-UPDATE.md`
4. `docs/WEB-CONTROL.md`
5. `docs/MUSIC-TRANSFER.md`
