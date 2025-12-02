import pandas as pd
import os

import matplotlib.pyplot as plt

from .vote_tracker import VoteTracker

class VotingAnalyzer:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
        self.vote_tracker = VoteTracker(base_dir)
        self.base_dir = base_dir
    
    def generate_voting_report(self):
        if not os.path.exists(self.vote_tracker.votes_file):
            print("No voting data available")
            return
        
        votes_df = pd.read_csv(self.vote_tracker.votes_file)
        total_transients = len(votes_df)
        total_votes = votes_df[['agn_votes', 'interesting_votes', 'star_votes', 'junk_votes']].sum().sum()
        
        print("=== VOTING ANALYSIS ===")
        print(f"Transients: {total_transients}, Total Votes: {total_votes}, Avg: {total_votes/total_transients:.2f}")
        
        # Category breakdown
        category_totals = {
            'AGN': votes_df['agn_votes'].sum(),
            'Interesting': votes_df['interesting_votes'].sum(),
            'Star': votes_df['star_votes'].sum(),
            'Junk': votes_df['junk_votes'].sum()
        }
        
        print("=== VOTE DISTRIBUTION ===")
        for category, count in category_totals.items():
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            print(f"{category}: {count} votes ({percentage:.1f}%)")
        
        print()
        
        # Top voted transients
        votes_df['total_votes'] = votes_df[['agn_votes', 'interesting_votes', 'star_votes', 'junk_votes']].sum(axis=1)
        top_voted = votes_df.nlargest(5, 'total_votes')
        
        print("=== TOP 5 MOST VOTED TRANSIENTS ===")
        for _, row in top_voted.iterrows():
            tid = row['transient_id']
            if '_' in tid and len(tid) > 15:
                coord, obs = tid.split('_', 1)
                tid = f"{coord}_{obs[:6]}..."
            
            print(f"{tid}: {int(row['total_votes'])} votes")
            print(f"  AGN: {int(row['agn_votes'])}, Int: {int(row['interesting_votes'])}, Star: {int(row['star_votes'])}, Junk: {int(row['junk_votes'])}")
        
        print()
        
        consensus = votes_df[votes_df['total_votes'] >= 3]
        if len(consensus) > 0:
            print("=== CONSENSUS ANALYSIS ===")
            print(f"Transients with 3+ votes: {len(consensus)} ({len(consensus)/len(votes_df)*100:.1f}%)")
            
            for _, row in consensus.iterrows():
                max_v = max(row['agn_votes'], row['interesting_votes'], row['star_votes'], row['junk_votes'])
                if max_v > row['total_votes'] / 2:
                    winner = ['AGN', 'Interesting', 'Star', 'Junk'][
                        [row['agn_votes'], row['interesting_votes'], row['star_votes'], row['junk_votes']].index(max_v)
                    ]
                    conf = max_v / row['total_votes'] * 100
                    tid = row['transient_id']
                    if '_' in tid and len(tid) > 15:
                        coord, obs = tid.split('_', 1)
                        tid = f"{coord}_{obs[:6]}..."
                    print(f"  {tid}: {winner} ({conf:.0f}%)")
        
        print()
        if os.path.exists(self.vote_tracker.classifications_file):
            class_df = pd.read_csv(self.vote_tracker.classifications_file)
            counts = class_df['classification'].value_counts()
            
            print("=== CLASSIFICATION RESULTS ===")
            for cls, count in counts.items():
                print(f"{cls}: {count}")
            
            avg_conf = class_df.groupby('classification')['confidence'].mean()
            print("\n=== AVG CONFIDENCE ===")
            for cls, conf in avg_conf.items():
                print(f"{cls}: {conf:.2f}")
        
        print()
        queue = self.vote_tracker.get_priority_queue()
        if queue:
            print("=== TOP 10 PRIORITY ===")
            for i, tid in enumerate(queue[:10]):
                votes = self.vote_tracker.get_transient_votes(tid)
                if votes:
                    score = votes['Interesting']*5 + votes['AGN']*4 + votes['Star']*3 + votes['Junk']*2
                    print(f"{i+1}. {tid} ({score})")
    
    def plot_voting_statistics(self):
        if not os.path.exists(self.vote_tracker.votes_file):
            print("No data to plot")
            return
        
        votes_df = pd.read_csv(self.vote_tracker.votes_file)
        if len(votes_df) == 0:
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Transient Voting Analysis', fontsize=16, fontweight='bold')
        totals = {
            'AGN': votes_df['agn_votes'].sum(),
            'Interesting': votes_df['interesting_votes'].sum(),
            'Star': votes_df['star_votes'].sum(),
            'Junk': votes_df['junk_votes'].sum()
        }
        totals = {k: v for k, v in totals.items() if v > 0}
        
        if totals:
            colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
            ax1.pie(totals.values(), labels=totals.keys(), autopct='%1.1f%%', colors=colors[:len(totals)])
        ax1.set_title('Vote Distribution')
        
        votes_df['total_votes'] = votes_df[['agn_votes', 'interesting_votes', 'star_votes', 'junk_votes']].sum(axis=1)
        ax2.hist(votes_df['total_votes'], bins=max(1, len(votes_df)//5), alpha=0.7, color='skyblue')
        ax2.set_xlabel('Total Votes')
        ax2.set_ylabel('Transients')
        ax2.set_title('Vote Counts')
        ax2.grid(alpha=0.3)
        
        # 3. Category breakdown stacked bar chart (moved from bottom right)
        categories = ['interesting_votes', 'agn_votes', 'star_votes', 'junk_votes']
        category_labels = ['Interesting', 'AGN', 'Star', 'Junk']
        
        if len(votes_df) > 0:
            # Show top 12 transients with stacked votes
            top_12 = votes_df.nlargest(min(12, len(votes_df)), 'total_votes')
            bottom = [0] * len(top_12)
            
            # Updated colors - Interesting gets most prominent color
            colors_stack = ['#4ecdc4', '#ff6b6b', '#45b7d1', '#f9ca24']
            
            for i, (category, label, color) in enumerate(zip(categories, category_labels, colors_stack)):
                ax3.bar(range(len(top_12)), top_12[category], bottom=bottom, 
                       label=label, color=color, alpha=0.8)
                bottom = [sum(x) for x in zip(bottom, top_12[category])]
            
            # Clean up transient names for display - intelligent truncation for coordinate-based names
            clean_labels = []
            for name in top_12['transient_id']:
                # For coordinate-based names like "2227-55_134258682", keep the coordinate part prominent
                if '_' in name and '-' in name.split('_')[0]:
                    # Coordinate_observation format: show coordinate + shortened observation
                    coord_part, obs_part = name.split('_', 1)
                    clean_name = f"{coord_part}_{obs_part[:4]}.." if len(obs_part) > 6 else name
                else:
                    # Other formats: simple truncation
                    clean_name = name[:10] + '..' if len(name) > 12 else name
                clean_labels.append(clean_name)
            
            ax3.set_xlabel('Transients')
            ax3.set_ylabel('Votes')
            ax3.set_title(f'Vote Breakdown - Top {len(top_12)} Transients')
            ax3.set_xticks(range(len(top_12)))
            ax3.set_xticklabels(clean_labels, rotation=45, ha='right')
            ax3.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize='small')
            ax3.grid(True, alpha=0.3)
        else:
            ax3.text(0.5, 0.5, 'No data to display', ha='center', va='center')
            ax3.set_title('Vote Breakdown by Transient')
        
        interesting = votes_df[votes_df['interesting_votes'] > 0].nlargest(min(10, len(votes_df)), 'interesting_votes')
        
        if len(interesting) > 0:
            labels = []
            for name in interesting['transient_id']:
                if '_' in name and '-' in name.split('_')[0]:
                    c, o = name.split('_', 1)
                    labels.append(f"{c}_{o[:4]}.." if len(o) > 6 else name)
                else:
                    labels.append(name[:12] + '..' if len(name) > 14 else name)
            
            bars = ax4.bar(range(len(interesting)), interesting['interesting_votes'], 
                          color='#4ecdc4', alpha=0.8, edgecolor='darkgreen')
            
            for i, (bar, v) in enumerate(zip(bars, interesting['interesting_votes'])):
                if v > 0:
                    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, 
                            str(int(v)), ha='center', va='bottom', fontweight='bold')
            
            ax4.set_title(f'Top {len(interesting)} Interesting')
            ax4.set_xticks(range(len(interesting)))
            ax4.set_xticklabels(labels, rotation=45, ha='right')
            ax4.grid(alpha=0.3)
            
            if len(bars) > 0:
                bars[0].set_color('#ff6b6b')
        
        plt.tight_layout()
        plot_path = os.path.join(self.base_dir, 'voting_data', 'voting_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved plots to: {plot_path}")
        plt.show()
    
    def export_detailed_results(self):
        if not os.path.exists(self.vote_tracker.votes_file):
            return
        
        df = pd.read_csv(self.vote_tracker.votes_file)
        df['total_votes'] = df[['agn_votes', 'interesting_votes', 'star_votes', 'junk_votes']].sum(axis=1)
        df['priority_score'] = df['interesting_votes']*5 + df['agn_votes']*4 + df['star_votes']*3 + df['junk_votes']*2
        df = df.sort_values('priority_score', ascending=False)
        
        if os.path.exists(self.vote_tracker.classifications_file):
            class_df = pd.read_csv(self.vote_tracker.classifications_file)
            df = df.merge(class_df, on='transient_id', how='left')
        
        path = os.path.join(self.base_dir, 'voting_data', 'detailed_voting_results.csv')
        df.to_csv(path, index=False)
        print(f"\nExported to: {path}")
        return path


def main():
    analyzer = VotingAnalyzer()
    analyzer.generate_voting_report()
    analyzer.plot_voting_statistics()
    analyzer.export_detailed_results()

if __name__ == "__main__":
    main()