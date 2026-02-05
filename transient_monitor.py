import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
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

# DECam Integration
sys.path.append(os.path.join(os.path.dirname(__file__), 'decam_integration'))

try:
    from decam_image_processor import DECamImageProcessor # type: ignore
    DECAM_AVAILABLE = True
except ImportError:
    DECAM_AVAILABLE = False
    print("Warning: DECam integration not available")

# TS Map Extractor Integration
sys.path.append(os.path.join(os.path.dirname(__file__), 'ts_integration'))

try:
    from ts_map_extractor import TSMapExtractor, generate_ts_map_cutout # type: ignore
    TSMAP_AVAILABLE = True
except ImportError:
    TSMAP_AVAILABLE = False
    print("Warning: TS map extractor not available")

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

# Global verbose flag (set via --verbose/-v argument)
VERBOSE = False

CASDA_USERNAME = os.getenv('CASDA_USERNAME_PERSONAL', 'ishaang6@illinois.edu')
CASDA_PASSWORD = os.getenv('CASDA_PASSWORD_PERSONAL', 'obscos_transient')
DATALAB_USERNAME = os.getenv('DATALAB_USERNAME')
DATALAB_PASSWORD = os.getenv('DATALAB_PASSWORD')
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

# DECam data directories
DECAM_DATA_DIR = os.path.join(BASE_DIR, 'decam_data')
DECAM_IMAGES_DIR = os.path.join(BASE_DIR, 'decam_images')

# TS maps directory
TS_MAPS_DIR = os.path.join(BASE_DIR, 'ts_maps')

# Socket Mode token for Events API (reactions/voting)
SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')

# Initialize Slack app
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

# Processors will be initialized in setup_directories() with correct verbose flag
askap_processor = None
wise_processor = None
decam_processor = None
ts_map_extractor = None
vote_tracker = VoteTracker(BASE_DIR) if VOTING_AVAILABLE else None
reaction_handler = ReactionHandler(app, BASE_DIR) if VOTING_AVAILABLE else None

def setup_directories():
    global askap_processor, wise_processor, decam_processor, ts_map_extractor
    for d in [ASKAP_DATA_DIR, ASKAP_IMAGES_DIR, WISE_DATA_DIR, WISE_IMAGES_DIR, DECAM_DATA_DIR, DECAM_IMAGES_DIR, TS_MAPS_DIR]:
        os.makedirs(d, exist_ok=True)
    
    # Initialize processors with verbose flag
    if ASKAP_AVAILABLE:
        askap_processor = ASKAPImageProcessor(CASDA_USERNAME, CASDA_PASSWORD, ASKAP_DATA_DIR, ASKAP_IMAGES_DIR, verbose=VERBOSE)
    if WISE_AVAILABLE:
        wise_processor = WISEImageProcessor(WISE_DATA_DIR, WISE_IMAGES_DIR, verbose=VERBOSE)
    if DECAM_AVAILABLE:
        decam_processor = DECamImageProcessor(DATALAB_USERNAME, DATALAB_PASSWORD, DECAM_DATA_DIR, DECAM_IMAGES_DIR, verbose=VERBOSE)
    if TSMAP_AVAILABLE:
        ts_map_extractor = TSMapExtractor(TS_MAPS_DIR)

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

def load_processed_transients(verbose=True):
    if os.path.exists(NEW_TRANSIENTS_CSV):
        df = pd.read_csv(NEW_TRANSIENTS_CSV)
        if verbose:
            print(f"Loaded {len(df)} processed transients")
        return df
    return pd.DataFrame(columns=['source', 'observation', 'ra[deg]', 'dec[deg]', 
                                'field', 'time', 'test_statistic', 'status', 'processed_at'])

SAVE_COLS = ['source', 'observation', 'ra[deg]', 'dec[deg]', 'field', 'time', 'test_statistic', 'status', 'processed_at']

