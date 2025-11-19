"""
Vote Tracker for Transient Classification System
Manages vote counts, classifications, and priority ordering
"""

import pandas as pd
import os
from collections import defaultdict
import heapq

class VoteTracker:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
        
        self.votes_file = os.path.join(base_dir, 'voting_data', 'vote_counts.csv')
        self.classifications_file = os.path.join(base_dir, 'voting_data', 'classifications.csv')
        
        self.thresholds = {"AGN": 3, "Interesting": 2, "Star": 2, "Junk": 3}
        os.makedirs(os.path.dirname(self.votes_file), exist_ok=True)
    
    def update_vote_counts(self, transient_id, reaction_counts):
        votes_df = pd.read_csv(self.votes_file) if os.path.exists(self.votes_file) else pd.DataFrame(columns=['transient_id', 'agn_votes', 'interesting_votes', 'star_votes', 'junk_votes'])
        
        if transient_id in votes_df['transient_id'].values:
            idx = votes_df[votes_df['transient_id'] == transient_id].index[0]
            votes_df.loc[idx, 'agn_votes'] = reaction_counts.get('milky_way', 0)
            votes_df.loc[idx, 'interesting_votes'] = reaction_counts.get('fire', 0)
            votes_df.loc[idx, 'star_votes'] = reaction_counts.get('star', 0)
            votes_df.loc[idx, 'junk_votes'] = reaction_counts.get('wastebasket', 0)
        else:
            new_row = {'transient_id': transient_id, 'agn_votes': reaction_counts.get('milky_way', 0), 'interesting_votes': reaction_counts.get('fire', 0), 'star_votes': reaction_counts.get('star', 0), 'junk_votes': reaction_counts.get('wastebasket', 0)}
            votes_df = pd.concat([votes_df, pd.DataFrame([new_row])], ignore_index=True)
        
        votes_df.to_csv(self.votes_file, index=False)
        print(f"Updated votes for {transient_id}: {reaction_counts}")
        self.update_classifications()
    
    def update_classifications(self):
        if not os.path.exists(self.votes_file):
            return
            
        votes_df = pd.read_csv(self.votes_file)
        class_df = pd.read_csv(self.classifications_file) if os.path.exists(self.classifications_file) else pd.DataFrame(columns=['transient_id', 'classification', 'confidence'])
        
        for _, row in votes_df.iterrows():
            votes = {'AGN': row['agn_votes'], 'Interesting': row['interesting_votes'], 'Star': row['star_votes'], 'Junk': row['junk_votes']}
            classification = self.classify_transient(votes)
            confidence = max(votes.values()) / sum(votes.values()) if sum(votes.values()) > 0 else 0
            
            if row['transient_id'] in class_df['transient_id'].values:
                idx = class_df[class_df['transient_id'] == row['transient_id']].index[0]
                class_df.loc[idx, ['classification', 'confidence']] = [classification, confidence]
            else:
                new_row = {'transient_id': row['transient_id'], 'classification': classification, 'confidence': confidence}
                class_df = pd.concat([class_df, pd.DataFrame([new_row])], ignore_index=True)
        
        class_df.to_csv(self.classifications_file, index=False)
    
    def classify_transient(self, votes):
        max_category = max(votes, key=votes.get)
        return max_category if max(votes.values()) >= self.thresholds.get(max_category, 999) else "Unclassified"
    
    def get_priority_queue(self):
        if not os.path.exists(self.votes_file):
            return []
        
        votes_df = pd.read_csv(self.votes_file)
        priority_heap = []
        for _, row in votes_df.iterrows():
            score = row['agn_votes']*4 + row['interesting_votes']*3 + row['star_votes']*2 + row['junk_votes']
            heapq.heappush(priority_heap, (-score, row['transient_id']))
        return [transient_id for _, transient_id in sorted(priority_heap)]
    
    def get_top_transients(self, n=5):
        return self.get_priority_queue()[:n]
    
    def get_transient_votes(self, transient_id):
        if not os.path.exists(self.votes_file):
            return None
        votes_df = pd.read_csv(self.votes_file)
        row = votes_df[votes_df['transient_id'] == transient_id]
        if len(row) > 0:
            r = row.iloc[0]
            return {'AGN': r['agn_votes'], 'Interesting': r['interesting_votes'], 'Star': r['star_votes'], 'Junk': r['junk_votes']}
        return None