#!/usr/bin/env python3
"""
Test voting functionality by checking stored votes.
"""
import os
import sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from voting_system.vote_tracker import VoteTracker

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    tracker = VoteTracker(base_dir)
    
    print("=" * 60)
    print("Vote Tracker Status")
    print("=" * 60)
    
    # Check if votes file exists
    if not os.path.exists(tracker.votes_file):
        print(f"\nNo votes file found at: {tracker.votes_file}")
        print("\nTo test voting:")
        print("1. Run: python transient_monitor.py --listen")
        print("2. Go to Slack and add reactions (🔥 🌌 ⭐ 🗑️) to transient posts")
        print("3. Check this script again to see recorded votes")
        return
    
    # Load votes directly from CSV
    votes_df = pd.read_csv(tracker.votes_file)
    
    if len(votes_df) == 0:
        print("\nNo votes recorded yet.")
        return
    
    print(f"\nVotes file: {tracker.votes_file}")
    print(f"Total transients with votes: {len(votes_df)}")
    print("-" * 60)
    
    for _, row in votes_df.iterrows():
        print(f"\n{row['transient_id']}:")
        print(f"  🔥 Interesting: {row['interesting_votes']}")
        print(f"  🌌 AGN: {row['agn_votes']}")
        print(f"  ⭐ Star: {row['star_votes']}")
        print(f"  🗑️ Junk: {row['junk_votes']}")
    
    # Show classifications if they exist
    if os.path.exists(tracker.classifications_file):
        print("\n" + "=" * 60)
        print("Classifications")
        print("=" * 60)
        class_df = pd.read_csv(tracker.classifications_file)
        for _, row in class_df.iterrows():
            print(f"  {row['transient_id']}: {row['classification']} ({row['confidence']:.1%} confidence)")
    
    # Show priority queue
    print("\n" + "=" * 60)
    print("Priority Queue (by vote score)")
    print("=" * 60)
    top = tracker.get_top_transients(10)
    for i, tid in enumerate(top, 1):
        votes = tracker.get_transient_votes(tid)
        if votes:
            score = votes['Interesting']*5 + votes['AGN']*4 + votes['Star']*3 + votes['Junk']*2
            print(f"{i}. {tid}: {score} points")

if __name__ == "__main__":
    main()
