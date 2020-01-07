import os
import time
import re
import json
from random import randint
from slack import RTMClient # v2 slackclient
import requests

# Return code constants
ERROR_CODE = -1
VALID_CODE = 0

# Read data from secrets directory & instantiate Slack Client (RTM)
secrets_data = {}
with open("secrets/secrets.json", "r") as f:
    secrets_data = json.load(f)
slack_client = RTMClient(token=secrets_data["BOT_USER_ACCESS_TOKEN"])

# bots's user ID in Slack: value is assigned after the bot starts up
bot_id = None
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

@RTMClient.run_on(event="message")
def handle_event(**payload):
    """
    Method that is triggered whenever a message is recieved in a shared channel
    with the bot. Parses the message and handles accordingly.
    """
    data = payload["data"]
    web_client = payload["web_client"]
    bot_id = web_client.api_call("auth.test")["user_id"]

    command, channel = parse_bot_commands(data, bot_id)
    if command:
        handle_command(web_client, command, channel)

def parse_bot_commands(event_data, bot_id):
    """
    Extracts message if bot is mentioned, otherwise, returns None
    """
    user_id, message = parse_direct_mention(event_data["text"])
    if user_id == bot_id:
        return message, event_data["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
    Parses the message text if able, otherwise, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(web_client, command, channel):
    """
    Method called when valid command/mention is detected and handles
    accordingly.
    """
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
    web_client.chat_postMessage(
        channel=channel,
        text=response or default_response
    )

def get_help_menu():
    """ Returns a help menu to assist user in bot usage """
    return "```Usage: @rebrandlybot [url|help]\n\n" + \
    "Description: Provide the bot with a URL and it will generate a\n" + \
    "shortened, rebranded, link hitting the Rebrandly API.\n" + \
    "Example:\n" + \
    "\t> @rebrandlybot https://www.samplesite.com\n```"

def create_short_url(provided_url):
    """
    Generates a POST to the Rebrandly API with a provided_url (longUrl)
    that needs to be shortened (rebranded). Returns the status code and
    resultant URL (if one was generated)
    """
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
                try:
                    error_response += "> " + str(error["code"]) + ": " + str(error["verbose"]) + "\n"
                except KeyError: # No verbose descriptor
                    error_response += "> " + str(error["code"]) + "\n"
            return (ERROR_CODE, error_response)
    return (ERROR_CODE, None)

if __name__ == "__main__":
    print("Starting Slack Bot...")
    slack_client.start()
