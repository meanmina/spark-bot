#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import re
import os
from random import choice
from bot_helpers import MENTION_REGEX, PERSON_ID, create_message, list_memberships
from dominion import Dominion


cmd_list = []

INSULTS = [
    'has eyes like a pug\'s eyes - oversized, dry and susceptible to ulcers',
    'has a spine like a pug\'s spine - rounded and likely to cause back pain',
    'has a nose like a pugs\'s nose - barely able to allow air to pass through',
    'has a brain like a pug\'s brain - likely to get encephalitis, have seizures and cause death',
]


def cmd(regex, tag=False):
    def cmd_decorator(fn):
        def inner(obj, text, **kwargs):
            if tag:
                if PERSON_ID not in text:
                    return
            text = re.sub(PERSON_ID, '', text).strip()
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
        '##Help\n'
        '####Setup\n'
        'Use the following commands for game setup by tagging the bot in the message\n'
        '* **help**: Show this message\n'
        '* **new**: Create a new game - currently does nothing\n'
        '####In Progress\n'
        'In play you not longer need to tag the bot\n'
        '* **smack** <tag>: Send and insult\n'
    )

    def __init__(self, db_conn):
        self.admin_room = os.environ['ADMIN_ROOM']
        self.send_message(self.admin_room, 'Hello')

        self.db_cur = db_conn.cursor()

    def parse_message(self, message):
        ''' parse a generic message from spark '''
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
        else:
            print(message)
            text = message.get('text')
            print(text)

        print('Saw message - {}'.format(text))
        for func in cmd_list:
            func(self, text, room=room, sender=sender)

    def send_message(self, room, text, markdown=False):
        data = {'roomId': room}
        if markdown:
            data['markdown'] = text
        else:
            data['text'] = text
        create_message(data=data)

    # example of a command decorator
    # use regex to match a message, groups with be passed in as *args
    @cmd('(?i)help', tag=True)
    def send_help(self, room, **kwargs):
        self.send_message(room, self.help_text, markdown=True)

    @cmd('(?i)new', tag=True)
    def create_game(self, room, **kwargs):
        if room in self.games:
            self.send_message(room, 'Game already in {}'.format(self.games[room].state))
        else:
            self.games[kwargs.get('room')] = Dominion(admin=kwargs.get('sender'))

    @cmd('(?i)smack ([\w ]*)')
    def smack(self, target, room, **kwargs):
        data = {'roomId': room}
        people = list_memberships(data=data)
        for person in people['items']:
            name = person.get('personDisplayName')
            print(name)
            print(person['personId'])
            if target == name or target == person['personId']:
                self.send_message(room, '{} {}'.format(name, choice(INSULTS)))
                break
        else:
            self.send_message(room, 'It\'s rude to talk about people behind their back')
