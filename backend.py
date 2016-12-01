#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import re
from bot_helpers import MENTION_REGEX, PERSON_ID, create_message


class MessageHandler:
    ''' handles spark messages '''

    help_text = (
        '#  Help'
        '* There is no help for this template\n'
    )

    # regex for commands
    help_pattern = '(?i)\help'

    def __init__(self, api_calls):
        self.api_calls = api_calls

    def parse_message(self, message):
        ''' parse a generic message from spark '''
        room = message.get('roomId')
        sender = message.get('personId')
        html = message.get('html')

        # possible check for missing fields
        if None in [room, sender, html]:
            pass

        # swap all mentions for the person_id
        text = re.sub(MENTION_REGEX, '\g<1>', html)

        # remove mentions of the bot and strip whitespace
        text = re.sub(PERSON_ID, '', text).strip()

        print('Saw message - {}'.format(text))

        # help message
        if re.match(self.help_pattern, text):
            self.send_message(room, self.help_text, markdown=True)

    def send_message(self, room, text, markdown=False):
        data = {'roomId': room}
        if markdown:
            data['markdown'] = text
        else:
            data['text'] = text
        create_message(data=data)
