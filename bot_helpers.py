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


def create_message(data):
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


def create_webhook(room_id=None):
    params = {
        'targetUrl': 'https://kernel-sanders.herokuapp.com/messages',
        'resource': 'messages',
        'event': 'created',
        'secret': 'finger licking good',
    }
    if room_id is not None:
        # creating a webhook from a room is done with admin's account
        headers = ADMIN_HEADERS
        params['name'] = room_id
        params['filter'] = 'roomId={}'.format(room_id)
    else:
        # creating a generic webhook is done with bot's account
        headers = HEADERS
        params['name'] = 'mentions'

    return requests.post(
        API_TEMPLATE.format('webhooks'),
        json=params,
        headers=headers,
    )


def check_own_webhook():
    r = requests.get(
        API_TEMPLATE.format('webhooks'),
        headers=HEADERS,
    )
    hooks = [hook['name'] for hook in json.loads(r.text)['items']]
    return 'mentions' in hooks
