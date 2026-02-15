# Hardware Configurations

This project is designed to work with various hardware combinations. Below are tested configurations and guides for setting them up.

## Philosophy

- **Code should be hardware-agnostic** where possible
- **Configuration over code changes** for hardware differences
- **Document tested combinations** so others can replicate or contribute new configs

## Tested & Working Configurations

### Configuration: Raspberry Pi 5 + Hosyond 7" + MillSO USB Mic

**Status:** ✅ Fully tested and working
**Last verified:** 2026-02-15
**Setup guide:** [docs/hardware-configs/rpi5-hosyond-millso.md](docs/hardware-configs/rpi5-hosyond-millso.md)

**Hardware:**
- **Compute:** Raspberry Pi 5 (4GB RAM)
- **Display:** Hosyond 7" IPS LCD Capacitive Touch Screen, 1024×600 HDMI
- **Microphone:** MillSO Portable Mini USB Computer Microphone Plug&Play
  - Detected as ALSA card 2, device 0
  - Requires ALSA configuration (see setup guide)

**Key notes:**
- USB microphone requires `.asoundrc` configuration to set as default input
- Display works with specific HDMI settings in `/boot/firmware/config.txt`
- Touch screen functionality confirmed working

---

## Untested but Likely Compatible

These configurations haven't been tested but should work with minimal changes:

### Raspberry Pi 4 (3/4/8GB)
- Should work identically to Pi 5 setup
- May have slightly lower performance

### Any USB Audio Interface
- Any USB microphone/interface that appears as an ALSA device should work
- Will need `.asoundrc` configured with the correct card/device numbers
- Check device with: `arecord -l`

### Any HDMI Display
- Resolution is configurable in `/boot/firmware/config.txt`
- App uses pygame which is display-resolution agnostic
- Touch screen support varies by hardware

---

## Future Hardware Support

Want to add support for new hardware? See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Testing new configurations
- Documenting hardware-specific setup
- Submitting configuration guides

### Requested Configurations

None yet. Open an issue to request testing on specific hardware.

---

## Hardware Abstraction

The codebase uses these strategies to remain hardware-agnostic:

- **Audio:** Uses default ALSA device (configured via `.asoundrc`)
- **Display:** pygame auto-detects display capabilities
- **Configuration:** Hardware-specific values in `src/pi_audio/config.py`

See [CLAUDE.md](CLAUDE.md) for guidance on maintaining hardware independence.