def save_new_transients(new_df, processed_df):
    """Save multiple transients (batch mode)."""
    new_df = new_df.copy()
    new_df['processed_at'] = pd.Timestamp.now(tz='UTC').isoformat()
    subset = new_df[[c for c in SAVE_COLS if c in new_df.columns]]
    # Ensure processed_df only has correct columns
    if len(processed_df) > 0:
        processed_df = processed_df[[c for c in SAVE_COLS if c in processed_df.columns]]
        combined = pd.concat([processed_df, subset], ignore_index=True)
    else:
        combined = subset
    combined.to_csv(NEW_TRANSIENTS_CSV, index=False)

def save_single_transient(row, processed_df):
    """Save one transient immediately after posting (prevents duplicates on interrupt)."""
    row_data = {
        'source': row['source'],
        'observation': row['observation'],
        'ra[deg]': row['ra[deg]'],
        'dec[deg]': row['dec[deg]'],
        'field': row['field'],
        'time': row['time'],
        'test_statistic': row['test_statistic'],
        'status': row['status'],
        'processed_at': pd.Timestamp.now(tz='UTC').isoformat()
    }
    new_row = pd.DataFrame([row_data])
    # Ensure processed_df only has correct columns
    if len(processed_df) > 0:
        processed_df = processed_df[[c for c in SAVE_COLS if c in processed_df.columns]]
        combined = pd.concat([processed_df, new_row], ignore_index=True)
    else:
        combined = new_row
    combined.to_csv(NEW_TRANSIENTS_CSV, index=False)

def process_transient_coordinates(row):
    if 'centroid_ra[deg]' in row.index and not pd.isna(row['centroid_ra[deg]']):
        ra, dec = float(row['centroid_ra[deg]']), float(row['centroid_dec[deg]'])
    else:
        ra, dec = float(row['ra[deg]']), float(row['dec[deg]'])
    return (ra + 360 if ra < 0 else ra), dec

def extract_ts_map_for_transient(row, ra, dec):
    """Extract TS map from g3 file for this transient."""
    if not TSMAP_AVAILABLE or not ts_map_extractor:
        return None
    
    # TS map g3 files only exist for ra5hdec-* fields
    field = row.get('field', '')
    if not field.startswith('ra5hdec'):
        return None
    
    return ts_map_extractor.extract_ts_map_from_row(row)

def generate_askap_image_for_transient(row, ra, dec, ts_map_path=None):
    if not ASKAP_AVAILABLE or not askap_processor:
        return None
    name = f"{row['source']}_{row['observation']}"
    return askap_processor.process_transient(name, ra, dec, ts_map_path)

def generate_wise_image_for_transient(row, ra, dec, ts_map_path=None):
    if not WISE_AVAILABLE or not wise_processor:
        return None
    name = f"{row['source']}_{row['observation']}"
    return wise_processor.process_transient_wise_image(name, ra, dec, ts_map_path)

def generate_decam_image_for_transient(row, ra, dec, ts_map_path=None):
    if not DECAM_AVAILABLE or not decam_processor:
        return None
    name = f"{row['source']}_{row['observation']}"
    return decam_processor.process_transient(name, ra, dec, ts_map_path)

def generate_reference_links(ra, dec):
    legacy_url = f"https://www.legacysurvey.org/viewer?ra={ra:.5f}&dec={dec:.5f}&layer=ls-dr10&zoom=14&mark={ra:.5f},{dec:.5f}"
    simbad_url = f"http://simbad.u-strasbg.fr/simbad/sim-coo?Coord={ra:.5f}+{dec:.5f}"
    return legacy_url, simbad_url

