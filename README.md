# Serverless Rebrandly Slack Bot
This Slack Bot can be installed to provide your workspace with a quick and easy way to shorten URLs using the [`Rebrandly API`](https://developers.rebrandly.com/docs). The bot supports various commands to help interface with the API as a convenient utility to join your workspace. 
   - See [supported commands](#supported-commands) for examples on how to utilize these commands.

The Rebrandly Bot leverages AWS Lambda to provide serverless compute power to support the functionality of the bot without needing to stand up a server to host a listener-script.

# Getting Started
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

2. Add a **Scope** under the **OAuth & Permissions** tab
   - Add `app_mentions:read` 

3. Navigate to **Install App** and install it to your workspace
   - You will be provided with a **Bot User OAuth Access Token**. Save this token which will be used later when we configure the Lambda Function.

4. Next, navigate to **Event Subscriptions** so that we can setup our Bot User to subscribe to a specific event to respond to, `app_mention`.
   - When you toggle the option to ON, it will show a text entry for a **Request URL** to verify your endpoint. 
   - Slack provides a *challenge* in order to verify the endpoint and proceed with the subscription.
   - We will need to setup the first lambda function following [these steps](#primary-lambda-function-setup) before proceeding. Once done, return to begin completing step 5 below.

5. Verifying our Lambda Function Endpoint
   - Paste the API Endpoint into the entry and complete the verification challenge
   - Once verified, select **Subscribe to Bot Events** and subscribe to the `app_mention` event


That's it from the Slack side! Now we can finish configuring the [primary lambda function](#primary-lambda-function-setup) (Step 3).


## AWS Lambda Setup
We will be setting up two lambda functions to support this bots functionality. The reason for the second function is due to the Slack API have a `timeout` parameter set **3 seconds** where the computation/processing done by the lambda functiom must complete and return an `HTTP 200 OK` response within 3 seconds. 

If it fails to send that response within 3 seconds, it will retry the same request assuming the first request failed or timed out. To resolve this issue, the primary lambda function will be setup to *Asynchronously* Invoke the secondary lambda function and immediately return the requested `HTTP 200 OK` response while the secondary function continues processing the command.

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
      - Select **Review Policy** and save the new policy for this role

5. Adding a **Destination**
   - Selection **Destination** for the primary lambda function and enter the following values
       - Source: `Asynchronous Invocation`
       - Condition: `On Success`
       - Destination: Paste the `ARN` of the secondary lambda function and `Save`


Now the primary lambda function is setup to recieve incoming requests, asynchronously process the request and immediately return the required `200 HTTP OK` response back to the Slack API.


### Secondary Lambda Function Setup
This lamdba function, which for this guide we will name `rebrandly-event`, is structured to handle the data processing associated with the user interaction. Its main responsibility is to parse the command from the user and make the associated API call to Rebrandly to generate and post a response to the Slack Channel.

1. Navigate to the AWS Console and create a new **Lambda Function**
   - Name it and select **Python3.x** for the language & **Create Function**
   - Copy the **ARN** of THIS function and paste it into the corresponding locations as noted in the **primary lambda function setup** above
      - Inside the **Function Code**
      - Inside the **Destination** configuration

2. For the **Trigger**, create an **API Gateway**, same as the primary function.


3. Setup `Function Code`
   - Inside of the `lambda` directory is the `lambda_function.py` and `requirement.txt` needed to support the bot's functionality.
   - From the root directory, run the following sequence of commands to install the requirements & `zip` the contents of the directory.
   ```
   # install dependencies
   $ cd lambda
   $ pip install -r requirements --system -t .
   $ cd ..

   # zip directory
   $ pwd
   /some/path/to/rebrandly-bot
   $ cd lambda; zip -r ../lambda.zip *
   ```
   - Now import that newly created `lambda.zip` file into the secondary function code section


Now the secondary lambda function is setup and ready to go! Assuming everything is connected as it should be, you can now invite your SlackApp to any channel and interact with it using the [supported commands](#supported-commands) below!


# Supported Commands
