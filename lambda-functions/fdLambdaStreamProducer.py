# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# Producer that will run every minute to produce synthetic real-time data to an input Kafka topic

import boto3
import datetime
import json
import os
import random
import csv
from time import sleep
from datetime import datetime
import uuid
from faker import Faker

faker = Faker()
from kafka import KafkaProducer

msk = boto3.client("kafka")

def lambda_handler(event, context):
    # Get bootstrap servers and Input Kafka topic
    Input_kafka_topic = os.environ["InputKafkaTopic"]
    cluster_arn = os.environ["mskClusterArn"]
    response = msk.get_bootstrap_brokers(ClusterArn=cluster_arn)

    # Initialize the producer
    producer = KafkaProducer(security_protocol="SSL",
                             bootstrap_servers=response["BootstrapBrokerStringTls"],
                             value_serializer=lambda x: json.dumps(x).encode("utf-8"),
                             retry_backoff_ms=500,
                             request_timeout_ms=20000)

    # Read Reference data, to be used to generate synthetic transactions

    refData = os.environ['LAMBDA_TASK_ROOT'] + "/ref_data.csv"


    # Store Reference data in array
    
    with open(refData) as csv_file:
       lines = [line for line in csv.reader(csv_file)]

    # Randomly select 35 rows
    
    chosen_rows = random.choices(lines, k=35)
    # Iteratee over the 35 chosen rows. For each row generate a transaction event
    # Use faker and random to generate:
        # 1- Transaction amount
        # 2- Currency - on of 'usd','gbp','egp','cad','eur']
        # 3- Event ID
        # 4- User Agent 
        # 5- Product category
    # Use datetime to capture timestamp

    for row in chosen_rows:
        data = {}
        data['transaction_amt'] = random.randint(5,2000)
        data['ip_address'] = row[10]
        data['email_address'] = row[11]
        data['transaction_currency'] = random.choice(['usd','gbp','egp','cad','eur'])
        data['event_id'] = faker.uuid4()
        data['entity_id'] = row[0]
        data['event_time'] = datetime.now().isoformat(sep='T')
        data['billing_longitude'] = row[8]
        data['billing_state'] = row[5]
        data['user_agent'] = faker.chrome()
        data['billing_street'] = row[3]
        data['billing_city'] = row[4]
        data['card_bin'] = row[1]
        data['customer_name'] = row[2]
        data['product_category'] = random.choice(['entertainment','food_dining','gas_transport','grocery_net','grocery_pos','health_fitness','home','kids_pets', 'misc_net', 'misc_pos', 'personal_care', 'travel', 'shopping_net', 'shopping_pos'])
        data['customer_job'] = row[9]
        data['phone'] = row[12]
        data['billing_latitude'] = row[7]
        data['billing_zip'] = row[6]
        print(data)
        try:
            # Send the generated transaction as kafka record to a kafka topic
            future = producer.send(Input_kafka_topic, value=data)
            producer.flush()
            record_metadata = future.get(timeout=10)
            # Log the output to cloudwatch
            print("sent event with TS {} to Kafka! topic {} partition {} offset {}".format(data['event_time'],record_metadata.topic, record_metadata.partition, record_metadata.offset))
        except Exception as e:
            # Catch exceptions
            print(e.with_traceback())
        # Sleep 1.5 second before sending the next record
        sleep(1.5)