# Wi-Fi + Hostname Fallback Provisioning Design

## Goal

When the Raspberry Pi cannot join a known Wi-Fi network, it should automatically create a temporary setup network and host a configuration page that lets a user:

1. Enter Wi-Fi SSID
2. Enter Wi-Fi password
3. Enter a new device hostname

After submission, the device applies these settings to the OS configuration, restarts networking, and returns to normal radio operation.

---

## Scope and Non-Goals

### In scope
- Detecting offline state at boot.
- Enabling fallback AP mode only when offline.
- Serving a local setup page/API.
- Persisting Wi-Fi credentials and hostname in system config.
- Controlled transition from setup mode back to station mode.

### Out of scope (initial phase)
- Full captive portal DNS interception behavior for all clients.
- WPA-Enterprise / EAP Wi-Fi auth.
- Multi-network profile management UI.
- Localization and advanced UX polish.

---

## Existing System Context

Current repo behavior already provides:
- A Pi-hosted backend with JSON endpoints (`web/pi_backend.py`).
- A hosted web UI (`web/radio.html`) served by backend.
- A systemd service to run the web backend (`systemd/radio-web-backend.service`).

The installation flow currently expects hostname and Wi-Fi to be set during Raspberry Pi imaging, not through runtime setup.

This design extends the existing backend pattern with a provisioning mode and controlled privileged helper actions.

---

## High-Level Architecture

### Components
1. **Connectivity monitor (systemd oneshot/service)**
   - Runs at boot to determine if device has viable network.
   - Starts provisioning target when offline.

2. **Provisioning network stack**
   - AP service (recommended: NetworkManager hotspot profile, fallback: hostapd + dnsmasq).
   - Static gateway IP (e.g., `192.168.50.1`).

3. **Provisioning backend mode**
   - Existing `pi_backend.py` extended with:
     - `GET /setup/config`
     - `POST /setup/apply`
   - Setup mode serves a dedicated page (`web/setup.html`).

4. **Privileged apply helper**
   - Root-owned script (e.g., `/usr/local/lib/radio/apply-network-config`) to:
     - write Wi-Fi profile
     - set hostname
     - sync `/etc/hosts`
     - reload/restart network stack
   - Invoked via locked-down sudoers rule from backend service account.

5. **State marker**
   - File marker for setup mode (`/var/lib/radio/setup-mode`), used for observability and idempotence.

### Boot behavior
1. Normal boot starts radio services as today.
2. Connectivity monitor checks for successful Wi-Fi association + default route + DNS reachability (time-bounded).
3. If online: ensure setup mode is down.
4. If offline: bring up AP + setup backend page and keep radio playback services available locally.

---

## Detailed Flow

### A) Offline detection

Recommended logic (all within 20-30 seconds max):
- Check link + association (`iw`/`nmcli`).
- Check default route exists.
- Optional DNS probe (`resolvectl query` or ping gateway).

If no valid connectivity by timeout:
- Start `radio-provisioning.target`.
- Enable AP profile `radio-setup`.
- Expose setup UI at `http://192.168.50.1:8080/setup.html`.

### B) User setup interaction

UI form fields:
- `ssid` (required)
- `password` (required, min length 8 for WPA2)
- `hostname` (required, RFC1123-like validation: lowercase alnum + hyphen, max 63)

POST payload to `/setup/apply`:
```json
{
  "ssid": "HomeWiFi",
  "password": "secret1234",
  "hostname": "kitchen-radio"
}
```

### C) Apply transaction

Backend validates input and invokes helper script.
Helper script actions (ordered):
1. Create backup snapshot:
   - Wi-Fi config backup
   - previous hostname
2. Write new Wi-Fi profile atomically (temp file + move).
3. Apply hostname with `hostnamectl set-hostname`.
4. Update `127.0.1.1` line in `/etc/hosts`.
5. Restart networking / reconnect Wi-Fi.
6. Stop AP mode services.
7. Return success with message: "Reconnecting, this page will close in ~30s".

If any step fails:
- Emit structured error.
- Keep AP + setup page active.
- Roll back partial changes where possible.

