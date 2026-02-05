# Transient Monitor - Architecture Guide

## How Programs Run on Servers

### 1. One-time vs Always-running Programs

| Type | Example | How it works |
|------|---------|--------------|
| **One-time** | A Python script that processes a file | Runs, does its job, exits |
| **Always-running** | A web server, Slack bot listener | Runs forever, waiting for things to happen |

The transient monitor has **both**:
- **Checking for new transients** → One-time (run it, post any new ones, done)
- **Listening for votes** → Always-running (needs to stay connected to Slack)

---

## 2. Cron - The Scheduler

**Cron** is like an alarm clock for your computer. You tell it "run this command every 15 minutes" and it does it automatically.

### Cron Syntax
```
┌─────────── minute (0-59)
│ ┌───────── hour (0-23)  
│ │ ┌─────── day of month (1-31)
│ │ │ ┌───── month (1-12)
│ │ │ │ ┌─── day of week (0-6, Sunday=0)
│ │ │ │ │
* * * * *  command to run
```

### Common Examples
| Schedule | Cron Expression | Use Case |
|----------|-----------------|----------|
| Every 15 minutes | `*/15 * * * *` | Frequent transient checking |
| Every hour | `0 * * * *` | Hourly transient checking |
| Every day at 8 AM | `0 8 * * *` | Daily summary |
| Every Monday at 9 AM | `0 9 * * 1` | Weekly reports |

### Setting Up Cron

```bash
# Edit your crontab
crontab -e

# Add a line like this (check every 15 minutes):
*/15 * * * * /home/ishaang6/transient_monitor/run_monitor.sh >> /home/ishaang6/transient_monitor/logs/cron.log 2>&1

# View current cron jobs
crontab -l

# Remove all cron jobs (careful!)
crontab -r
```

**Tip**: The `>> logfile 2>&1` part saves output to a log file so you can debug issues.

---

## 3. Daemons - Background Processes

A **daemon** (pronounced "demon") is a program that runs in the background, even when you're not logged in.

### The Problem
If you run `python transient_monitor.py --listen` in a terminal and then close that terminal... the program dies!

### Solutions

| Method | How it works | Complexity | Best for |
|--------|--------------|------------|----------|
| **screen/tmux** | Creates a "virtual terminal" that persists | Easy | Development/testing |
| **nohup** | Keeps running after you log out | Easy | Quick one-offs |
| **systemd** | Proper Linux service, auto-restarts if it crashes | Medium | Production |

### Using Screen (Recommended for Development)

```bash
# Start a new screen session named "votes"
screen -S votes

# Run your command
./run_monitor.sh --listen

# Detach from screen (it keeps running): Press Ctrl+A, then D

# List running screens
screen -ls

# Reattach to your screen
screen -r votes

# Kill a screen session (from inside)
exit
# or press Ctrl+A, then K
```

### Using nohup (Simple but Limited)

```bash
# Run in background, immune to hangups
nohup ./run_monitor.sh --listen > logs/votes.log 2>&1 &

# Check if it's running
ps aux | grep transient_monitor

# Kill it
pkill -f "transient_monitor.py --listen"
```

### Using systemd (Production)

Create a service file at `/etc/systemd/system/transient-votes.service`:

```ini
[Unit]
Description=Transient Monitor Vote Listener
After=network.target

[Service]
Type=simple
User=ishaang6
WorkingDirectory=/home/ishaang6/transient_monitor
ExecStart=/home/ishaang6/transient_monitor/run_monitor.sh --listen
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Start the service
sudo systemctl start transient-votes

# Enable on boot
sudo systemctl enable transient-votes

# Check status
sudo systemctl status transient-votes

# View logs
journalctl -u transient-votes -f
```

---

## 4. Socket Mode - How Slack Voting Works

### Normal Webhooks (Not Used)
Slack calls YOUR server when something happens:
- Requires: A public URL, firewall rules, SSL certificate
- Complex to set up on internal servers

### Socket Mode (What We Use)
YOUR bot calls SLACK and keeps the connection open:
- Requires: Just the app token (SLACK_APP_TOKEN)
- Works behind firewalls
- No public URL needed

