#!/usr/bin/python3
'''
    Backend webapi for the ll bot
'''
from bottle import Bottle, abort
from backend import MessageHandler
from .bottle_helpers import webapi, picture
from bot_helpers import SparkApi


class Server:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.last_message = None
        self.token_set = False
        self._app = Bottle()

    def start(self):
        ''' start the server '''
        self._app.run(host=self.host, port=self.port)

    @webapi('POST', '/messages')
    def get_messages(self, data):
        ''' Receive a message from a spark webhook '''
        if not self.token_set:
            abort(503, 'Bot has no access token')

        try:
            message_id = data['data']['id']
        except KeyError:
            abort(400, 'expected message id')

        message_info = self.api_calls.get_message_info(message_id)
        try:
            self.backend.parse_message(message_info)
        except Exception as err:
            print(err)

    @webapi('POST', '/token')
    def set_token(self, data):
        ''' set the spark bearer token, this is also the point we init the backend '''
        access_token = data.get('token', '')
        headers = {"Authorization": "Bearer {}".format(access_token)}
        self.api_calls = SparkApi(headers)
        self.backend = MessageHandler(self.api_calls)
        self.token_set = True

    # example of serving up an image
    @picture('/images/letter')
    def letter_pic(self):
        ''' picture of a letter (uses by the ll game) '''
        # name of an image in ./images/
        return 'letter_big.jpg'
