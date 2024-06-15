FROM ultralytics/yolov5:latest-cpu
WORKDIR /usr/src/app
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN curl -L https://github.com/ultralytics/yolov5/releases/download/v6.1/yolov5s.pt -o yolov5s.pt

ENV S3_BUCKET_NAME="davidhei-aws-polybotservice-bucket"
ENV SQS_QUEUE_URL="https://sqs.us-east-2.amazonaws.com/019273956931/davidhei-AWS-polybot-SQS"
ENV DYNAMODB_TABLE_NAME="davidhei-AWS-polybot-DynamoDB-table"
ENV POLYBOT_RESULTS_URL="https://davidhei-polybot.int-devops.click/results"
ENV AWS_REGION="us-east-2"

EXPOSE 80

COPY . .

CMD ["python3", "app.py"]
