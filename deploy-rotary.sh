#!/bin/bash
# deploy-rotary.sh - Update running rotary switch radio from git

set -e

echo "=== Deploying Rotary Switch Radio Updates ==="
echo ""

# 1. Pull latest from GitHub
echo "→ Pulling latest changes..."
git pull origin main

# 2. Update scripts
echo "→ Updating scripts..."
sudo cp bin/radio_lib.py /usr/local/bin/
sudo cp bin/rotary-controller /usr/local/bin/
sudo cp bin/radio-play /usr/local/bin/
sudo cp bin/update-stations /usr/local/bin/
sudo chmod +x /usr/local/bin/{rotary-controller,radio-play,update-stations}

# 3. Update configs
echo "→ Updating configs..."
sudo cp config/hardware-rotary.yaml /home/radio/
sudo cp config/stations.yaml /home/radio/
sudo chown radio:radio /home/radio/*.yaml

# 4. Update MPD config
echo "→ Updating MPD config..."
sudo cp etc/mpd.conf /etc/mpd.conf

# 5. Update web backend and UI
echo "→ Updating web backend + UI..."
sudo mkdir -p /home/radio/radio-headless/web
sudo cp web/pi_backend.py /home/radio/radio-headless/web/
sudo cp web/radio.html /home/radio/radio-headless/web/
sudo chown -R radio:radio /home/radio/radio-headless/web

# 6. Update systemd service
echo "→ Updating systemd service..."
sudo cp systemd/rotary-controller.service /etc/systemd/system/
sudo cp systemd/radio-update-stations.service /etc/systemd/system/
sudo cp systemd/radio-update-stations.timer /etc/systemd/system/
sudo cp systemd/radio-web-backend.service /etc/systemd/system/

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

# Enable timer/backend if not already enabled
sudo systemctl enable --now radio-update-stations.timer 2>/dev/null || true
sudo systemctl enable --now radio-web-backend.service 2>/dev/null || true

# 7. Restart services
echo "→ Restarting services..."
sudo systemctl restart rotary-controller.service
sudo systemctl restart mpd.service
sudo systemctl restart radio-web-backend.service

echo ""
echo "✓ Deployment complete!"
echo ""
echo "Service status:"
echo "---------------"
sudo systemctl is-active rotary-controller.service && echo "✓ rotary-controller: running" || echo "✗ rotary-controller: failed"
sudo systemctl is-active mpd.service && echo "✓ mpd: running" || echo "✗ mpd: failed"
sudo systemctl is-active radio-web-backend.service && echo "✓ web backend: running" || echo "✗ web backend: failed"
systemctl is-active radio-update-stations.timer && echo "✓ update-stations timer: active" || echo "✗ update-stations timer: inactive"
echo ""
echo "For detailed logs:"
echo "  tail -f /home/radio/logs/rotary.log"
echo "  tail -f /home/radio/logs/update-stations.log"
echo "  sudo journalctl -u rotary-controller.service -n 20"
echo "  sudo journalctl -u radio-update-stations.service -n 20"
echo "  sudo journalctl -u radio-web-backend.service -n 20"
echo ""
