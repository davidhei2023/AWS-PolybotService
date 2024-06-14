import flask
import os
import json
import boto3
from bot import ObjectDetectionBot
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig

aws_region = os.environ.get('AWS_REGION', 'us-east-2')

client = boto3.session.Session().client(service_name='secretsmanager', region_name=aws_region)
cache_config = SecretCacheConfig()
cache = SecretCache(config=cache_config, client=client)

try:
    TELEGRAM_TOKEN_SECRET = cache.get_secret_string('davidhei-telegram-token')
    TELEGRAM_TOKEN = json.loads(TELEGRAM_TOKEN_SECRET).get("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        raise ValueError("The TELEGRAM_TOKEN could not be found in the secrets manager.")
except Exception as e:
    print(f"Error retrieving TELEGRAM_TOKEN from Secrets Manager: {str(e)}")
    raise

TELEGRAM_APP_URL = os.environ.get('TELEGRAM_APP_URL')
if not TELEGRAM_APP_URL:
    raise ValueError("The TELEGRAM_APP_URL environment variable is not set.")

dynamodb = boto3.resource('dynamodb', region_name=aws_region)
table_name = os.environ.get('DYNAMODB_TABLE_NAME')
if not table_name:
    raise ValueError("The DYNAMODB_TABLE_NAME environment variable is not set.")
table = dynamodb.Table(table_name)

sqs_client = boto3.client('sqs', region_name=aws_region)
sqs_queue_url = os.environ.get('SQS_QUEUE_URL')
if not sqs_queue_url:
    raise ValueError("The SQS_QUEUE_URL environment variable is not set.")

app = flask.Flask(__name__)

# Flask routes
@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    try:
        req = flask.request.get_json()
        bot.handle_message(req['message'])
        return 'Ok'
    except Exception as e:
        print(f"Error handling webhook request: {str(e)}")
        return 'Error', 500


@app.route(f'/results', methods=['POST'])
def results():
    try:
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
    except Exception as e:
        print(f"Error processing results: {str(e)}")
        return 'Error', 500


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    try:
        req = flask.request.get_json()
        bot.handle_message(req['message'])
        return 'Ok'
    except Exception as e:
        print(f"Error handling load test: {str(e)}")
        return 'Error', 500


if __name__ == "__main__":
    try:
        bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL, sqs_queue_url, aws_region)
        app.run(host='0.0.0.0', port=8443)
    except Exception as e:
        print(f"Error starting Flask application: {str(e)}")
