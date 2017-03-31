#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import re
import os
import json
from collections import defaultdict
from bot_helpers import (MENTION_REGEX, PERSON_ID, create_message, get_person_info, list_messages,
                         list_memberships)


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
        '+ cluck **meal** [options] --> Order chicken\n'
        '+ cluck for **person** **meal** [options] --> Order for someone else (use mentions)\n'
        '+ bukaa --> See the list of order options\n'
        '+ I paid **X** for chicken --> Indicate that you paid money in RFC\n'
        '+ **person**/**I** paid **person**/**me** **X** --> general payment from a to b\n'
        '+ show order --> Show what has been ordered so far\n'
        '+ place order --> Confirms current order and applies charges\n'
        '+ cancel order --> Cancels your own order\n'
        '+ cancel order for **person** --> Cancel someone elses order\n'
        '+ clear order --> Clears current order, nobody is charged\n'
        '+ money --> See who owes what\n'
        '+ help --> Display this message'
    )

    orders_text = (
        '###Menu\n'
        '+ **meal** --> t=tower, f=fillet, p=popcorn, b=beef burger REQUIRED\n'
        '+ -s --> spicy flag, include if you want a spicy burger (ignored if meal is \'p\')\n'
        '+ -d=**drink** --> can of choice, no spaces allowed\n'
        '+ -no_wings --> no wings for this order (default is to have wings)\n'
        '+ -no_overwrite --> adds additional orders if this person already has one\n'
        '+ -note --> anything after this will be added as a comment on the order\n'
    )

    def __init__(self, db_conn):
        self.admin_room = os.environ['ADMIN_ROOM']
        self.send_message(self.admin_room, 'Hello')

        self.db_cur = db_conn.cursor()

        self.orders = []
        self.money = defaultdict(int)
        self.load_state()

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

    @cmd('(?i)help')
    def send_help(self, **kwargs):
        self.send_message(kwargs.get('room'), self.help_text, markdown=True)

    @cmd('(?i)bukaa')
    def odering_info(self, **kwargs):
        self.send_message(kwargs.get('room'), self.orders_text, markdown=True)

    @cmd('(?i)cluck for (\w+) (\w)(?:$| )([ -=\w]*)')
    def order_other(self, person, meal, args, room, **kwargs):
        ''' pretend to be ordering from someone else - patch the arguments to the cmd decorator '''
        valid_people = set(member['personId'] for member in list_memberships(room)['items'])
        if person not in valid_people:
            self.send_message(room, '{} is not a valid input'.format(person))
            return
        text = 'cluck {} {}'.format(meal, args)
        # alter the sender and pass the command through
        self.order(text, **{'room': room, 'sender': person})

    @cmd('(?i)cluck (\w)(?:$| )([ -=\w]*)')
    def order(self, meal, args, room, sender, **kwargs):
        ''' put an order in for chicken '''
        person_info = get_person_info(sender)
        if meal == 'b':
            self.send_message(room, 'Beef burgers (like all things) are inferior to chicken')
            self.send_message(
                room,
                '{} has selected: famine'.format(person_info.get('displayName'))
            )
            return
        if meal not in MEALS:
            self.send_message(room, 'I did not understand meal choice of {}'.format(meal))
            return
        else:
            meal_name, price = MEALS[meal]

        args, *comment = args.split('-note ')
        order_args = {
            key: None if not val else val[0]
            for key, *val in [
                arg.split('=')
                for arg in args.strip().split(' ')
            ]
        }

        spicy = None
        if meal != 'p':
            spicy = '-s' in order_args

        if '-no_wings' in order_args:
            wings = 0
        else:
            wings = 3
            price += 1

        drink = order_args.get('-d', 'pepsi')

        if '-no_overwrite' not in order_args:
            self.orders = [order for order in self.orders if order[0] != sender]

        self.orders.append([
            sender,
            {
                'meal': meal_name,
                'spicy': spicy,
                'wings': wings,
                'drink': drink,
                'notes': comment,
                'price': price,
            }
        ])

        self.send_message(
            room,
            u'{} ordered a {}{} meal with {} hot wings and a can of {}{}. '
            'That costs £{:0.2f}'.format(
                person_info.get('displayName'),
                '' if meal == 'p' else ('spicy ' if spicy else 'regular '),
                meal_name,
                3 if wings else 0,
                drink,
                '' if not comment else ' ({})'.format(comment[0]),
                price
            )
        )
        self.save_state()

    @cmd('(?i)money')
    def show_money(self, room, **kwargs):
        money = defaultdict(int)
        for person, order in self.orders:
            money[person] -= order['price']

        for person, amount in self.money.items():
            money[person] += amount

        credit = [
            '{} is owed £{:0.2f}'.format(
                get_person_info(person).get('displayName'),
                amount,
            )
            for person, amount in money.items()
            if amount > 0
        ]
        debt = [
            '{} owes £{:0.2f}'.format(
                get_person_info(person).get('displayName'),
                abs(amount),
            )
            for person, amount in money.items()
            if amount < 0
        ]

        self.send_message(
            room,
            '### Credit\n{}\n### Debt\n{}'.format(
                '\n\n'.join(credit),
                '\n\n'.join(debt),
            ),
            markdown=True
        )

    @cmd('(?i)show order')
    def show_order(self, **kwargs):
        all_drinks = defaultdict(int)
        all_meals = defaultdict(int)
        min_wings = 0
        all_wings = 0
        comments = []

        for person, order in self.orders:
            if order['meal'] == 'popcorn':
                all_meals[order['meal']] += 1
            else:
                all_meals[
                    '{} {}'.format(
                        'spicy' if order['spicy'] else 'regular',
                        order['meal']
                    )
                ] += 1
            all_drinks[order['drink']] += 1
            min_wings += order['wings']
            if order['notes']:
                comments.append('{} requested "{}"'.format(
                    get_person_info(person).get('displayName'),
                    order['notes'][0])
                )

        tens = max((min_wings + 3) // 10, 0)
        rest = min_wings - (tens * 10)  # may be negative
        for threes in range(3):
            if threes * 3 >= rest:
                all_wings = (10 * tens) + (3 * threes)
                break

        self.send_message(
            kwargs.get('room'),
            '###Meals\n'
            '{}\n\n'
            '###Wings\n'
            '{}\n\n'
            '###Drinks\n'
            '{}{}'.format(
                '\n'.join('{} - {}'.format(k, v) for k, v in dict(all_meals)),
                all_wings,
                '\n'.join('{} - {}'.format(k, v) for k, v in dict(all_drinks)),
                '' if not comments else '\n\n###Notes\n{}'.format('\n\n'.join(comments)),
            ),
            markdown=True
        )

    @cmd('(?i)cancel order for (\w+)')
    def cancel_other(self, person, room, **kwargs):
        valid_people = set(member['personId'] for member in list_memberships(room)['items'])
        if person not in valid_people:
            self.send_message(room, '{} is not a valid input'.format(person))
            return
        text = 'cancel order'
        # alter the sender and pass the command through
        self.cancel_order(text, **{'room': room, 'sender': person})

    @cmd('(?i)cancel order(?! f)')
    def cancel_order(self, room, sender):
        self.orders = [order for order in self.orders if order[0] != sender]
        self.save_state()
        self.send_message(room, 'done')

    @cmd('(?i)place order')
    def place_order(self, **kwargs):
        for person, order in self.orders:
            self.money[person] -= order['price']
        self.send_message(kwargs.get('room'), 'Placing the following order:\n\n')

        # must be given matching regex to propagate command
        self.show_order('show order', **kwargs)
        self.clear_order('clear order', **kwargs)

    @cmd('(?i)clear order')
    def clear_order(self, room, **kwargs):
        self.orders = []
        self.save_state()
        self.send_message(room, 'done')

    @cmd('(?i)i paid ([\d\.]+) for chicken')
    def paid_rfc(self, amount, room, sender, **kwargs):
        try:
            money = float(amount)
        except ValueError:
            self.send_message(room, '{} is not a valid amount of money'.format(
                amount,
            ))
        else:
            self.money[sender] += money
        self.save_state()
        self.send_message(room, 'done')

    @cmd('(?i)(\w+) paid (\w+) ([\d\.]+)')
    def paid_person(self, payer, payee, amount, room, sender):
        if payer.lower() == 'i':
            payer = sender
        if payee.lower() == 'me':
            payee = sender

        valid_people = set(member['personId'] for member in list_memberships(room)['items'])
        if payer not in valid_people:
            self.send_message(room, '{} is not a valid input'.format(payer))
            return
        if payee not in valid_people:
            self.send_message(room, '{} is not a valid input'.format(payee))
            return

        try:
            money = float(amount)
        except ValueError:
            self.send_message(room, '{} is not a valid amount of money'.format(
                amount,
            ))
        else:
            self.money[payer] += money
            self.money[payee] -= money
        self.save_state()
        self.send_message(room, 'done')

    def send_message(self, room, text, markdown=False):
        data = {'roomId': room}
        if markdown:
            data['markdown'] = text
        else:
            data['text'] = text
        create_message(data=data)

    def save_state(self):

        state = json.dumps(
            {
                'orders': self.orders,
                # convert money to regular dict
                'money': dict(self.money)
            },
            separators=(',', ':')
        )
        self.send_message(self.admin_room, 'state={}'.format(state))

    def load_state(self):
        messages = list_messages(self.admin_room, limit=100)['items']
        for message in messages:
            text = message.get('text', '')
            if text[:6] == 'state=':
                state = json.loads(text[6:])
                self.orders = state.get('orders', [])

                # load money back into default dict
                for person, amount in state.get('money', {}).items():
                    self.money[person] = amount
                break
        else:
            print('No state found - carrying on regardless')
