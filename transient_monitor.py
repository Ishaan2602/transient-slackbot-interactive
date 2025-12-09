import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
from slack_bolt import App
import schedule
import time
import threading

sys.path.append(os.path.join(os.path.dirname(__file__), 'askap_integration'))

try:
    from askap_image_processor import ASKAPImageProcessor # type: ignore
    ASKAP_AVAILABLE = True
except ImportError:
    ASKAP_AVAILABLE = False
    print("Warning: ASKAP integration not available")

# WISE Integration
sys.path.append(os.path.join(os.path.dirname(__file__), 'wise_integration'))

try:
    from wise_image_processor import WISEImageProcessor # type: ignore
    WISE_AVAILABLE = True
except ImportError:
    WISE_AVAILABLE = False
    print("Warning: WISE integration not available")

# Voting System Integration
sys.path.append(os.path.join(os.path.dirname(__file__), 'voting_system'))

try:
    from voting_system.vote_tracker import VoteTracker # type: ignore
    from voting_system.reaction_handler import ReactionHandler # type: ignore
    VOTING_AVAILABLE = True
except ImportError:
    try:
        # Fallback to direct import
        from vote_tracker import VoteTracker # type: ignore
        from reaction_handler import ReactionHandler # type: ignore
        VOTING_AVAILABLE = True
    except ImportError:
        VOTING_AVAILABLE = False
        print("Warning: Voting system not available")

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
CHANNEL_ID = "C09KLUNLU68"
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET', 'de2481e9523c65ac16ae1c5bad90a28d')

CASDA_USERNAME = os.getenv('CASDA_USERNAME_PERSONAL', 'ishaang6@illinois.edu')
CASDA_PASSWORD = os.getenv('CASDA_PASSWORD_PERSONAL', 'obscos_transient')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSIENTS_TXT = os.path.join(BASE_DIR, 'transients.txt')
NEW_TRANSIENTS_CSV = os.path.join(BASE_DIR, 'new_transients.csv')
LAST_CHECK_FILE = os.path.join(BASE_DIR, 'last_check.txt')

# ASKAP data directories
ASKAP_DATA_DIR = os.path.join(BASE_DIR, 'askap_data')
ASKAP_IMAGES_DIR = os.path.join(BASE_DIR, 'askap_images')

# WISE data directories
WISE_DATA_DIR = os.path.join(BASE_DIR, 'wise_data')
WISE_IMAGES_DIR = os.path.join(BASE_DIR, 'wise_images')

# Initialize Slack app
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

askap_processor = ASKAPImageProcessor(CASDA_USERNAME, CASDA_PASSWORD, ASKAP_DATA_DIR, ASKAP_IMAGES_DIR) if ASKAP_AVAILABLE else None
wise_processor = WISEImageProcessor(WISE_DATA_DIR, WISE_IMAGES_DIR) if WISE_AVAILABLE else None
vote_tracker = VoteTracker(BASE_DIR) if VOTING_AVAILABLE else None
reaction_handler = ReactionHandler(app, BASE_DIR) if VOTING_AVAILABLE else None

def setup_directories():
    for d in [ASKAP_DATA_DIR, ASKAP_IMAGES_DIR, WISE_DATA_DIR, WISE_IMAGES_DIR]:
        os.makedirs(d, exist_ok=True)

def load_last_check_time():
    try:
        if os.path.exists(LAST_CHECK_FILE):
            with open(LAST_CHECK_FILE, 'r') as f:
                return datetime.fromisoformat(f.read().strip())
    except:
        pass
    return pd.Timestamp.now(tz='UTC') - timedelta(hours=24)

def save_last_check_time(t):
    with open(LAST_CHECK_FILE, 'w') as f:
        f.write(t.isoformat())

def load_processed_transients():
    if os.path.exists(NEW_TRANSIENTS_CSV):
        df = pd.read_csv(NEW_TRANSIENTS_CSV)
        print(f"Loaded {len(df)} processed transients")
        return df
    return pd.DataFrame(columns=['source', 'observation', 'ra[deg]', 'dec[deg]', 
                                'field', 'time', 'test_statistic', 'status', 'processed_at'])

