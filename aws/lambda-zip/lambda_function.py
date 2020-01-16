import json
import time
import logging
import requests
import slack

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Return code constants
ERROR_CODE = -1
VALID_CODE = 0

BOT_USER_OAUTH_TOKEN = "[INSERT BOT USER OAUTH TOKEN]"
REBRANDLY_API_KEY = "[INSERT REBRANDLY API KEY]"

def lambda_handler(event, context):
    logger.info("Triggered AWS Lambda: rebrandly-event")

    # Extract vars from body
    body = json.loads(event["body"])
    channel = body["event"]["channel"]
    text = body["event"]["text"].split()
    response_text = ' '.join(text[1:])
    
    logger.info("Event: {}".format(event))
    logger.info("Body: {}".format(body))
    logger.info("ChanneL: {}".format(channel))
    logger.info("Text: {}".format(text))
    logger.info("Response Text: {}".format(response_text))

    response = handle_command(response_text)

    web_client = slack.WebClient(token=BOT_USER_OAUTH_TOKEN)
    web_client.chat_postMessage(
        channel=channel,
        text=response
    )

    return {
        'statusCode': 200,
        'body': 'Process for rebrandly-event has been completed!'
    }

def handle_command(text):
    """
    Handles the current command accordingly & posts response
    using the WebClient.
    """
    # Default response is help text for the user
    default_response = "Hmmm, I didn't quite catch that."
    invalid_url_response = "Hmmm, the url you provided was invalid, please try again"
    response = None

    if text.startswith("help"):
        response = get_help_menu()
    elif text.startswith("list"):
        response = list_links()
    else:
        status_code, rebranded_link = rebrand_link(text)
        if status_code == VALID_CODE:
            response = "Destination: \n" + "> " + str(text) + "\n" + \
                        "New URL:     \n" + "> " + str(rebranded_link)
        else:
            if rebranded_link:
                response = "Request returned error with the following message: \n" + rebranded_link
            else:
                response = invalid_url_response

    return response or default_response

def get_help_menu():
    """ Returns a help menu to assist user in bot usage """
    return "```Usage: @rebrandlybot [url|help]\n\n" + \
    "Description: Provide the bot with a URL and it will generate a\n" + \
    "shortened, rebranded, link hitting the Rebrandly API.\n" + \
    "Example:\n" + \
    "\t> @rebrandlybot https://www.samplesite.com\n```"

def list_links(limit="5"):
    """
    Generates a GET request to the Rebrandly API @ https://api.rebrandly.com/v1/links
    Gets information on the generated links and data returned will be used to display
    latest, existing links to user.
    """
    params = {
        "apikey": REBRANDLY_API_KEY,
        "limit": "5"
    }

    links = requests.get("https://api.rebrandly.com/v1/links", params=params)
    logger.info("GET Response: {}".format(links.text))
    links_json = json.loads(links.text)
    logger.info("GET Response total: {}".format(len(links_json)))

    res_links = "```"
    i = 1
    for link in links_json:
        # Extract items
        destination = link["destination"]
        short_url = link["shortUrl"]
        domain = link["domainName"]
        slashtag = link["slashtag"]
        res_links += "[{}] Destination: {}\n".format(i, destination) + \
        "    Short URL:   {}\n".format(short_url) + \
        "    Domain:      {}\n".format(domain) + \
        "    Slashtag:    {}\n".format(slashtag)
        i += 1
    res_links += "```"

    return res_links

def rebrand_link(destination):
    """
    Generates a POST to the Rebrandly API with a destination URL (longUrl)
    that needs to be shortened (rebranded). Returns the status code and
    resultant URL (if one was generated)
    """
    destination = destination[1:-1] # Remove brackets: '<https... >'
    linkRequest = {
        "destination": destination,
        "domain": { "fullName": "rebrand.ly" }
    } 

    requestHeaders = {
        "Content-type": "application/json",
        "apikey": REBRANDLY_API_KEY
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