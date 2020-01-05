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

# Return code constants
ERROR_CODE = -1
VALID_CODE = 0

# Read data from secrets directory
data = {}
with open("secrets/secrets.json", "r") as f:
    data = json.load(f)

# instantiate Slack client
slack_client = SlackClient(data["BOT_USER_ACCESS_TOKEN"])

# bots's user ID in Slack: value is assigned after the bot starts up
bot_id = None
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
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
    invalid_url_response = "Hmmm, the url you provided was invalid, please try again"
    response = None

    if command.startswith("help"):
        response = get_help_menu()
    else:
        status_code, rebranded_link = create_short_url(command)
        if status_code == VALID_CODE:
            response = "Destination: \n" + "> " + str(command) + "\n" + \
                    "New URL:     \n" + "> " + str(rebranded_link)
        else:
            if rebranded_link:
                response = "Request returned error with the following message: \n" + rebranded_link
            else:
                response = invalid_url_response

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )

def get_help_menu():
    return "```Usage: @rebrandlybot [url|help]\n\n" + \
    "Description: Provide the bot with a URL and it will generate a\n" + \
    "shortened, rebranded, link hitting the Rebrandly API.\n" + \
    "Example:\n" + \
    "\t> @rebrandlybot https://www.samplesite.com\n```"

def create_short_url(provided_url):
    provided_url = provided_url[1:-1] # remove brackets: '<https://...>'

    linkRequest = {
        "destination": str(provided_url),
        "domain": { "fullName": "rebrand.ly" }
    }

    requestHeaders = {
        "Content-type": "application/json",
        "apikey": data["REBRANDLY_API_KEY"]
    }

    r = requests.post(
        "https://api.rebrandly.com/v1/links",
        data = json.dumps(linkRequest),
        headers=requestHeaders
    )

    # Return response if one exists
    # pylint: disable=maybe-no-member
    if (r.status_code == requests.codes.ok):
        link = r.json()
        print("Long URL was %s\nshort URL is https://%s\n" % (link["destination"], link["shortUrl"]))
        return (VALID_CODE, "https://" + link["shortUrl"])
    else:
        r_data = r.json()
        if len(r_data["errors"]) != 0: # errors exist
            error_response = ""
            for error in r_data["errors"]:
                error_response += "> " + str(error["code"]) + ": " + str(error["verbose"]) + "\n"
            return (ERROR_CODE, error_response)
    return (ERROR_CODE, None)

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Slack Bot is now running!")
        bot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")