def format_transient_message(row, ra, dec, askap_image_path=None, wise_image_path=None, decam_image_path=None, ts_map_image_path=None):
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
    
    # TS Map status (SPT-3G)
    if ts_map_image_path and os.path.exists(ts_map_image_path):
        image_fields.append({
            "type": "mrkdwn",
            "text": "*SPT TS Map:* ✓ Available"
        })
    else:
        image_fields.append({
            "type": "mrkdwn",
            "text": "*SPT TS Map:* Not available"
        })
    
    # ASKAP image status
    if askap_image_path and os.path.exists(askap_image_path):
        image_fields.append({
            "type": "mrkdwn",
            "text": "*ASKAP Radio:* ✓"
        })
    elif ASKAP_AVAILABLE:
        image_fields.append({
            "type": "mrkdwn",
            "text": "*ASKAP Radio:* No data"
        })
    
    # WISE image status
    if wise_image_path and os.path.exists(wise_image_path):
        image_fields.append({
            "type": "mrkdwn",
            "text": "*WISE Infrared:* ✓"
        })
    elif WISE_AVAILABLE:
        image_fields.append({
            "type": "mrkdwn",
            "text": "*WISE Infrared:* Pending"
        })
    
    # DECam image status
    if decam_image_path and os.path.exists(decam_image_path):
        image_fields.append({
            "type": "mrkdwn",
            "text": "*DECam Optical:* ✓"
        })
    elif DECAM_AVAILABLE:
        image_fields.append({
            "type": "mrkdwn",
            "text": "*DECam Optical:* Pending"
        })
    
    if image_fields:
        blocks.append({
            "type": "section",
            "fields": image_fields
        })
    
    # Add reference links
    legacy_url, simbad_url = generate_reference_links(ra, dec)
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*View location:* <{legacy_url}|Legacy Survey> | <{simbad_url}|SIMBAD>"
        }
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

def post_transient_to_slack(row, ra, dec, askap_image_path=None, wise_image_path=None, decam_image_path=None, ts_map_image_path=None):
    """Post transient detection to Slack with optional images."""
    source_name = f"{row['source']}_{row['observation']}"
    blocks = format_transient_message(row, ra, dec, askap_image_path, wise_image_path, decam_image_path, ts_map_image_path)
    
    # Post the main message with detailed blocks first
    response = app.client.chat_postMessage(
        channel=CHANNEL_ID,
        text=f"New transient detected: {source_name}",
        blocks=blocks,
        unfurl_links=False
    )
    
    message_ts = response.get("ts") if response.get("ok") else None
    
    # Add voting reactions to the main message
    if VOTING_AVAILABLE and reaction_handler and message_ts:
        reaction_handler.add_voting_reactions(CHANNEL_ID, message_ts)
    
    # Upload images as a separate message (not threaded)
    images_to_upload = []
    if ts_map_image_path and os.path.exists(ts_map_image_path):
        images_to_upload.append(ts_map_image_path)
    if askap_image_path and os.path.exists(askap_image_path):
        images_to_upload.append(askap_image_path)
    if wise_image_path and os.path.exists(wise_image_path):
        images_to_upload.append(wise_image_path)
    if decam_image_path and os.path.exists(decam_image_path):
        images_to_upload.append(decam_image_path)
    
    if images_to_upload:
        app.client.files_upload_v2(
            channel=CHANNEL_ID,
            file_uploads=[
                {"file": img_path, "title": os.path.basename(img_path)}
                for img_path in images_to_upload
            ],
            initial_comment=f"Images for {source_name}"
        )
    
    print(f"  ✓ Posted to Slack ({len(images_to_upload)} images)")
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
        
        # Initialize DECam processor
        if DECAM_AVAILABLE and decam_processor:
            print("Authenticating with Data Lab...")
            if not decam_processor.authenticate():
                print("Data Lab authentication failed - proceeding without images")
        
        # Process all new transients
        transients_to_post = final_new_transients
        total_count = len(transients_to_post)
        
        for i, (index, row) in enumerate(transients_to_post.iterrows()):
            remaining = total_count - (i + 1)
            source_name = f"{row['source']}_{row['observation']}"
            ra, dec = process_transient_coordinates(row)
            
            # Extract TS map FITS (if available)
            ts_map_path = None
            ts_map_image_path = None
            if TSMAP_AVAILABLE and ts_map_extractor:
                ts_map_path = extract_ts_map_for_transient(row, ra, dec)
                if ts_map_path:
                    ts_map_image_path = generate_ts_map_cutout(ts_map_path, source_name, ra, dec, TS_MAPS_DIR)
            
            # Condensed status line with TS map note
            ts_note = "TS:✓" if ts_map_path else "TS:✗"
            print(f"[{i+1}/{total_count}] {source_name} @ ({ra:.4f}, {dec:.4f}) {ts_note}")
            
            # Generate images (condensed - errors only)
            askap_image_path = generate_askap_image_for_transient(row, ra, dec, ts_map_path) if ASKAP_AVAILABLE and askap_processor else None
            wise_image_path = generate_wise_image_for_transient(row, ra, dec, ts_map_path) if WISE_AVAILABLE and wise_processor else None
            decam_image_path = generate_decam_image_for_transient(row, ra, dec, ts_map_path) if DECAM_AVAILABLE and decam_processor else None
            
            # Post to Slack (includes TS map image if available)
            post_transient_to_slack(row, ra, dec, askap_image_path, wise_image_path, decam_image_path, ts_map_image_path)
            
            # Save THIS transient immediately (prevents duplicates if interrupted)
            save_single_transient(row, processed_transients)
            processed_transients = load_processed_transients(verbose=False)  # Reload to include new entry
            
            # Brief wait between transients
            if remaining > 0:
                time.sleep(15)
        
        # Handle first run
        if len(processed_transients) == 0:
            historical_new = data_transients[data_transients['status'] == 'new']
            if len(historical_new) > 0:
                print(f"Marking {len(historical_new)} historical transients as processed")
                save_new_transients(historical_new, pd.DataFrame())
        
    else:
        print("No new transients found - exiting")
        
        # First run handling
        if len(processed_transients) == 0:
            historical_new = data_transients[data_transients['status'] == 'new']
            if len(historical_new) > 0:
                print(f"First run: Marking {len(historical_new)} historical transients as processed")
                save_new_transients(historical_new, pd.DataFrame())
        
        # Exit early since there's nothing to process
        sys.exit(0)
    
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

