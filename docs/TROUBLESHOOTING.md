# Troubleshooting Guide: Radio Unresponsive, No Audio, Web Page Won't Load

This guide covers the most common failure scenario: the radio is silent, the hardware
controls have no effect, and the web interface at `http://<hostname>:8080` does not load.

---

## Quick Checklist

Before diving in, verify the basics:

- [ ] The Pi has power (status LED is lit)
- [ ] The Pi is connected to your Wi-Fi network (not in setup-AP mode)
- [ ] You can `ping <hostname>` or `ping <ip>` from your computer
- [ ] The audio cable / speaker / amplifier is connected and powered

If the Pi is unreachable on your network at all, jump to
[Network / Wi-Fi problems](#network--wi-fi-problems).

---

## 1. Check Service Status

SSH into the Pi and run:

```bash
systemctl status mpd rotary-controller radio-web-backend
```

All three services should show `active (running)`. A status of `failed` or
`inactive` is the most common root cause. Address whichever service is not
running using the steps below.

---

## 2. Web Page Won't Load

**Symptom:** `http://<hostname>:8080` returns "connection refused", times out, or
shows a browser error page.

### Check the web backend service

```bash
systemctl status radio-web-backend
```

If it is not running:

```bash
sudo systemctl start radio-web-backend
sudo systemctl status radio-web-backend   # confirm it started
```

### Read the service logs

```bash
# Systemd journal (most recent entries first)
journalctl -u radio-web-backend -n 50 --no-pager

# Backend log file
cat /home/radio/logs/radio-web-backend.log 2>/dev/null || echo "(no log file)"
```

Look for Python tracebacks or port-conflict messages.

### Confirm the port is open

```bash
ss -tlnp | grep 8080
```

If nothing appears, the process is not listening. Restart the service:

```bash
sudo systemctl restart radio-web-backend
```

### Confirm the Pi is reachable

From your computer:

```bash
ping <hostname>         # or ping <ip address>
curl http://<hostname>:8080/config
```

If `ping` fails, see [Network / Wi-Fi problems](#network--wi-fi-problems).

---

## 3. Radio Not Playing Music

**Symptom:** The radio is powered and controls appear responsive, but no audio
comes out.

### Check the MPD service

```bash
systemctl status mpd
```

If MPD is not running, start it:

```bash
sudo systemctl start mpd
sudo systemctl status mpd
```

### Check MPD's own status via mpc

```bash
mpc status
```

Example of healthy output:

```
WWOZ New Orleans
[playing] #1/1   0:04:12 (100%)
volume: 60%   repeat: off   random: off   single: off   consume: off
```

Common problem states and fixes:

| mpc output | Meaning | Fix |
|---|---|---|
| `[stopped]` | Playback is stopped | Run `mpc play` |
| `error: Connection refused` | MPD is not running | `sudo systemctl start mpd` |
| `volume: 0%` | Volume is muted | `mpc volume 60` |
| Stream URL shown but no audio | Network stream unreachable | See [Stream connectivity](#stream-connectivity) |

### Test playback manually

```bash
# Play whatever is in the current playlist
mpc play

# Play bank 0, station 0 explicitly
radio-play 0 0
```

If `radio-play` reports an error, check its log:

```bash
tail -50 /home/radio/logs/radio-play.log
```

### Check audio output

```bash
# List ALSA output devices
aplay -l

# Quick sine-wave test through the default output (Ctrl-C to stop)
speaker-test -t sine -f 440 -c 2
```

If the hardware DAC is missing from `aplay -l`, the HiFiBerry (or other audio
hat) is not recognized. Verify `/boot/firmware/config.txt` (or `/boot/config.txt`
on older OS) contains the correct overlay line, for example:

```
dtoverlay=hifiberry-dac
```

Reboot after any `config.txt` change.

### Check MPD logs

```bash
journalctl -u mpd -n 100 --no-pager
```

---

## 4. Hardware Controls Unresponsive

**Symptom:** Turning the rotary switches or volume encoder has no effect.

### Check the rotary controller service

```bash
systemctl status rotary-controller
```

If it is not running, start it:

```bash
sudo systemctl start rotary-controller
sudo systemctl status rotary-controller
```

### Read the rotary controller logs

```bash
# Systemd journal
journalctl -u rotary-controller -n 50 --no-pager

# Log file
tail -50 /home/radio/logs/rotary.log
```

Look for:

- `GPIO already in use` — another process is holding a GPIO pin
- `OSError: [Errno 121] Remote I/O error` — I2C volume encoder not found
- Python `ImportError` — a required package is missing

### Verify I2C (volume encoder)

```bash
i2cdetect -y 1
```

The Adafruit Seesaw volume encoder should appear at address `0x36`. If it does
not, check the physical wiring and that I2C is enabled:

```bash
raspi-config nonint get_i2c    # returns 0 if enabled
sudo raspi-config               # Interface Options → I2C → Yes
```

### Check state file

The controller reads and writes `~radio/.radio-state` to track the current bank,
station, and volume:

```bash
cat /home/radio/.radio-state
```

If the file is corrupted or missing, the controller will create a fresh one on
next start. Delete it and restart if you suspect it is the cause:

```bash
sudo rm /home/radio/.radio-state
sudo systemctl restart rotary-controller
```

---

## 5. Restart Everything at Once

If the exact failing component is unclear, restart all radio services together:

```bash
sudo systemctl restart mpd rotary-controller radio-web-backend
sleep 3
systemctl status mpd rotary-controller radio-web-backend
```

---

## 6. Reboot the Pi

A clean reboot resolves most transient problems (stale GPIO locks, network stack
issues, MPD state corruption):

```bash
sudo reboot
```

After ~60 seconds, verify the services came up:

```bash
systemctl status mpd rotary-controller radio-web-backend
```

All three should be `active (running)`.

---

## 7. Network / Wi-Fi Problems

If the Pi is not reachable on your network at all, it may have lost its Wi-Fi
connection and fallen back to setup-AP mode.

**Signs of setup-AP mode:**

- A Wi-Fi network named `RADIO-SETUP-XXXX` (where XXXX are the last four hex
  digits of the Pi's MAC address) appears on your phone or laptop.

**To reconnect:**

1. Join the `RADIO-SETUP-XXXX` network from your phone or laptop.
   Password: `radio-setup-1234`
2. Open `http://192.168.4.1:8080/setup` in a browser.
3. Enter your Wi-Fi SSID and password and submit.
4. The Pi will rejoin your network and the setup AP will disappear.

If no setup-AP network appears and the Pi is not on your main network, it is
unreachable without physical access. See
[REMOTE-RECOVERY-WIFI-LOSS.md](REMOTE-RECOVERY-WIFI-LOSS.md) for details.

---

## 8. Stream Connectivity

Internet radio streams require a working internet connection. If the Pi is
online but streams are silent:

```bash
# Test DNS resolution
ping -c 3 google.com

# Test a known stream URL (replace URL with one from config/stations.yaml)
mpc clear
mpc add <stream-url>
mpc play
mpc status
```

MPD will report a stream error in `mpc status` if the URL is unreachable or
the station is offline. This is a station-side issue, not a Pi issue; try a
different station.

---

## 9. Diagnose with the Smoke Test

The repository includes a configuration validator:

```bash
sudo /usr/local/bin/smoke-test-config
```

This checks that required files, services, and hardware paths are present and
reports any missing items.

---

## 10. Collect Logs for Further Help

If none of the above resolves the problem, collect logs before asking for help:

```bash
journalctl -u mpd -u rotary-controller -u radio-web-backend \
    --since "1 hour ago" --no-pager > /tmp/radio-logs.txt

cat /home/radio/logs/rotary.log >> /tmp/radio-logs.txt
cat /home/radio/logs/radio-play.log >> /tmp/radio-logs.txt

echo "--- mpc status ---" >> /tmp/radio-logs.txt
mpc status >> /tmp/radio-logs.txt 2>&1

echo "--- aplay -l ---" >> /tmp/radio-logs.txt
aplay -l >> /tmp/radio-logs.txt 2>&1

echo "--- service status ---" >> /tmp/radio-logs.txt
systemctl status mpd rotary-controller radio-web-backend >> /tmp/radio-logs.txt

cat /tmp/radio-logs.txt
```

Share the contents of `/tmp/radio-logs.txt` when reporting an issue.

---

## Summary: Most Common Fixes

| Symptom | Most likely cause | Fix |
|---|---|---|
| Web page won't load | `radio-web-backend` stopped | `sudo systemctl restart radio-web-backend` |
| No audio, controls work | MPD stopped or volume 0 | `sudo systemctl start mpd` / `mpc volume 60` |
| Controls unresponsive | `rotary-controller` stopped | `sudo systemctl restart rotary-controller` |
| Everything dead | General crash or bad state | `sudo reboot` |
| Pi unreachable on LAN | Wi-Fi lost, in setup-AP mode | Connect to `RADIO-SETUP-XXXX` AP and reconfigure |
