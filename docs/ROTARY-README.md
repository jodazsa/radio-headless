# Rotary Switch Radio Variant

This is a variant of the radio-headless project that uses **BCD rotary switches** instead of rotary encoders and has **no OLED display**.

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
- I2C Address: 0x36

## Installation

### Raspberry Pi OS + microSD setup (from scratch)

1. **Install Raspberry Pi Imager** on your computer (Mac/Windows/Linux):
   https://www.raspberrypi.com/software/
2. Insert the microSD card into your computer.
3. In Raspberry Pi Imager, click **CHOOSE DEVICE**, **CHOOSE OS**, and **CHOOSE STORAGE**:
   - Device: your Raspberry Pi model (for example, Pi Zero 2 W)
   - OS: **Raspberry Pi OS Lite (64-bit)**
   - Storage: your microSD card
4. Click **NEXT** → **EDIT SETTINGS** (recommended), then set:
   - Hostname (any value you want, for example `radio`)
   - Username/password (any login user is fine)
   - Wi-Fi SSID/password + country (if using Wi-Fi)
   - Locale/timezone
   - Enable SSH
5. Click **SAVE** then **YES** to apply those settings.
6. Click **YES** to write the card and wait for flash + verify to complete.
7. Eject the microSD card safely from your computer.
8. With power disconnected from the Pi, insert the microSD card.
9. Connect power and wait about 1-2 minutes for first boot.
10. SSH from your computer:

```bash
ssh <your-user>@<hostname>.local
# example: ssh alex@radio.local
```

11. Continue with the project installation steps below.

### Fresh Installation

```bash
# Clone the repo
cd ~
git clone https://github.com/jodazsa/radio-headless.git
cd radio-headless

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
# Should show 0x36 (volume encoder)

# Check HiFiBerry MiniAmp is detected by ALSA
aplay -l
# Should list a HiFiBerry/HifiBerry card

# Show clear HiFiBerry status (CONNECTED + ENABLED, or NOT DETECTED)
if aplay -l | grep -qi hifiberry; then
  echo "HiFiBerry MiniAmp status: CONNECTED and ENABLED"
else
  echo "HiFiBerry MiniAmp status: NOT DETECTED (check wiring/overlay/reboot)"
fi

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

## Local Music Files (for offline stations)

If you use stations with `type: mp3_loop_random_start` or `type: mp3_dir_random_start_then_in_order`, see:

- [Music Transfer Guide](./MUSIC-TRANSFER.md)

## Updating from GitHub

```bash
cd ~/radio-headless
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

If positions advance out-of-order (for example `0,2,1,3,...` or `0,4,2,6,...`),
your switch output code order does not match the bit significance configured in
`station_switch` / `bank_switch`. You can fix this two ways:

1. Rewire pins so switch code lines map directly to `bit0/bit1/bit2/bit3`
2. Keep wiring as-is and use `station_decode_map` / `bank_decode_map` to map
   raw codes back to logical positions.

Example mappings for a common FR01 wiring pattern:

- Bank raws: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 12]` → map `12: 9`
- Station raws: `[0, 2, 1, 3, 4, 6, 5, 7, 8, 9]` → swap `1↔2` and `5↔6`

```yaml
switches:
  bank_decode_map:
    12: 9

  station_decode_map:
    1: 2
    2: 1
    5: 6
    6: 5
```

### Volume Not Working

```bash
# Check I2C
i2cdetect -y 1
# Should show 0x36

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
