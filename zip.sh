#!/bin/bash

# Install requirements & zip directory
cd lambda
pip3 install -r requirements.txt --system -t .
zip -r ../lambda.zip *
cd ..
