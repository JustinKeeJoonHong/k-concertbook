#!/bin/bash

# Set necessary variables
LAMBDA_FUNCTION_PREFIX="ticketmaster_"  # prefix for Lambda function names

# First positional argument is the Python file to deploy (e.g. event.py)
FILE_NAME=$1

# Validate input
if [ -z "$FILE_NAME" ]; then
  echo "Error: please provide the Python file to deploy (ex: ./deploy_lambda.sh event.py)"
  exit 1
fi

# Create Lambda function name from file name
LAMBDA_FUNCTION_NAME="${LAMBDA_FUNCTION_PREFIX}${FILE_NAME%.*}"

# Zip file name
ZIP_FILE="lambda_function_package.zip"

# Clean up any existing temporary files
rm -f $ZIP_FILE
rm -f lambda_function.py

# Copy selected Python file to lambda_function.py for packaging
cp $FILE_NAME lambda_function.py

# Include lambda_function.py and Redis-related folders when creating the zip
zip -r $ZIP_FILE lambda_function.py redis redis-3.5.3.dist-info

# Update Lambda function code
aws lambda update-function-code --function-name $LAMBDA_FUNCTION_NAME --zip-file fileb://$ZIP_FILE

# Clean up temporary copy
rm -f lambda_function.py
