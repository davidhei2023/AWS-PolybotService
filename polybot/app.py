import time
import flask
import os
import json
import boto3
import botocore
import botocore.session
from bot import ObjectDetectionBot
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig
import requests

aws_region = os.environ.get('AWS_REGION', 'us-east-2')

client = botocore.session.get_session().create_client('secretsmanager', region_name=aws_region)
cache_config = SecretCacheConfig()
cache = SecretCache(config=cache_config, client=client)

TELEGRAM_TOKEN_SECRET = cache.get_secret_string('davidhei-telegram-token')
TELEGRAM_TOKEN = json.loads(TELEGRAM_TOKEN_SECRET).get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("The TELEGRAM_TOKEN could not be found in the secrets manager.")

TELEGRAM_APP_URL = os.environ.get('TELEGRAM_APP_URL')
if not TELEGRAM_APP_URL:
    raise ValueError("The TELEGRAM_APP_URL environment variable is not set.")

# print(f"TELEGRAM_APP_URL: {TELEGRAM_APP_URL}")
# print(f"TELEGRAM_TOKEN: {TELEGRAM_TOKEN[:5]}{'*' * (len(TELEGRAM_TOKEN) - 5)}")

app = flask.Flask(__name__)

dynamodb = boto3.resource('dynamodb', region_name=aws_region)
table_name = os.environ.get('DYNAMODB_TABLE_NAME')
if not table_name:
    raise ValueError("The DYNAMODB_TABLE_NAME environment variable is not set.")
table = dynamodb.Table(table_name)


# Flask routes
@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = flask.request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


@app.route(f'/results', methods=['POST'])
def results():
    if os.environ.get('TEST_MODE'):
        # If TEST_MODE is set, return a mock response
        return 'Test mode active. No actual results.', 200

    prediction_id = flask.request.args.get('predictionId')
    response = table.get_item(Key={'prediction_id': prediction_id})
    if 'Item' in response:
        item = response['Item']
        chat_id = item['chat_id']
        labels = item['labels']

        text_results = f"Prediction results for image {item['original_img_path']}:\n"
        for label in labels:
            text_results += f"- {label['class']} at ({label['cx']:.2f}, {label['cy']:.2f}) with size ({label['width']:.2f}, {label['height']:.2f})\n"

        bot.send_text(chat_id, text_results)
        return 'Ok'
    else:
        return 'No results found', 404


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = flask.request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)
    app.run(host='0.0.0.0', port=8443)
