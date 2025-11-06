"""
Transient Monitor with ASKAP Image Integration

Monitors transients.txt for new detections and posts to Slack with ASKAP images.
Data flow: transients.txt -> new_transients.csv -> Slack notifications
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from slack_bolt import App
from slack_sdk.errors import SlackApiError
import schedule
import time
import threading

# ASKAP Integration
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'askap_integration'))

try:
    from askap_image_processor import ASKAPImageProcessor # type: ignore
    ASKAP_AVAILABLE = True
except ImportError:
    ASKAP_AVAILABLE = False
    print("Warning: ASKAP integration not available")

# Personal DM 
#SLACK_BOT_TOKEN = 'xoxb-451463007363-961890814290-FkmLQF1HKzTDGAeebVvzU7Y7' # invalid!
#CHANNEL_ID = "D09H0DHR56C"  # Personal channel

# Transientbot Channel
SLACK_BOT_TOKEN = 'xoxb-451463007363-9618908142950-FkmLQF1HKzTDGAeebVvzU7Y7'
CHANNEL_ID = "C09KLUNLU68"  # transientbot channel

# tbd
#SLACK_BOT_TOKEN = 'xoxb---------------'
#CHANNEL_ID = "--------"  # future channel

SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET', 'de2481e9523c65ac16ae1c5bad90a28d')

# ASKAP Configuration
# NOTE: using CASDA_USERNAME_'PERSONAL' for now! Change later
CASDA_USERNAME = os.getenv('CASDA_USERNAME_PERSONAL', 'ishaang6@illinois.edu')
CASDA_PASSWORD = os.getenv('CASDA_PASSWORD_PERSONAL', 'obscos_transient')

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSIENTS_TXT = os.path.join(BASE_DIR, 'transients.txt')
NEW_TRANSIENTS_CSV = os.path.join(BASE_DIR, 'new_transients.csv')
LAST_CHECK_FILE = os.path.join(BASE_DIR, 'last_check.txt')

# ASKAP data directories
ASKAP_DATA_DIR = os.path.join(BASE_DIR, 'askap_data')
ASKAP_IMAGES_DIR = os.path.join(BASE_DIR, 'askap_images')

# Initialize Slack app
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

# Initialize ASKAP processor (if available)
askap_processor = None
if ASKAP_AVAILABLE:
    askap_processor = ASKAPImageProcessor(
        username=CASDA_USERNAME,
        password=CASDA_PASSWORD,
        data_dir=ASKAP_DATA_DIR,
        images_dir=ASKAP_IMAGES_DIR
    )

def setup_directories():
    """Create necessary directories."""
    os.makedirs(ASKAP_DATA_DIR, exist_ok=True)
    os.makedirs(ASKAP_IMAGES_DIR, exist_ok=True)

def load_last_check_time():
    """Load the last check time from file, or return a default time."""
    try:
        if os.path.exists(LAST_CHECK_FILE):
            with open(LAST_CHECK_FILE, 'r') as f:
                dt = datetime.fromisoformat(f.read().strip())
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pd.Timestamp.now(tz='UTC').tz)
                return dt
    except:
        pass
    return pd.Timestamp.now(tz='UTC') - timedelta(hours=24)

def save_last_check_time(check_time):
    """Save the current check time to file."""
    with open(LAST_CHECK_FILE, 'w') as f:
        if isinstance(check_time, datetime) and check_time.tzinfo is None:
            check_time = pd.Timestamp(check_time, tz='UTC')
        f.write(check_time.isoformat())

def load_processed_transients():
    """Load previously processed transients from CSV."""
    if os.path.exists(NEW_TRANSIENTS_CSV):
        processed = pd.read_csv(NEW_TRANSIENTS_CSV)
        print(f"Loaded {len(processed)} previously processed transients")
        return processed
    
    return pd.DataFrame(columns=['source', 'observation', 'ra[deg]', 'dec[deg]', 
                                'field', 'time', 'test_statistic', 'status', 'processed_at'])

def save_new_transients(new_transients_df, processed_df):
    """Append new transients to the processed transients CSV."""
    new_transients_df = new_transients_df.copy()
    new_transients_df['processed_at'] = pd.Timestamp.now(tz='UTC').isoformat()
    
    columns_to_save = ['source', 'observation', 'ra[deg]', 'dec[deg]', 
                      'field', 'time', 'test_statistic', 'status', 'processed_at']
    new_transients_subset = new_transients_df[columns_to_save]
    
    if len(processed_df) > 0:
        combined_df = pd.concat([processed_df, new_transients_subset], ignore_index=True)
    else:
        combined_df = new_transients_subset
    
    combined_df.to_csv(NEW_TRANSIENTS_CSV, index=False)
    print(f"Saved {len(new_transients_df)} new transients to CSV")

def process_transient_coordinates(row):
    """Process coordinates, using centroid if available, otherwise ra/dec."""
    # Use centroid coordinates if available and valid
    if ('centroid_ra[deg]' in row.index and 
        not pd.isna(row['centroid_ra[deg]']) and 
        not np.isnan(float(row['centroid_ra[deg]']))):
        ra = float(row['centroid_ra[deg]'])
        dec = float(row['centroid_dec[deg]'])
    else:
        ra = float(row['ra[deg]'])
        dec = float(row['dec[deg]'])
    
    # Ensure RA is in [0, 360) range
    if ra < 0:
        ra = ra + 360.0
    
    return ra, dec

def generate_askap_image_for_transient(row, ra, dec):
    """Generate ASKAP image for a transient."""
    if not ASKAP_AVAILABLE or askap_processor is None:
        return None
    
    source_name = f"{row['source']}_{row['observation']}"
    
    print(f"Generating ASKAP image for {source_name}...")
    image_path = askap_processor.process_transient(source_name, ra, dec)
    
    if image_path:
        print(f"ASKAP image generated: {os.path.basename(image_path)}")
    else:
        print(f"Failed to generate ASKAP image for {source_name}")
        
    return image_path

def format_transient_message(row, ra, dec, askap_image_path=None):
    """Format a transient detection into a Slack message with rich blocks."""
    source_name = f"{row['source']}_{row['observation']}"
    
    # Convert RA to hours:minutes:seconds
    ra_hours = ra / 15.0
    ra_h = int(ra_hours)
    ra_m = int((ra_hours - ra_h) * 60)
    ra_s = ((ra_hours - ra_h) * 60 - ra_m) * 60
    
    # Convert Dec to degrees:arcminutes:arcseconds
    dec_sign = "+" if dec >= 0 else "-"
    dec_abs = abs(dec)
    dec_d = int(dec_abs)
    dec_m = int((dec_abs - dec_d) * 60)
    dec_s = ((dec_abs - dec_d) * 60 - dec_m) * 60
    
    detection_time = pd.to_datetime(row['time']).strftime('%Y-%m-%d %H:%M:%S UTC')
    
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
                    "text": f"*Peak Flux:*\n{row['peak_flux[mJy]']:.2f} mJy"
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
    
    # Add ASKAP image status
    if askap_image_path and os.path.exists(askap_image_path):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*ASKAP Radio Image:* Generated"
            }
        })
    elif ASKAP_AVAILABLE:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📸 *ASKAP Radio Image:* No data available for this location"
            }
        })
    
    blocks.append({"type": "divider"})
    
    return blocks

def post_transient_to_slack(row, ra, dec, askap_image_path=None):
    """Post transient detection to Slack with optional ASKAP image."""
    source_name = f"{row['source']}_{row['observation']}"
    blocks = format_transient_message(row, ra, dec, askap_image_path)
    
    # Upload image if available
    if askap_image_path and os.path.exists(askap_image_path):
        app.client.files_upload_v2(
            channel=CHANNEL_ID,
            file=askap_image_path,
            title=f"ASKAP Radio Image - {source_name}",
            initial_comment=""
        )
        print(f"Uploaded ASKAP image for {source_name}")
    
    # Post the message
    app.client.chat_postMessage(
        channel=CHANNEL_ID,
        text=f"New transient detected: {source_name}",
        blocks=blocks
    )
    
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
            
            # Post to Slack
            post_transient_to_slack(row, ra, dec, askap_image_path)
            
            if i < len(transients_to_post) - 1:
                time.sleep(2)
        
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