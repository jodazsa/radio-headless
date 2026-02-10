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

# I2C encoder should typically appear at 0x49
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
- `systemd/` – service/timer unit files
- `etc/mpd.conf` – MPD configuration
- `docs/` – usage guides and maintenance notes

---

## Daily/Operational Commands

### Update a running device from git

```bash
cd ~/radio-headless
./deploy-rotary.sh
```

### Check current service state

```bash
sudo systemctl is-active rotary-controller.service
sudo systemctl is-active mpd.service
systemctl is-active radio-update-stations.timer
```

### Follow logs

```bash
tail -f /home/radio/logs/rotary.log
sudo journalctl -u rotary-controller.service -f
sudo journalctl -u radio-update-stations.service -f
```

---

## Additional Documentation

- `docs/ROTARY-README.md` – rotary-switch variant behavior and wiring
- `docs/MUSIC-TRANSFER.md` – loading offline music content
- `docs/AUTO-UPDATE.md` – update automation details

