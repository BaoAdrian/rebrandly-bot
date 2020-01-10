# AWS Lambda


# Connecting Bot to AWS Lambda

## 1. Create your Lambda Function
   - On the AWS Lambda Console, navigate to **Functions** > **Create Function**
   - Select **Author From Scratch** since the code is provided for your convenience
   - Give your function a name
   - Select **Python3.7** for your Runtime configuration
   - Keep **Permissions** the same
   - Select **Create Function**


## 2. Configure a Trigger for your Lambda Function
   - Add a **Trigger** > **API Gateway**
   - Under **API** > **Create a new API** > `HTTP API** > **Add**
   - Copy and Save the **API Endpoint** that was just created
      - This is the endpoint used by the Slash Command below


## 3. Define your Lambda Function
Under the **Function Code** section on the Lambda Function dashboard, you are given the option to use inline code or upload from zip/S3 Bucket.
- We will be using an S3 Bucket (TLDR: AWS Lambda does not natively support use of the `requests` module so we must upload a zipped folder with our code/dependencies)

### Setting up zipped folder
- Make a directory called `lambda`
   ```
   $ pwd
   /some/path/to/rebrandly-bot/aws
   $ mkdir lambda
   ```
- Copy `lambda_function.py` into the new directory & setup virtualenv to install `requests`
   ```
   $ cp lambda_functio.py lambda
   $ cd lambda
   $ virtualenv env
   $ source env/bin/activate
   (env) $ pip install requests -t .
   ```
- Now change to parent directory and run the following command to zip the contents of the `lambda` directory, excluding the directory itself
   ```
   cd lambda; zip -r ../lambda.zip *
   ```
- The above should have created a `lambda.zip` inside of `rebrandly-bot/aws`. This is the zipped file that you will upload to S3.
- Once uploaded to S3, select the bucket and copy the URL provided as the **Object URL** 

### Link Function Code to S3 Bucket Zipped Resource
Navigate back to the Lambda Function Defintion and paste that **Object URL** inside of **Function Code** > **Code Entry Type** > **Upload a file from Amazon S3**

At this point, you have created and defined an Amazon Lambda Function whose Function Code is housed inside of an Amazon S3 Bucket with its associated dependencies. Now we can use the API Endpoint URL generated above to configure our Slash Command below.

## 4. Creating Slash Command
   - Navigate to Slack API dashboard for your installed app > **Features** > **Slash Command** > **Create New Command**
   - Enter command, for example: `/rebrand`
   - Enter request URL, this is the **API Endpoint** noted above in Step 2.
      - Append your `apikey` you generated from Rebrandly as a query string parameter
      - Example: `https://apiendpointforaws?apikey=[INSERTKEY]`
   - Enter Short Description
   - Enter Usage Hint
   - **Save**


Now you can open up your workspace and test serverless slack bot using 
```
/rebrand help
```