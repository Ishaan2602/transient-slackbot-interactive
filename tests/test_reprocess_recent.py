#!/usr/bin/env python3
"""
Remove recent processed transients from new_transients.csv to allow reprocessing.
Useful for testing the monitor without waiting for new live transients.
"""
import pandas as pd
import os
import sys
import argparse
from datetime import datetime

def remove_recent_processed_transients(count=5, base_dir=None):
    """Remove the N most recently processed transients from tracking file."""
    base_dir = base_dir or os.path.dirname(os.path.dirname(__file__))
    csv_path = os.path.join(base_dir, 'new_transients.csv')
    
    if not os.path.exists(csv_path):
        print(f"No tracking file at: {csv_path}")
        return False
    
    df = pd.read_csv(csv_path)
    if len(df) == 0:
        print("No processed transients to remove")
        return False
    
    count = min(count, len(df))
    print(f"Total processed: {len(df)}")
    print(f"Removing last {count} for reprocessing")
    
    # Sort by processed_at to get most recent
    if 'processed_at' in df.columns:
        df['processed_at'] = pd.to_datetime(df['processed_at'], format='ISO8601')
        df = df.sort_values('processed_at')
    
    # Keep all except the last N
    remaining = df.iloc[:-count]
    removed = df.iloc[-count:]
    
    print(f"\nWill be reprocessed on next run:")
    for _, row in removed.iterrows():
        source_id = f"{row['source']}_{row['observation']}"
        proc_at = row.get('processed_at', 'unknown')
        print(f"  {source_id} (processed: {proc_at})")
    
    # Save updated tracking file
    remaining.to_csv(csv_path, index=False)
    print(f"\nUpdated tracking file: {len(df)} → {len(remaining)}")
    return True

def run_transient_monitor(base_dir=None):
    """Run the transient monitor check."""
    base_dir = base_dir or os.path.dirname(os.path.dirname(__file__))
    print("\n" + "="*60)
    print("Running transient monitor check...")
    print("="*60)
    
    try:
        sys.path.insert(0, base_dir)
        from transient_monitor import check_for_new_transients, setup_directories
        setup_directories()
        check_for_new_transients()
        print("\n" + "="*60)
        print("Check complete!")
        print("="*60)
        return True
    except Exception as e:
        print(f"Error running monitor: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Remove recent processed transients and optionally rerun monitor'
    )
    parser.add_argument(
        '--count', '-n', 
        type=int, 
        default=5,
        help='Number of recent transients to remove (default: 5)'
    )
    parser.add_argument(
        '--run', '-r',
        action='store_true',
        help='Run transient monitor after removing transients'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Show what would be removed without actually removing'
    )
    
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    print("="*60)
    print(f"Test Reprocess Recent Transients")
    print("="*60)
    print(f"Removing: {args.count} transients")
    print(f"Base dir: {base_dir}")
    print("="*60 + "\n")
    
    if args.dry_run:
        csv_path = os.path.join(base_dir, 'new_transients.csv')
        df = pd.read_csv(csv_path)
        if 'processed_at' in df.columns:
            df['processed_at'] = pd.to_datetime(df['processed_at'], format='ISO8601')
            df = df.sort_values('processed_at')
        removed = df.tail(args.count)
        print(f"Would remove {len(removed)} transients:")
        for _, row in removed.iterrows():
            print(f"  {row['source']}_{row['observation']}")
        return
    
    if not remove_recent_processed_transients(args.count, base_dir):
        print("Failed to remove transients")
        sys.exit(1)
    
    if args.run:
        if not run_transient_monitor(base_dir):
            print("Monitor run failed")
            sys.exit(1)
    else:
        print("\nTo run monitor manually:")
        print("  python transient_monitor.py")
        print("Or automatically:")
        print("  python tests/test_reprocess_recent.py --run")

if __name__ == "__main__":
    main()
