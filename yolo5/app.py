import os
import boto3
import botocore
import requests
import json
import time
from pathlib import Path
from decimal import Decimal
from loguru import logger
from detect import run

AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')
POLYBOT_RESULTS_URL = os.getenv('POLYBOT_RESULTS_URL')

sqs_client = boto3.client('sqs', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

table = dynamodb.Table(DYNAMODB_TABLE_NAME)
coco_yaml_path = 'data/coco128.yaml'
names = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light', 
         'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 
         'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 
         'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 
         'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 
         'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 
         'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 
         'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 
         'teddy bear', 'hair drier', 'toothbrush']


def consume():
    while True:
        response = sqs_client.receive_message(QueueUrl=SQS_QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=5)

        if 'Messages' in response:
            message = json.loads(response['Messages'][0]['Body'])
            receipt_handle = response['Messages'][0]['ReceiptHandle']
            prediction_id = response['Messages'][0]['MessageId']

            logger.info(f'prediction: {prediction_id}. start processing')

            img_name = message['img_name']
            chat_id = message['chat_id']
            original_img_path = f'/tmp/{img_name}'

            try:
                s3_client.download_file(S3_BUCKET_NAME, img_name, original_img_path)
                logger.info(f'prediction: {prediction_id}/{original_img_path}. Download img completed')
            except boto3.exceptions.S3UploadFailedError as e:
                logger.error(f'Failed to download image from S3: {str(e)}')
                continue
            except botocore.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                if (error_code == '403'):
                    logger.error(f'Access denied to S3 object: {img_name}. Check your S3 bucket policy and IAM role permissions.')
                else:
                    logger.error(f'ClientError while accessing S3 object: {str(e)}')
                continue

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

            s3_client.upload_file(str(predicted_img_path), S3_BUCKET_NAME, f'predicted/{img_name}')
            logger.info(f'prediction: {prediction_id}. Uploaded predicted image to S3')

            pred_summary_path = Path(f'static/data/{prediction_id}/labels/{img_name.split(".")[0]}.txt')
            if pred_summary_path.exists():
                with open(pred_summary_path) as f:
                    labels = f.read().splitlines()
                    labels = [line.split(' ') for line in labels]

                # Debugging: Log the labels
                logger.debug(f'Labels: {labels}')

                try:
                    labels = [{
                        'class': names[int(l[0])],
                        'cx': Decimal(l[1]),
                        'cy': Decimal(l[2]),
                        'width': Decimal(l[3]),
                        'height': Decimal(l[4]),
                    } for l in labels]
                except IndexError as e:
                    logger.error(f'IndexError while processing labels: {str(e)}')
                    logger.error(f'Problematic labels: {labels}')
                    continue

                logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')

                prediction_summary = {
                    'prediction_id': prediction_id,
                    'original_img_path': original_img_path,
                    'predicted_img_path': str(predicted_img_path),
                    'labels': labels,
                    'time': Decimal(str(time.time())),  # Convert float time to Decimal
                    'chat_id': chat_id
                }

                table.put_item(Item=prediction_summary)
                logger.info(f'prediction: {prediction_id}. Stored prediction summary in DynamoDB')

                try:
                    response = requests.post(f'{POLYBOT_RESULTS_URL}', params={'predictionId': prediction_id})
                    response.raise_for_status()  # Raise an error for bad status codes
                    logger.info(f'prediction: {prediction_id}. Notified Polybot microservice successfully')
                except requests.exceptions.RequestException as e:
                    logger.error(f'prediction: {prediction_id}. Failed to notify Polybot microservice. Error: {str(e)}')
                    if response is not None:
                        logger.error(f'Response status code: {response.status_code}')
                        logger.error(f'Response text: {response.text}')

            sqs_client.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
            logger.info(f'prediction: {prediction_id}. Deleted message from SQS queue')


if __name__ == "__main__":
    consume()
