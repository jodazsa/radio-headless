# radio-headless

## Start Here: OS Recommendation and Fresh Install

Use a **Debian-based Raspberry Pi image**:

1. **Recommended:** Raspberry Pi OS Lite 64-bit based on **Debian Bookworm**.
2. **Also acceptable:** Raspberry Pi OS / Debian based on **Debian Trixie** (if all packages in `install-rotary.sh` are available).

Why this matters:
- The install scripts rely on `apt`, `systemd`, `raspi-config`, and Raspberry Pi GPIO/I2C tooling.
- Audio configuration expects Raspberry Pi boot config locations (`/boot/firmware/config.txt` or `/boot/config.txt`).

### Fresh OS Install + First Boot

1. Flash your SD card with **Raspberry Pi OS Lite (64-bit)** in Raspberry Pi Imager.
2. In the Imager advanced settings, set:
   - hostname
   - username/password
   - Wi-Fi credentials (if needed)
   - SSH enabled
3. Boot the Pi and SSH in.

### Bring This Repo Up on a Fresh System

```bash
# 0) Install git
sudo apt-get update
sudo apt-get install -y git

# 1) Get code
cd ~
git clone https://github.com/jodazsa/radio-headless.git
cd radio-headless

# 2) Run installer (as regular user, not root)
chmod +x install-rotary.sh
./install-rotary.sh

# 3) Reboot (required for audio/I2C changes)
sudo reboot
```

After reboot, verify the services/hardware:

```bash
# Service health
sudo systemctl status rotary-controller
sudo systemctl status mpd
systemctl status radio-update-stations.timer

# I2C encoder should typically appear at 0x36
i2cdetect -y 1

# HiFiBerry/DAC detection
aplay -l

# Runtime logs
tail -f /home/radio/logs/rotary.log
tail -f /home/radio/logs/update-stations.log
```

---

## What This Repository Contains

This repository configures a **headless Raspberry Pi radio** with:
- MPD-based playback
- station/bank selection via rotary hardware
- I2C volume encoder support
- systemd services + timer for unattended operation

### Key Paths

- `install-rotary.sh` – first-time provisioning on a fresh Pi
- `deploy-rotary.sh` – pull/update scripts and restart services on an existing installation
- `bin/` – runtime scripts (`rotary-controller`, `radio-play`, `update-stations`, shared `radio_lib.py`)
- `config/` – station list and hardware pin mapping
- `systemd/` – service/timer unit files (including the web backend service)
- `etc/mpd.conf` – MPD configuration
- `docs/` – usage guides and maintenance notes
- `web/` – local browser UI and Pi-hosted backend for remote control

---

## Daily/Operational Commands

### Update a running device from git

```bash
cd ~/radio-headless
./deploy-rotary.sh
```

### Pull a specific fix onto an already-running Raspberry Pi

Use this when you pushed a repo fix (for example, a knob rotation sequence fix) and want that exact update running on the Pi.

```bash
# 1) SSH into your Pi
ssh <pi-user>@<pi-hostname-or-ip>

# 2) Go to the installed repo
cd ~/radio-headless

# 3) Confirm branch and local state
git status -sb
git branch --show-current

# 4) Pull latest changes from origin
git fetch origin
git pull --ff-only origin main

# 5) Re-deploy scripts/services from this repo copy
./deploy-rotary.sh
```

If `git pull --ff-only` fails because local files were edited on the Pi:

```bash
# Option A: keep local edits temporarily
git stash push -u -m "pi-local-changes"
git pull --ff-only origin main
./deploy-rotary.sh

# Option B: discard local edits (destructive)
# git reset --hard HEAD
# git clean -fd
# git pull --ff-only origin main
# ./deploy-rotary.sh
```

Validate that the fix is active:

```bash
# show the latest deployed commit
git log -1 --oneline

# confirm rotary service is running new code
sudo systemctl status rotary-controller --no-pager
tail -n 80 /home/radio/logs/rotary.log
```

Tip: if behavior still matches the old version, reboot once after deploy:

```bash
sudo reboot
```

### Check current service state

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

QoL tip: adjust backend bind/port or file paths in `/etc/default/radio-web-backend`, then restart:

```bash
sudo systemctl restart radio-web-backend.service
```

---

## Additional Documentation

- `docs/ROTARY-README.md` – rotary-switch variant behavior and wiring
- `docs/MUSIC-TRANSFER.md` – loading offline music content
- `docs/AUTO-UPDATE.md` – update automation details
- `docs/WEB-CONTROL.md` – run the Pi-hosted web backend and browser UI for network control
