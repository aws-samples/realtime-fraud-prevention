#  Real time Fraud Prevention and Visualisation using Amazon Fraud Detector

  
This repository accompanies the [Build and visualize a real-time fraud prevention system using Amazon Fraud Detector](https://aws.amazon.com/blogs/machine-learning/build-and-visualize-a-real-time-fraud-prevention-system-using-amazon-fraud-detector/) blog post. It contains **one** [AWS Cloudformation](https://aws.amazon.com/cloudformation/) template. 

The template deploys:
1. Sample transaction producer running as an [AWS Lambda Function](https://aws.amazon.com/lambda/). The function is scheduled to run every minute generating 30 transactions per minute.
2. [Amazon Managed Streaming for Apache Kafka (MSK)](https://aws.amazon.com/msk/) cluster, that contains 2 topics with default names of *transactions* and *processed_transactions*. Both topics will be automatically created by the producer and the stream processor.
3. PyFlink stream processing job that runs as an [Amazon Kinesis Data Analytics](https://aws.amazon.com/kinesis/data-analytics/) application. The job consumes each transaction as soon as it is written to the *transactions* (input) topic, invokes [Amazon Fraud Detector](https://aws.amazon.com/fraud-detector/) APIs ([GetEventPrediction](https://docs.aws.amazon.com/frauddetector/latest/api/API_GetEventPrediction.html)) in real time to generate fraud predictions and writes the outcome to *processed_transactions* (output) topic.
4. Consumer Lambda function reads data from *processed_transactions* topic and sends email notifications for transactions flagged as fraudulent by Amazon Fraud Detector.
5. Private [Amazon OpenSearch Service (successor to Amazon Elasticsearch Service)](https://aws.amazon.com/opensearch-service/) domain in a provisioned VPC. it is used to persistently stores each transaction with its corresponding fraud outcome.
6. Kafka connector running on [MSK Connect](https://aws.amazon.com/msk/features/msk-connect/) that reads processed transactions from *processed_transactions* topic and sinks the data to an OpenSearch index. Allowing us to visualise the transactions insights in real time.
7. An [AWS Cloud9](https://aws.amazon.com/cloud9/) environment to import the pre-created dashboard to OpenSearch Dashboards.



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

1. [Install Python](https://realpython.com/installing-python/) 3.8.2 or later
2. [AWS CLI already configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) with Administrator permission
3. Amazon Fraud Detector published with the following below variable names, follow [this blog](https://aws.amazon.com/blogs/machine-learning/detect-online-transaction-fraud-with-new-amazon-fraud-detector-features/) as a reference
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

## Package and upload solution artifacts.

1. Clone the repo onto your local development machine using `git clone <repo url>`.
2. Change directory to solution repository.

```

cd realtime-fraud-prevention
```

### Install Lambda functions dependencies and package code

```bash
pip3 install -r ./lambda-functions/requirements.txt -t ./lambda-functions

(cd lambda-functions; zip -r ../Artifacts/lambda-functions.zip .)
```

This will:
Install required dependencies for the Lambda functions as per requirements.txt file.
Then package all artifacts into lambda-functions.zip file that will be created under the Artifacts directory. 

### Install Kinesis Data Analytics PyFlink application dependencies and package code

```bash
pip3 install -r ./RealTimeFraudPrevention/bin/requirements.txt -t ./RealTimeFraudPrevention/lib/packages

curl https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka_2.11/1.11.2/flink-sql-connector-kafka_2.11-1.11.2.jar --output ./RealTimeFraudPrevention/lib/flink-sql-connector-kafka_2.11-1.11.2.jar

zip -r ./Artifacts/RealTimeFraudPrevention.zip ./RealTimeFraudPrevention
```

This will:
Install required dependencies for the Apache Flink application as per requirements.txt file.
Then package all artifacts into RealTimeFraudPrevention.zip file that will be created under the Artifacts directory. 

### Download Kafka connector

```bash

(cd Artifacts; curl -L -O https://d1i4a15mxbxib1.cloudfront.net/api/plugins/confluentinc/kafka-connect-elasticsearch/versions/11.1.6/confluentinc-kafka-connect-elasticsearch-11.1.6.zip)
```

### Upload solution artifacts

1. Run the following command to create a unique Amazon S3 bucket which will be used to store the solution artifacts.

Replace:
* **<S3_Bucket_name>** with your unique bucket name and 
* **<Amazon_Fraud_Detector_Region>** with the region used to deploy the Amazon Fraud Detector model ([requirement #3](https://github.com/aws-samples/realtime-fraud-prevention/blob/main/README.md#general-requirements) above). E.g. *eu-west-1* 

```

aws s3 mb s3://<S3_Bucket_name> --region <Amazon_Fraud_Detector_Region>
```


2. Run the following command to sync the solution artifacts with the newly created buckets. 

**Note: All artifacts should be stored on the bucket root**

```

aws s3 sync ./Artifacts/ s3://<S3_Bucket_name>
```

## Deploy solution

There are 2 options to deploy the solution:
1. Using AWS Console
    * Follow [Build and visualise Realtime Fraud Prevention system using Amazon Fraud Detector](https://aws.amazon.com/blogs/machine-learning/build-and-visualize-a-real-time-fraud-prevention-system-using-amazon-fraud-detector/) blog post.
2. Using AWS CLI
    * Run the following command to deploy the CloudFormation template

Replace:

* **<S3_Bucket_name>** --> The bucket you created in the upload solution artifacts step above.
* The Amazon Fraud Detector Model Output Parameters created following ([requirement #3](https://github.com/aws-samples/realtime-fraud-prevention#package-and-upload-solution-artifacts) above)
    * **<Amazon_Fraud_Detector_Entity_Type>** --> Entity type name in Amazon Fraud Detector. E.g *customer*
    * **<Amazon_Fraud_Detector_Event_Name>** --> Event type name in Amazon Fraud Detector. E.g *transaction*
    * **<Amazon_Fraud_Detector_Name>** --> Entity type name in Amazon Fraud Detector. E.g *transaction_event*
* **<MSK_Input_Topic_Name>** --> Input Kafka topic name. E.g *transactions*
* **<MSK_Output_Topic_Name>** --> Output Kafka topic name. E.g *processed_transactions*. **Use the default name if you are planning to use the pre-created dashboard.**
* **<Email_Address_For_Notifications>** --> Email to receive email notifications
* **<OpenSearch_Master_Username>** --> OpenSearch master username
* **<OpenSearch_Master_User_Password>** --> OpenSearch master user password. The password needs to comply with the below requirements
    * Minimum 8 characters long.
    * Contains at least one uppercase letter, one lowercase letter, one digit, and one of the following special characters ```+_-@^%=!£#.```.
* **<Amazon_Fraud_Detector_Region>** -->the region used to deploy Amazon Fraud Detector. E.g. eu-west-1
* **<Stack_name>** CloudFormation stack name. The stack name must satisfy the regular expression pattern: [a-z][a-z0-9\-]+ and must be less than 15 characters long. For example; *fraud-prevention*

```

aws cloudformation create-stack --template-body file://Realtime_Fraud_Prevention_CFN.yml --parameters \
ParameterKey=BucketName,ParameterValue=<S3_Bucket_name> \
ParameterKey=FraudDetectorEntityType,ParameterValue=<Amazon_Fraud_Detector_Entity_Type> \
ParameterKey=FraudDetectorEventName,ParameterValue=<Amazon_Fraud_Detector_Event_Name> \
ParameterKey=FraudDetectorName,ParameterValue=<Amazon_Fraud_Detector_Name> \
ParameterKey=KafkaInputTopic,ParameterValue=<MSK_Input_Topic_Name> \
ParameterKey=KafkaOutputTopic,ParameterValue=<MSK_Output_Topic_Name> \
ParameterKey=S3SourceCodePath,ParameterValue=lambda-functions.zip \
ParameterKey=S3connectorPath,ParameterValue=confluentinc-kafka-connect-elasticsearch-11.1.6.zip \
ParameterKey=YourEmail,ParameterValue=<Email_Address_For_Notifications> \
ParameterKey=OpenSearchMasterUsername,ParameterValue=<OpenSearch_Master_Username> \
ParameterKey=OpenSearchMasterPassword,ParameterValue=<OpenSearch_Master_User_Password>  \
--capabilities CAPABILITY_NAMED_IAM \
--region <Amazon_Fraud_Detector_Region> \
--stack-name <Stack_name>
```

The stack will approximately take 30 minutes to deploy.


### Enable solution

Using AWS CLI, make sure you are at the same region used while deployment.

1. To start generating synthetic transaction data:

    * Run the command that can be retrieved from the value of **EnableEventRule** Key in Ouptut tab in CloudFormation console, it looks like

```
aws events enable-rule --name <EventBridge_rule_name>
```

2. To start consuming the processed transactions and sending email notifications:

    * Run the command that can be retrieved from the value of **EnableEventSourceMapping** Key in Ouptut tab in CloudFormation console, it looks like

```
aws lambda update-event-source-mapping --uuid <Event_Source_mapping_UUID> --enabled
```

### Import pre-created OpenSearch Dashboards

To import the pre-created dashboad, follow the steps below:

1. In AWS Cloud9 console, open the provisioned IDE environment
2. Run the following command to download dashboard.ndjson (OpenSearch Dashboard Object definition) file


```

wget https://github.com/aws-samples/realtime-fraud-prevention/blob/main/Artifacts/dashboard.ndjson
```

3. Run the following command to generate the appropriate authorization cookies needed to import the dashboards

Replace:

* **<OpenSearch_dashboard_link>** --> Could be retrieved from the Ouptut tab in CloudFormation console. Copy the value for *OpenSearchDashboardLink* Key, including the trailing */_dashboards*.
* **<OpenSearch_Master_Username>** --> OpenSearch master username used earlier while deploying [the stack](https://github.com/aws-samples/realtime-fraud-prevention#deploy-solution).
* **<OpenSearch_Master_User_Password>** --> OpenSearch master user password used earlier while deploying [the stack](https://github.com/aws-samples/realtime-fraud-prevention#deploy-solution).

```

curl -X POST <OpenSearch_dashboard_link>/auth/login \
-H "osd-xsrf: true" -H "content-type:application/json" \
-d '{"username":"<OpenSearch_Master_Username>", "password" : "<OpenSearch_Master_User_Password>"} ' \
-c auth.txt
```



4. Run the following command that will import the dashboards

Replace:

* **<OpenSearch_dashboard_link>** --> Could be retrieved from the Ouptut tab in CloudFormation console. Copy the value for *OpenSearchDashboardLink* Key, including the trailing */_dashboards*.

```

curl -XPOST <OpenSearch_dashboard_link>/api/saved_objects/_import \
-H "osd-xsrf:true" -b auth.txt --form file=@dashboard.ndjson
```


## Accessing OpenSearch Dashboards

OpenSearch is created in a private VPC. Therefore to access OpenSearch Dashboards, you will need to create a Windows jump server **in the public subnet of the provisioned VPC**. 

1. Open the Amazon EC2 console at [https://console.aws.amazon.com/ec2/](https://console.aws.amazon.com/ec2/)
    * Make sure you are at the correct AWS region, used earlier to deploy the solution.
3. From the console dashboard, choose *Launch Instance*.
4. Step 1: Choose an Amazon Machine Image (AMI)
    * Select Microsoft Windows Server 2019 Base. Notice that this AMI is marked "Free tier eligible."
5. Step 2: Choose an Instance Type
    * Select The t2.micro instance type. It is eligible for the free tier. 
    * *In Regions where t2.micro is unavailable, you can use a t3.micro instance under the free tier.*
6. Step 3: Configure Instance Details
    * Network: Select the provisioned VPC, it will look like ```vpc_<ID> | <CloudFormation Stack Name> ```.
    * Subnet: Select the public subnet of the provisioned VPC, it will look like ``` subnet_<ID> | <CloudFormation Stack Name>-public-subnet ```.
    * Scroll down and expand Advanced Details: in User data, paste the following command to install Google Chrome.
```

<powershell>
$Path = $env:TEMP; $Installer = "chrome_installer.exe"; Invoke-WebRequest "http://dl.google.com/chrome/chrome_installer.exe" -OutFile $Path\$Installer; Start-Process -FilePath $Path\$Installer -Args "/silent /install" -Verb RunAs -Wait; Remove-Item $Path\$Installer
</powershell>
```
  
6. Click *Review and Launch* then *Launch*.
7. When prompted for a key pair, select create a new pair
      * Key pair type: Choose *RSA*.
      * Key pair name: Give a name for the key.
      * Download Key Pair, Save .pem file in a safe location in your local machine.
      * Click *Launch Instances*.
8. Click View Instances, It can take a few minutes for the instance to be ready so that you can connect to it. Check that your instance has passed its status checks.

9. Follow the instructions in the [connect to EC2 instance tutorial to connect to your Windows instance using an RDP client](https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/EC2_GetStarted.html#ec2-connect-to-instance-windows)
  
10. Open Google Chrome and paste the link of the OpenSearchDashboard that can be retrieved from the value of **OpenSearchDashboardLink** Key in Ouptut tab in CloudFormation console, it will look like ```https://vpc-<opensearch_name>-<opensearch_ID>.<region>.es.amazonaws.com/_dashboards```
  
11. On the OpenSearch login console, enter the Username and Password used while creating CloudFormation Template
    * **<OpenSearch_Master_Username>** --> OpenSearch master username.
    * **<OpenSearch_Master_User_Password>** --> OpenSearch master user password.

12. In the navigation pane, choose Dashboard. 
A new sample fraud detection dashboard opens, which is updated in real time.


13. **[Optional]** Follow the instructions in the [clean EC2 instance tutorial to effectively terminate an instance which also deletes it](https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/EC2_GetStarted.html#ec2-clean-up-your-instance)

  ## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.

