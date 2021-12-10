#  Real time Fraud Prevention and Visualisation using Amazon Fraud Detector

  
This repository accompanies the [Real time Fraud Prevention and Visualisation using Amazon Fraud Detector](https://aws.amazon.com/blogs/big-data/automating-bucketing-of-streaming-data-using-amazon-athena-and-aws-lambda/) blog post. It contains **one** [AWS Cloudformation](https://aws.amazon.com/cloudformation/) template. 

The template deploys:
1. Sample transaction producer running as an [AWS Lambda Function](https://aws.amazon.com/lambda/). The function is scheduled to run every minute generating 30 transactions per minute.
2. [Amazon MSK](https://aws.amazon.com/msk/) cluster, that contains 2 topics with default names of *transactions* and *processed_transactions*. Both topics will be automatically created by the producer and the stream processor.
3. PyFlink stream processing job that runs as an [Amazon Kinesis Data Analytics](https://aws.amazon.com/kinesis/data-analytics/). The job processes each transaction as soon as it is written to the *transactions* (input) topic, invokes [Amazon Fraud Detector](https://aws.amazon.com/fraud-detector/) APIs ([GetEventPrediction](https://docs.aws.amazon.com/frauddetector/latest/api/API_GetEventPrediction.html)) in real time to generate fraud predictions and writes the outcome to *processed_transactions* (output) topic.
4. Consumer Lambda function that the reads data from *processed_transactions* topic and sends email notifications for blocked transactions.
5. Sink Kafka connector running on [MSK Connect](https://aws.amazon.com/msk/features/msk-connect/) that reads processed transactions from *processed_transactions* topic and sinks the data to an OpenSearch index. Allowing us to visualise the transactions in real time.
6. Private [Amazon OpenSearch Service (successor to Amazon Elasticsearch Service)](https://aws.amazon.com/opensearch-service/) domain in a provisioned VPC
7. An [AWS Cloud9](https://aws.amazon.com/cloud9/) environment to import a pre-created dashboard to OpenSearch Dashboards



```bash
├──Artifacts                          <-- Directory that will hold solution Artifacts
│   ├── dashboard.ndjson              <-- An export of a sample OpenSearch dashboard to visualise transaction data
├── lambda-functions                  <-- Directory contains Lambda functions code
│   ├── fdLambdaConsumer.py           <-- Consumer Lambda function code
│   ├── fdLambdaStreamProducer.py     <-- Producer Lambda function code
│   └── LambdaConfig.py               <-- Configuration Lambda function code
│   └── requirements.txt              <-- Dependencies file for Lambda functions
└── RealTimeFraudPrevention           <-- Directory contains Kinesis Data Analytics PyFlink application code 
│   ├── main.py                       <-- Kinesis Data Analytics PyFlink application code 
│   ├── bin
│   │   ├── requirements.txt          <-- Dependencies file for Kinesis Data Analytics PyFlink application code 
├── Realtime_Fraud_Prevention_CFN.yml <-- CloudFormation Templatet
└── README.md
```


## General Requirements

* [Install Python](https://realpython.com/installing-python/) 3.8.2 or later
* AWS CLI already configured with Administrator permission
* Amazon Fraud Detector published with the following below variable names, follow [this blog](https://aws.amazon.com/blogs/machine-learning/detect-online-transaction-fraud-with-new-amazon-fraud-detector-features/) as a reference
    * 'order_price' - Manadatory 
    * 'customer_email' - Mandatory
    * 'ip_address' - Mandatory
    * 'payment_currency' - Mandatory
    * 'billing_longitude' - Optional
    * 'billing_latitude' - Optional
    * 'billing_zip' - Optional
    * 'billing_state' - Optional
    * 'user_agent' - Optional
    * 'billing_street' - Optional
    * 'billing_city' - Optional
    * 'card_bin' - Optional
    * 'customer_name' - Optional
    * 'product_category' - Optional
    * 'customer_job' - Optional
    * 'phone' - Optional

## Installation Instructions

1. Clone the repo onto your local development machine using `git clone <repo url>`.
2. Change directory to solution repo

```

cd realtime-fraud-prevention

```


### Install Lambda functions dependencies and package code

```bash
pip3 install -r ./lambda-functions/requirements.txt -t ./lambda-functions

(cd lambda-functions; zip -r ../Artifacts/lambda-functions.zip .)
```

### Install Kinesis Data Analytics PyFlink application dependencies and package code

```bash

python3 -m venv ./RealTimeFraudPrevention

./RealTimeFraudPrevention/bin/pip3 install -r ./RealTimeFraudPrevention/bin/requirements.txt -t ./RealTimeFraudPrevention/lib/packages

wget https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka_2.11/1.11.2/flink-sql-connector-kafka_2.11-1.11.2.jar -P ./RealTimeFraudPrevention/lib

zip -r ./Artifacts/RealTimeFraudPrevention.zip ./RealTimeFraudPrevention
```

### Download Kafka connector

```bash

(cd Artifacts; curl -L -O https://d1i4a15mxbxib1.cloudfront.net/api/plugins/confluentinc/confluentinc-kafka-connect-elasticsearch-11.1.3.zip)

```

### Upload solution artifacts

1. Run the following command to create a unique Amazon S3 bucket which will be used to store the solution artifacts. 

```

aws s3 mb s3://<S3_Bucket_name> --region <Amazon_Fraud_Detector_Region>

```
Replace:
* **<S3_Bucket_name>** with your unique bucket name and 
* **<Amazon_Fraud_Detector_Region>** with the region used to deploy Amazon Fraud Detector. E.g. *eu-west-1*

2. Run the following command to sync the solution artifacts with the newly created buckets

```

aws s3 sync ./Artifacts/ s3://<S3_Bucket_name>

```

### Deploy solution

1. Run the following command to deploy the CloudFormation template

```

aws cloudformation create-stack --template-body file://Realtime_Fraud_Prevention_CFN.yml --parameters \
ParameterKey=BucketName,ParameterValue=<S3_Bucket_name> \
ParameterKey=FraudDetectorEntityType,ParameterValue=<Amazon_Fraud_Detector_Entity_Type> \
ParameterKey=FraudDetectorEventName,ParameterValue=<Amazon_Fraud_Detector_Event_Name> \
ParameterKey=FraudDetectorName,ParameterValue=<Amazon_Fraud_Detector_Name> \
ParameterKey=KafkaInputTopic,ParameterValue=<MSK_Input_Topic_Name> \
ParameterKey=KafkaOutputTopic,ParameterValue=<MSK_Output_Topic_Name> \
ParameterKey=S3SourceCodePath,ParameterValue=lambda-functions.zip \
ParameterKey=S3connectorPath,ParameterValue=confluentinc-kafka-connect-elasticsearch-11.1.3.zip \
ParameterKey=YourEmail,ParameterValue=<Email_Address_For_Notifications> \
ParameterKey=OpenSearchMasterUsername,ParameterValue=<OpenSearch_Master_Username> \
ParameterKey=OpenSearchMasterPassword,ParameterValue=<OpenSearch_Master_User_Password>  \
--capabilities CAPABILITY_NAMED_IAM \
--region <Amazon_Fraud_Detector_Region> \
--stack-name <Stack_name>

```
Replace:

* **<S3_Bucket_name>** --> The bucket you created earlier
* **<Amazon_Fraud_Detector_Entity_Type>** --> Entity type name in Amazon Fraud Detector. E.g *customer*
* **<Amazon_Fraud_Detector_Event_Name>** --> Event type name in Amazon Fraud Detector. E.g *transaction*
* **<Amazon_Fraud_Detector_Name>** --> Entity type name in Amazon Fraud Detector. E.g *transaction_event*
* **<MSK_Input_Topic_Name>** --> Input Kafka topic name. E.g *transactions*
* **<MSK_Output_Topic_Name>** --> Output Kafka topic name. E.g *processed_transactions*. **Use the default name if you are planning on using the pre-created dashboard.**
* **<Email_Address_For_Notifications>** --> Email to receive email notifications
* **<OpenSearch_Master_Username>** --> OpenSearch master username
* **<OpenSearch_Master_User_Password>** --> OpenSearch master user password. The password needs to comply with the below requirements
    * Minimum 8 characters long.
    * Contains at least one uppercase letter, one lowercase letter, one digit, and one special character.
* **<Amazon_Fraud_Detector_Region>** -->the region used to deploy Amazon Fraud Detector. E.g. eu-west-1
* **<Stack_name>** CloudFormation stack name. The stack name must satisfy regular expression pattern: [a-z][a-z0-9\-]+. For example; *fraudblog-1*


The stack will take approximately 30 minutes to deploy.


## Post Deployment 

### Enable solution

1. Using AWS CLI, run the following command to start generating synthetic transaction data:

```

aws events enable-rule --name <EventBridge_rule_name>

```

Replace:

* **<EventBridge_rule_name>** --> The command can be retrieved from the Ouptut tab in CloudFormation console. Copy the value for *EnableEventRule* Key.


2. Now run the following command to start consuming the processed transactions and sending email notifications:

```

aws lambda update-event-source-mapping --uuid <Event_Source_mapping_UUID> --enabled


```

Replace:

* **<Event_Source_mapping_UUID>** --> The command can be retrieved from the Ouptut tab in CloudFormation console. Copy the value for *EnableEventSourceMapping* Key.


### Importing pre-created OpenSearch Dashboards

To import the pre-created dashboad, follow the steps below:

1. In AWS Cloud9 console, open the provisioned IDE environment
2. Run the following command to download dashboard.ndjson (OpenSearch Dashboard Object definition) file


```

wget https://github.com/AhmedsZamzam/realtime-fraud-prevention.git/Artifacts/dashboard.ndjson 


```

3. Run the following command generate the appropriate authorization cookies needed to import the dashboards


```

curl -X POST <OpenSearch_dashboard_link>/auth/login \
-H "osd-xsrf: true" -H "content-type:application/json" \
-d '{"username":"<OpenSearch_Master_Username>", "password" : "<OpenSearch_Master_User_Password>"} ' \
-c auth.txt

```

Replace:

* **<OpenSearch_dashboard_link>** --> Opensearch Dashboard Link including the trailing */_dashboards*. Could be retrieved from the Ouptut tab in CloudFormation console. Copy the value for *OpenSearchDashboardLink* Key.
* **<OpenSearch_Master_Username>** --> OpenSearch master username used earlier when creating the stack
* **<OpenSearch_Master_User_Password>** --> OpenSearch master user password used earlier when creating the stack

3. Run the following command generate the appropriate authorization cookies needed to import the dashboards


```

curl -XPOST <OpenSearch_dashboard_link>/api/saved_objects/_import \
-H "osd-xsrf:true" -b auth.txt --form file=@dashboard.ndjson

```
 
Replace:

* **<OpenSearch_dashboard_link>** --> Opensearch Dashboard Link

4. Now the dashboard is imported


#### Accessing OpenSearch Dashboards

OpenSearch is created in a private VPC. Therefore to access OpenSearch Dashboards, you will need to create a [Windows jump server](https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/EC2_GetStarted.html). 

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.

