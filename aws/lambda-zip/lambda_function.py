import os, re, json, time
import logging
import requests
import slack

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Return code constants
ERROR_CODE = -1
VALID_CODE = 0

BOT_USER_OAUTH_TOKEN = os.environ['BOT_USER_OAUTH_TOKEN']
REBRANDLY_API_KEY = os.environ['REBRANDLY_API_KEY']

def lambda_handler(event, context):
    logger.info("Triggered AWS Lambda: rebrandly-event")

    # Extract vars from body
    body = json.loads(event["body"])
    channel = body["event"]["channel"]
    text = body["event"]["text"].split()
    command_text = ' '.join(text[1:])
    
    logger.info("Body: {}".format(body))
    logger.info("Channel: {}".format(channel))
    logger.info("Text: {}".format(text))
    logger.info("Response Text: {}".format(command_text))

    response = handle_command(command_text)

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
    
    @param text String text to be parsed and processed
    @return generated response depending on user's command request
    """
    # Default response is help text for the user
    is_rebrand = False
    default_response = "Hmmm, I didn't quite catch that."
    invalid_url_response = "Hmmm, the url you provided was invalid, please try again"
    response = None

    if text.startswith("help"):
        response = get_help_menu()
    elif text.startswith("where"):
        response = get_github_repo()
    elif text.startswith("list"):
        response = list_links(text)
    elif text.startswith("count"):
        response = count_links()
    elif text.startswith("rebrand-custom"):
        is_rebrand = True
        destination = text.split()[1]
        status_code, rebranded_link = rebrand_custom_link(text)
    elif text.startswith("rebrand"):
        is_rebrand = True
        destination = text.split()[1]
        status_code, rebranded_link = rebrand_link(destination)
        
    # Customize response if it is rebrand
    if is_rebrand:
        if status_code == VALID_CODE:
            response = "Destination:\n> {}\n".format(destination) + \
                       "New URL:    \n> {}\n".format(rebranded_link)
        else:
            if rebranded_link:
                response = "Received the following error:\n> {}".format(rebranded_link)
            else:
                response = invalid_url_response
    
    return response or default_response

def get_help_menu():
    return "This is how you can interact with me:\n" + \
        "```@rebrandlybot [command]```\n" + \
        "Supported *commands*:\n" + \
        "\t`help` Displays this help menu\n" + \
        "\t`rebrand [url]` Rebrands the provided url with auto-generated slashtag\n" + \
        "\t`rebrand-custom [url] [domain|slashtag]` Accepts custom domain & slashtag values\n" + \
        "\t`list [limit|orderBy|orderDir]` Lists the latest rebranded links\n" + \
        "\t`count` Counts the total number of rebranded links\n" + \
        "\t`where` Shows you where my code is located with usage examples\n"

def rebrand_custom_link(text):
    """
    Generates a POST to the Rebrandly API with a custom parameters set by
    the user. Returns status code and resultant URL (if one was generated).
    
    @param text String text to be parsed for rebranding with arguments
    @return resultant (CODE, RESPONSE) result from call to rebrand_link(...)
    """
    logger.info("Recieved REBRAND-CUSTOM request: {}".format(text))
    
    params = text.split()
    destination = params[1]
    
    default_args = {
        "slashtag": None,
        "domain": None
    }
    text = text.replace("=", " ")
    text = ' '.join(text.split()[2:])
    try:
        args = extract_args(text, default_args)
    except:
        return (ERROR_CODE, "Unable to extract arguments. Please verify the formatting and try again.")

    slashtag, domain = None, None

    # Extract validate slashtag & domain
    if args["slashtag"]:
        if not (re.match("^[A-Za-z0-9_-]*$", args["slashtag"]) and len(args["slashtag"]) >= 1 and len(args["slashtag"]) <= 40):
            args["slashtag"] = default_args["slashtag"] # revert to default

    if args["domain"]:
        idx = value.find('|')
        args["domain"] = value[idx+1:-1]

    return rebrand_link(destination, args["slashtag"], args["domain"])


def rebrand_link(destination, slashtag=None, domain=None):
    """
    Generates a POST to the Rebrandly API with a destination URL (longUrl)
    that needs to be shortened (rebranded). Returns the status code and
    resultant URL (if one was generated).
    
    @param destination Destination string parsed from message event
    @param slashtag String slashtag to be used (None or string)
    @param domain String domain to be used (None or string)
    @return (CODE, RESPONSE) tuple used to generate response by caller
    """
    logger.info("Received REBRAND request")
    logger.info("Destination: {}".format(destination))
    destination = destination[1:-1] # Remove brackets: '<https... >'
    linkRequest = {
        "destination": destination
    }

    # Add customizations if requested
    if slashtag:
        linkRequest["slashtag"] = slashtag
    if domain:
        linkRequest["domain"] = { "fullName": domain }

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
        return (VALID_CODE, "https://" + link["shortUrl"])
    else:
        r_data = r.json()
        if len(r_data["errors"]) != 0: # errors exist
            error_response = ""
            for error in r_data["errors"]:
                try:
                    error_response += "> {}: {}\n".format(str(error["code"]), str(error["verbose"]))
                except KeyError: # No verbose descriptor
                    error_response += "> {}\n".format(str(error["code"]))
            return (ERROR_CODE, error_response)
            
    return (ERROR_CODE, None)

def list_links(text):
    """
    Generates a GET request to the Rebrandly API @ https://api.rebrandly.com/v1/links
    Gets information on the generated links and data returned will be used to display
    latest, existing links to user.
    
    @param text String command text to be processed for args
    @return String response to be posted to the Slack channel as response
    """
    logger.info("Recieved LIST request: {}".format(text))
    
    default_args = {
        "limit" : "10",
        "orderBy": "createdAt",
        "orderDir": "desc"
    }
    
    # Overwrite default args (if required)
    text = text.replace("=", " ")
    text = ' '.join(text.split()[1:])
    try:
        args = extract_args(text, default_args)
    except:
        return "Recieved the following error:\n" + \
        "> Unable to extract arguments. Please verify the formatting and try again."

    params = {
        "apikey": REBRANDLY_API_KEY,
        "limit": args["limit"],
        "orderBy": args["orderBy"],
        "orderDir": args["orderDir"]
    }
    links = requests.get("https://api.rebrandly.com/v1/links", params=params)
    links_json = json.loads(links.text)

    # Generate Slack Response from Bot User
    response = "Here are the last `{}` rebranded links:```".format(args["limit"])
    i = 1
    for link in links_json:
        response += "[{}] Destination: {}\n".format(i, link["destination"]) + \
        "    Short URL:   {}\n".format(link["shortUrl"]) + \
        "    ID:          {}\n".format(link["id"]) + \
        "    Domain:      {}\n".format(link["domainName"]) + \
        "    Slashtag:    {}\n".format(link["slashtag"])
        i += 1
    response += "```"

    return response

def extract_args(params, default_args):
    """
    Utility method used to extract arguments from command text
    
    @param params String containing arguments added by user
    @param default_args Dictionary containing default args for functionality
    @return An updated default_args dictionary containing updated args
    """
    params = params.split()
    logger.info("Params: {}".format(params))
    for i in range(0, len(params), 2):
        key,value = params[i], params[i+1]
        default_args[key] = value
        logger.info("Extracted arg: ({}, {})".format(key, value))
    
    return default_args

def count_links():
    """
    Retrieves the total count of all rebranded links under 
    the current API_KEY
    Sample text: count limit=10
    """
    logger.info("Received COUNT request")
    params = {
        "apikey": REBRANDLY_API_KEY
    }
    
    response = requests.get("https://api.rebrandly.com/v1/links/count", params=params)
    logger.info("Count Response: {}".format(response.text))
    res_json = json.loads(response.text)
    
    try:
        return "Total Links: `{}`".format(res_json["count"])
    except:
        return "Something went wrong while retrieving the count!"

def get_github_repo():
    """ Generates response containing Github repo where bot code is located """
    return "You can find my code here: `https://github.com/BaoAdrian/rebrandly-bot`\n" + \
    "Feel free to report bugs or request for features by opening a new Issue!"