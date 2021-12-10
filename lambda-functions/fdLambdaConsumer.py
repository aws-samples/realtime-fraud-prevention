# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import base64
import boto3
import json
import os
from datetime import datetime
from decimal import *

sns = boto3.client('sns')

def lambda_handler(event, context):
    # Get SNS Topic ARN 
    topic_arn = os.environ["SNSTopicArn"]

    # Iterate over events
    for partition_key, partition_value in event['records'].items():
        for record_value in partition_value:
            data = json.loads(base64.b64decode(record_value['value']))

            # For each event, check if the outcome is 'block' 

            if data["fd"]["outcome"] == 'block':
                # Construct the message to SNS. Sending the following:
                # 1- EventID
                # 2- The outcome
                # 3- Entity ID or optionally Customer name by using data["customer_name"]
                # 4- Transaction Amount

                Message= '''
                A transaction has been flagged. Please find the details:
                
                        TransactionID: {0}
                        Outcome:  {1}
                        Timestamp: {2}
                        EntityID: {3}
                        transaction Amount: {4}
                
                Please review transaction
                '''.format(data["event_id"],data["fd"]["outcome"],data["event_time"],data["entity_id"],data["transaction_amt"])

                # Publish the message to an SNS topic
                
                response = sns.publish(
                    TopicArn=topic_arn,
                    Message= Message,
                    Subject='FRAUD ALERT: Transaction has been flagged!'
                )
                print('FRAUD')
                print(data)
            else:
                # If not block - do nothing
                print(data)
