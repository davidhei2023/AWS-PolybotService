FROM python:3.10-alpine
WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install -r requirements.txt

ENV TELEGRAM_APP_URL="https://davidhei-polybot.int-devops.click"
ENV DYNAMODB_TABLE_NAME="davidhei-AWS-polybot-DynamoDB-table"
ENV POLYBOT_RESULTS_URL="https://davidhei-polybot.int-devops.click"
ENV SQS_QUEUE_URL="https://sqs.us-east-2.amazonaws.com/019273956931/davidhei-AWS-polybot-SQS"
ENV S3_BUCKET_NAME="davidhei-aws-polybotservice-bucket"
ENV AWS_REGION="us-east-2"
ENV POLYBOT_RESULTS_URL="https://davidhei-polybot.int-devops.click/results"

RUN echo '#!/bin/bash' > /print_build_info.sh \
    && echo 'echo "Docker Image Build Date and Time: $(date)"' >> /print_build_info.sh \
    && chmod +x /print_build_info.sh

EXPOSE 8443

COPY . .

CMD ["sh", "-c", "/print_build_info.sh && python app.py"]