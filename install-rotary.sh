#!/bin/bash
# install-rotary.sh - Setup for rotary switch radio variant
# This variant uses BCD rotary switches instead of encoders + OLED

set -e  # Exit on any error


copy_file_safe() {
    local src="$1"
    local dest="$2"
    local dest_target="$dest"

    if [ -d "$dest" ]; then
        dest_target="$dest/$(basename "$src")"
    fi

    local src_abs dest_abs
    src_abs="$(readlink -f "$src" 2>/dev/null || true)"
    dest_abs="$(readlink -f "$dest_target" 2>/dev/null || true)"

    if [ -n "$src_abs" ] && [ -n "$dest_abs" ] && [ "$src_abs" = "$dest_abs" ]; then
        echo "  Skipping copy for $src (source and destination are the same file)"
        return 0
    fi

    cp "$src" "$dest"
}

echo "=== Radio Project Installation (Rotary Switch Variant) ==="
echo ""

# Check if running as correct user (not root)
if [ "$EUID" -eq 0 ]; then 
    echo "Please run as regular user, not root"
    exit 1
fi

# 1. System update
echo "→ Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Enable I2C (for volume encoder)
echo "→ Enabling I2C..."
sudo raspi-config nonint do_i2c 0

# 3. Enable audio and HiFiBerry DAC
echo "→ Enabling audio and HiFiBerry DAC..."
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    CONFIG_FILE="/boot/config.txt"
else
    echo "WARNING: Could not find boot config file"
    CONFIG_FILE=""
fi

if [ -n "$CONFIG_FILE" ]; then
    # Add HiFiBerry DAC overlay if not present
    if ! grep -q "dtoverlay=hifiberry-dac" "$CONFIG_FILE"; then
        echo "dtoverlay=hifiberry-dac" | sudo tee -a "$CONFIG_FILE"
        echo "  Added HiFiBerry DAC overlay"
    else
        echo "  HiFiBerry DAC overlay already configured"
    fi
    
    # Comment out default audio if present (conflicts with HiFiBerry)
    if grep -q "^dtparam=audio=on" "$CONFIG_FILE"; then
        sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on # Disabled for HiFiBerry/' "$CONFIG_FILE"
        echo "  Disabled default audio (using HiFiBerry instead)"
    fi
fi

# 4. Install system packages
echo "→ Installing system packages..."
sudo apt install -y \
    mpd \
    mpc \
    python3-pip \
    python3-yaml \
    python3-rpi.gpio \
    i2c-tools \
    libjpeg-dev \
    zlib1g-dev

# 5. Create radio user if it doesn't exist
echo "→ Setting up radio user..."
if ! id -u radio >/dev/null 2>&1; then
    sudo useradd -m -s /bin/bash radio
    echo "Radio user created"
fi
sudo usermod -aG audio,i2c,gpio radio

# 5b. Create radio directories with correct permissions
echo "→ Creating radio directories..."
sudo mkdir -p /home/radio/audio
sudo mkdir -p /home/radio/backups
sudo mkdir -p /home/radio/logs
sudo chmod 755 /home/radio
sudo chmod 755 /home/radio/audio
sudo chmod 755 /home/radio/logs
sudo chown -R radio:radio /home/radio

# 5c. Setup MPD directories and permissions
echo "→ Setting up MPD directories..."
sudo mkdir -p /var/lib/mpd/playlists
sudo mkdir -p /var/lib/mpd/music
sudo touch /var/lib/mpd/tag_cache
sudo touch /var/lib/mpd/state
sudo touch /var/lib/mpd/sticker.sql
sudo chown -R mpd:audio /var/lib/mpd
sudo chmod -R 775 /var/lib/mpd

# Make sure mpd user can access radio's audio directory
sudo usermod -aG audio mpd

# 6. Install Python packages
echo "→ Installing Python packages..."
pip3 install --break-system-packages \
    adafruit-circuitpython-seesaw \
    adafruit-blinka \
    RPi.GPIO \
    python-mpd2

# 7. Deploy files
echo "→ Deploying configuration and scripts..."

# Copy scripts (note: no oled-display for this variant)
sudo copy_file_safe bin/radio_lib.py /usr/local/bin/
sudo copy_file_safe bin/rotary-controller /usr/local/bin/
sudo copy_file_safe bin/radio-play /usr/local/bin/
sudo copy_file_safe bin/update-stations /usr/local/bin/
sudo chmod +x /usr/local/bin/{rotary-controller,radio-play,update-stations}