def save_new_transients(new_df, processed_df):
    new_df = new_df.copy()
    new_df['processed_at'] = pd.Timestamp.now(tz='UTC').isoformat()
    cols = ['source', 'observation', 'ra[deg]', 'dec[deg]', 'field', 'time', 'test_statistic', 'status', 'processed_at']
    subset = new_df[cols]
    combined = pd.concat([processed_df, subset], ignore_index=True) if len(processed_df) > 0 else subset
    combined.to_csv(NEW_TRANSIENTS_CSV, index=False)
    print(f"Saved {len(new_df)} transients")

def process_transient_coordinates(row):
    if 'centroid_ra[deg]' in row.index and not pd.isna(row['centroid_ra[deg]']):
        ra, dec = float(row['centroid_ra[deg]']), float(row['centroid_dec[deg]'])
    else:
        ra, dec = float(row['ra[deg]']), float(row['dec[deg]'])
    return (ra + 360 if ra < 0 else ra), dec

def generate_askap_image_for_transient(row, ra, dec):
    if not ASKAP_AVAILABLE or not askap_processor:
        return None
    name = f"{row['source']}_{row['observation']}"
    print(f"Generating ASKAP for {name}...")
    return askap_processor.process_transient(name, ra, dec)

def generate_wise_image_for_transient(row, ra, dec):
    if not WISE_AVAILABLE or not wise_processor:
        return None
    name = f"{row['source']}_{row['observation']}"
    print(f"Generating WISE for {name}...")
    return wise_processor.process_transient_wise_image(name, ra, dec)

def format_transient_message(row, ra, dec, askap_image_path=None, wise_image_path=None):
    source_name = f"{row['source']}_{row['observation']}"
    
    ra_hours = ra / 15.0
    ra_h = int(ra_hours)
    ra_m = int((ra_hours - ra_h) * 60)
    ra_s = ((ra_hours - ra_h) * 60 - ra_m) * 60
    
    dec_sign = "+" if dec >= 0 else "-"
    dec_abs = abs(dec)
    dec_d = int(dec_abs)
    dec_m = int((dec_abs - dec_d) * 60)
    dec_s = ((dec_abs - dec_d) * 60 - dec_m) * 60
    
    detection_time = pd.to_datetime(row['time']).strftime('%Y-%m-%d %H:%M UTC')
    
    time = pd.to_datetime(row['time']).strftime('%Y-%m-%d %H:%M UTC')
    
    # Determine peak flux display
    if pd.notna(row['peak_flux[mJy]']):
        peak_flux_text = f"{row['peak_flux[mJy]']:.2f} mJy"
    else:
        peak_flux_text = f"{row['peak_flux_90[mJy]']:.2f} mJy (90 GHz), {row['peak_flux_150[mJy]']:.2f} mJy (150 GHz)"
    
    # Build message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"New Transient: {source_name}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Coordinates:*\nRA: {ra_h:02d}h {ra_m:02d}m {ra_s:05.2f}s\nDec: {dec_sign}{dec_d:02d}° {dec_m:02d}' {dec_s:05.2f}\""
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Detection Time:*\n{detection_time}"
                }
            ]
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Test Statistic:*\n{row['test_statistic']:.1f}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Field:*\n{row['field']}"
                }
            ]
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Peak Flux:*\n{peak_flux_text}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{row['status']}"
                }
            ]
        }
    ]
    
    # Add duration if available
    if 'fwhm[days]' in row.index and not pd.isna(row['fwhm[days]']):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Duration (FWHM):* {row['fwhm[days]']:.2f} days"
            }
        })
    
    # Add image status section
    image_fields = []
    
    # ASKAP image status
    if askap_image_path and os.path.exists(askap_image_path):
        image_fields.append({
            "type": "mrkdwn",
            "text": "*ASKAP Radio:* Generated"
        })
    elif ASKAP_AVAILABLE:
        image_fields.append({
            "type": "mrkdwn",
            "text": "*ASKAP Radio:* No data available"
        })
    
    # WISE image status
    if wise_image_path and os.path.exists(wise_image_path):
        image_fields.append({
            "type": "mrkdwn",
            "text": "*WISE Infrared:* Generated"
        })
    elif WISE_AVAILABLE:
        image_fields.append({
            "type": "mrkdwn",
            "text": "*WISE Infrared:* Processing..."
        })
    
    if image_fields:
        blocks.append({
            "type": "section",
            "fields": image_fields
        })
    
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "Vote: 🔥 Interesting | 🌌 AGN | ⭐ Star | 🗑️ Junk"
        }]
    })
    
    return blocks

