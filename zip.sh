#!/bin/bash

# Install requirements
cd lambda
pip3 install -r requirements.txt --system -t .
cd ..

# Create zipped folder for import
cd lambda; zip -r ../lambda.zip *
cd ..
