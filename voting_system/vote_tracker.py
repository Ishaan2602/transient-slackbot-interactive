import pandas as pd
import os
import heapq

class VoteTracker:
    def __init__(self, base_dir=None):
        base_dir = base_dir or os.path.dirname(os.path.dirname(__file__))
        self.votes_file = os.path.join(base_dir, 'voting_data', 'vote_counts.csv')
        self.classifications_file = os.path.join(base_dir, 'voting_data', 'classifications.csv')
        self.thresholds = {"AGN": 3, "Interesting": 2, "Star": 2, "Junk": 3}
        os.makedirs(os.path.dirname(self.votes_file), exist_ok=True)
    
    def update_vote_counts(self, transient_id, reaction_counts):
        votes_df = pd.read_csv(self.votes_file) if os.path.exists(self.votes_file) else \
                   pd.DataFrame(columns=['transient_id', 'agn_votes', 'interesting_votes', 'star_votes', 'junk_votes'])
        
        row_data = {
            'transient_id': transient_id,
            'agn_votes': reaction_counts.get('milky_way', 0),
            'interesting_votes': reaction_counts.get('fire', 0),
            'star_votes': reaction_counts.get('star', 0),
            'junk_votes': reaction_counts.get('wastebasket', 0)
        }
        
        if transient_id in votes_df['transient_id'].values:
            idx = votes_df[votes_df['transient_id'] == transient_id].index[0]
            for col in ['agn_votes', 'interesting_votes', 'star_votes', 'junk_votes']:
                votes_df.loc[idx, col] = row_data[col]
        else:
            votes_df = pd.concat([votes_df, pd.DataFrame([row_data])], ignore_index=True)
        
        votes_df.to_csv(self.votes_file, index=False)
        print(f"Updated votes for {transient_id}: {reaction_counts}")
        self.update_classifications()
    
    def update_classifications(self):
        if not os.path.exists(self.votes_file):
            return
        
        votes_df = pd.read_csv(self.votes_file)
        class_df = pd.read_csv(self.classifications_file) if os.path.exists(self.classifications_file) else \
                   pd.DataFrame(columns=['transient_id', 'classification', 'confidence'])
        
        for _, row in votes_df.iterrows():
            votes = {
                'AGN': row['agn_votes'],
                'Interesting': row['interesting_votes'],
                'Star': row['star_votes'],
                'Junk': row['junk_votes']
            }
            
            max_category = max(votes, key=votes.get)
            classification = max_category if votes[max_category] >= self.thresholds.get(max_category, 999) else "Unclassified"
            confidence = max(votes.values()) / sum(votes.values()) if sum(votes.values()) > 0 else 0
            
            if row['transient_id'] in class_df['transient_id'].values:
                idx = class_df[class_df['transient_id'] == row['transient_id']].index[0]
                class_df.loc[idx, ['classification', 'confidence']] = [classification, confidence]
            else:
                new_row = {'transient_id': row['transient_id'], 'classification': classification, 'confidence': confidence}
                class_df = pd.concat([class_df, pd.DataFrame([new_row])], ignore_index=True)
        
        class_df.to_csv(self.classifications_file, index=False)
    
    def get_priority_queue(self):
        if not os.path.exists(self.votes_file):
            return []
        
        votes_df = pd.read_csv(self.votes_file)
        priority_heap = []
        
        for _, row in votes_df.iterrows():
            score = row['interesting_votes']*5 + row['agn_votes']*4 + row['star_votes']*3 + row['junk_votes']*2
            heapq.heappush(priority_heap, (-score, row['transient_id']))
        
        return [tid for _, tid in sorted(priority_heap)]
    
    def get_top_transients(self, n=5):
        return self.get_priority_queue()[:n]
    
    def get_transient_votes(self, transient_id):
        if not os.path.exists(self.votes_file):
            return None
        
        votes_df = pd.read_csv(self.votes_file)
        row = votes_df[votes_df['transient_id'] == transient_id]
        
        if len(row) > 0:
            r = row.iloc[0]
            return {
                'AGN': r['agn_votes'],
                'Interesting': r['interesting_votes'],
                'Star': r['star_votes'],
                'Junk': r['junk_votes']
            }
        return None