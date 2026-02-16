# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pi-audio** is a sound level display application for Raspberry Pi. This is a Python project (see `.gitignore` for Python conventions).

## Features
- Current SPL(A) level
- Rolling history chart of the last 30 seconds of the sound level
- Scrolling spectrogram / overtone analyzer (FFT-based, logarithmic frequency axis)
- Real-time pitch detection (YIN algorithm) with note name, octave, cents deviation, and piano-roll chart
- Flexible panel layout: toggle up to two panels (Overtones, Meter, Pitch) or show current values only
- Configurable via in-app settings screen (persisted to `~/.config/pi-audio/settings.json`)

## Build & Run

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Run the app locally
uv run python -m pi_audio

# Lint
uv run ruff check src/
uv run ruff format --check src/
```

## Deployment to Pi

**Primary deployment target:** admin@piaudio.local

Use `deploy.sh` to sync changes to the Pi:

```bash
# Sync files only
./deploy.sh

# Sync and run the app on Pi
./deploy.sh --run
```

The script uses rsync to sync files and can optionally run the app on the Pi. Configuration:
- **PI_HOST** environment variable (default: `admin@piaudio.local`)
- **PI_PATH** environment variable (default: `~/pi-audio`)

The Pi uses a pre-existing `.venv` directory. The app runs via `source .venv/bin/activate && python -m pi_audio` (not using `uv` on the Pi).

## Architecture

- `src/pi_audio/config.py` — constants (display, audio, colors, spectrogram)
- `src/pi_audio/audio.py` — audio capture via sounddevice, A-weighted SPL calculation, FFT for spectrogram
- `src/pi_audio/pitch.py` — YIN-based pitch detection (frequency estimation, note/octave/cents mapping)
- `src/pi_audio/spectrogram.py` — spectrogram renderer (log-frequency mapping, color LUT, pygame surface rendering)
- `src/pi_audio/settings.py` — persistent user settings (history length, thresholds, display mode)
- `src/pi_audio/main.py` — pygame init, main loop, screen management
- `src/pi_audio/screens/base.py` — abstract Screen base class
- `src/pi_audio/screens/meter.py` — SPL readout + rolling history chart + spectrogram + pitch panel (flexible panel layout)
- `src/pi_audio/screens/settings.py` — settings UI with sliders

## Hardware Compatibility

**Design Philosophy:** Code should be hardware-agnostic. Use configuration over code changes.

### Tested Hardware

See [HARDWARE.md](HARDWARE.md) for complete list of tested configurations.

**Primary test configuration:**
- Raspberry Pi 5 (4GB)
- Hosyond 7" 1024×600 HDMI display
- MillSO USB microphone (ALSA card 2, device 0)
- Full setup: [docs/hardware-configs/rpi5-hosyond-millso.md](docs/hardware-configs/rpi5-hosyond-millso.md)

### Hardware Abstraction Strategy

- **Audio Input:** Uses ALSA default device (no hardcoded device IDs)
  - Users configure default via `~/.asoundrc` on their system
  - App calls `sd.InputStream()` without device parameter
  - This allows any USB microphone/interface to work without code changes

- **Display:** pygame auto-detects resolution and capabilities
  - No hardcoded display dimensions in rendering logic
  - Users configure HDMI output via `/boot/firmware/config.txt`

- **Configuration:** Hardware-specific values in `src/pi_audio/config.py`
  - Sample rate, block size, history length
  - Display colors and fonts
  - Change here rather than in implementation files

### Adding New Hardware Support

When adding support for new hardware:
1. Test the configuration works
2. Document in `docs/hardware-configs/[hardware-name].md`
3. Add to tested configurations in `HARDWARE.md`
4. Note any required ALSA config, display settings, or driver requirements
5. If code changes are needed, ensure they're generic (not hardware-specific)