---

## Systemd Design

### New units
- `radio-connectivity-check.service` (oneshot, boot-time decision)
- `radio-provisioning.target`
- `radio-provisioning-ap.service` (if using hostapd/dnsmasq path)
- Optional `radio-provisioning-cleanup.service`

### Existing unit updates
- `radio-web-backend.service`
  - Add environment flag to allow setup routes only in setup mode.
  - Consider `After=network-online.target` for normal mode.

### Ordering
- `multi-user.target`
  - starts backend as usual
  - starts connectivity check
- connectivity check may pull in provisioning target

This keeps startup deterministic and avoids racing between normal and provisioning stack.

---

## Security Model

1. **No generic shell endpoint expansion**
   - Keep command whitelist strict for `/command`.
   - Provisioning uses dedicated endpoint and helper.

2. **Input validation**
   - SSID length and charset restrictions.
   - Password minimum/maximum lengths.
   - Hostname regex + normalization.

3. **Least privilege**
   - Backend remains `User=radio`.
   - Only one sudo command allowed via `/etc/sudoers.d/radio-provisioning`.

4. **Secrets handling**
   - Never log raw password.
   - Redact sensitive fields in backend logs.

5. **Network exposure**
   - Setup endpoints enabled only while setup marker exists.
   - Optionally require one-time setup token shown on console/log.

---

## Data Ownership: “Update code” Interpretation

The robust implementation is to update **system configuration** (source of truth), not hardcode SSID/hostname into repo files.

What should update:
- Active hostname (`/etc/hostname`, `/etc/hosts`, kernel hostname)
- Active Wi-Fi connection profile

What should not be required:
- Editing repository source files for every SSID/hostname change.

Repo changes will instead make software read runtime OS state and display it where relevant.

---

## Proposed File/Area Changes (Implementation Phase)

- `web/pi_backend.py`
  - add setup routes and validation
  - add helper invocation path and safe response model
- `web/setup.html` (new)
  - setup form and status UX
- `systemd/radio-web-backend.service`
  - optional env toggle(s)
- `install-rotary.sh`
  - install provisioning helper + sudoers + new systemd units
- `systemd/` (new units)
  - connectivity check + provisioning target/services
- `docs/WEB-CONTROL.md`
  - add setup/provisioning operational notes
- `docs/` (this design doc)

---

## Failure Modes and Recovery

1. **Wrong password entered**
   - Reconnect attempt fails; AP mode remains enabled after timeout.
   - Setup page shows failure and allows retry.

2. **Invalid hostname**
   - Backend returns 400 with field-specific error.

3. **Network stack restart failure**
   - Roll back to previous Wi-Fi profile if possible.
   - Keep AP mode available.

4. **Power loss during apply**
   - Atomic writes + backups reduce corruption risk.
   - Next boot runs connectivity check and can re-enter setup mode.

---

## Observability

- Journal tags:
  - `radio-provisioning`
  - `radio-connectivity-check`
- Metrics/log events:
  - setup mode entered/exited
  - apply success/failure reasons
  - reconnect timing

Add quick diagnostics commands to docs:
- `systemctl status radio-connectivity-check`
- `systemctl status radio-provisioning.target`
- `journalctl -u radio-web-backend -u radio-connectivity-check -f`

---

## Rollout Plan

### Phase 1 (MVP)
- Manual AP startup + setup page + apply endpoint.
- Hostname + single Wi-Fi credential write.
- Reboot after apply.

### Phase 2
- Automatic boot detection and AP fallback.
- Better reconnect UX without full reboot.

### Phase 3
- Hardened captive portal behavior and setup-token security.
- Optional multi-profile Wi-Fi management.

---

## Acceptance Criteria

1. Device with no valid Wi-Fi starts AP within 30s of boot.
2. User can join AP and open setup page from phone/laptop.
3. Submitting valid SSID/password/hostname applies successfully.
4. Device rejoins target Wi-Fi and is reachable by new hostname.
5. Setup AP is disabled when normal connectivity is restored.
6. Invalid inputs are rejected with clear errors.
7. No sensitive credentials appear in logs.

