#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import re
import os
from bot_helpers import MENTION_REGEX, PERSON_ID, create_message


cmd_list = []


def cmd(regex):
    def cmd_decorator(fn):
        def inner(obj, text, **kwargs):
            match = re.match(regex, text)
            if not match:
                print('no match with {}'.format(regex))
                return
            return fn(obj, *match.groups(), **kwargs)
        cmd_list.append(inner)
        return inner
    return cmd_decorator


class MessageHandler:
    ''' handles spark messages '''

    help_text = (
        '###Help\n'
        '1 cluck [options]            Order chicken\n'
        '2 bukaa                      See the list of order options\n'
        '3 paid <£X> for chicken      Indicate that you paid money in RFC\n'
        '4 paid <£X> to <person>      Indicate you paid money to a person (must use mentions)\n'
        '5 help                       Display this message'
    )

    orders_text = (
        '###Menu\n'
        '1 -m=<meal>       t=tower, f=fillet, p=popcorn\n'
        '2 -s              spicy flag, include if you want a spicy burger (ignored if -m=p)\n'
        '3 -d=<drink>      can of choice\n'
        '4 -no_wings       no wings for this order (default is to have wings)'
    )

    def __init__(self, db_conn):
        self.admin_room = os.environ['ADMIN_ROOM']
        self.send_message(self.admin_room, 'Hello')

        self.db_cur = db_conn.cursor()

    def parse_message(self, message):
        ''' parse a generic message from spark '''
        print('Saw message - {}'.format(message))
        room = message.get('roomId')
        sender = message.get('personId')
        if sender == PERSON_ID:
            return
        # use html if we have it (it has more information)
        if 'html' in message:
            text = message['html']
            # swap all mentions for the person_id
            text = re.sub(MENTION_REGEX, '\g<1>', text)
            # replace html paragraphs with newlines
            text = re.sub('<p>', '', text)
            text = re.sub('</p>', '\n\n', text)
            # remove mentions of the bot and strip whitespace
            text = re.sub(PERSON_ID, '', text).strip()
        else:
            text = message.get('text')

        print('message text - {}'.format(text))
        for func in cmd_list:
            func(self, text, room=room, sender=sender)

    # example of a command decorator
    # use regex to match a message, groups with be passed in as *args
    @cmd('(?i)help')
    def send_help(self, **kwargs):
        self.send_message(kwargs.get('room'), self.help_text, markdown=True)

    @cmd('(?i)bukaa')
    def odering_info(self, **kwargs):
        self.send_message(kwargs.get('room'), self.help_text, markdown=True)

    @cmd('(?i)cluck -m=(\w+)([ -=\w]*)')
    def order(self, meal, *args, **kwargs):
        self.send_message(
            kwargs.get('room'),
            'You ordered {} with args {}'.format(meal, args),
        )

    def send_message(self, room, text, markdown=False):
        data = {'roomId': room}
        if markdown:
            data['markdown'] = text
        else:
            data['text'] = text
        create_message(data=data)
