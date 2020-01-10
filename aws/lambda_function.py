import json
import logging
import requests
import base64 # data encoded in base 64
from urllib import parse as urlparse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Return code constants
ERROR_CODE = -1
VALID_CODE = 0

def lambda_handler(event, context):
    """
    Triggered function that is executed with a POST to the 
    Lambda Function's endpoint is made (slack interaction).

    @param event Dictionary of information regarding the triggered event
    @param context LamdaContext object
    @return Dictionary with status code and body text to display
    """
    logger.info("Event: {}".format(event))
    decoded_data_json = decode_query_string(event["body"])
    
    # Assumption: text: ['some_url'] (only one given url)
    try:
        text = decoded_data_json["text"][0]
    except KeyError: 
        return {
            'statusCode': 200,
            'body': "Whoops, looks like you missed the `URL`!"
        }
    
    # Check if user requested help menu
    if text.startswith("help"):
        help_message = "```Usage: /rebrand [url|help]\n\n" + \
        "Description: Provide the bot with a URL and it will generate a\n" + \
        "shortened, rebranded, link hitting the Rebrandly API.\n" + \
        "Example:\n" + \
        "\t> /rebrand https://www.samplesite.com\n```"
        return {
            'statusCode': 200,
            'body': help_message
        }

    # Proceed to Rebrand destination URL
    destination = text
    logger.info("Destination: {}".format(destination))
    apiKey = extract_apikey(event["queryStringParameters"])
    status_code, response = rebrand_link(destination, apiKey)

    if status_code == VALID_CODE:
        logger.info("Generated new link, {}, with status code {} for destination url {}".format(response, status_code, destination))
        body_text = "Destination:   \n> {}\nRebranded URL: \n> {}\n".format(destination, response)
    else:
        logger.info("ERROR! Rebrandly returned the following response: {}".format(response))
        body_text = "Whoops! Looks like the `Rebrandly` returned the following error:\n{}".format(response)
    
    return {
        'statusCode': 200,
        'body': body_text
    }

def decode_query_string(encoded_qs):
    """
    Decodes the base64-encoded query string and returns JSON
    formatted data.

    @param encoded_qs Query String to be decoded
    @return JSON formatted data from the encoded query string
    """
    # Decode base64-encoded query string
    base64_encoded_data = encoded_qs
    base64_bytes = base64_encoded_data.encode('ascii')
    decoded_data_bytes = base64.b64decode(base64_bytes)
    decoded_data = decoded_data_bytes.decode('ascii')
    
    # Use urllib to parse qs into JSON formatted data
    decoded_data_str = json.dumps(urlparse.parse_qs(decoded_data))
    
    logger.info("Decoded Data: {}".format(decoded_data))
    logger.info("Decoded Data JSON: {}".format(decoded_data_str))
    
    return json.loads(decoded_data_str)
    
def extract_apikey(qs_params):
    """
    Extracts APIKEY from the query string parameters
    
    @param qs_params Dictionary of query string parameters
    @return extracted apikey as a String
    """
    apiKey = qs_params["apikey"]
    logger.info("API Key: {}".format(apiKey))
    return apiKey

def rebrand_link(destination, apiKey):
    """
    Performs a POST on the Rebrandly API with a formatted request
    to generated a rebranded link to a provided destination,

    @param destination Original URL to be rebranded
    @param apiKey APIKEY to Rebrandly for API usage
    @return (status_code, response) tuple resulting from POST to API
    """
    linkRequest = {
        "destination": str(destination),
        "domain": { "fullName": "rebrand.ly" } # NOTE: Change to correct domain
    } 

    requestHeaders = {
        "Content-type": "application/json",
        "apikey": str(apiKey)
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
                    error_response += "> " + str(error["code"]) + ": " + str(error["verbose"]) + "\n"
                except KeyError: # No verbose descriptor
                    error_response += "> " + str(error["code"]) + "\n"

            if error: # log error if they exist
                logger.info("Error: {}".format(error_response))

            return (ERROR_CODE, error_response)
    return (ERROR_CODE, None)
