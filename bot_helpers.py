'''
    some useful spark bot suff
'''
import os
import requests
import json

MENTION_REGEX = r'<spark-mention.*?data-object-id="(\w+)".*?spark-mention>'
PERSON_ID = os.environ['PERSON_ID']
HEADERS = {"Authorization": "Bearer {}".format(os.environ['TOKEN'])}


def get_person_info(self, person_id):
    r = requests.get(
        'https://api.ciscospark.com/v1/people/{}'.format(person_id),
        headers=HEADERS
    )
    return json.loads(r.text)

def get_message_info(self, message_id):
    r = requests.get(
        'https://api.ciscospark.com/v1/messages/{}'.format(message_id),
        headers=HEADERS
    )
    return json.loads(r.text)

def create_message(self, data):
    return requests.post(
        'https://api.ciscospark.com/v1/messages',
        data=data,
        headers=HEADERS
    )