```
┌──────────┐                    ┌──────────┐
│  Your    │ ──WebSocket───────▶│  Slack   │
│  Bot     │ ◀─────────────────│  Server  │
└──────────┘   "hey, someone    └──────────┘
               added a 🔥!"
```

The bot maintains a persistent connection, and Slack pushes events through it.

### Required Tokens

| Token | Format | Purpose |
|-------|--------|---------|
| `SLACK_BOT_TOKEN` | `xoxb-...` | Post messages, read channels |
| `SLACK_APP_TOKEN` | `xapp-...` | Socket Mode connection |

---

## 5. Architecture Options

### Option A: Manual (Testing Only)
```
You manually run:
1. ./run_monitor.sh           # posts transients, exits
2. ./run_monitor.sh --listen  # keep terminal open for votes
```
- ✅ Simple
- ❌ Stops when you log out
- ❌ No automation

### Option B: Semi-automated (Recommended to Start)
```
Cron runs every 15 min:     ./run_monitor.sh
You run in screen/tmux:     ./run_monitor.sh --listen
```
- ✅ Transient checking is automated
- ✅ Vote listener survives logout
- ✅ Easy to monitor and debug
- ❌ Vote listener won't restart if server reboots

### Option C: Fully Automated (Production)
```
Cron runs every 15 min:     ./run_monitor.sh  
systemd service runs:       ./run_monitor.sh --listen
```
- ✅ Fully automated
- ✅ Auto-restarts on crash/reboot
- ✅ Proper logging
- ❌ Requires sudo access
- ❌ More complex to set up

---

## 6. Quick Start Guide

### Step 1: Set Up Cron for Transient Checking

```bash
# Open crontab editor
crontab -e

# Add this line (checks every 15 minutes):
*/15 * * * * cd /home/ishaang6/transient_monitor && ./run_monitor.sh >> logs/cron.log 2>&1
```

### Step 2: Start Vote Listener in Screen

```bash
# Create logs directory if needed
mkdir -p /home/ishaang6/transient_monitor/logs

# Start a screen session
screen -S votes

# Run the vote listener
cd /home/ishaang6/transient_monitor
./run_monitor.sh --listen

# Detach: Press Ctrl+A, then D
```

### Step 3: Verify Everything Works

```bash
# Check cron is set
crontab -l

# Check vote listener is running
screen -ls

# Reattach to see vote listener
screen -r votes
```

---

## 7. Troubleshooting

### Cron Not Running?
```bash
# Check cron logs
grep CRON /var/log/syslog

# Make sure run_monitor.sh is executable
chmod +x /home/ishaang6/transient_monitor/run_monitor.sh

# Test the command manually first
cd /home/ishaang6/transient_monitor && ./run_monitor.sh
```

### Vote Listener Died?
```bash
# Check if screen session exists
screen -ls

# If not, restart it
screen -S votes
./run_monitor.sh --listen
# Ctrl+A, D to detach
```

### Check Logs
```bash
# Cron output
tail -f /home/ishaang6/transient_monitor/logs/cron.log

# Vote listener (if using nohup)
tail -f /home/ishaang6/transient_monitor/logs/votes.log
```

---

## 8. File Structure

```
transient_monitor/
├── run_monitor.sh          # Main entry point
├── transient_monitor.py    # Core logic
├── .env                    # Slack tokens (NEVER commit!)
├── logs/                   # Log files
│   ├── cron.log
│   └── votes.log
├── voting_data/            # Vote storage
│   ├── vote_counts.csv
│   └── classifications.csv
└── data/
    └── posted_transients.csv
```

---

## 9. Questions to Discuss with PI

1. **Polling frequency**: How often should we check for new transients?
   - 15 minutes (responsive, minimal load)
   - 1 hour (conservative)
   
2. **Vote listener setup**: 
   - Screen/tmux (simple, manual restart after reboot)
   - systemd service (auto-restart, requires sudo)

3. **Account**: Should this run on your personal account or a service account?

4. **Monitoring**: Do you want alerts if the bot stops working?
