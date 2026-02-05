#!/bin/bash
# Transient Monitor Run Script
# Sets up environment and runs the monitor (use for cron jobs)

# Change to project directory
cd /home/ishaang6/transient_monitor || exit 1

# Source environment (loads CVMFS python and env vars)
source ~/.bash_profile

# Refresh transients.txt from live data
./refresh_data.sh

# Run the transient monitor with timestamped output
{
    echo "========== Monitor run started at $(date) =========="
    python transient_monitor.py
    echo "========== Monitor run finished at $(date) =========="
} >> monitor.log 2>&1
