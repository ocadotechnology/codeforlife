"""
© Ocado Group
Created on 29/11/2024 at 15:59:40(+00:00).

This file contains all the variables required and/or exposed by Ocado's
Technology Platform.

NOTE: All variables should be retrieved like so: `os.getenv("key")`.
"""

import os

# App configuration.

APP_ID = os.getenv("APP_ID")
APP_VERSION = os.getenv("APP_VERSION")

# AWS S3 configuration.

AWS_S3_APP_BUCKET = os.getenv("aws_s3_app_bucket")
AWS_S3_APP_FOLDER = os.getenv("aws_s3_app_folder")

# Database configuration.

DB_NAME = os.getenv("DB_NAME")
DB_SCHEMA_NAME = os.getenv("DB_SCHEMA_NAME")
DB_INSTANCE_NAME = os.getenv("DB_INSTANCE_NAME")
DB_DATA_PATH = (
    f"{AWS_S3_APP_FOLDER}/dbMetadata/"
    + (f"{DB_INSTANCE_NAME}/" if DB_INSTANCE_NAME else "")
    + f"{DB_NAME}/{DB_SCHEMA_NAME}.dbdata"
)
