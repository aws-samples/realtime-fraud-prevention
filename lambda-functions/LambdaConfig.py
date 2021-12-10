# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import datetime
import json
import os
import random
from time import sleep
from datetime import datetime
import cfnresponse
import logging


msk = boto3.client("kafka")
kda = boto3.client('kinesisanalyticsv2')
connect = boto3.client('kafkaconnect')

def lambda_handler(event, context):
    
    
    stack_name = os.environ["stackname"]

    # Logic to handle Stack delete
    
    if event["RequestType"] == 'Delete':

        try:
            # List All connectors with the stackName as the prefix and get the ARN of the connector

            response = connect.list_connectors(connectorNamePrefix=stack_name)
            connectorArn=response['connectors'][0]['connectorArn']

            #Delete the connector
            response = connect.delete_connector(connectorArn=connectorArn)

            # Wait for 60 seconds for the connector to get deleted. Otherwise this Lambda function will get deleted before recieving a response

            sleep(60)
        
        except Exception as e:
            logging.error('Exception: %s' % e, exc_info=True)

        # Return Results

        #Send success message to CFn to continue deleting the stack

        status = cfnresponse.SUCCESS
        cfnresponse.send(event, context, status, {})
        
    else:
    
        print('Received event: %s' % json.dumps(event))
        status = cfnresponse.SUCCESS

        # Get Env variables
    
        msk_cluster_arn = os.environ["mskClusterArn"]
    
        msk_response_bootstrap = msk.get_bootstrap_brokers(ClusterArn=msk_cluster_arn)
        bootstrap_servers=msk_response_bootstrap["BootstrapBrokerStringTls"]
        
        kda_name = os.environ["kdaName"]
        subnet_1 = os.environ["subnet1"]
        subnet_2 = os.environ["subnet2"]
        sg_id = os.environ["sgID"]

        aws_account = os.environ["awsAccount"]
        aws_region = os.environ["awsRegion"]
        opensearch_username = os.environ["opensearchUsername"]
        opensearch_password = os.environ["opensearchPassword"]
        opensearch_endpoint = os.environ["opensearchDomainEndpoint"]
        file_key = os.environ["s3connectorkey"]
        connector_role_arn= os.environ["mskconnectRole"]
        processed_topic=os.environ["topic"]
        mskconnect_log_group=os.environ["logGroupName"]
    
    
    
        #kda = f"arn:aws:kinesisanalytics:{aws_region}:{aws_account}:application/{kda_name}"]

        # Get current version of MSK cluster
        
        msk_response_describe = msk.describe_cluster(ClusterArn=msk_cluster_arn)
        msk_current_version= msk_response_describe["ClusterInfo"]["CurrentVersion"]
    
    
        try:

            # Create MSK config to enable automatic topic creation
    
            msk_response_create = msk.create_configuration(
            Name=f'{stack_name}-msk-config',
            Description='The configuration to use on blog MSK clusters.',
            KafkaVersions=['2.2.1'],
            ServerProperties=b"auto.create.topics.enable = true")
    
            configuration_arn = msk_response_create["Arn"]
            configuration_revision = msk_response_create["LatestRevision"]["Revision"]


            # Update MSK Cluster config to use the newly created Config
    
            msk_response_update = msk.update_cluster_configuration(
            ClusterArn=msk_cluster_arn,
            ConfigurationInfo={
                'Arn': configuration_arn,
                'Revision': configuration_revision
            },
            CurrentVersion=msk_current_version)

            #################################################
            # Describe KDA application to get the exsisting properties of the application and current version ID
    
            kda_response_describe = kda.describe_application(ApplicationName=kda_name)
            current_application_version_Id =kda_response_describe["ApplicationDetail"]["ApplicationVersionId"]


            # Add VPC config to the current application version
    
            kda_response_vpc = kda.add_application_vpc_configuration(
            ApplicationName=kda_name,
            CurrentApplicationVersionId=current_application_version_Id,
            VpcConfiguration={
                'SubnetIds': [
                    subnet_1,subnet_2
                ],
                'SecurityGroupIds': [sg_id]
            })
            
            # Update the application properties to add bootstrap_servers
            
            
            kda_response_describe = kda.describe_application(ApplicationName=kda_name)
            current_application_version_Id =kda_response_describe["ApplicationDetail"]["ApplicationVersionId"]
            s3_bucket_arn = kda_response_describe["ApplicationDetail"]["ApplicationConfigurationDescription"]["ApplicationCodeConfigurationDescription"]["CodeContentDescription"]["S3ApplicationCodeLocationDescription"]["BucketARN"]
            
            properties = kda_response_describe["ApplicationDetail"]["ApplicationConfigurationDescription"]["EnvironmentPropertyDescriptions"]["PropertyGroupDescriptions"]
            properties[1]["PropertyMap"]["bootstrap.servers"]=bootstrap_servers
            
            kda_response_bootstrap = kda.update_application(
            ApplicationName=kda_name,
            CurrentApplicationVersionId=current_application_version_Id,
            ApplicationConfigurationUpdate={
                'ApplicationCodeConfigurationUpdate': {
                    'CodeContentTypeUpdate': 'ZIPFILE',
                    'CodeContentUpdate': {
                        'S3ContentLocationUpdate': {
                            'BucketARNUpdate': s3_bucket_arn,
                            'FileKeyUpdate': 'RealTimeFraudPrevention.zip'
                        }
                    }
                },
                'EnvironmentPropertyUpdates': {
                    'PropertyGroups': properties
                    }
            })


            # Start KDA application
    
    
            kda_response_start = kda.start_application(
            ApplicationName=kda_name,
            RunConfiguration={
                'FlinkRunConfiguration': {
                    'AllowNonRestoredState': True
                },
                'ApplicationRestoreConfiguration': {
                    'ApplicationRestoreType': 'SKIP_RESTORE_FROM_SNAPSHOT'
                }
            })


            ######################################################################
            # MSK Connect


            # Create Custom plugin to be used by the connector. Custom plugin is created using the opensource Confluent ElasticSearch Connector 
    
            plugin_name = f'{stack_name}-osplugin'
            connect_response_create_pl = connect.create_custom_plugin(
            contentType='ZIP',
            location={
                's3Location': {
                    'bucketArn': s3_bucket_arn,
                    'fileKey': file_key,
                    }
                },
            name=plugin_name)

            # Wait for custom plugin to be created
    
            sleep(45)


            # Create connector passing details from the Stack
            #   1- sink details (opensearch domain endpoint, opensearch username, opensearch passord)
            #   2- bootstrap_servers and topic to read from
            #   3- Networking delails - same VPC, subnet and SG as MSK Cluster
            #   4- Enabling logging and Cloudwatch Log Group
            #   5- Custom plugin created earlier
            #   6- IAM Role for MSK connect cluster
    
            connect_responsecreate_con = connect.create_connector(
            capacity={
                'autoScaling': {
                    'maxWorkerCount': 2,
                    'mcuCount': 1,
                    'minWorkerCount': 1,
                    'scaleInPolicy': {
                        'cpuUtilizationPercentage': 20
                    },
                    'scaleOutPolicy': {
                        'cpuUtilizationPercentage': 80
                    }
                }
            },
            connectorConfiguration={
                "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
                "connection.username": opensearch_username,
                "connection.password": opensearch_password,
                "tasks.max": "1",
                "topics": processed_topic,
                "key.ignore": "true",
                "connection.url": f'https://{opensearch_endpoint}:443',
                "schema.ignore": "true",
                "elastic.security.protocol":"SSL",
                "elastic.https.ssl.protocol":"TLSv1.2",
                "value.converter": "org.apache.kafka.connect.json.JsonConverter",
                "key.converter": "org.apache.kafka.connect.storage.StringConverter",
                "value.converter.schemas.enable": "false",
                "name": f'{stack_name}-os-sink'
            },
            connectorDescription='os-sink',
            connectorName=f'{stack_name}-os-sink',
            kafkaCluster={
                'apacheKafkaCluster': {
                    'bootstrapServers': bootstrap_servers,
                    'vpc': {
                        'securityGroups': [sg_id],
                        'subnets': [
                            subnet_1,subnet_2
                        ]
                    }
                }
            },
            kafkaClusterClientAuthentication={
                'authenticationType': 'NONE'
            },
            kafkaClusterEncryptionInTransit={
                'encryptionType': 'TLS'
            },
            kafkaConnectVersion='2.7.1',
            logDelivery={
                'workerLogDelivery': {
                    'cloudWatchLogs': {
                        'enabled': True,
                        'logGroup': mskconnect_log_group
                    }
                }
            },
            plugins=[
                {
                    'customPlugin': {
                        'customPluginArn': connect_response_create_pl["customPluginArn"],
                        'revision': 1
                    }
                },
            ],
            serviceExecutionRoleArn=connector_role_arn)

        # Catch errors
    
        except Exception as e:
            logging.error('Exception: %s' % e, exc_info=True)
            status = cfnresponse.FAILED

        # Send response to CFN to continue with Stack creation or rollback
    
        cfnresponse.send(event, context, status, {})
