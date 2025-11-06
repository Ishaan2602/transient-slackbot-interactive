import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from slack_bolt import App
from slack_sdk.errors import SlackApiError
import schedule
import time
import threading

# Configuration
SLACK_BOT_TOKEN = 'xoxb-451463007363-9618908142950-FkmLQF1HKzTDGAeebVvzU7Y7'
SLACK_SIGNING_SECRET = 'de2481e9523c65ac16ae1c5bad90a28d'
CHANNEL_ID = "C09KLUNLU68"

# File paths
TRANSIENTS_TXT = r'c:\Users\eluru\UIUC\obscos\transients.txt'
NEW_TRANSIENTS_CSV = r'c:\Users\eluru\UIUC\obscos\new_transients.csv'
LAST_CHECK_FILE = r'c:\Users\eluru\UIUC\obscos\last_check.txt'

# Initialize Slack app
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

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
    """Load the list of already processed transients."""
    try:
        if os.path.exists(NEW_TRANSIENTS_CSV):
            processed = pd.read_csv(NEW_TRANSIENTS_CSV)
            print(f"Loaded {len(processed)} previously processed transients")
            return processed
    except Exception as e:
        print(f"Error loading processed transients: {e}")
    
    return pd.DataFrame(columns=['source', 'observation', 'ra[deg]', 'dec[deg]', 
                                'field', 'time', 'test_statistic', 'status', 'processed_at'])

def save_new_transients(new_transients_df, processed_df):
    """Append new transients to the processed transients CSV."""
    try:
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
        print(f"Saved {len(new_transients_df)} new transients to {NEW_TRANSIENTS_CSV}")
        
    except Exception as e:
        print(f"Error saving new transients: {e}")

def process_transient_coordinates(row):
    """Process coordinates, using centroid if available, otherwise ra/dec."""
    if not np.isnan(row['centroid_ra[deg]']):
        ra = float(row['centroid_ra[deg]'])
        dec = float(row['centroid_dec[deg]'])
    else:
        ra = float(row['ra[deg]'])
        dec = float(row['dec[deg]'])
    
    if ra < 0:
        ra = ra + 360.0
    
    return ra, dec

def format_transient_message(row, ra, dec):
    """Format a transient detection into a Slack message."""
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
    
    detection_time = pd.to_datetime(row['time']).strftime('%Y-%m-%d %H:%M:%S UTC')
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"(TEST CODE) New Transient Detected: {source_name}"
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
    
    if not pd.isna(row['fwhm[days]']):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Duration (FWHM):* {row['fwhm[days]']:.2f} days"
            }
        })
    
    blocks.append({"type": "divider"})
    
    return blocks

def check_for_new_transients():
    """Check for new transients and post to Slack."""
    try:
        print(f"Loading transients data from {TRANSIENTS_TXT}")
        data_transients = pd.read_csv(TRANSIENTS_TXT, sep='\t')
        data_transients['time'] = pd.to_datetime(data_transients['time'])
        
        processed_transients = load_processed_transients()
        
        if len(processed_transients) > 0:
            data_transients['unique_id'] = data_transients['source'].astype(str) + '_' + data_transients['observation'].astype(str)
            processed_transients['unique_id'] = processed_transients['source'].astype(str) + '_' + processed_transients['observation'].astype(str)
            
            unprocessed_mask = ~data_transients['unique_id'].isin(processed_transients['unique_id'])
            new_transients = data_transients[unprocessed_mask]
        else:
            new_transients = data_transients.copy()
        
        status_filter = (data_transients['status'] == 'new') | (data_transients['status'].isna())
        
        if len(processed_transients) > 0:
            final_new_transients = data_transients[unprocessed_mask & status_filter]
        else:
            print("First run detected - skipping historical 'new' transients, focusing on recent additions")
            recent_threshold = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30)
            recent_nan_filter = (data_transients['status'].isna()) & (data_transients['time'] > recent_threshold)
            final_new_transients = data_transients[recent_nan_filter]
        
        print(f"Total transients in file: {len(data_transients)}")
        print(f"Previously processed: {len(processed_transients)}")
        print(f"Found {len(final_new_transients)} NEW transients to process")
        
        if len(final_new_transients) > 0:
            transients_to_post = final_new_transients.head(5)
            
            for index, row in transients_to_post.iterrows():
                try:
                    ra, dec = process_transient_coordinates(row)
                    blocks = format_transient_message(row, ra, dec)
                    
                    result = app.client.chat_postMessage(
                        channel=CHANNEL_ID,
                        text=f"New transient detected: {row['source']}_{row['observation']}",
                        blocks=blocks
                    )
                    
                    print(f"Posted transient {row['source']}_{row['observation']} to Slack")
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error posting transient {row['source']}: {e}")
            
            save_new_transients(transients_to_post, processed_transients)
            
            if len(processed_transients) == 0:
                historical_new = data_transients[data_transients['status'] == 'new']
                if len(historical_new) > 0:
                    print(f"Marking {len(historical_new)} historical 'new' transients as processed to avoid future notifications")
                    save_new_transients(historical_new, pd.DataFrame())
            
        else:
            print("No new transients found.")
            
            if len(processed_transients) == 0:
                historical_new = data_transients[data_transients['status'] == 'new']
                if len(historical_new) > 0:
                    print(f"First run: Marking {len(historical_new)} historical 'new' transients as processed")
                    save_new_transients(historical_new, pd.DataFrame())
        
        current_time = pd.Timestamp.now(tz='UTC')
        save_last_check_time(current_time)
        
    except Exception as e:
        print(f"Error checking for new transients: {e}")
        try:
            app.client.chat_postMessage(
                channel=CHANNEL_ID,
                text=f"Error checking for new transients: {str(e)}"
            )
        except:
            pass

def run_scheduler():
    """Run the scheduler to check for new transients."""
    print("Transient monitor scheduler is running...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def start_bolt_app():
    """Start the Bolt app."""
    print("Starting Bolt app...")
    app.start(port=int(os.environ.get("PORT", 3000)))

if __name__ == "__main__":
    schedule.every.day.at("12:00").minutes.do(check_for_new_transients)
    
    print("Running initial check for new transients...")
    check_for_new_transients()
    
    bolt_thread = threading.Thread(target=start_bolt_app)
    bolt_thread.daemon = True
    bolt_thread.start()
    
    run_scheduler()