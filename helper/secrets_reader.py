import os
import json
from pathlib import Path

import streamlit as st
import boto3
from botocore.exceptions import ClientError


class SecretsManager:
    @staticmethod
    def get_secret(key):
        secret_name = "cotf/ai/metacog"
        region_name = "ap-southeast-1"

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name="secretsmanager",
            region_name=region_name,
        )

        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise e

        secrets = json.loads(get_secret_value_response["SecretString"])
        return secrets[key]


class SecretsRetriever:
    def get_secret(self, name):
        current_directory = os.getcwd()
        file_path = Path(current_directory+'/.streamlit/secrets.toml')
        try:
            if file_path.exists():
                return st.secrets[name]
            else:
                return SecretsManager.get_secret(name)
        except:
            st.error(f'{name} secret cannot be read.')