'''
    some useful spark bot suff
'''
import os
import requests
import json

MENTION_REGEX = r'<spark-mention.*?data-object-id="(\w+)".*?spark-mention>'
PERSON_ID = os.environ['PERSON_ID']
HEADERS = {"Authorization": "Bearer {}".format(os.environ['TOKEN'])}

# To read messages other than those in which the bot is mentioned
ADMIN_HEADERS = {"Authorization": "Bearer {}".format(os.environ['ADMIN_TOKEN'])}


def get_person_info(person_id):
    r = requests.get(
        'https://api.ciscospark.com/v1/people/{}'.format(person_id),
        headers=ADMIN_HEADERS
    )
    return json.loads(r.text)


def get_message_info(message_id):
    r = requests.get(
        'https://api.ciscospark.com/v1/messages/{}'.format(message_id),
        headers=ADMIN_HEADERS
    )
    return json.loads(r.text)


def create_message(data):
    return requests.post(
        'https://api.ciscospark.com/v1/messages',
        data=data,
        headers=HEADERS
    )
