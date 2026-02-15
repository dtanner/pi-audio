# pi-audio

Real-time sound level meter for Raspberry Pi with A-weighted SPL measurement and rolling history display.

## Features

- **Live SPL(A) Measurement** - Real-time A-weighted sound pressure level in dB
- **Rolling History Chart** - 30-second visual history of sound levels
- **Hardware Flexibility** - Designed to work with various Pi models, displays, and USB microphones

## Quick Start

### Prerequisites

- Raspberry Pi (tested on Pi 5, should work on Pi 4)
- HDMI display (any resolution)
- USB microphone
- Raspberry Pi OS (64-bit) Desktop

### Installation

```bash
# Clone the repository
git clone <your-repo-url> pi-audio
cd pi-audio

# Install dependencies (requires uv - see setup guide if not installed)
uv sync

# Run the application
uv run python -m pi_audio
```

## Hardware Setup

For detailed setup instructions including OS installation, audio configuration, and display setup, see:

**[HARDWARE.md](HARDWARE.md)** - Tested hardware configurations

**Tested Configuration:**
- Raspberry Pi 5 + Hosyond 7" Display + MillSO USB Mic
- Full setup guide: [docs/hardware-configs/rpi5-hosyond-millso.md](docs/hardware-configs/rpi5-hosyond-millso.md)

## Development

```bash
# Lint code
uv run ruff check src/
uv run ruff format --check src/

# Format code
uv run ruff format src/
```

## Project Structure

- `src/pi_audio/config.py` - Display, audio, and color constants
- `src/pi_audio/audio.py` - Audio capture and A-weighted SPL calculation
- `src/pi_audio/main.py` - pygame initialization and main loop
- `src/pi_audio/screens/` - Screen implementations (meter display)

## How It Works

1. **Audio Capture** - Uses `sounddevice` to capture audio from the default ALSA device
2. **A-Weighting Filter** - Applies IEC 61672:2003 A-weighting filter to match human hearing perception
3. **SPL Calculation** - Converts RMS amplitude to dB SPL with calibration reference
4. **Display** - pygame renders current level and rolling history chart

## Contributing

Contributions welcome! Especially:
- New hardware configuration documentation
- Calibration improvements
- UI enhancements

## License

See [LICENSE](LICENSE) file for details. 