# Copy configs (use rotary-specific hardware config)
sudo copy_file_safe config/hardware-rotary.yaml /home/radio/
sudo copy_file_safe config/stations.yaml /home/radio/
sudo chown radio:radio /home/radio/*.yaml

# Copy MPD config
sudo copy_file_safe etc/mpd.conf /etc/mpd.conf

# Copy web backend and UI
sudo mkdir -p /home/radio/radio-headless/web
# Backward compatibility: allow running `python3 web/pi_backend.py` from /home/radio.
sudo ln -sfn /home/radio/radio-headless/web /home/radio/web
sudo copy_file_safe web/pi_backend.py /home/radio/radio-headless/web/
sudo copy_file_safe web/radio.html /home/radio/radio-headless/web/
sudo copy_file_safe web/setup.html /home/radio/radio-headless/web/
sudo chown -R radio:radio /home/radio/radio-headless/web


# Install privileged setup helper + sudoers policy
sudo mkdir -p /usr/local/lib/radio
sudo copy_file_safe bin/apply-network-config /usr/local/lib/radio/apply-network-config
sudo chown root:root /usr/local/lib/radio/apply-network-config
sudo chmod 750 /usr/local/lib/radio/apply-network-config
sudo copy_file_safe etc/sudoers.d/radio-provisioning /etc/sudoers.d/radio-provisioning
sudo chown root:root /etc/sudoers.d/radio-provisioning
sudo chmod 440 /etc/sudoers.d/radio-provisioning

# Copy systemd service (rotary + update timer + web backend)
sudo copy_file_safe systemd/rotary-controller.service /etc/systemd/system/
sudo copy_file_safe systemd/radio-update-stations.service /etc/systemd/system/
sudo copy_file_safe systemd/radio-update-stations.timer /etc/systemd/system/
sudo copy_file_safe systemd/radio-web-backend.service /etc/systemd/system/

# Install backend override env file if missing (QoL for custom port/paths)
if [ ! -f /etc/default/radio-web-backend ]; then
sudo tee /etc/default/radio-web-backend >/dev/null <<'EOF'
# Optional overrides for radio-web-backend.service
#BIND_HOST=0.0.0.0
#BIND_PORT=8080
#RADIO_PLAY_CMD=/usr/local/bin/radio-play
#RADIO_STATE_FILE=/home/radio/.radio-state
#WEB_ROOT=/home/radio/radio-headless/web
#WEB_DEFAULT_PAGE=radio.html
EOF
fi

sudo systemctl daemon-reload

# 8. Enable services
echo "→ Enabling services..."
sudo systemctl enable rotary-controller.service
sudo systemctl enable mpd.service
sudo systemctl enable --now radio-update-stations.timer
sudo systemctl enable --now radio-web-backend.service

# 9. Verify I2C hardware detection
echo ""
echo "→ Checking for I2C hardware..."
if command -v i2cdetect &> /dev/null; then
    echo ""
    echo "Scanning I2C bus 1 (GPIO 2,3):"
    i2cdetect -y 1 2>/dev/null || echo "  (I2C not yet active - reboot required)"
    echo ""
fi

echo "=== Installation Complete! ==="
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo ""
echo "1. REBOOT REQUIRED for I2C, audio, and HiFiBerry to work:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify I2C volume encoder is detected:"
echo "   i2cdetect -y 1"
echo "   Expected: 0x36 (Seesaw for volume encoder)"
echo ""
echo "3. Verify HiFiBerry audio device:"
echo "   aplay -l"
echo "   Should show HiFiBerry device"
echo ""
echo "4. Check GPIO switch connections:"
echo "   Station switch: GPIOs 10, 9, 22, 17"
echo "   Bank switch: GPIOs 5, 6, 13, 11"
echo ""
echo "5. Verify services:"
echo "   sudo systemctl status rotary-controller"
echo "   sudo systemctl status mpd"
echo "   systemctl status radio-update-stations.timer"
echo "   sudo systemctl status radio-web-backend"
echo ""
echo "6. Watch logs:"
echo "   tail -f /home/radio/logs/rotary.log"
echo "   tail -f /home/radio/logs/update-stations.log"
echo "   sudo journalctl -u radio-web-backend.service -f"
echo ""
echo "7. Open web UI:"
echo "   http://<pi-hostname-or-ip>:8080/"
echo ""
