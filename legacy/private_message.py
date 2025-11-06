import requests
import json
import os


slack_webhook_url = "https://hooks.slack.com/services/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"

def send_slack_message(message_text):
    """Sends a message to a Slack channel using an incoming webhook."""
    
    if not slack_webhook_url:
        print("Error: Slack Webhook URL not found.")
        return

    # The payload is a dictionary that gets converted to JSON
    slack_data = {'text': message_text}
    
    # Make the HTTP POST request to the webhook URL
    response = requests.post(
        slack_webhook_url,
        data=json.dumps(slack_data),
        headers={'Content-Type': 'application/json'}
    )
    
    # Check if the request was successful
    if response.status_code != 200:
        raise ValueError(
            f"Request to Slack returned an error {response.status_code}, "
            f"the response is:\n{response.text}"
        )
    print("Message sent successfully!")

# Call the function to send a message
if __name__ == "__main__":
    send_slack_message("Testing webhook message (legacy implementation).")