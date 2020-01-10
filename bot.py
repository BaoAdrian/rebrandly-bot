import os
import re
import time
import json
import logging
import requests
from random import randint
from slack import RTMClient # v2 slackclient

# Return code constants
ERROR_CODE = -1
VALID_CODE = 0

# bots's user ID in Slack: value is assigned after the bot starts up
rebrandly_bot = None
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

class RebrandlyBot:
    def __init__(self, secret_data):
        """ RebrandlyBot Constructor """
        self.secret_data = secret_data
        self.slack_client = RTMClient(token=secrets_data["BOT_USER_ACCESS_TOKEN"])

        self.event_data = {}
        self.web_client = None
        self.bot_id = None

        self.command = None
        self.channel = None

    def get_command(self):
        """
        Public Accessor for the command attribute
        @return command String command attribute
        """
        return self.command

    def start(self):
        """
        Starts the SlackBot using RTMClient.start()
        """
        print("Starting Slack Bot...")
        self.slack_client.start()

    def process_payload(self, payload):
        """
        Processes the event payload to parse the data, WebClient, and Bot ID
        needed to process the command accordingly.

        @param payload Dictionary of event data to be processed
        """
        self.event_data = payload["data"]
        self.web_client = payload["web_client"]
        self.bot_id = self.web_client.api_call("auth.test")["user_id"]

    def parse_bot_command(self):
        """
        Extracts associated command and channel from the current message. Sets
        the corresponding attributes if mentioned user matches the Bot ID. 
        Otherwise, sets the attributes to None
        """
        user_id, message = self.parse_direct_mention()
        if user_id == self.bot_id:
            self.command = message
            self.channel = self.event_data["channel"]
        else:
            self.command = None
            self.channel = None

    def parse_direct_mention(self):
        """
        Parses the message text if able, otherwise, returns None
        """
        matches = re.search(MENTION_REGEX, self.event_data["text"])
        # the first group contains the username, the second group contains the remaining message
        return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

    def handle_command(self):
        """
        Handles the current command accordingly & posts response
        using the WebClient.
        """
        # Default response is help text for the user
        default_response = "Hmmm, I didn't quite catch that."
        invalid_url_response = "Hmmm, the url you provided was invalid, please try again"
        response = None

        if self.command.startswith("help"):
            response = self.get_help_menu()
        else:
            status_code, rebranded_link = self.rebrand_link()
            if status_code == VALID_CODE:
                response = "Destination: \n" + "> " + str(self.command) + "\n" + \
                           "New URL:     \n" + "> " + str(rebranded_link)
            else:
                if rebranded_link:
                    response = "Request returned error with the following message: \n" + rebranded_link
                else:
                    response = invalid_url_response

        # Sends the response back to the channel
        self.web_client.chat_postMessage(
            channel=self.channel,
            text=response or default_response
        )

    def get_help_menu(self):
        """ Returns a help menu to assist user in bot usage """
        return "```Usage: @rebrandlybot [url|help]\n\n" + \
        "Description: Provide the bot with a URL and it will generate a\n" + \
        "shortened, rebranded, link hitting the Rebrandly API.\n" + \
        "Example:\n" + \
        "\t> @rebrandlybot https://www.samplesite.com\n```"

    def rebrand_link(self):
        """
        Generates a POST to the Rebrandly API with a destination URL (longUrl)
        that needs to be shortened (rebranded). Returns the status code and
        resultant URL (if one was generated)
        """
        destination = self.command[1:-1] # remove brackets from longUrl: '<https://...>'

        linkRequest = {
            "destination": str(destination),
            "domain": { "fullName": "rebrand.ly" }
        } 

        requestHeaders = {
            "Content-type": "application/json",
            "apikey": self.secret_data["REBRANDLY_API_KEY"]
        }

        r = requests.post(
            "https://api.rebrandly.com/v1/links",
            data = json.dumps(linkRequest),
            headers=requestHeaders
        )

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

@RTMClient.run_on(event="message")
def handle_event(**payload):
    """
    This method is triggered whenever a MESSAGE event occurs. Proceeds
    to process event data and handle command if RebrandlyBot is mentioned
    to generate a Rebranded URL.

    @param payload Dictionary of event data to be processed
    """
    rebrandly_bot.process_payload(payload)
    rebrandly_bot.parse_bot_command()
    if rebrandly_bot.get_command():
        rebrandly_bot.handle_command()


if __name__ == "__main__":
    # Read data from secrets directory & instantiate Slack Client (RTM)
    secrets_data = {}
    with open("secrets/secrets.json", "r") as f:
        secrets_data = json.load(f)
    
    rebrandly_bot = RebrandlyBot(secrets_data)
    rebrandly_bot.start()
