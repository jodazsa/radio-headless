# Web Control Setup (Browser -> backend on Pi -> local radio commands)

This setup runs the backend **on the radio-headless Raspberry Pi itself**.

## Architecture

- Browser sends HTTP requests to the Pi backend on port `8080`.
- Backend validates commands against a whitelist.
- Backend executes local Pi commands (`mpc`, `radio-play`) directly.

No SSH hop is required.

---

## 1) Copy/update files on the Pi

These files are included in this repo:

- `web/pi_backend.py`
- `web/pi-music-controller.html`

On the Pi:

```bash
cd ~/radio-headless
git pull --ff-only
```

---

## 2) Start backend on the Pi

From the repo on the Pi:

```bash
python3 web/pi_backend.py
```

Backend defaults:

- bind host: `0.0.0.0`
- bind port: `8080`

Optional env overrides:

```bash
BIND_HOST=0.0.0.0 BIND_PORT=8080 RADIO_PLAY_CMD=/home/radio/radio-headless/bin/radio-play python3 web/pi_backend.py
```

---

## 3) Verify backend from another machine

From laptop/desktop on same network:

```bash
curl -s http://<pi-hostname-or-ip>:8080/config | jq .
```

```bash
curl -s -X POST http://<pi-hostname-or-ip>:8080/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"mpc play"}' | jq .
```

```bash
curl -s -X POST http://<pi-hostname-or-ip>:8080/status \
  -H 'Content-Type: application/json' \
  -d '{}' | jq .
```

---

## 4) Use the included browser UI

Open `web/pi-music-controller.html` in your browser.

- Set **Backend URL** to `http://<pi-hostname-or-ip>:8080`.
- Click **Load Config** and **Refresh**.
- Use Play/Pause/Stop/Volume and `radio-play <bank> <station>` controls.

Tip: If you serve the HTML from the Pi hostname, the page auto-fills backend URL as `http://<that-hostname>:8080`.

---

## 5) Run backend as a service on Pi (recommended)

Create `/etc/systemd/system/radio-web-backend.service`:

```ini
[Unit]
Description=Radio web backend (local command mode)
After=network.target mpd.service

[Service]
User=radio
WorkingDirectory=/home/radio/radio-headless
Environment=BIND_HOST=0.0.0.0
Environment=BIND_PORT=8080
Environment=RADIO_PLAY_CMD=/home/radio/radio-headless/bin/radio-play
ExecStart=/usr/bin/python3 /home/radio/radio-headless/web/pi_backend.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable/start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now radio-web-backend.service
sudo systemctl status radio-web-backend.service
```

Logs:

```bash
sudo journalctl -u radio-web-backend.service -f
```

---

## 6) Troubleshooting

- `Command not allowed`:
  - whitelist regex in `ALLOWED_COMMANDS` does not match.
- `command_not_found` for `radio-play`:
  - set `RADIO_PLAY_CMD` to absolute path.
- `/status` fails:
  - confirm MPD is running: `sudo systemctl status mpd`.
- Browser cannot reach backend:
  - verify Pi IP/hostname, firewall, and that backend is bound to `0.0.0.0`.
- CORS/security tightening:
  - replace `Access-Control-Allow-Origin: *` with your trusted origin.

