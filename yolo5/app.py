import time
from pathlib import Path
from detect import run
import yaml
from loguru import logger
import os
import boto3
import requests
import json

images_bucket = os.environ.get('BUCKET_NAME', 'default-bucket')
queue_url = os.environ.get('SQS_QUEUE_URL', 'default-sqs-url')
dynamodb_table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'default-dynamodb-table')
polybot_results_url = os.environ.get('POLYBOT_RESULTS_URL', 'default-results-url')

sqs_client = boto3.client('sqs', region_name='us-east-2')
s3_client = boto3.client('s3', region_name='us-east-2')
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table(dynamodb_table_name)

coco_yaml_path = "data/coco128.yaml"
if not os.path.exists(coco_yaml_path):
    logger.warning(f"File '{coco_yaml_path}' not found. Creating default coco128.yaml...")

    # Create a default coco128.yaml file
    default_yaml = {
        'names': [
            'person',
            'bicycle',
            'car',
            # Add more classes as needed
        ]
    }

    with open(coco_yaml_path, 'w') as yaml_file:
        yaml.dump(default_yaml, yaml_file, default_flow_style=False)

    logger.info(f"Created default coco128.yaml at '{coco_yaml_path}'")

with open(coco_yaml_path, "r") as stream:
    names = yaml.safe_load(stream)['names']


def consume():
    while True:
        response = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=5)

        if 'Messages' in response:
            message = json.loads(response['Messages'][0]['Body'])
            receipt_handle = response['Messages'][0]['ReceiptHandle']
            prediction_id = response['Messages'][0]['MessageId']

            logger.info(f'prediction: {prediction_id}. start processing')

            img_name = message['img_name']
            chat_id = message['chat_id']
            original_img_path = f'/tmp/{img_name}'

            s3_client.download_file(images_bucket, img_name, original_img_path)
            logger.info(f'prediction: {prediction_id}/{original_img_path}. Download img completed')

            run(
                weights='yolov5s.pt',
                data=coco_yaml_path,
                source=original_img_path,
                project='static/data',
                name=prediction_id,
                save_txt=True
            )
            logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

            predicted_img_path = Path(f'static/data/{prediction_id}/{img_name}')

            s3_client.upload_file(str(predicted_img_path), images_bucket, f'predicted/{img_name}')
            logger.info(f'prediction: {prediction_id}. Uploaded predicted image to S3')

            pred_summary_path = Path(f'static/data/{prediction_id}/labels/{img_name.split(".")[0]}.txt')
            if pred_summary_path.exists():
                with open(pred_summary_path) as f:
                    labels = f.read().splitlines()
                    labels = [line.split(' ') for line in labels]
                    labels = [{
                        'class': names[int(l[0])],
                        'cx': float(l[1]),
                        'cy': float(l[2]),
                        'width': float(l[3]),
                        'height': float(l[4]),
                    } for l in labels]

                logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')

                prediction_summary = {
                    'prediction_id': prediction_id,
                    'original_img_path': original_img_path,
                    'predicted_img_path': str(predicted_img_path),
                    'labels': labels,
                    'time': time.time()
                }

                table.put_item(Item=prediction_summary)
                logger.info(f'prediction: {prediction_id}. Stored prediction summary in DynamoDB')

                response = requests.post(f'{polybot_results_url}/results', params={'predictionId': prediction_id})
                if response.status_code == 200:
                    logger.info(f'prediction: {prediction_id}. Notified Polybot microservice successfully')
                else:
                    logger.error(f'prediction: {prediction_id}. Failed to notify Polybot microservice')

            sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            logger.info(f'prediction: {prediction_id}. Deleted message from SQS queue')


if __name__ == "__main__":
    consume()
