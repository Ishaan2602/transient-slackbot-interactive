import os
import schedule
import time
from slack_bolt import App
from slack_sdk.errors import SlackApiError
import threading
from datetime import datetime

# --- Configuration ---
# In terminal, run:
# export SLACK_BOT_TOKEN='your-xoxb-token'
# export SLACK_SIGNING_SECRET='your-signing-secret'

#SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN_1")
#SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

SLACK_BOT_TOKEN = 'xoxb-451463007363-9618908142950-FkmLQF1HKzTDGAeebVvzU7Y7'
SLACK_SIGNING_SECRET = 'de2481e9523c65ac16ae1c5bad90a28d'

# Important!!
#CHANNEL_ID = "U09H0DHFQ56" # My profile ID
#CHANNEL_ID = "D09G52NBKHT" # Kedar DM channel
CHANNEL_ID = "C09KLUNLU68"

# Initialize your Bolt app
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

# --- Message Sending Function ---
def send_scheduled_message():
    """
    This function is called by the scheduler to send the message.
    """
    try:
        # Get the current time to include in the message
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # This is a simple Block Kit message.
        # You can build more complex messages using the Block Kit Builder: https://api.slack.com/tools/block-kit-builder
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Status Check",
                    #"emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Scheduled message sent at *{now}*"
                }
            },
            {
                "type": "divider"
            }
        ]

        # Call the chat.postMessage method using the WebClient
        result = app.client.chat_postMessage(
            channel=CHANNEL_ID,
            text="Fallback notification text-- scheduled message!",  # Fallback text for notifications
            blocks=blocks
        )
        print(f"Successfully sent message to {CHANNEL_ID} at {now}")

    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# --- Scheduling Logic ---
# Use the 'schedule' library to define your jobs.
# You can customize these to fit your needs.

# --- UNCOMMENT THE SCHEDULE YOU WANT TO USE ---

# For testing: send a message every 30 seconds
schedule.every(10).seconds.do(send_scheduled_message)
#schedule.every(1).hour.do(send_scheduled_message)

# Send a message every day at 12:00 PM
# schedule.every().day.at("12:00").do(send_scheduled_message)


# --- Main Application Logic ---
def run_scheduler():
    """
    Continuously runs the scheduler to check for pending jobs.
    """
    print("Scheduler is running...")
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_bolt_app():
    """
    Starts the Bolt app in a way that doesn't block the main thread.
    """
    # Note: Although we don't have listeners, starting the app is good practice
    print("Starting Bolt app...")
    app.start(port=int(os.environ.get("PORT", 3000)))

# This ensures the code only runs when this file is executed directly. Otherwise, it would run on import!
if __name__ == "__main__": 
    # Run the Bolt app in a separate thread so it doesn't block the scheduler.
    # The scheduler needs to run in the main thread.
    bolt_thread = threading.Thread(target=start_bolt_app)
    bolt_thread.daemon = True  # Daemon threads exit when the main program exits
    bolt_thread.start()
    
    # Start the scheduler
    run_scheduler()
