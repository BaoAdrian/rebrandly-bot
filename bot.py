import os
import time
import re
import json
import psycopg2
from random import randint
from slackclient import SlackClient

# Rebrandly dependencies
import requests
import json

# Read data from secrets directory
data = {}
with open("secrets/secrets.json", "r") as f:
    data = json.load(f)

# instantiate Slack client
slack_client = SlackClient(data["BOT_USER_ACCESS_TOKEN"])

# bots's user ID in Slack: value is assigned after the bot starts up
bot_id = None
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "`add [assignment] [due date]`"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == bot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    # Default response is help text for the user
    default_response = "Hmmm, I didn't quite catch that."
    response = None

    print("Command: {}".format(command))
    response = "Destination: " + str(command) + "\n" + \
               "New URL:     " + str(create_short_url(command))

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )


def create_short_url(provided_url):
    provided_url = provided_url[1:-1] # remove brackets

    linkRequest = {
    "destination": str(provided_url)
    , "domain": { "fullName": "rebrand.ly" }
    }

    requestHeaders = {
    "Content-type": "application/json",
    "apikey": data["REBRANDLY_API_KEY"]
    }

    r = requests.post("https://api.rebrandly.com/v1/links", 
        data = json.dumps(linkRequest),
        headers=requestHeaders)

    print("\n" + str(r.json()) + "\n")

    # pylint: disable=maybe-no-member
    if (r.status_code == requests.codes.ok):
        link = r.json()
        print("Long URL was %s, short URL is https://%s" % (link["destination"], link["shortUrl"]))
        return "https://" + link["shortUrl"]

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Assignment Bot is now running!")
        bot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")