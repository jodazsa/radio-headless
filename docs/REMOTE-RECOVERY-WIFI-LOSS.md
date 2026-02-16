# Remote Recovery Guide: Wi-Fi Unreachable + No Physical Access

## Scenario

This guide explains the failure mode where:

1. The Raspberry Pi cannot join its configured Wi-Fi network, **and**
2. You cannot physically reach the device (no keyboard/monitor access and no microSD access).

In this condition, treat the Pi as potentially **remote-only unreachable** until it can either rejoin a known network or someone can physically access it.

---

## What happens on the Pi

When the Pi boots and cannot reach Wi-Fi, the system is designed to support a setup/provisioning mode that can expose a local setup page to enter new Wi-Fi credentials and hostname settings. The backend includes setup endpoints and an apply flow for this purpose.

However, setup mode is still a **local-network recovery path**, not an internet-side recovery path:

- If the Pi creates an emergency setup access point, you must be near enough to connect to that AP.
- If you cannot physically get near the Pi, you also cannot join the fallback AP.
- Without LAN/Wi-Fi reachability or physical proximity, remote management commands (SSH/web UI) are unavailable.

Net effect: there is no guaranteed fully remote, out-of-band recovery channel in this repository alone.

---

## Practical impact to users

If this outage occurs, users should expect:

- The radio may continue whatever local playback behavior is possible.
- Scheduled online functions (for example station list refresh from remote URLs) will fail while offline.
- Web control and SSH from your normal network will fail because the Pi is not reachable on that network.
- If no one can physically access the site, recovery is blocked until network conditions change or onsite assistance is available.

---

## Why this is hard to recover remotely

A Wi-Fi credential/network mismatch creates a bootstrap problem:

- You need network access to send a fix.
- But the device needs the fix before it can rejoin the network.

Without a second management path (for example VPN over Ethernet, cellular modem, remote KVM, or a managed IoT control plane), remote-only recovery is generally impossible.

---

## Decision tree

1. **Can the original Wi-Fi return on its own?**
   - If yes, wait and monitor for the Pi to reappear.
2. **Is there any alternate reachable path already configured?**
   - Ethernet fallback, secondary Wi-Fi, VPN tunnel, or another remote agent.
   - If yes, use that path to update network settings.
3. **Is someone onsite (even non-technical)?**
   - Have them power-cycle and confirm status LEDs/router presence.
   - If provisioning AP is expected, have them connect and submit new credentials.
4. **No onsite help and no alternate path?**
   - Recovery must wait for onsite access.

---

## What to do once access is restored

After the Pi is reachable again:

1. Verify service health (`mpd`, `rotary-controller`, backend, update timer).
2. Confirm Wi-Fi credential correctness and SSID stability.
3. Validate station source URL reachability.
4. Review logs for root cause and recurrence indicators.
5. Add at least one out-of-band recovery option for future incidents.

---

## Preventive controls (recommended)

To reduce future lockout risk, consider:

- Preconfiguring **multiple Wi-Fi profiles** where possible.
- Keeping a wired Ethernet fallback available.
- Adding a secure remote access agent/VPN that auto-starts on boot.
- Using a smart PDU or remotely managed power outlet for controlled reboot.
- Documenting a simple onsite runbook for non-technical staff.

---

## Bottom line

If the Pi cannot access Wi-Fi and nobody can physically access the Pi or microSD card, recovery is usually limited to:

- waiting for the original network path to return, or
- getting onsite assistance.

This project provides strong local provisioning behavior, but does not by itself guarantee internet-side, no-touch recovery when the primary network path is gone.
