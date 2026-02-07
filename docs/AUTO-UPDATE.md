# Stations Auto-Update Feature

## Overview

Automatically pulls the latest `stations.yaml` from GitHub daily at 4 AM and 2 minutes after boot. Downloads are validated before installation, and the current file is backed up (keeping last 10).

## Configuration

Edit `/home/radio/hardware-rotary.yaml`:

```yaml
auto_update:
  enabled: true  # Set to false to disable
  github_url: "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/config/stations.yaml"
  local_path: "/home/radio/stations.yaml"
```

## Update Source Expectations

The default `github_url` in this repo points at a curated upstream stations list maintained by the project author. This is intentional so a fresh install can receive station updates without extra setup.

- If you want to track your own list, set `auto_update.github_url` to your own raw `stations.yaml` URL.
- If you want to keep local/manual edits only, set `auto_update.enabled: false`.
- `local_path` controls where updates are written (default `/home/radio/stations.yaml`).

## Usage

### Check Status

```bash
# View timer status and next run
systemctl status radio-update-stations.timer
systemctl list-timers radio-update-stations.timer
```

### Manual Update

```bash
# Trigger update now
sudo systemctl start radio-update-stations.service

# Or run directly
sudo -u radio /usr/local/bin/update-stations
```

### View Logs

```bash
# Tail update log
tail -f /home/radio/logs/update-stations.log

# View systemd journal
sudo journalctl -u radio-update-stations.service -n 50
```

### Disable/Enable

```bash
# Disable auto-updates
sudo systemctl stop radio-update-stations.timer
sudo systemctl disable radio-update-stations.timer

# Re-enable
sudo systemctl enable radio-update-stations.timer
sudo systemctl start radio-update-stations.timer
```

Or set `enabled: false` in the config file.

## Backups

Backups are in `/home/radio/backups/stations_TIMESTAMP.yaml` (last 10 kept).

### Restore from Backup

```bash
# List backups
ls -lh /home/radio/backups/

# Restore
sudo cp /home/radio/backups/stations_20260207_040002.yaml /home/radio/stations.yaml
sudo chown radio:radio /home/radio/stations.yaml
sudo systemctl restart rotary-controller.service
```

## How It Works

1. Timer triggers at 4 AM daily and 2 min after boot
2. Script downloads from configured GitHub URL
3. Content is SHA256-compared with current file (no-op if identical)
4. Downloaded YAML is validated (structure + at least one bank)
5. Current file is backed up with timestamp
6. New file is installed with correct permissions
7. Success/failure logged to `/home/radio/logs/update-stations.log`

## Troubleshooting

### Update Failed

```bash
# Check logs
tail -50 /home/radio/logs/update-stations.log

# Test GitHub URL manually
curl -I "YOUR_GITHUB_RAW_URL"
```

Common issues:
- **Network error**: Check internet connection
- **HTTP 404**: GitHub URL is incorrect
- **Validation failed**: Downloaded file has structural problems
- **Permission denied**: Check ownership (`sudo chown radio:radio /home/radio/stations.yaml`)

### Timer Not Running

```bash
# Check if enabled
systemctl is-enabled radio-update-stations.timer

# Enable if needed
sudo systemctl enable radio-update-stations.timer
sudo systemctl start radio-update-stations.timer
```

## Security

- Runs as `radio` user (not root)
- Downloads validated before installation (YAML structure + banks check)
- Original file always backed up before changes
- Failed updates never overwrite existing file
- Only configured GitHub URL is accepted
- SHA256 comparison prevents unnecessary writes
