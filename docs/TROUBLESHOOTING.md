# Troubleshooting run_monitor.sh

## Common Issues

### 1. Environment variables not loaded

**Symptom**: 
```
BoltError: Either an env variable `SLACK_BOT_TOKEN` or `token` argument in the constructor is required.
```

**Cause**: Current shell session hasn't loaded ~/.bash_profile

**Fix**: Reload environment variables
```bash
source ~/.bash_profile
```

**Verify**:
```bash
echo $SLACK_BOT_TOKEN
# Should show: xoxb-451463007363-...
```

**Why this happens**:
- Env vars must be in `~/.bashrc` (for interactive shells) or `~/.bash_profile` (for login shells)
- Changes only apply to NEW shells or after `source ~/.bashrc`

**Fixed**: Environment variables are now in BOTH files:
- `~/.bashrc` - Loaded automatically for new terminal sessions ✅
- `~/.bash_profile` - Loaded for SSH/login shells and by run_monitor.sh ✅

**Quick test**:
```bash
# Should work immediately in new terminals:
python transient_monitor.py

# Or reload in current session:
source ~/.bashrc && python transient_monitor.py
```

---

### 2. Exit Code 127 - Command Not Found

Exit code 127 means "command not found" - this happens when:

### 1. Running from wrong directory
```bash
# ❌ Wrong
run_monitor.sh

# ✅ Correct
/home/ishaang6/transient_monitor/run_monitor.sh
# or
cd /home/ishaang6/transient_monitor && ./run_monitor.sh
```

### 2. Not executable (fixed - script has +x)
```bash
chmod +x /home/ishaang6/transient_monitor/run_monitor.sh
```

### 3. Cron doesn't have PATH
In crontab, use absolute path:
```bash
# ❌ Wrong (cron can't find script)
*/15 * * * * run_monitor.sh

# ✅ Correct
*/15 * * * * /home/ishaang6/transient_monitor/run_monitor.sh
```

## Testing

### Test directly
```bash
cd /home/ishaang6/transient_monitor
./run_monitor.sh
# Should run without errors
```

### Test in cron environment (minimal PATH)
```bash
env -i HOME=$HOME /home/ishaang6/transient_monitor/run_monitor.sh
# If this works, cron will work
```

### Check logs
```bash
tail -f /home/ishaang6/transient_monitor/monitor.log
```

## Working Cron Entry

Add to crontab (`crontab -e`):
```bash
# Check for new transients every 15 minutes
*/15 * * * * /home/ishaang6/transient_monitor/run_monitor.sh
```

The script handles:
- ✅ Sourcing ~/.bash_profile (CVMFS python + env vars)
- ✅ Refreshing transients.txt from /sptlocal/
- ✅ Running transient_monitor.py
- ✅ Logging to monitor.log with timestamps
