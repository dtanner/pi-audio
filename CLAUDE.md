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

## Hardware Developed On
Compute: Raspberry Pi 5. My testing device has 4GB of RAM
Display: Hosyond 7 Inch IPS LCD Capacitive Touch Screen Pi Monitor 1024×600 HDMI
Microphone: MillSO Portable Mini USB Computer Microphone Plug&Play
