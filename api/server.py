#!/usr/bin/python3
'''
    Backend webapi for the ll bot
'''
from bottle import Bottle, abort
from backend import MessageHandler
from .bottle_helpers import webapi, picture
from bot_helpers import get_message_info


class Server:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.last_message = None
        self.backend = MessageHandler()
        self._app = Bottle()

    def start(self):
        ''' start the server '''
        self._app.run(host=self.host, port=self.port)

    @webapi('POST', '/messages')
    def get_messages(self, data):
        ''' Receive a message from a spark webhook '''
        try:
            message_id = data['data']['id']
        except KeyError:
            abort(400, 'expected message id')

        message_info = get_message_info(message_id)
        try:
            self.backend.parse_message(message_info)
        except Exception as err:
            print(err)

    @picture('/images/avatar')
    def letter_pic(self):
        ''' picture to use for the dominion bot image '''
        return 'dominion.jpg'
