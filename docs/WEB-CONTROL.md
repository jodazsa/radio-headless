# Web Control Setup (Browser -> backend on Pi -> local radio commands)

This setup runs the backend **on the radio-headless Raspberry Pi itself** and has the Pi host the HTML UI.

## Architecture

- Browser opens the UI from the Pi (`http://<pi-hostname-or-ip>:8080/`).
- UI sends API requests to that same backend origin.
- Backend validates commands against a whitelist.
- Backend executes local Pi commands (`mpc`, `radio-play`) directly.

No SSH hop is required.

---

## 1) Copy/update files on the Pi

These files are included in this repo:

- `web/pi_backend.py`
- `web/radio.html`
- `systemd/radio-web-backend.service`

On the Pi:

```bash
cd ~/radio-headless
git pull --ff-only
```

---

## 2) Start backend manually (quick test)

From the repo on the Pi:

```bash
cd ~/radio-headless
python3 web/pi_backend.py
```

If you run `python3 web/pi_backend.py` from `~` (home) instead of `~/radio-headless`, Python will look for `/home/radio/web/pi_backend.py` and fail with `No such file or directory`.

Then browse to:

```text
http://<pi-hostname-or-ip>:8080/
```

Backend defaults:

- bind host: `0.0.0.0`
- bind port: `8080`
- web root: `web/`

Optional env overrides:

```bash
BIND_HOST=0.0.0.0 BIND_PORT=8080 WEB_ROOT=/home/radio/radio-headless/web RADIO_PLAY_CMD=/usr/local/bin/radio-play python3 web/pi_backend.py
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

## 4) Run backend as a service on Pi (recommended)

This repo now includes `systemd/radio-web-backend.service`.

Install/refresh unit and start:

```bash
sudo cp ~/radio-headless/systemd/radio-web-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now radio-web-backend.service
sudo systemctl status radio-web-backend.service
```

Browse to the hosted UI:

```text
http://<pi-hostname-or-ip>:8080/
```

Logs:

```bash
sudo journalctl -u radio-web-backend.service -f
```

The install/deploy scripts now create `/etc/default/radio-web-backend` (if missing) so you can tweak host/port/path settings without editing the unit file:

```bash
sudo nano /etc/default/radio-web-backend
sudo systemctl restart radio-web-backend.service
```


---

## 5) Troubleshooting

- `Command not allowed`:
  - whitelist regex in `ALLOWED_COMMANDS` does not match.
- `command_not_found` for `radio-play`:
  - set `RADIO_PLAY_CMD` to absolute path.
- `/status` fails:
  - confirm MPD is running: `sudo systemctl status mpd`.
- Browser cannot reach backend:
  - verify Pi IP/hostname, firewall, and that backend is bound to `0.0.0.0`.
- `cp: ... are the same file` during install/deploy:
  - this happens when the repo is already at `/home/radio/radio-headless` and a script copies `web/pi_backend.py` onto itself.
  - update to the latest `install-rotary.sh` / `deploy-rotary.sh`; they now skip same-file copies so service enable/start steps still run.
- Backend not running after reboot:
  - check `sudo systemctl is-enabled radio-web-backend.service` (should be `enabled`).
  - if disabled or failed, run:
    ```bash
    cd ~/radio-headless
    ./deploy-rotary.sh
    sudo systemctl enable --now radio-web-backend.service
    sudo systemctl status radio-web-backend.service --no-pager
    ```
- CORS/security tightening:
  - replace `Access-Control-Allow-Origin: *` with your trusted origin.
