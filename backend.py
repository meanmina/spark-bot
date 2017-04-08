#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import re
import os
from collections import defaultdict
from bot_helpers import MENTION_REGEX, PERSON_ID, create_message


cmd_list = []

MEALS = {
    't': ['tower', 4.0],
    'f': ['fillet', 3.5],
    'p': ['popcorn', 4.0],
}


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
        '1. cluck [options] --> Order chicken\n'
        '2. bukaa --> See the list of order options\n'
        '3. paid <X> for chicken --> Indicate that you '
        'paid money in RFC\n'
        '4. paid <X> to <person> --> Indicate you paid money to a person '
        '(must use mentions)\n'
        '5. show order --> Show what has been ordered so far\n'
        '6. clear order --> Clear all current orders\n'
        '7. help --> Display this message'
    )

    orders_text = (
        '###Menu\n'
        '1. -m=<meal> --> t=tower, f=fillet, p=popcorn\n'
        '2. -s --> spicy flag, include if you want a spicy burger (ignored if -m=p)\n'
        '3. -d=<drink> --> can of choice\n'
        '4. -no_wings --> no wings for this order (default is to have wings)'
    )

    def __init__(self, db_conn):
        self.admin_room = os.environ['ADMIN_ROOM']
        self.send_message(self.admin_room, 'Hello')

        self.db_cur = db_conn.cursor()

        self.all_drinks = defaultdict(int)
        self.all_meals = defaultdict(int)
        self.min_wings = 0

    @property
    def all_wings(self):
        tens = (self.min_wings - 3) // 10
        rest = self.min_wings - (tens * 10)  # may be negative
        for threes in range(2):
            if threes * 3 >= rest:
                return (10 * tens) + (3 * threes)

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
        self.send_message(kwargs.get('room'), self.orders_text, markdown=True)

    @cmd('(?i)cluck -m=(\w+)([ -=\w]*)')
    def order(self, meal, args, **kwargs):
        room = kwargs.get('room')
        if meal not in MEALS:
            self.send_message(room, 'I did not understand meal choice of {}'.format(meal))
        else:
            meal_name, price = MEALS[meal]

        order_args = {
            key: None if not val else val[0]
            for key, *val in [
                arg.split('=')
                for arg in args.strip().split(' ')
            ]
        }

        spicy = '-s' in order_args
        wings = '-no_wings' not in order_args
        drink = order_args.get('-d', 'pepsi')

        if meal == 'p':
            self.all_meals[meal_name] += 1
        else:
            self.all_meals['{} {}'.format('spicy' if spicy else 'regular', meal_name)] += 1
        self.all_drinks[drink] += 1
        self.min_wings += 3 if wings else 0

        self.send_message(
            kwargs.get('room'),
            u'{} ordered a {}{} meal with {} hot wings and a can of {}. '
            'That costs £{:0.2f}'.format(
                kwargs.get('sender'),
                '' if meal == 'p' else ('spicy ' if spicy else 'regular '),
                meal_name,
                3 if wings else 0,
                drink,
                price
            )
        )

    @cmd('(?i)show order')
    def show_order(self, **kwargs):
        self.send_message(
            kwargs.get('room'),
            '### meals\n'
            '{}\n\n'
            '### wings\n'
            '{}\n\n'
            '### drinks\n'
            '{}'.format(
                dict(self.all_meals),
                self.all_wings,
                dict(self.all_drinks)
            ),
        )

    @cmd('(?i)clear order')
    def clear_order(self, **kwargs):
        self.all_drinks = defaultdict(int)
        self.all_meals = defaultdict(int)
        self.min_wings = 0

    def send_message(self, room, text, markdown=False):
        data = {'roomId': room}
        if markdown:
            data['markdown'] = text
        else:
            data['text'] = text
        create_message(data=data)
