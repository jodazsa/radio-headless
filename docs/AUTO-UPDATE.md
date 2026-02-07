# Stations Auto-Update Feature

## Overview

The radio-headless project now includes an automatic update feature that pulls the latest `stations.yaml` from a configurable GitHub URL on a daily schedule. This ensures your radio always has the latest station list without manual intervention.

## How It Works

1. **Daily Updates**: The system automatically checks for updates at 4:00 AM every day
2. **Boot Updates**: On system boot, updates are checked after a 2-minute delay
3. **Validation**: Downloaded files are validated before installation
4. **Backup**: Current `stations.yaml` is backed up before any changes
5. **Safety**: If validation fails, the update is aborted and existing file is kept

## Configuration

The auto-update feature is configured in `/home/radio/hardware-rotary.yaml`:

```yaml
auto_update:
  # Enable/disable auto-updates
  enabled: true
  
  # GitHub raw URL to pull stations.yaml from
  github_url: "https://raw.githubusercontent.com/jodazsa/radio/refs/heads/main/config/stations.yaml"
  
  # Local path where stations.yaml is installed
  local_path: "/home/radio/stations.yaml"
```

### Configuration Options

- **enabled** (bool): Set to `false` to disable auto-updates
- **github_url** (string): The raw GitHub URL to your stations.yaml file
- **local_path** (string): Where to install the downloaded file (usually `/home/radio/stations.yaml`)

## Components

### 1. Update Script (`/usr/local/bin/update-stations`)

Python script that:
- Reads configuration from `hardware-rotary.yaml`
- Downloads stations.yaml from GitHub using `urllib` (no external dependencies)
- Validates the downloaded file structure
- Creates timestamped backups (keeps last 10)
- Installs the new file with correct permissions
- Logs all operations to `/home/radio/logs/update-stations.log`

### 2. Systemd Service (`radio-update-stations.service`)

One-shot service that runs the update script when triggered by the timer.

### 3. Systemd Timer (`radio-update-stations.timer`)

Schedules the update service to run:
- Daily at 4:00 AM
- 2 minutes after system boot
- Uses `Persistent=true` to catch up on missed runs

## Usage

### Check Timer Status

```bash
# Check if timer is active
systemctl status radio-update-stations.timer

# View next scheduled run
systemctl list-timers radio-update-stations.timer
```

### Manual Update

To manually trigger an update:

```bash
# Run as radio user
sudo -u radio /usr/local/bin/update-stations

# Or trigger the service
sudo systemctl start radio-update-stations.service
```

### View Logs

```bash
# Tail the update log
tail -f /home/radio/logs/update-stations.log

# View systemd journal
sudo journalctl -u radio-update-stations.service -n 50

# View all timer activations
sudo journalctl -u radio-update-stations.timer
```

### Disable Auto-Updates

To temporarily disable updates without removing the service:

```bash
# Stop and disable the timer
sudo systemctl stop radio-update-stations.timer
sudo systemctl disable radio-update-stations.timer
```

Or edit `/home/radio/hardware-rotary.yaml` and set:

```yaml
auto_update:
  enabled: false
```

### Re-enable Auto-Updates

```bash
# Enable and start the timer
sudo systemctl enable radio-update-stations.timer
sudo systemctl start radio-update-stations.timer
```

## Backups

Backups are stored in `/home/radio/backups/` with timestamps:

```
/home/radio/backups/
├── stations_20260207_040002.yaml
├── stations_20260206_040001.yaml
└── stations_20260205_040003.yaml
```

The system automatically keeps the 10 most recent backups and deletes older ones.

### Restore from Backup

To restore a previous version:

```bash
# List available backups
ls -lh /home/radio/backups/

# Restore a specific backup
sudo cp /home/radio/backups/stations_20260207_040002.yaml /home/radio/stations.yaml
sudo chown radio:radio /home/radio/stations.yaml

# Restart the radio controller to pick up changes
sudo systemctl restart rotary-controller.service
```

## Validation

The update script validates downloaded files to ensure they:
1. Are valid YAML syntax
2. Contain a `banks:` section
3. Have at least one bank defined
4. Follow the expected structure (using `validate_stations_config()` from `radio_lib`)

If validation fails, the update is aborted and the existing file remains unchanged.

## Troubleshooting

### Update Failed

Check the log for errors:
```bash
tail -50 /home/radio/logs/update-stations.log
```

Common issues:
- **Network error**: Check internet connection
- **GitHub URL incorrect**: Verify `github_url` in config
- **Validation failed**: The downloaded file has structural problems
- **Permission denied**: Check file ownership and permissions

### Timer Not Running

```bash
# Check timer status
systemctl status radio-update-stations.timer

# Check if timer is enabled
systemctl is-enabled radio-update-stations.timer

# Enable if needed
sudo systemctl enable radio-update-stations.timer
sudo systemctl start radio-update-stations.timer
```

### Test Download Manually

```bash
# Test if the URL is accessible
curl -I "https://raw.githubusercontent.com/jodazsa/radio/refs/heads/main/config/stations.yaml"

# Download and check content
curl "https://raw.githubusercontent.com/jodazsa/radio/refs/heads/main/config/stations.yaml" | head -20
```

## Security Considerations

- The script runs as the `radio` user (not root)
- Downloads are validated before installation
- Original file is always backed up before changes
- Only files from the configured GitHub URL are accepted
- The script will never overwrite the file if validation fails

## Integration with Deployment

The auto-update feature is automatically installed and enabled when using:
- `install-rotary.sh` (initial installation)
- `deploy-rotary.sh` (updates)

Both scripts will:
1. Install the update-stations script
2. Install systemd service and timer
3. Enable the timer
4. Show timer status after deployment
