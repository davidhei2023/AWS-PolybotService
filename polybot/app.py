import flask
import os
import json
from bot import ObjectDetectionBot
import botocore.session
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig

client = botocore.session.get_session().create_client('secretsmanager')
cache_config = SecretCacheConfig()
cache = SecretCache(config=cache_config, client=client)

secret_string = cache.get_secret_string('davidhei-telegram-token')
secret_json = json.loads(secret_string)
TELEGRAM_TOKEN = secret_json["TELEGRAM_TOKEN"]
TELEGRAM_APP_URL = os.environ.get('TELEGRAM_APP_URL')

print(f"TELEGRAM_TOKEN: {TELEGRAM_TOKEN}")
print(f"TELEGRAM_APP_URL: {TELEGRAM_APP_URL}")

app = flask.Flask(__name__)


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

    # TODO: Retrieve results from DynamoDB using prediction_id

    chat_id = ...
    text_results = ...

    bot.send_text(chat_id, text_results)
    return 'Ok'


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = flask.request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)
    app.run(host='0.0.0.0', port=8443)
