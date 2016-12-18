'''
    some useful spark bot suff
'''
import os
import requests
import json

API_TEMPLATE = 'https://api.ciscospark.com/v1/{}'
MENTION_REGEX = r'<spark-mention.*?data-object-id="(\w+)".*?spark-mention>'
PERSON_ID = os.environ['PERSON_ID']
HEADERS = {
    "Authorization": "Bearer {}".format(os.environ['TOKEN']),
    "Content-Type": "application/json; charset=utf-8"
}

# To read messages other than those in which the bot is mentioned
ADMIN_HEADERS = {
    "Authorization": "Bearer {}".format(os.environ['ADMIN_TOKEN']),
}

PREFIX = 'https://api.ciscospark.com/v1/'


def get_person_info(person_id):
    r = requests.get(
        API_TEMPLATE.format('people/' + person_id),
        headers=ADMIN_HEADERS
    )
    return json.loads(r.text)


def get_message_info(message_id):
    r = requests.get(
        API_TEMPLATE.format('messages/' + message_id),
        headers=ADMIN_HEADERS
    )
    return json.loads(r.text)


def send_message(room, text, markdown=False, direct=False):
    if direct:
        data = {'toPersonId': room}
    else:
        data = {'roomId': room}
    if markdown:
        data['markdown'] = text
    else:
        data['text'] = text
    return requests.post(
        API_TEMPLATE.format('messages'),
        json=data,
        headers=HEADERS,
    )


def list_messages(room_id, limit=None):
    params = {'roomId': room_id}
    if limit is not None:
        params['max'] = limit

    r = requests.get(
        API_TEMPLATE.format('messages'),
        params=params,
        headers=ADMIN_HEADERS,
    )
    return json.loads(r.text)


def list_memberships(room_id):
    r = requests.get(
        API_TEMPLATE.format('memberships'),
        params={'roomId': room_id},
        headers=ADMIN_HEADERS,
    )
    return json.loads(r.text)
