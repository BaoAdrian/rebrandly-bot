# Rebrandly Slack Bot
This Slack Bot can be installed to provide your workspace with a quick and easy way to shorten URLs using the [Rebrandly API](https://developers.rebrandly.com/docs). Simply provide the bot with a URL to shorten and it will return the resultant response from the Rebrandly API.

# Getting Started
There are a couple ways to setup this SlackApp with your Workspace. You will need to complete the following:
- Complete the process of creating and installing a [SlackApp](https://api.slack.com/)
   - Save the `OAuth Access Token` & `Bot User OAuth Access Token` generated by the Slack API if you deploy the bot code
- Setup [Rebrandly](https://developers.rebrandly.com/docs/get-started) Credentials and save the APIKEY
- Deploy the both using any of the options below:
   - [Deploying the Bot Code](#deploying-bot-code) locally/on some host
   - Connect the bot to an [AWS Lambda Function](#aws-lambda)

## Deploying Bot Code
1. Clone this repo and rename the provided `templates` directory to `secrets`. This directory is included in the `.gitignore` file to ensure all secrets are ommitted from tracking/commits.
    ```
    $ mv templates secrets
    ```


2. Modify the provided `secrets.json.template` file to contain your Slackbot API & Rebrandly secrets.
    ```
    $ mv secrets.json.template secrets.json
    ```


3. Create and enter a `virtualenv` (installing if necessary using `pip install virtualenv`) and install the requirements
    ```
    $ virtualenv bot
    $ source bot/bin/activate
    (bot) $ pip install -r requirements
    ````


4. Run the bot. If successfully running, you should see a message following the execution
    ```
    (bot) $ python bot.py
    Slack Bot is now running!
    ```


5. Now you can go into your workspace and interact with the bot using the formatting [below](#interacting with the bot)!

## Interacting with the bot
Currently, the bot supports the operation to shorten any provided URL using the following interaction:
```
@[botname] [url]
```

For example, if you named your bot `rebrandlybot`, then the following will generate a rebranded URL:
```
@rebrandlybot https://www.sample.com
```

To ask the bot for help, use:
```
@rebrandlybot help
<help info>
```


## AWS Lambda
Lambda Functions provide the Serverless functionality needed to run the bot _as needed_. It will only require compute-power/resources when its associated endpoint is triggered.

See [here](./aws) for assistance in configuring the Lambda Function