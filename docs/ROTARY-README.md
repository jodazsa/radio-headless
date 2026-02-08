# Rotary Switch Radio Variant

This is a variant of the radio-voice project that uses **BCD rotary switches** instead of rotary encoders and has **no OLED display**.

## Hardware Differences

### Original Radio (Encoder + OLED)
- 3x Rotary encoders (bank, station, volume)
- 128x32 OLED display
- 4x Push buttons

### Rotary Switch Radio (This Variant)
- 2x 10-position BCD rotary switches (bank, station)
- 1x Rotary encoder (volume only)
- 1x Push button (on volume encoder)
- **No display**

## Hardware Components

### Required
- Raspberry Pi Zero 2 W
- HiFiBerry MiniAmp (or compatible DAC)
- 2x 10-position BCD rotary switches
- 1x Adafruit Seesaw I2C Encoder Breakout (for volume)

### BCD Rotary Switch Wiring

**Station Selector Switch:**
- Bit 0 (value 1): GPIO 10
- Bit 1 (value 2): GPIO 9
- Bit 2 (value 4): GPIO 22
- Bit 3 (value 8): GPIO 17
- Common: Ground

**Bank Selector Switch:**
- Bit 0 (value 1): GPIO 5
- Bit 1 (value 2): GPIO 6
- Bit 2 (value 4): GPIO 13
- Bit 3 (value 8): GPIO 11
- Common: Ground

### Volume Encoder (I2C)
- SDA: GPIO 2 (Pin 3)
- SCL: GPIO 3 (Pin 5)
- VCC: 3.3V
- GND: Ground
- I2C Address: 0x49

## Installation

### Raspberry Pi OS + microSD setup (from scratch)

1. **Download Raspberry Pi Imager** on your computer (Mac/Windows/Linux).
2. Insert the microSD card into your computer (using a card reader if needed).
3. In Raspberry Pi Imager:
   - **Raspberry Pi Device**: choose your Pi model (for example, Pi Zero 2 W)
   - **Operating System**: choose **Raspberry Pi OS Lite (64-bit)**
   - **Storage**: choose your microSD card
4. Click **Next** and choose **Edit Settings** (recommended), then configure:
   - Hostname
      - echo1 - currently running encoder version
      - wolfmann - prototype for rotary, no screen version
   - Username/password
      - username:  radio
   - Wi-Fi SSID/password + country
   - Locale/timezone
   - Enable SSH
5. Click **Save** then **Yes** to apply OS customization.
6. Click **Write** and wait for flashing + verification to finish.
7. **Safely eject** the microSD card from your computer.
8. With the Pi powered off, **insert the microSD card into the Raspberry Pi**.
9. Power on the Pi and wait ~1-2 minutes for first boot.
10. SSH into the Pi from your computer:

```bash
ssh <your-user>@<hostname>.local
# example: ssh radio@hostname.local
```

11. Continue with the project installation steps below.

### Fresh Installation

```bash
# Clone the repo
cd ~
git clone git@github.com:jodazsa/radio-voice.git
cd radio-voice

# Run rotary variant installation
chmod +x install-rotary.sh
./install-rotary.sh

# Reboot
sudo reboot
```

### After Reboot

```bash
# Verify services
sudo systemctl status rotary-controller
sudo systemctl status mpd

# Check I2C
i2cdetect -y 1
# Should show 0x49 (volume encoder)

# Watch logs
tail -f /home/radio/logs/rotary.log
```

## How It Works

### BCD Encoding
Each switch position (0-9) is encoded as a 4-bit binary pattern:

| Position | Bit3 | Bit2 | Bit1 | Bit0 | Decimal |
|----------|------|------|------|------|---------|
| 0        | 0    | 0    | 0    | 0    | 0       |
| 1        | 0    | 0    | 0    | 1    | 1       |
| 2        | 0    | 0    | 1    | 0    | 2       |
| 3        | 0    | 0    | 1    | 1    | 3       |
| 4        | 0    | 1    | 0    | 0    | 4       |
| 5        | 0    | 1    | 0    | 1    | 5       |
| 6        | 0    | 1    | 1    | 0    | 6       |
| 7        | 0    | 1    | 1    | 1    | 7       |
| 8        | 1    | 0    | 0    | 0    | 8       |
| 9        | 1    | 0    | 0    | 1    | 9       |

**Note:** Switches are active LOW (grounded = 1, floating = 0)

### Behavior
- **Instant switching**: When you turn either switch, the radio immediately plays the new bank/station
- **No settle delay**: Unlike encoders, switches give deterministic positions
- **State persistence**: Last position is saved to `/home/radio/.radio-state`
- **Volume control**: Single encoder with same behavior as original radio

## Configuration

Edit `/home/radio/hardware-rotary.yaml` to customize:

```yaml
switches:
  station_switch:
    bit0: 10  # Change these if you wire differently
    bit1: 9
    bit2: 22
    bit3: 17
  
  bank_switch:
    bit0: 5
    bit1: 6
    bit2: 13
    bit3: 11

polling:
  switch_poll_interval: 0.1  # How often to check switches
  switch_debounce: 0.05      # Ignore changes faster than this
```

## Updating from GitHub

```bash
cd ~/radio-voice
./deploy-rotary.sh
```

## Troubleshooting

### Switches Not Responding

Check GPIO connections:
```bash
# Test reading GPIO pins directly
gpio readall

# Watch logs
tail -f /home/radio/logs/rotary.log
```

### Wrong Station Playing

Check switch wiring matches configuration in `hardware-rotary.yaml`

### Volume Not Working

```bash
# Check I2C
i2cdetect -y 1
# Should show 0x49

# Test encoder directly
sudo -u radio /usr/local/bin/rotary-controller
# Turn volume, watch for log output
```

## Shared Components

These files are **shared** with the encoder+OLED variant:
- `bin/radio_lib.py` - Shared library functions
- `bin/radio-play` - Playback controller
- `config/stations.yaml` - Station list (100 stations across 10 banks)
- `etc/mpd.conf` - MPD configuration

These files are **unique** to this variant:
- `bin/rotary-controller` - Switch + encoder controller
- `config/hardware-rotary.yaml` - Hardware configuration
- `systemd/rotary-controller.service` - Service file

## Logs

View logs in real-time:
```bash
tail -f /home/radio/logs/rotary.log
```

Or check systemd journal:
```bash
sudo journalctl -u rotary-controller.service -f
```

## Advantages of This Design

✅ **Deterministic** - Switches give exact positions, no encoder drift
✅ **Instant feedback** - No settle delay needed
✅ **Simple** - Fewer components than encoder version
✅ **Reliable** - Mechanical switches are very durable
✅ **No display needed** - You know what position you're at by feel

## Disadvantages

❌ **No visual feedback** - Can't see station names
❌ **Limited to 10 positions** - Can't easily expand beyond 10 banks/stations per switch
❌ **More GPIO pins** - Uses 8 GPIO pins instead of 2 I2C

## Adding Visual Feedback (Optional)

If you want some feedback without a full display, consider:
- **LEDs** - Show current bank/station position
- **7-segment displays** - Show numbers via I2C or GPIO
- **Status LED** - Single LED to indicate playing/paused

These can be added without changing the core controller logic.
