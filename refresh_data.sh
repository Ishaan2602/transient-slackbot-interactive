#!/bin/bash
# copy live data to local folder

src="/sptlocal/transfer/rsync/transfer_database/transients.txt"
dest="$HOME/transient_monitor/transients.txt"

cp $src $dest
echo "refreshed data at $(date)"