# Serverless Rebrandly Bot
In a standard deployment, the bot (`bot.py`) needs to be running on a Server to actively listen to incoming messages. This would require something like EC2, for instance. To move away from requiring a server, we can utilize Serverless Lambda Functions to handle incoming requests that will ping the Rebrandly API only when needed. 

# Context for Slack API
We will be setting up the Slack Bot using the [`Events API`](https://api.slack.com/events-api) that will be subscribed to the [`app_mention`](https://api.slack.com/events) event. 

One of the caveats with the Slack API is that any request that is made when a subscribed event is triggered requires an `200 OK` HTTP response within 3 seconds of the initial request. Since our bot may perform some additional processing based on the interaction with the user, our data processing may take more than 3 seconds to execute.

Ideally, we would set up a single Lambda Function that gets triggered with the `app_mention` event, performs some compute/processing, then responds to the user (via slack) and returns the `200 OK` HTTP response. However, if the compute/processing takes longer than 3 seconds, Slack API is configured to resend another identical request to the Lambda Function, essentially repeating the exact same process as before. When this happens, you will see multiple duplicated messages from the bot because each request succeeds in its compute/processing BUT does not return the status code within the 3 second time frame.

The simplest solution would be to spawn a new thread and execute the data processing on that thread while the main thread immediately returns the `200 OK` HTTP response. The problem here is that AWS Lambda does not support threading for asynchronous execution, i.e. once the main thread is complete, the other thread that spawned does not finish executing, regardless of how it is asynchronously invoked.

Because of this, we will need to setup 2 Lambda Functions, one to setup an asynchronous call and return the response within 3 seconds, and the other to implement the processing portion of the bot logic.

# Getting Started
To get these components connected, we will need to complete the following
- Setup Lambda Functions
- Setup Slack App using Slack API

# Lambda Functions
This is the breakdown of the lambda functions, which for this example we will call `rebrandly-recieve` and `rebrandly-processing`

## rebrandly-recieve
This function will simply take the event data, asynchronously invoke the secondary lambda function (`rebrandly-processing`) and pass it the event data, then immediately return the `200 OK` HTTP response signifying the request was successfully recieved. 

`lambda_function.py` for this function:
```
import json
import boto3

def lambda_handler(event, context):
    client = boto3.client('lambda')
    
    # Asynchronous call to rebrandly-processing
    res = client.invoke(
        FunctionName='[INSERT ARN OF SECONDARY FUNCTION]',
        InvocationType='Event',
        Payload=json.dumps(event).encode('utf-8')
    )
    
    return {
        'statusCode': 200,
        'body': "Primary Lambda Function Completed"
    }
```


### Trigger
As a **Trigger** for this function, setup an API Gateway using the HTTP API and save the **API Endpoint** as this is the endpoint that will be triggered for the subscribed `app_mention` event detailed further below.
```
Slack Bot Interaction triggers app_mention event
 \__ Sends POST to API Endpoint
      \__ Triggers rebrandly-receive
           \__ Asynchronously invokes rebrandly-processing
           \__ Returns 200 OK HTTP response
```

### Destination
The destination for this primary Lambda Function will be the secondary Lambda Function that we will define below. Be sure to setup the corresponding permissions so that this function can invoke the secondary function:

```
Resource > [ARN OF SECONDARY FUNCTION]
Action > Allow: lambda:InvokeFunction
```

## rebrandly-processing
This function performs the processing of the event data that is provided when the `app_mention` event gets triggered. 

The code has been provided for you in `lambda_function.py` but requires some additional steps to integrate it with the secondary lambda function. 

Since AWS Lambda does not natively support the `requests` module, we need to create a zipped package containing the code and its dependencies. We can use `requirements.txt` for this purpose.

Change directory to access the function code and requirements & install them using `pip`
```
$ cd lambda-zip
$ pip install -r requirements.txt -t .
```

Move back a directory level and run the following commands to create a zip named `lambda.zip`
```
$ cd ..
$ cd lambda-zip; zip -r ../lambda.zip *
```

Now there should be a `lambda.zip` that can then be imported to AWS. Because AWS Lambda limits zip imports to 50MB in size, create an `S3 Bucket` to hold the code/dependencies. Once uploaded, copy the **Object URL** and paste that into the Lambda Function S3 Bucket URL entry.
```
Function Code > Code entry type > Upload a file from Amazon S3
```

Now the code should be good to go!


### Trigger
Similar to the primary lambda function, setup an **API Gateway** using the HTTP API. 


### Destination
No destination is required since the POST to the Rebrandly API occurs within the `lambda_functon.py` code.


# Slack App
To setup the SlackApp to listen to the required `app_mention` event, you first need to Enable Events under the Event Subscription tab on the Dashboard. 

Enter the **API Endpoint** for `rebrandly-receive` in the text field entry to verify the URL. Complete the challenge necessary to verify the endpoint.

Next, add `app_mention` under Subscribe to bot events. This should adjust the **Scope** of your bot under **OAuth and Permissions** but if it did not, you will need to add:
```
app_mentions:read
channels:read
chat:write
commands
im:read
```

Now whenever the correspond event is triggered, the API Endpoint will be triggered, executing the Rebrandly request and posting the response to the channel!