def post_transient_to_slack(row, ra, dec, askap_image_path=None, wise_image_path=None):
    """Post transient detection to Slack with optional ASKAP and WISE images."""
    source_name = f"{row['source']}_{row['observation']}"
    blocks = format_transient_message(row, ra, dec, askap_image_path, wise_image_path)
    
    # Post the main message with detailed blocks first
    response = app.client.chat_postMessage(
        channel=CHANNEL_ID,
        text=f"New transient detected: {source_name}",
        blocks=blocks
    )
    
    # Get the message timestamp for threading images
    message_ts = response.get("ts") if response.get("ok") else None
    
    # Add voting reactions to the main message
    if VOTING_AVAILABLE and reaction_handler and message_ts:
        reaction_handler.add_voting_reactions(CHANNEL_ID, message_ts)
    
    # Upload images as replies to the main message (threaded)
    if message_ts:
        if askap_image_path and os.path.exists(askap_image_path):
            print(f"Uploading ASKAP image for {source_name}...")
            app.client.files_upload_v2(
                channel=CHANNEL_ID,
                file=askap_image_path,
                title=f"ASKAP Radio Image - {source_name}",
                thread_ts=message_ts,
                initial_comment=""
            )
            print(f"ASKAP image uploaded for {source_name}")
        
        if wise_image_path and os.path.exists(wise_image_path):
            print(f"Uploading WISE image for {source_name}...")
            app.client.files_upload_v2(
                channel=CHANNEL_ID,
                file=wise_image_path,
                title=f"WISE Infrared Image - {source_name}",
                thread_ts=message_ts,
                initial_comment=""
            )
            print(f"WISE image uploaded for {source_name}")
    
    print(f"Posted {source_name} to Slack")
    return True

def check_for_new_transients():
    """Check for new transients and post to Slack with ASKAP images."""
    print(f"\nChecking for new transients - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load transients data
    print(f"Loading data from {os.path.basename(TRANSIENTS_TXT)}")
    if not os.path.exists(TRANSIENTS_TXT):
        print(f"Error: Transients file not found: {TRANSIENTS_TXT}")
        return
    
    data_transients = pd.read_csv(TRANSIENTS_TXT, sep='\t')
    data_transients['time'] = pd.to_datetime(data_transients['time'])
    
    processed_transients = load_processed_transients()
    
    # Identify new transients
    if len(processed_transients) > 0:
        data_transients['unique_id'] = data_transients['source'].astype(str) + '_' + data_transients['observation'].astype(str)
        processed_transients['unique_id'] = processed_transients['source'].astype(str) + '_' + processed_transients['observation'].astype(str)
        
        unprocessed_mask = ~data_transients['unique_id'].isin(processed_transients['unique_id'])
    else:
        unprocessed_mask = pd.Series([True] * len(data_transients), index=data_transients.index)
    
    # Filter by status
    status_filter = (data_transients['status'] == 'new') | (data_transients['status'].isna())
    
    if len(processed_transients) > 0:
        final_new_transients = data_transients[unprocessed_mask & status_filter]
    else:
        print("First run detected - processing recent transients only")
        recent_threshold = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30)
        recent_filter = (data_transients['status'].isna()) & (data_transients['time'] > recent_threshold)
        final_new_transients = data_transients[recent_filter]
    
    print(f"Total transients: {len(data_transients)}, Processed: {len(processed_transients)}, New: {len(final_new_transients)}")
    
    if len(final_new_transients) > 0:
        # Initialize ASKAP processor
        if ASKAP_AVAILABLE and askap_processor:
            print("Authenticating with CASDA...")
            if not askap_processor.authenticate():
                print("CASDA authentication failed - proceeding without images")
        
        # Process up to 5 transients per run
        transients_to_post = final_new_transients.head(5)
        
        for i, (index, row) in enumerate(transients_to_post.iterrows()):
            print(f"\nProcessing {i+1}/{len(transients_to_post)}: {row['source']}_{row['observation']}")
            
            # Get coordinates
            ra, dec = process_transient_coordinates(row)
            print(f"Coordinates: RA={ra:.6f}°, Dec={dec:.6f}°")
            
            # Generate ASKAP image
            askap_image_path = None
            if ASKAP_AVAILABLE and askap_processor:
                askap_image_path = generate_askap_image_for_transient(row, ra, dec)
            
            # Generate WISE image
            wise_image_path = None
            if WISE_AVAILABLE and wise_processor:
                wise_image_path = generate_wise_image_for_transient(row, ra, dec)
            
            # Post to Slack (this includes uploading images)
            post_transient_to_slack(row, ra, dec, askap_image_path, wise_image_path)
            
            # Substantial delay between transients to ensure all uploads complete
            if i < len(transients_to_post) - 1:
                print(f"Waiting 5 seconds to ensure all uploads complete before next transient...")
                time.sleep(5)
        
        # Save processed transients
        save_new_transients(transients_to_post, processed_transients)
        
        # Handle first run
        if len(processed_transients) == 0:
            historical_new = data_transients[data_transients['status'] == 'new']
            if len(historical_new) > 0:
                print(f"Marking {len(historical_new)} historical transients as processed")
                save_new_transients(historical_new, pd.DataFrame())
        
    else:
        print("No new transients found")
        
        # First run handling
        if len(processed_transients) == 0:
            historical_new = data_transients[data_transients['status'] == 'new']
            if len(historical_new) > 0:
                print(f"First run: Marking {len(historical_new)} historical transients as processed")
                save_new_transients(historical_new, pd.DataFrame())
    
    # Update last check time
    current_time = pd.Timestamp.now(tz='UTC')
    save_last_check_time(current_time)
    
    print(f"Check completed at {current_time.strftime('%H:%M:%S')}")

