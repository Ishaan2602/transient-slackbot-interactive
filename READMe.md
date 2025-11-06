# Transient Monitor

Checks for new transients and posts them to slack workspace with radio images.

## Setup

Install modules:
pip install -r install_requirements.txt

Run monitor (scheduled for 12:00 PM):
python transient_monitor.py

## Config information

Set these environment variables:
export CASDA_USERNAME_PERSONAL='your_email@domain.com'
export CASDA_PASSWORD_PERSONAL='your_password'

Update the Slack tokens in `transient_monitor.py` with the appropriate bot tokens.

## How it works

1. Reads `transients.txt` for new entries
2. Gets ASKAP radio images if available
3. Posts to Slack channel
4. Tracks what's been processed in `new_transients.csv`

## Testing

```bash
python tests/test_askap_setup.py
python tests/test_image_generation.py
python utilities/view_last_transients.py
```

## Notes

- Runs daily at 12:00 PM automatically (will push server-side and test with ngrok later)
- Not all transients will have ASKAP images (expected)
- Check Slack bot permissions if messages don't appear