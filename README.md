# Serverless Rebrandly Slack Bot
This Slack Bot can be installed to provide your workspace with a quick and easy way to shorten URLs using the [`Rebrandly API`](https://developers.rebrandly.com/docs). The bot supports various commands to help interface with the API as a convenient utility to join your workspace. 
   - See [supported commands](#supported-commands) for examples on how to utilize these commands.

The Rebrandly Bot leverages AWS Lambda to provide serverless compute power to support the functionality of the bot without needing to stand up a server to host a listener-script.

# Getting Started
You can choose to follow the guide below setting up the three components in order, however, it may be easier to initially just **Create** the two required lambda functions (without configuring anything) so that you can access their **ARN** values when needed without having to jump around the setup process.
- [Prerequisites](#prerequisites)
- [Bot User Setup](#setting-up-slack-app-as-a-bot-user)
- [AWS Lambda Setup](#aws-lambda-setup)

## Prerequisites
This repository assumes you have already obtained the following:
- [`Rebrandly`](https://developers.rebrandly.com/docs/get-started) API Key
- [`AWS`](https://aws.amazon.com/console/) login credentials

The bots backend is implemented using Lambda Functions. If you are unfamiliar with these, here is their [documentation](https://docs.aws.amazon.com/lambda/index.html) to get started.

Additionally, it makes use of various HTTP Requests using the `requests` module, feel free to read through this [guide](https://realpython.com/python-requests/) to gain familiarity with Python requests.

## Setting up Slack App as a Bot User
This portion requires you to navigate to the [`Slack API`](https://api.slack.com/) Dashboard and **Start Building** your SlackApp.

1. Select **Start Building** from the dashboard & enter the requested App name & workspace.

2. Add a **Bot OAuth Token Scope** under the **OAuth & Permissions** tab
   - Add `app_mentions:read` & `chat:write`

3. Navigate to **Install App to Workspace** and install it to your workspace
   - Save the  **Bot User OAuth Access Token** as it will be used in the lambda function setup.

4. Navigate to **Event Subscriptions** to setup subscription to the `app_mention` event
   - Toggle the option to ON and it will show a text entry for a **Request URL** to verify your API endpoint for your primary lambda function. 
      - Slack provides a *challenge* in order to verify the endpoint and proceed with the subscription.
   - If you haven't already, proceed to *Step 1* of the primary lambda function setup [below](#primary-lambda-function-setup) before proceeding. Once done, return to begin completing step 5 below.

5. Verifying our Lambda Function Endpoint
   - Paste the **API Endpoint** into the **Request URL** entry and complete the verification challenge
      - You can use the following snippet to complete the verification challenge:
         ```
         return {
            'statusCode': 200,
            'body': json.loads(event["body"])["challenge"]
         }
         ```
   - Once verified, select **Subscribe to Bot Events** and subscribe to the `app_mention` event


That's it from the Slack side! Now we can finish configuring the [primary lambda function](#primary-lambda-function-setup) (Step 3).


## AWS Lambda Setup
We will be setting up two lambda functions to support this bots functionality. The reason for the second function is due to the Slack API having a `timeout` parameter set to **3 seconds** where the computation/processing done by the lambda functiom must complete and return an `HTTP 200 OK` response within 3 seconds. 

If it fails to send that response within 3 seconds, it will retry the same request assuming the first request failed or timed out, resulting in duplicate responses. To resolve this issue, the primary lambda function will be setup to *Asynchronously* Invoke the secondary lambda function and immediately return the requested `HTTP 200 OK` response while the secondary function continues processing the command.

### Primary Lambda Function Setup
1. Navigate to the AWS Console and create a new **Lambda Function**
   - Name it whatever you would like but for this guide, we will refer to this function as `rebrandly-receive`
   - Selet **Python3.x** for the language & **Create Function**

2. For the **Trigger**, create an **API Gateway** and select **HTTP** as your endpoint
   - There should now be an **API Endpoint** listed below, save this endpoint as this is the endpoint that the SlackApp will make a POST request to.
   - Now we can return back to the [challenge](#setting-up-slack-app-as-a-bot-user) (Step 5) to verify this endpoint.

3. Setup **Function Code**
   - Paste the following code into the code section (Note the need to enter the ARN for the second lambda function below)
    ```
    import json, boto3

    def lambda_handler(event, context):
        client = boto3.client('lambda')
        
        # Asynchronous call to rebrandly-event
        res = client.invoke(
            FunctionName='[ARN_OF_SECONDARY_FUNCTION]',
            InvocationType='Event',
            Payload=json.dumps(event).encode('utf-8')
        )

        return {
            'statusCode': 200,
            'body': "Primary Lambda Function Completed"
        }
    ```

4. Setup the **InvokeFunction** permissions/role
   - In order to invoke execution of a lambda function from another lambda function, you must have the necessary permissions to do so, namely: **InvokeFunction**
      - Through the [AWS Console](https://us-east-2.console.aws.amazon.com/console/home), select **IAM** and select **Roles** on the side pane
      - Since you have already created this function (`rebrandly-receive`), there should be an existing role named `rebrandly-receive-role-SOMEHASH`. Click on this role
      - Select **Add inline policy** and use the following information on the next page:
         - Service: **Lambda**
         - Actions: **InvokeFunction**
         - Resources: Add **ARN** of secondary lambda function that will be created below
         - Request Conditions: No action required (see Step 1 of Secondary Function setup below)
      - Select **Review Policy**, name the policy and **Create Policy** to confirm


Now the primary lambda function is setup to recieve incoming requests, asynchronously process the request and immediately return the required `200 HTTP OK` response back to the Slack API.


### Secondary Lambda Function Setup
This lamdba function, which for this guide we will name `rebrandly-event`, is structured to handle the data processing associated with the user interaction. Its main responsibility is to parse the command from the user and make the associated API call to Rebrandly to generate and post a response to the Slack Channel.

1. Navigate to the AWS Console and create a new **Lambda Function**
   - Name it and select **Python3.x** for the language & **Create Function**
   - Copy the **ARN** of THIS function and paste it into the corresponding locations as noted in the **primary lambda function setup** above
      - Inside the **Function Code**

2. Setup **Function Code**
   - Inside of the `lambda` directory is the `lambda_function.py` and `requirements.txt` needed to support the bot's functionality. These will need to be zipped and imported in Lambda.
   - The provided `zip.sh` bash script performs the necessary actions to install & zip the dependencies/code into a file named `lambda.zip`
      ```
      $ bash zip.sh
      ```
   - **Import** the newly created `lambda.zip` file into the secondary function code section

3. Environment Variables
   - You will notice after the import of the **Function Code** that it uses environment variables to extract the `BOT_USER_OAUTH_TOKEN` and the `REBRANDLY_API_KEY`
   - In the **Environment Variables** section, add two key-value pairs for the above variables
   - Save any changes made to the Function configuration

NOTE: If you wish to extend the `timeout` timeframe, modify the **Basic Settings** `Timeout` parameter to whatever value you see reasonable for your usecase

Now the secondary lambda function is setup and ready to go! Assuming everything is connected as it should be, you can now invite your SlackApp to any channel and interact with it using the [supported commands](#supported-commands) below!


# Interacting with the bot
The Bot is setup to trigger a response whenever it is mentioned in a channel it has been added to (`app_mentioned` event). 

You must mentioned the bot then provide it with some command and any additional arguments supported by that command (see [supported commands](#supported-commands) for more info on accepted commands/arguments).
```
@rebrandlybot [command] [args]
```

# Supported Commands
**`help`**
- Displays a help menu to the user listing supported commands and general usage
- Command: `help`
- Args: None

**`rebrand [url]`**
- Rebrands the provided `url` with the default domain/slashtag generation methods
- Command: `rebrand`
- Args: 
   - (Required) `url` that will be rebranded/shortened by the API
- Sample Usage:
   ```
   @rebrandlybot rebrand https://someurl.com
   ```

**`rebrand-custom [url] [domain|slashtag]`**
- Same functionality as the above command but with the added feature of customizing the domain and/or slashtag attributes of the rebranded link
- Command: `rebrand-custom`
- Args: 
   - (Required) `url`: URL that will be rebranded/shortened by the API
   - (Optional) `domain`: custom domain that the rebrand will be stored under
   - (Optional) `slashtag`: custom slashtag that the rebranded link will use
- Sample Usage:
   ```
   @rebrandlybot rebrand-custom https://someurl.com domain=rebrand.ly slashtag=someawesomesite
   ```

**`search [show] [destination|slashtag|domain]`**
- Searches for links matching any provided arguments such as destination, domain, and slashtag
- Command: `search`
- Args:
   - (Optional) `show`: Flag you can set to display the resulting info from a requested search
   - (Optional) `destination`: Destination URL target for search
   - (Optional) `slashtag`: Slashtag target for search
   - (Optional) `domain`: Domain target for search
- Sample Usage:
   - Searches all rebranded links pointing to the given `destination`
      ```
      @rebrandlybot search show destination=https://someurl.com
      ```
   - Searches (and shows) all rebranded links under the given `domain`
      ```
      @rebrandlybot search show domain=rebrand.ly
      ```
   - Searches (and shows) all rebranded links pointing to a given `destination` under a specifid `domain`
      ```
      @rebrandlybot search show destination=https://someurl.com domain=rebrand.ly
      ```
 

**`list [limit|orderBy|orderDir]`**
- Lists information on a specific number of links (default = 10)
- Command: `list`
- Args: 
   - (Optional) `limit`: Limits the number of results returned to the value you set
   - (Optional) `orderBy`: Sorting criteria to apply to the list command
      - Options include: `createdAt` (default), `updatedAt`, `title`, and `slashtag`
   - (Optional) `orderDir`: Sorting direction to apply to collection, either `asc` or `desc` (default)
- Sample Usage:
   - Displays the last 10 rebranded links ordered by slashtag
      ```
      @rebrandlybot list limit = 10 orderBy = slashtag
      ```

**`count`**
- Counts the total number of rebranded links
- Command: `count`
- Args: None

**`where`**
- Provides user with link to public repository where this helpful guide is provided
- Command: `where`
- Args: None