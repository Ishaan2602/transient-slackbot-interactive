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
        reaction = event.get("reaction")
        channel = event.get("item", {}).get("channel")
        timestamp = event.get("item", {}).get("ts")
        user = event.get("user")
        
        if not all([reaction, channel, timestamp]) or reaction not in self.reaction_map:
            return
        
        transient_id = self._extract_transient_id(channel, timestamp)
        if not transient_id:
            return
        
        reaction_counts = self._get_message_reactions(channel, timestamp)
        self.vote_tracker.update_vote_counts(transient_id, reaction_counts)
        print(f"Reaction {action}: {reaction} by {user} for {transient_id}")
    
    def _extract_transient_id(self, channel, timestamp):
        import re
        
        result = self.app.client.conversations_history(
            channel=channel, latest=timestamp, limit=1, inclusive=True
        )
        
        if not result.get("ok") or not result.get("messages"):
            return None
        
        text = result["messages"][0].get("text", "")
        
        patterns = [
            r"New Transient:\s*([\w-]+_\d+)",
            r"Transient:\s*([\w-]+_\d+)",
            r"([\d-]+_\d+)",
            r"AT(\d{4}\w+)",
            r"SN(\d{4}\w+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1) if "Transient:" in pattern else match.group(0)
        
        return None
    
    def _get_message_reactions(self, channel, timestamp):
        result = self.app.client.reactions_get(channel=channel, timestamp=timestamp)
        
        if not result.get("ok"):
            return {}
        
        reactions = result.get("message", {}).get("reactions", [])
        reaction_counts = {}
        bot_user_id = self.app.client.auth_test().get("user_id")
        
        for r in reactions:
            name = r.get("name")
            count = r.get("count", 0)
            users = r.get("users", [])
            
            if bot_user_id in users:
                count = max(0, count - 1)
            
            if name in self.reaction_map and count > 0:
                reaction_counts[self.reaction_map[name]] = count
        
        return reaction_counts
    
    def add_voting_reactions(self, channel, timestamp):
        for reaction in ["fire", "milky_way", "star", "wastebasket"]:
            try:
                self.app.client.reactions_add(channel=channel, name=reaction, timestamp=timestamp)
            except:
                pass
    
    def get_voting_summary(self, transient_id):
        votes = self.vote_tracker.get_transient_votes(transient_id)
        if not votes or sum(votes.values()) == 0:
            return "No votes recorded"
        
        total = sum(votes.values())
        return f"*Votes ({total} total):*\nAGN: {votes['AGN']}\nInteresting: {votes['Interesting']}\nStar: {votes['Star']}\nJunk: {votes['Junk']}"