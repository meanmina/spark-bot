'''
    some useful spark bot suff
'''
import requests
import json

MENTION_REGEX = r'<spark-mention.*?data-object-id="(\w+)".*?spark-mention>'
PERSON_ID = ''  # Your bot person ID


class SparkApi:
    ''' class for adding headers to an api call '''

    def __init__(self, headers):
        self.headers = headers

    def get_person_info(self, person_id):
        r = requests.get(
            'https://api.ciscospark.com/v1/people/{}'.format(person_id),
            headers=self.headers
        )
        return json.loads(r.text)

    def get_message_info(self, message_id):
        r = requests.get(
            'https://api.ciscospark.com/v1/messages/{}'.format(message_id),
            headers=self.headers,
        )
        return json.loads(r.text)

    def create_message(self, data):
        return requests.post(
            'https://api.ciscospark.com/v1/messages',
            data=data,
            headers=self.headers
        )
