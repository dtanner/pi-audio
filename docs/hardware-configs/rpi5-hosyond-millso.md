# Setup Guide: Raspberry Pi 5 + Hosyond 7" Display + MillSO USB Microphone

**Status:** ✅ Tested and working
**Last verified:** 2026-02-15

## Hardware Components

| Component | Model/Specs | Notes |
|-----------|-------------|-------|
| **Compute** | Raspberry Pi 5 (4GB RAM) | 8GB model should work identically |
| **Display** | Hosyond 7" IPS LCD Capacitive Touch Screen<br>1024×600 HDMI | Touch screen confirmed working |
| **Microphone** | MillSO Portable Mini USB Computer Microphone<br>Plug&Play | Appears as ALSA card 2, device 0 |
| **OS** | Raspberry Pi OS (64-bit) Desktop | Tested on Debian version, kernel 6.12.62 |

## Step-by-Step Setup

### 1. Install Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Flash SD card with **Raspberry Pi OS (64-bit) Desktop**
3. In Imager settings (⚙️):
   - Set hostname (e.g., `piaudio`)
   - Configure username/password
   - Enable SSH if desired
   - Configure WiFi if needed
4. Boot the Pi and complete initial setup

### 2. System Update

```bash
sudo apt update
sudo apt upgrade -y
```

### 3. Install System Dependencies

```bash
sudo apt install -y \
    python3-dev \
    libportaudio2 \
    portaudio19-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev
```

### 4. Install uv (Python Package Manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 5. Configure Display (Hosyond 7" 1024×600)

Edit boot configuration:
```bash
sudo nano /boot/firmware/config.txt
```

Add at the end:
```ini
# 1024x600 HDMI display
hdmi_group=2
hdmi_mode=87
hdmi_cvt=1024 600 60 6 0 0 0
hdmi_drive=2
```

Save and reboot:
```bash
sudo reboot
```

**Touch screen:** Should work automatically. If not, check manufacturer's documentation for drivers.

### 6. Configure USB Microphone (MillSO)

#### 6.1 Verify Microphone Detection

```bash
arecord -l
```

Expected output:
```
**** List of CAPTURE Hardware Devices ****
card 2: SF558 [SF-558], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

**Note the card number (2) and device number (0)** - you'll need these if different.

#### 6.2 Create ALSA Configuration

Create `~/.asoundrc`:
```bash
nano ~/.asoundrc
```

Add this content (adjust card numbers if yours differ):
```
pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:0,0"
    }
    capture.pcm {
        type plug
        slave.pcm "hw:2,0"
    }
}

ctl.!default {
    type hw
    card 2
}
```

This sets:
- **Playback** → card 0 (HDMI/headphone jack)
- **Capture** → card 2 (USB microphone)

#### 6.3 Test Audio Recording

```bash
arecord -d 3 -f cd test.wav
aplay test.wav
```

Should record 3 seconds and play it back without errors.

### 7. Install Pi Audio Application

```bash
cd ~
git clone <your-repo-url> pi-audio
cd pi-audio
uv sync
```

### 8. Test the Application

```bash
uv run python -m pi_audio
```

You should see:
- Current SPL(A) level displayed
- Rolling 30-second history chart
- Values updating in real-time

### 9. Create Desktop Shortcut (Optional)

```bash
mkdir -p ~/Desktop
cat > ~/Desktop/pi-audio.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Pi Audio Meter
Comment=Sound level display with SPL(A) meter
Exec=/home/YOUR_USERNAME/.local/bin/uv run python -m pi_audio
Path=/home/YOUR_USERNAME/pi-audio
Icon=audio-input-microphone
Terminal=false
Categories=AudioVideo;Audio;
EOF
chmod +x ~/Desktop/pi-audio.desktop
```

Replace `YOUR_USERNAME` with your actual username.

On first click, you may need to mark it as trusted.

## Troubleshooting

### No audio input / "audio open error"

**Problem:** `arecord` or the app can't find the microphone.

**Solutions:**
1. Verify USB mic is detected: `arecord -l`
2. Check `.asoundrc` has correct card/device numbers
3. Test with explicit device: `arecord -D plughw:2,0 -d 3 test.wav`

### Display resolution wrong

**Problem:** Screen shows wrong resolution or black borders.

**Solutions:**
1. Check `/boot/firmware/config.txt` has correct `hdmi_cvt` values
2. Try different `hdmi_mode` values (see [Raspberry Pi display documentation](https://www.raspberrypi.com/documentation/computers/config_txt.html#hdmi-mode))
3. Reboot after changes

### Touch screen not working

**Problem:** Touch input not recognized.

**Solutions:**
1. Check if touch events are detected: `evtest` (may need to install)
2. Some touch screens need manufacturer-specific drivers
3. Check Hosyond documentation or support forums

### App won't start / pygame errors

**Problem:** Application crashes on startup.

**Solutions:**
1. Ensure all system dependencies installed (step 3)
2. Check you're running on the Pi's desktop, not over SSH
3. Verify display is detected: `echo $DISPLAY` (should show `:0` or similar)

## Hardware-Specific Notes

### Microphone Calibration

The MillSO USB microphone is calibrated in code with a reference of ~94 dB SPL at full scale. This is a typical value for consumer USB mics but may not be accurate for this specific model.

**For accurate readings:**
1. Use a calibrated sound level meter as reference
2. Adjust the calibration constant in `src/pi_audio/audio.py:82`
3. Current line: `db = 20 * np.log10(rms) + 94.0`

### Display Color Profile

The Hosyond 7" display has good color accuracy for an IPS panel. No color calibration needed for this application.

## References

- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [ALSA Configuration Guide](https://alsa.opensrc.org/Asoundrc)
- [uv Documentation](https://docs.astral.sh/uv/)
- Hosyond Display: Check manufacturer's website for latest drivers/docs
- MillSO Microphone: Plug & play, no additional drivers needed
