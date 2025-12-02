import pandas as pd
import os
import sys
import argparse
from datetime import datetime

def remove_recent_processed_transients(count=5, base_dir=None):
    base_dir = base_dir or os.path.dirname(os.path.dirname(__file__))
    csv_path = os.path.join(base_dir, 'new_transients.csv')
    
    if not os.path.exists(csv_path):
        print(f"No file at: {csv_path}")
        return False
    
    df = pd.read_csv(csv_path)
    if len(df) == 0:
        return False
    
    count = min(count, len(df))
    print(f"Processed: {len(df)}, removing {count} for reprocessing")
    
    if 'processed_at' in df.columns:
        df['processed_at'] = pd.to_datetime(df['processed_at'], format='ISO8601')
        df = df.sort_values('processed_at')
    
    remaining = df.iloc[:-count]
    removed = df.iloc[-count:]
    
    print("Removing:")
    for _, row in removed.iterrows():
        print(f"  {row['source']}_{row['observation']}")
    
    remaining.to_csv(csv_path, index=False)
    print(f"Reduced from {len(df)} to {len(remaining)}")
    return True

def run_transient_monitor(base_dir=None):
    base_dir = base_dir or os.path.dirname(os.path.dirname(__file__))
    print("\nRunning transient check...")
    
    try:
        sys.path.insert(0, base_dir)
        from transient_monitor import check_for_new_transients, setup_directories
        setup_directories()
        check_for_new_transients()
        print("Check complete")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', '-n', type=int, default=5)
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    print(f"Reprocessing {args.count} transients")
    
    if not remove_recent_processed_transients(args.count, base_dir):
        return 1
    
    if not run_transient_monitor(base_dir):
        return 1
    
    print("\nDone - check Slack")
    return 0

if __name__ == "__main__":
    exit(main())