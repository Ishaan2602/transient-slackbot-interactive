#!/bin/bash
# Test Reprocess Script
# Removes recent processed transients and reruns monitor (for testing)

# Change to project directory
cd /home/ishaang6/transient_monitor || exit 1

# Source environment (loads CVMFS python and env vars)
source ~/.bash_profile

# Run test_reprocess_recent with auto-run
{
    echo "========== Test reprocess started at $(date) =========="
    python tests/test_reprocess_recent.py --count 3 --run
    echo "========== Test reprocess finished at $(date) =========="
} >> monitor.log 2>&1
