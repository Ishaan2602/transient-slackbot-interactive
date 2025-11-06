# Transient Monitoring System with ASKAP Integration

This system monitors astronomical transients and automatically posts notifications to Slack with optional ASKAP radio images.

## Quick Start

1. **Install dependencies:**
   pip install -r install_requirements.txt

2. **Run the monitor:**
   python transient_monitor.py

### Slack Configuration
- **Bot Token:** Set in `transient_monitor.py` or environment variable
- **Channel ID:** Configure target Slack channel
- **Signing Secret:** Required for Slack app authentication

### ASKAP Configuration
- **CASDA Username:** CASDA account email
- **CASDA Password:**  CASDA account password
- **Data Directories:** Automatically created in project folder

### Environment Variables (Recommended)
```bash
export CASDA_USERNAME_PERSONAL='your_email@domain.com'
export CASDA_PASSWORD_PERSONAL='your_password'
```

## Testing

1. **Test ASKAP setup:**
   ```bash
   python tests/test_askap_setup.py
   ```

2. **Test image generation:**
   ```bash
   python tests/test_image_generation.py
   ```

3. **View recent transients:**
   ```bash
   python utilities/view_last_transients.py
   ```

## Scheduling

The monitor runs:
- **Initial check** on startup
- **Scheduled checks** daily at 12:00 PM
- **Background Slack app** for real-time integration

## ASKAP Integration

When enabled, the system:
1. Queries CASDA for ASKAP radio images around transient coordinates
2. Downloads 2.5 arcminute cutouts
3. Processes data to 2D images
4. Creates thumbnails with axes


### Other notes

1. **No ASKAP images:** Expected for some coordinate pairs