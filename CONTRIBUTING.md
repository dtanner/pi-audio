# Contributing to Pi Audio

Thanks for your interest in contributing! This guide covers how to add support for new hardware configurations.

## Adding New Hardware Configuration

Have you gotten pi-audio working on hardware not listed in [HARDWARE.md](HARDWARE.md)? Please document it!

### 1. Test the Configuration

Ensure everything works:
- [ ] Audio capture from microphone
- [ ] Display renders correctly
- [ ] SPL values are reasonable
- [ ] Touch input works (if applicable)

### 2. Document Your Setup

Create a new file: `docs/hardware-configs/[your-hardware].md`

Use this template:

```markdown
# Setup Guide: [Hardware Name]

**Status:** ✅ Tested and working
**Last verified:** YYYY-MM-DD

## Hardware Components

| Component | Model/Specs | Notes |
|-----------|-------------|-------|
| **Compute** | [model] | |
| **Display** | [model] | |
| **Microphone** | [model] | ALSA card X, device Y |
| **OS** | [OS version] | |

## Step-by-Step Setup

[Your detailed setup instructions]

### Display Configuration

[Any specific display settings]

### Audio Configuration

[ALSA configuration with correct card/device numbers]

```bash
arecord -l
# Show the output
```

[Your `.asoundrc` contents]

## Troubleshooting

[Any issues you encountered and how you solved them]

## Hardware-Specific Notes

[Any calibration info, quirks, or tips]

## References

[Links to hardware documentation, drivers, etc.]
```

### 3. Update HARDWARE.md

Add your configuration to the "Tested & Working Configurations" section:

```markdown
### Configuration: [Your Hardware Name]

**Status:** ✅ Fully tested and working
**Last verified:** YYYY-MM-DD
**Setup guide:** [docs/hardware-configs/your-file.md](docs/hardware-configs/your-file.md)

**Hardware:**
- **Compute:** [model]
- **Display:** [model]
- **Microphone:** [model]
  - Detected as ALSA card X, device Y
  - [Any special notes]

**Key notes:**
- [Important setup details]
```

### 4. Submit a Pull Request

- Include photos of your setup (optional but appreciated)
- Mention any code changes needed (there shouldn't be any if design is followed)
- Note if you tested multiple variations (e.g., different Pi models)

## Code Contributions

### General Guidelines

- Maintain hardware abstraction - avoid hardcoding device-specific values
- Follow existing code style (use `ruff` for linting)
- Test on actual hardware before submitting
- Update documentation if behavior changes

### Code Style

```bash
# Check code
uv run ruff check src/

# Format code
uv run ruff format src/
```

### Architecture Principles

1. **Hardware-agnostic code** - No hardcoded device IDs or hardware assumptions
2. **Configuration over code** - Put hardware-specific values in `config.py` or user config files
3. **Fail gracefully** - Handle missing hardware with clear error messages
4. **Document assumptions** - If code assumes something about hardware, document it

### Areas for Contribution

- **Calibration improvements** - Better SPL calibration methods
- **UI enhancements** - Additional display modes, settings screens
- **Audio features** - Frequency analysis, peak detection, logging
- **Configuration** - Runtime config file, device selection UI
- **Testing** - Automated tests for audio processing

## Questions?

Open an issue to discuss before starting major changes.
