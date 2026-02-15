# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pi-audio** is a sound level display application for Raspberry Pi. This is a Python project (see `.gitignore` for Python conventions).

## Features
- Current SPL(A) level
- Rolling history chart of the last 30 seconds of the sound level

## Build & Run

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Run the app
uv run python -m pi_audio

# Lint
uv run ruff check src/
uv run ruff format --check src/
```

## Architecture

- `src/pi_audio/config.py` — constants (display, audio, colors)
- `src/pi_audio/audio.py` — audio capture via sounddevice, A-weighted SPL calculation
- `src/pi_audio/main.py` — pygame init, main loop, screen management
- `src/pi_audio/screens/base.py` — abstract Screen base class
- `src/pi_audio/screens/meter.py` — SPL readout + rolling history chart

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
