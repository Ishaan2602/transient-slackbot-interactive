from slack_bolt import App
from .vote_tracker import VoteTracker

class ReactionHandler:
    def __init__(self, app, base_dir=None):
        self.app = app
        self.vote_tracker = VoteTracker(base_dir)
        self.reaction_map = {"milky_way": "milky_way", "fire": "fire", "star": "star", "wastebasket": "wastebasket"}
        self._register_handlers()
    
    def _register_handlers(self):
        @self.app.event("reaction_added")
        def handle_reaction_added(event, say):
            self._process_reaction_event(event, say, action="added")
        
        @self.app.event("reaction_removed") 
        def handle_reaction_removed(event, say):
            self._process_reaction_event(event, say, action="removed")
    
    def _process_reaction_event(self, event, say, action="added"):
        """Process reaction addition/removal events"""
        try:
            # Extract event details
            reaction = event.get("reaction")
            channel = event.get("item", {}).get("channel")
            timestamp = event.get("item", {}).get("ts")
            user = event.get("user")
            
            if not all([reaction, channel, timestamp]):
                print(f"Incomplete reaction event data: {event}")
                return
            
            # Check if this is a voting reaction
            if reaction not in self.reaction_map:
                return
            
            # Get transient ID from message 
            transient_id = self._extract_transient_id(channel, timestamp)
            if not transient_id:
                return
            
            # Get reaction counts
            reaction_counts = self._get_message_reactions(channel, timestamp)
            
            # Update vote tracker
            self.vote_tracker.update_vote_counts(transient_id, reaction_counts)
            
            print(f"Reaction {action}: {reaction} by {user} for transient {transient_id}")
            
        except Exception as e:
            print(f"Error processing reaction event: {e}")
    
    def _extract_transient_id(self, channel, timestamp):
        """Extract transient ID from Slack message"""
        try:
            # Get message content to extract transient ID
            result = self.app.client.conversations_history(
                channel=channel,
                latest=timestamp,
                limit=1,
                inclusive=True
            )
            
            if not result.get("ok") or not result.get("messages"):
                return None
            
            message_text = result["messages"][0].get("text", "")
            
            # Extract transient ID from message format
            # Look for patterns like "New Transient: AT2024abc" or similar
            import re
            patterns = [
                r"Transient:\s*(\w+)",
                r"AT(\d{4}\w+)",
                r"SN(\d{4}\w+)", 
                r"ID:\s*(\w+)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message_text)
                if match:
                    return match.group(1) if "ID:" in pattern or "Transient:" in pattern else match.group(0)
            
            return None
            
        except Exception as e:
            print(f"Error extracting transient ID: {e}")
            return None
    
    def _get_message_reactions(self, channel, timestamp):
        """Get current reaction counts for a message"""
        try:
            result = self.app.client.reactions_get(
                channel=channel,
                timestamp=timestamp
            )
            
            if not result.get("ok"):
                return {}
            
            reactions = result.get("message", {}).get("reactions", [])
            reaction_counts = {}
            
            for reaction_data in reactions:
                reaction_name = reaction_data.get("name")
                count = reaction_data.get("count", 0)
                users = reaction_data.get("users", [])
                
                bot_user_id = self.app.client.auth_test().get("user_id")
                if bot_user_id in users:
                    count = max(0, count - 1)
                
                if reaction_name in self.reaction_map and count > 0:
                    reaction_type = self.reaction_map[reaction_name]
                    reaction_counts[reaction_type] = count
            
            return reaction_counts
            
        except Exception as e:
            print(f"Error getting message reactions: {e}")
            return {}
    
    def add_voting_reactions(self, channel, timestamp):
        """Add voting reaction options to a new transient message"""
        try:
            for reaction in ["milky_way", "fire", "star", "wastebasket"]:
                try:
                    self.app.client.reactions_add(channel=channel, name=reaction, timestamp=timestamp)
                except Exception as e:
                    if "invalid_name" not in str(e):
                        print(f"Failed to add reaction {reaction}: {e}")
            print(f"Added voting reactions to message {timestamp}")
        except Exception as e:
            print(f"Error adding voting reactions: {e}")
    
    def get_voting_summary(self, transient_id):
        votes = self.vote_tracker.get_transient_votes(transient_id)
        if not votes or sum(votes.values()) == 0:
            return "No votes recorded"
        
        total = sum(votes.values())
        return f"*Votes ({total} total):*\nAGN: {votes['AGN']}\nInteresting: {votes['Interesting']}\nStar: {votes['Star']}\nJunk: {votes['Junk']}"