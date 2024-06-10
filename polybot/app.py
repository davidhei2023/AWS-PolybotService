import flask
import os
import json
import boto3
from bot import ObjectDetectionBot
import botocore.session
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig

aws_region = os.environ.get('AWS_REGION', 'us-east-2')

client = botocore.session.get_session().create_client('secretsmanager', region_name=aws_region)
cache_config = SecretCacheConfig()
cache = SecretCache(config=cache_config, client=client)

secret_string = cache.get_secret_string('davidhei-telegram-token')
secret_json = json.loads(secret_string)
TELEGRAM_TOKEN = secret_json["TELEGRAM_TOKEN"]
TELEGRAM_APP_URL = os.environ.get('TELEGRAM_APP_URL')

print(f"Webhook URL: {TELEGRAM_APP_URL}")

app = flask.Flask(__name__)

dynamodb = boto3.resource('dynamodb', region_name=aws_region)
table = dynamodb.Table(os.environ['DYNAMODB_TABLE_NAME'])


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
    prediction_id = flask.request.args.get('predictionId')

    # Retrieve results from DynamoDB using prediction_id
    response = table.get_item(Key={'prediction_id': prediction_id})
    if 'Item' in response:
        item = response['Item']
        chat_id = item['chat_id']
        labels = item['labels']

        # Format text results
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