def run_scheduler():
    """Run the scheduler to check for new transients."""
    print("Scheduler running - checks daily at 12:00 PM")
    while True:
        schedule.run_pending()
        time.sleep(60)

# Slack command handlers
@app.message("voting results")
def handle_voting_results(message, say):
    """Handle voting results command"""
    if not VOTING_AVAILABLE or not vote_tracker:
        say("Voting system not available")
        return
    
    try:
        # Get top priority transients
        top_transients = vote_tracker.get_top_transients(10)
        
        if not top_transients:
            say("No votes recorded yet")
            return
        
        response = "*Voting Results - Top Priority Transients:*\n\n"
        
        for i, transient_id in enumerate(top_transients):
            votes = vote_tracker.get_transient_votes(transient_id)
            if votes:
                total = sum(votes.values())
                if total > 0:
                    response += f"*{i+1}. {transient_id}* (Total: {total})\n"
                    response += f"   AGN: {votes['AGN']} | Interesting: {votes['Interesting']} | "
                    response += f"Star: {votes['Star']} | Junk: {votes['Junk']}\n\n"
        
        if len(response) < 100:  # Only header
            say("No votes recorded yet")
        else:
            say(response)
            
    except Exception as e:
        say(f"Error getting voting results: {e}")

@app.message("vote summary")
def handle_vote_summary(message, say):
    """Handle vote summary command for specific transient"""
    text = message.get('text', '')
    words = text.split()
    
    if len(words) < 3:
        say("Usage: vote summary <transient_id>")
        return
    
    transient_id = words[2]
    
    if not VOTING_AVAILABLE or not reaction_handler:
        say("Voting system not available")
        return
    
    summary = reaction_handler.get_voting_summary(transient_id)
    say(f"*{transient_id}*\n{summary}")

def start_bolt_app():
    """Start the Slack Bolt app."""
    print("Starting Slack app...")
    app.start(port=int(os.environ.get("PORT", 3000)))

if __name__ == "__main__":
    print("Transient Monitor with ASKAP Integration")
    print(f"Data source: {os.path.basename(TRANSIENTS_TXT)}")
    print(f"Tracking file: {os.path.basename(NEW_TRANSIENTS_CSV)}")
    if ASKAP_AVAILABLE:
        print("ASKAP images: ENABLED")
    else:
        print("ASKAP images: DISABLED")
    
    setup_directories()
    
    # Schedule daily checks
    schedule.every().day.at("12:00").do(check_for_new_transients)
    
    print("Running initial check...")
    check_for_new_transients()
    
    # Start Slack app in background
    bolt_thread = threading.Thread(target=start_bolt_app)
    bolt_thread.daemon = True
    bolt_thread.start()
    
    run_scheduler()