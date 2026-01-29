# Transient Monitor

Checks for new transients and posts multi-wavelength images to slack with voting system.

## Setup

Install modules:
pip install -r install_requirements.txt

Run monitor (scheduled for 12:00 PM):
python transient_monitor.py

## Config information

Set these environment variables:
export CASDA_USERNAME_PERSONAL='your_email@domain.com'
export CASDA_PASSWORD_PERSONAL='your_password'
export DATALAB_USERNAME='your_datalab_username'
export DATALAB_PASSWORD='your_datalab_password'

Update the Slack tokens in `transient_monitor.py` with the appropriate bot tokens.

## How it works

1. Reads `transients.txt` for new entries
2. Gets multi-wavelength images (ASKAP radio, WISE infrared, DECam optical)
3. Adds TS map overlays if available in `ts_maps/` directory
4. Posts to Slack channel with voting reactions
5. Tracks what's been processed in `new_transients.csv`

## Testing

```bash
python tests/test_askap_setup.py
python tests/test_reprocess_recent.py
python test_ts_overlay.py
python utilities/view_last_transients.py
```

## Notes

- Runs daily at 12:00 PM automatically
- Not all transients will have images from all surveys (expected)
- TS overlays show 1σ, 2σ, 3σ contours if `{source_name}_TSmap.fits` exists
- Check Slack bot permissions if messages don't appear