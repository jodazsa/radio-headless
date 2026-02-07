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
sudo chmod +x /usr/local/bin/{rotary-controller,radio-play}

# 3. Update configs
echo "→ Updating configs..."
sudo cp config/hardware-rotary.yaml /home/radio/
sudo cp config/stations.yaml /home/radio/
sudo chown radio:radio /home/radio/*.yaml

# 4. Update MPD config
echo "→ Updating MPD config..."
sudo cp etc/mpd.conf /etc/mpd.conf

# 5. Update systemd service
echo "→ Updating systemd service..."
sudo cp systemd/rotary-controller.service /etc/systemd/system/
sudo systemctl daemon-reload

# 6. Restart services
echo "→ Restarting services..."
sudo systemctl restart rotary-controller.service
sudo systemctl restart mpd.service

echo ""
echo "✓ Deployment complete!"
echo ""
echo "Service status:"
echo "---------------"
sudo systemctl is-active rotary-controller.service && echo "✓ rotary-controller: running" || echo "✗ rotary-controller: failed"
sudo systemctl is-active mpd.service && echo "✓ mpd: running" || echo "✗ mpd: failed"
echo ""
echo "For detailed logs:"
echo "  tail -f /home/radio/logs/rotary.log"
echo "  sudo journalctl -u rotary-controller.service -n 20"
echo ""
