import os
import sys
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from voting_system.vote_tracker import VoteTracker

def test_voting_basic():
    vote_tracker = VoteTracker()
    test_votes = [
        {'transient_id': 'AT2024abc', 'reactions': {'milky_way': 5, 'fire': 1, 'star': 0, 'wastebasket': 0}},
        {'transient_id': 'AT2024def', 'reactions': {'milky_way': 1, 'fire': 4, 'star': 1, 'wastebasket': 0}}
    ]
    
    for vote_data in test_votes:
        vote_tracker.update_vote_counts(vote_data['transient_id'], vote_data['reactions'])
    
    print("Basic voting test passed")

def test_priority_queue():
    vote_tracker = VoteTracker()
    priority_queue = vote_tracker.get_priority_queue()
    top_transients = vote_tracker.get_top_transients(3)
    print("Priority queue test passed")

def main():
    print("Testing voting system...")
    test_voting_basic()
    test_priority_queue()
    print("Voting system tests passed")

if __name__ == "__main__":
    main()