#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import re
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
        '#  Help'
        '* There is no help for this template\n'
    )

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
        for func in cmd_list:
            func(self, text, room=room, sender=sender)

    @cmd('(?i)help')
    def send_help(self, **kwargs):
        self.send_message(kwargs.get('room'), self.help_text, markdown=True)

    def send_message(self, room, text, markdown=False):
        data = {'roomId': room}
        if markdown:
            data['markdown'] = text
        else:
            data['text'] = text
        create_message(data=data)
