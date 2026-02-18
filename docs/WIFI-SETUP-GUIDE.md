# Wi-Fi Setup Guide: Changing Your Router Password

A step-by-step walkthrough for when you change the Wi-Fi password on your
router and need to reconnect the radio.

---

## What happens when the password changes

The radio tries to connect to its saved Wi-Fi network every time it boots
(and continuously while running). When the password no longer matches, the
connection fails. After about 60 seconds of failed connectivity checks, the
radio automatically creates its own temporary Wi-Fi network — a setup
hotspot — so you can give it the new credentials from your phone.

You do not need a computer, a keyboard, or a monitor attached to the Pi.
Everything is done from your iPhone over Wi-Fi.

---

## Before you start

You will need:

- The **new Wi-Fi network name** (SSID) and **password** from your router.
- Your **iPhone** (or any phone/tablet/laptop with a browser).
- To be within Wi-Fi range of the radio.

---

## Step 1 — Change the password on your router

Do this however you normally would (router admin page, ISP app, etc.). Once
the password changes, every device on that network needs the new password —
including the radio.

After the change, the radio will lose its connection. This is expected.

---

## Step 2 — Wait for the radio's setup hotspot to appear

The radio checks for internet connectivity every 10 seconds. After 60
seconds of being offline, it creates a temporary setup hotspot:

| Setting  | Value                                           |
|----------|-------------------------------------------------|
| SSID     | **RADIO-SETUP-XXXX** (last 4 hex digits of the Pi's MAC address) |
| Password | **radio-setup-1234**                            |
| IP       | 192.168.4.1                                     |

> If the radio was already running when you changed the router password, the
> hotspot will appear roughly one minute later. If the radio boots fresh
> after the change, it will appear about one minute after power-on.

---

## Step 3 — Connect your iPhone to the setup hotspot

1. Open **Settings > Wi-Fi** on your iPhone.
2. Look for a network named **RADIO-SETUP-XXXX** (the exact last four
   characters depend on your Pi's hardware — look for anything starting with
   `RADIO-SETUP-`).
3. Tap it and enter the password: **radio-setup-1234**
4. Your iPhone will connect. You may see a "No Internet Connection" warning
   — that is normal. The radio's hotspot is a local network only, it does
   not provide internet access.

### If your iPhone keeps switching back to your home Wi-Fi

iPhones sometimes auto-rejoin known networks. If it keeps dropping the
`RADIO-SETUP` connection:

- Go to **Settings > Wi-Fi**, tap the **(i)** next to your home network,
  and toggle **Auto-Join** off temporarily.
- Then reconnect to `RADIO-SETUP-XXXX`.
- Re-enable Auto-Join on your home network after you are done.

### If a "captive portal" page pops up and then dismisses itself

Tap Safari and manually navigate to the setup address in Step 4. The
captive-portal popup sometimes interferes; using Safari directly is more
reliable.

---

## Step 4 — Open the setup page

Open **Safari** (or any browser) and go to:

```
http://192.168.4.1:8080/setup.html
```

You will see a dark-themed page titled **Configure Internet** with three
fields.

---

## Step 5 — Enter your new Wi-Fi details

Fill in the form:

| Field             | What to enter                              | Rules                          |
|-------------------|--------------------------------------------|--------------------------------|
| **Wi-Fi Name (SSID)** | Your router's network name            | Required, max 32 characters    |
| **Wi-Fi Password**    | The new password you set on the router | 8 to 63 characters (WPA2)     |
| **Device Hostname**   | A name for the radio on your network   | Lowercase letters, numbers, hyphens only (e.g. `kitchen-radio`) |

> The hostname is how the radio identifies itself on your local network.
> If you are not sure what to put, use whatever it was before (e.g.
> `kitchen-radio`), or just pick something descriptive.

---

## Step 6 — Tap "Apply Settings"

Tap the orange **Apply Settings** button.

The status area below the form will show:

> *Applying settings... this can take up to 30 seconds.*

Behind the scenes, the radio is:

1. Saving the new Wi-Fi credentials.
2. Setting the hostname.
3. Shutting down the setup hotspot.
4. Connecting to your router with the new password.
5. Verifying it can reach the internet (up to 60 seconds).

---

## Step 7 — Check the result

### Success

If everything works, the status message will read:

> *Settings applied. Joined Wi-Fi and exited setup mode.*

At this point:
- The setup hotspot (`RADIO-SETUP-XXXX`) will disappear.
- Your iPhone will disconnect from it automatically.
- The radio is now on your home network with the new credentials.

**Reconnect your iPhone to your normal home Wi-Fi.** (If you turned off
Auto-Join in Step 3, turn it back on.)

### Failure — wrong password or network unreachable

If the radio cannot connect with the credentials you entered, the status
will show an error like:

> *wifi connectivity check failed; setup AP re-enabled*

The setup hotspot will come back up so you can try again. Double-check
the SSID spelling and password, then repeat from Step 5.

### Failure — you lost the page

When the radio tears down the hotspot to try connecting, your phone loses
its connection to `192.168.4.1`. If the attempt fails and the hotspot comes
back, you may need to:

1. Reconnect to `RADIO-SETUP-XXXX` in your iPhone Wi-Fi settings.
2. Open `http://192.168.4.1:8080/setup.html` in Safari again.

---

## Step 8 — Verify the radio is working

Once back on your home Wi-Fi, confirm the radio is online:

- **Listen** — if it was playing a stream before, it should resume playback
  once it has internet access again.
- **Web UI** — open `http://<hostname>.local:8080` in Safari (replace
  `<hostname>` with whatever you entered, e.g.
  `http://kitchen-radio.local:8080`). You should see the radio control page.
- **Router admin** — check your router's connected-devices list for the
  hostname you set.

---

## Troubleshooting

### The setup hotspot never appears

- **Wait longer.** The grace period is 60 seconds from when the radio goes
  offline, plus time for the AP to start. Give it two full minutes.
- **Power-cycle the radio.** Unplug it, wait a few seconds, plug it back
  in. The hotspot should appear about one minute after boot.
- **Check range.** You need to be within normal Wi-Fi range of the Pi.

### I can connect to the hotspot but the setup page does not load

- Make sure you are going to `http://192.168.4.1:8080/setup.html` — note
  **http** (not https) and port **8080**.
- Try a hard-refresh in Safari (pull down on the page).
- Check that your iPhone has not silently switched back to your home
  network.

### "Setup mode is not enabled on this device right now"

The setup page loaded but the status says setup mode is not active. This
means the radio thinks it is already online. If you believe it should be in
setup mode, power-cycle the radio and wait for the hotspot to appear again.

### The radio connected but I cannot reach it by hostname

- `.local` hostname resolution (mDNS/Bonjour) requires your iPhone and the
  Pi to be on the same network. Verify both are on your home Wi-Fi.
- Try the Pi's IP address instead. Check your router's admin page for the
  IP assigned to the radio's hostname.
- Some routers block mDNS traffic between devices. In that case, use the IP
  address directly.

---

## Quick reference

| Item                   | Value / Location                        |
|------------------------|-----------------------------------------|
| Setup hotspot SSID     | `RADIO-SETUP-XXXX` (last 4 of MAC)     |
| Setup hotspot password | `radio-setup-1234`                      |
| Setup page URL         | `http://192.168.4.1:8080/setup.html`    |
| Hotspot appears after  | ~60 seconds offline                     |
| Apply timeout          | Up to 60 seconds                        |
| Normal web UI          | `http://<hostname>.local:8080`          |
