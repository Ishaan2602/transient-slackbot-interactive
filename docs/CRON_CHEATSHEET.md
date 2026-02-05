# SPT-3G Transient Monitor - Cron Setup

## Quick Commands
```bash
crontab -l          # View cron jobs
crontab -e          # Edit cron jobs
crontab -r          # Remove all cron jobs
```

## Cron Syntax
```
* * * * * command
│ │ │ │ └── Day of week (0-7)
│ │ │ └──── Month (1-12)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)
```

## Recommended Setup

### Production: Check for new transients every 15 minutes
```bash
*/15 * * * * /home/ishaang6/transient_monitor/run_monitor.sh
```

### Testing: Reprocess last 3 transients every hour (for development)
```bash
0 * * * * /home/ishaang6/transient_monitor/test_reprocess.sh
```

### Other intervals
```bash
# Every hour
0 * * * * /home/ishaang6/transient_monitor/run_monitor.sh

# Every 6 hours
0 */6 * * * /home/ishaang6/transient_monitor/run_monitor.sh

# Daily at noon
0 12 * * * /home/ishaang6/transient_monitor/run_monitor.sh
```

## What run_monitor.sh Does
1. Sources `~/.bash_profile` (loads CVMFS Python + environment variables)
2. Runs `refresh_data.sh` to update transients.txt
3. Runs `transient_monitor.py` with timestamped output to `monitor.log`

## View Logs
```bash
tail -f /home/ishaang6/transient_monitor/monitor.log
```

## Environment Variables (in ~/.bash_profile)
- `SLACK_BOT_TOKEN` - Slack bot authentication
- `SLACK_SIGNING_SECRET` - Slack signing secret
- `CASDA_USERNAME_PERSONAL` / `CASDA_PASSWORD_PERSONAL` - ASKAP auth
- `DATALAB_USERNAME` / `DATALAB_PASSWORD` - DECam auth
