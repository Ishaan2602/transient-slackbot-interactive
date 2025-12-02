import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from voting_system.vote_tracker import VoteTracker

if __name__ == "__main__":
    tracker = VoteTracker()
    
    votes = [
        ('AT2024abc', {'milky_way': 5, 'fire': 1, 'star': 0, 'wastebasket': 0}),
        ('AT2024def', {'milky_way': 1, 'fire': 4, 'star': 1, 'wastebasket': 0})
    ]
    
    for tid, reactions in votes:
        tracker.update_vote_counts(tid, reactions)
    
    queue = tracker.get_priority_queue()
    top = tracker.get_top_transients(3)
    
    print("Voting tests passed")