def start_socket_mode():
    """Start Slack app in Socket Mode for receiving events (reactions)."""
    if not SLACK_APP_TOKEN:
        print("Warning: SLACK_APP_TOKEN not set - voting/reactions won't work")
        return
    print("Starting Socket Mode for Slack events...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='SPT-3G Transient Monitor')
    parser.add_argument('--daemon', '-d', action='store_true', help='Run as daemon with scheduler and voting')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output from image processors')
    parser.add_argument('--listen', '-l', action='store_true', help='Listen for votes only (no transient check)')
    args = parser.parse_args()
    
    # Set verbose flag (VERBOSE is declared at module level)
    VERBOSE = args.verbose
    
    print("Transient Monitor with ASKAP Integration")
    print(f"Data source: {os.path.basename(TRANSIENTS_TXT)}")
    print(f"Tracking file: {os.path.basename(NEW_TRANSIENTS_CSV)}")
    if ASKAP_AVAILABLE:
        print("ASKAP images: ENABLED")
    if SLACK_APP_TOKEN:
        print("Socket Mode: ENABLED (voting available)")
    else:
        print("Socket Mode: DISABLED (set SLACK_APP_TOKEN for voting)")
    
    setup_directories()
    
    # Listen-only mode: just receive votes, don't process transients
    if args.listen:
        print("\nListening for votes only (Ctrl+C to stop)...")
        start_socket_mode()
    else:
        print("\nRunning check...")
        check_for_new_transients()
        
        # Daemon mode: continuous monitoring + voting
        if args.daemon:
            schedule.every().day.at("12:00").do(check_for_new_transients)
            # Start socket mode in background thread
            if SLACK_APP_TOKEN:
                socket_thread = threading.Thread(target=start_socket_mode)
                socket_thread.daemon = True
                socket_thread.start()
            run_scheduler()
        else:
            print("Done. Use --daemon to run continuously, or --listen to receive votes.")