import boto3
import json
import io
import os
import urllib.parse
from jeffy.framework import setup
from google.cloud import vision


class FullTextSearch():
    def __init__(self):
        self.client_vision = vision.ImageAnnotatorClient()
        dynamodb_table = os.environ.get('DYNAMODB_TABLE')
        resource_dynamodb = boto3.resource('dynamodb')
        self.dynamodb = resource_dynamodb.Table(dynamodb_table)
        self.s3 = boto3.client('s3')

    def get_s3_object_body(self, bucket, object_key):
        response = self.s3.get_object(
            Bucket=bucket,
            Key=object_key
        )
        return response['Body'].read()

    def detect(self, content):
        image = vision.types.Image(content=content)
        response = self.client_vision.document_text_detection(image=image)
        return response

    def extract_text(self, data):
        for page in data.full_text_annotation.pages:
            text = [symbol.text for block in page.blocks for paragraph in block.paragraphs for word in paragraph.words for symbol in word.symbols]
        return ''.join(text)

    def insert_datastore(self, words, object_key):
        with self.dynamodb.batch_writer() as batch:
            for word in list(set(words)):
                batch.put_item(
                    Item={
                        'word': word,
                        'object_key': object_key
                    }
                )
        return True

    def ngram(self, target, n):
        return [target[idx:idx + n] for idx in range(len(target) - n + 1)]


app = setup()
google_application_credentials = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
ssm_key = os.environ.get('SSM_KEY')
ssm = boto3.client('ssm')
response = ssm.get_parameters(
    Names=[
        ssm_key
    ],
    WithDecryption=True
)

if len(response['InvalidParameters']) > 0:
    app.logger.info({'response': response})
    raise Exception('InvalidParameters')

credentials = {}
for param in response['Parameters']:
    credentials[param['Name']] = param['Value']

with open(google_application_credentials, 'w') as file:
    file.write(credentials[ssm_key])


@app.decorator.auto_logging
def detect_document(event, context):
    app.logger.info({'event': event})

    s3_bucket = event['Records'][0]['s3']['bucket']['name']
    s3_object_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    app.logger.info({'s3_bucket':s3_bucket,'s3_object_key':s3_object_key})

    fts = FullTextSearch()

    s3_body = fts.get_s3_object_body(s3_bucket, s3_object_key)

    detect_data = fts.detect(s3_body)

    if detect_data.error.message:
        app.logger.info({'detect_data.error.message': detect_data.error.message})
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                detect_data.error.message))

    text = fts.extract_text(detect_data)
    app.logger.info({'text': text})

    for n in range(1, 6):
        fts.insert_datastore(fts.ngram(text, n), s3_object_key)

    return True
