#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import re
import os
import json
from collections import defaultdict
from bot_helpers import (MENTION_REGEX, PERSON_ID, create_message, get_person_info, list_messages,
                         list_memberships, create_webhook, get_webhook_by_name, delete_webhook)
from poll import Poll


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


def get_display_name(p_id):
    if p_id == 'rfc':
        display_name = 'The chicken shop'
    else:
        display_name = get_person_info(p_id).get('displayName', 'Unknown')
    return display_name


class MessageHandler:
    ''' handles spark messages '''

    polls = []
    room_polls = {}

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
        '+ set default **order** --> Set your default order\n'
        '+ help --> Display this message\n'
        '###Doodle\n'
        '* open **title** [options] --> Open new poll with options (comma separated list)\n'
        '* vote **title** [options] --> Vote for poll with options\n'
        '* close **title** --> Close poll and pick winner\n'
        '* reopen **title** --> Reopen poll\n'
        '* details **title** --> Get poll details\n'
        '* list --> Get list of active polls\n'
        '###TO DO\n'
        '+ add deadline --> close on deadline\n'
        '+ set notification --> notify regularly before close'
    )

    poll_details_text = (
        '###{}\n' # title
        '{}\n\n' # description
        # add poll_option_text for every option
    )
    poll_winners_text = (
        '###Winners for **{}**\n' # winner title
        '{}\n\n' # description
    )
    poll_option_text = (
        '{}. {}\n' # num_votes, option
    )

    orders_text = (
        '###Menu\n'
        '+ no args places your default order if you have one\n'
        '{}\n\n'
        '####Options\n'
        '+ -s --> spicy flag, include if you want a spicy burger '
        '(ignored if meal can\'t be spicy)\n'
        '+ -d=**drink** --> can of choice, no spaces allowed\n'
        '+ -no_wings --> no wings for this order (default is to have wings)\n'
        '+ -no_overwrite --> adds additional orders if this person already has one\n'
        '+ -extra=**cost** --> The price of any extra items you are ordering\n'
        '+ -note --> anything after this will be added as a comment on the order\n'
    )

    def __init__(self, db_conn):
        self.admin_room = os.environ['ADMIN_ROOM']
        self.send_message(self.admin_room, 'Hello')

        if get_webhook_by_name('all messages') is None:
            self.send_message(self.admin_room, 'Didn\'t find bot webhook, creating now')
            create_webhook()
            self.send_message(self.admin_room, 'done')

        # self.db_cur = db_conn.cursor()

        self.orders = []
        self.default_orders = {}
        self.menu = {}
        self.money = defaultdict(float)
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

    @cmd('(?i)hook me up')
    def create_admin_webhook(self, sender, room, **kwargs):
        if sender != os.environ['ADMIN_ID']:
            self.send_message(room, 'Sorry, you need to be an admin for this')
            return
        r = create_webhook(room)
        if r.ok:
            self.send_message(room, 'You\'re good to go')
        else:
            self.send_message(room, 'Got {} as the create webhook response'.format(r.status_code))

    @cmd('(?i)open (\w+) (\[,?\w+*,?\])')
    def open_poll(self, title, options, room, sender, **kwargs):
        display_name = get_display_name(sender)
        print("options ", options)

        poll = Poll(title, options, room)
        if room in self.room_polls:
            self.room_polls[room].append(poll)
        else:
            self.room_polls[room] = [poll]
        self.send_message(room, 'Poll open =)')
        self.post_poll_details(poll, room)

    @cmd('(?i)vote (\w+) ([^,]+)')
    def vote_poll(self, title, options, room, sender, **kwargs):
        display_name = get_display_name(sender)

        if len(title) == 0:
            self.send_message(room, '@{}, you need to set a title :-|'.format(display_name))
            return
        options = options.split(',')
        if len(options) == 0:
            self.send_message(room, '@{}, what are you even voting for? :-?'.format(display_name))
            return

        polls = None
        if room in self.room_polls:
            polls = self.room_polls[room]
        poll = None

        if not polls:
            self.send_message(room, 'There are no polls in this room')
            return
        valid_polls = {poll.title: poll for poll in polls}
        if title not in valid_polls:
            self.send_message(room, 'That poll does not live in this room')
            return
        else:
            poll = valid_polls[title]

        for idx, opt in enumerate(poll.options):
            if opt in options:
                poll.votes[idx] += 1


    @cmd('(?i)close (\w+)')
    def close_poll(self, title, room, sender, **kwargs):
        display_name = get_display_name(sender)

        if len(title) == 0:
            self.send_message(room, '@{}, which poll am I supposed to close? :-|'.format(display_name))
            return

        polls = None
        if room in self.room_polls:
            polls = self.room_polls[room]
        poll = None

        if not polls:
            self.send_message(room, 'There are no polls in this room')
            return
        valid_polls = {poll.title: poll for poll in polls}
        if title not in valid_polls:
            self.send_message(room, 'That poll does not live in this room')
            return
        else:
            poll = valid_polls[title]

        # close poll
        poll.closed = True
        self.post_poll_winners(poll, room)

    @cmd('(?i)reopen (\w+)')
    def reopen_poll(self, title, room, sender, **kwargs):
        display_name = get_display_name(sender)

        if len(title) == 0:
            self.send_message(room, '@{}, which poll am I supposed to reopen? :-|'.format(display_name))
            return

        polls = None
        if room in self.room_polls:
            polls = self.room_polls[room]
        poll = None

        if not polls:
            self.send_message(room, 'There are no polls in this room')
            return
        valid_polls = {poll.title: poll for poll in polls}
        if title not in valid_polls:
            self.send_message(room, 'That poll does not live in this room')
            return
        else:
            poll = valid_polls[title]

        # reopen poll
        poll.closed = False
        self.post_poll_details(poll, room)

    @cmd('(?i)details (\w+)')
    def get_poll_details(self, title, room, sender, **kwargs):
        polls = None
        if room in self.room_polls:
            polls = self.room_polls[room]
        poll = None

        if not polls:
            self.send_message(room, 'There are no polls in this room')
            return
        valid_polls = {poll.title: poll for poll in polls}
        if title not in valid_polls:
            self.send_message(room, 'That poll does not live in this room')
            return
        else:
            poll = valid_polls[title]
        self.post_poll_details(poll, room)

    @cmd('(?i)list')
    def list_polls(self, room, sender, **kwargs):
        polls = None
        if room in self.room_polls:
            polls = self.room_polls[room]
        polls_in_room = (
            '###Polls in this room:\n'
        )

        if not polls:
            polls_in_room += '* **NONE**'
        else:
            # loop through polls and add titles to list
            for poll in polls:
                if poll.closed:
                    continue
                polls_in_room += '* {}\n'.format(poll.title)
        # send msg with the list of polls
        self.send_message(
            room,
            polls_in_room,
            markdown=True
        )

    def post_poll_details(self, poll, room):
        # add title and desc for poll
        poll_details = self.poll_details_text.format(poll.title, poll.description)
        print("post options ", poll.options)
        # add votes and options
        for idx, opt in enumerate(poll.options):
            poll_details += self.poll_option_text.format(poll.votes[idx], opt)
        # send poll_details message
        self.send_message(room,
            poll_details,
            markdown=True
        )

    def post_poll_winners(self, poll, room):
        # add title and desc for poll
        poll_winners = self.poll_winners_text.format(poll.title, poll.description)
        # add votes and winning options
        for count, x in enumerate([idx for idx, val in sorted(enumerate(a), key=lambda x:x[1])]):
            # only print top 3 winners
            if count >= 3:
                break
            # add poll winner to list
            poll_winners += self.poll_option_text.format(poll.votes[x], poll.options[x])
        # send poll_details message
        self.send_message(room,
            poll_winners,
            markdown=True
        )

    @cmd('(?i)unhook me')
    def remove_admin_webhook(self, sender, room, **kwargs):
        if sender != os.environ['ADMIN_ID']:
            self.send_message(room, 'Sorry, you need to be an admin for this')
            return
        hook_id = get_webhook_by_name(room, bot=False)
        if hook_id is None:
            self.send_message(room, 'I couldn\'t find a webhook for this room')
        else:
            r = delete_webhook(hook_id)
            if r.ok:
                self.send_message(room, 'deleted')
            else:
                self.send_message(room, 'Got back {}'.format(r.status_code))

    @cmd('(?i)add to menu: (\w+), ([\w ]+), ([\d.]+),? ?(\w)?')
    def add_to_menu(self, key, name, price, spicy, sender, room, **kwargs):
        if sender != os.environ['ADMIN_ID']:
            self.send_message(room, 'Sorry, this is an admin only command')
            return

        if key in self.menu:
            self.send_message(room, 'Warning: Overwriting existing menu item')

        if name in self.menu:
            self.send_message(room, 'there is already a menu item with this name')
            return

        try:
            p = float(price)
        except ValueError:
            self.send_message(room, '{} is not a valid cost'.format(price))
            return

        spicy = spicy or 'n'
        self.menu[key] = [name, p, spicy == 'y']
        self.save_state()

    @cmd('(?i)bukaa')
    def odering_info(self, **kwargs):
        self.send_message(
            kwargs.get('room'),
            self.orders_text.format(
                '\n'.join([
                    '+ **{}**={} (£{:0.2f})'.format(key, name, price)
                    for key, (name, price, _) in self.menu.items()
                ])
            ),
            markdown=True
        )

    @cmd('(?i)set default ([\w -=]+)')
    def set_default(self, order, sender, room, **kwargs):
        self.default_orders[sender] = order
        self.save_state()
        self.send_message(room, 'done')

    @cmd('(?i)cluck$')
    def default_order(self, sender, room, **kwargs):
        if sender not in self.default_orders:
            self.send_message(
                room,
                'I don\'t know your default order, use "set default" to tell me'
            )
        else:
            text = 'cluck {}'.format(self.default_orders[sender])
            self.order(text, room=room, sender=sender)

    @cmd('(?i)cluck for (\w+) (\w+)(?:$| )([ -=\w.]*)')
    def order_other(self, person, meal, args, room, **kwargs):
        ''' pretend to be ordering from someone else - patch the arguments to the cmd decorator '''
        valid_people = set(member['personId'] for member in list_memberships(room)['items'])
        if person not in valid_people:
            self.send_message(room, '{} is not a valid input'.format(person))
            return
        text = 'cluck {} {}'.format(meal, args)
        # alter the sender and pass the command through
        self.order(text, room=room, sender=person)

    @cmd('(?i)cluck (\w+)(?:$| )([ -=\w.]*)')
    def order(self, meal, args, room, sender, **kwargs):
        ''' put an order in for chicken '''
        display_name = get_display_name(sender)
        if meal == 'b':
            self.send_message(room, 'Beef burgers (like all things) are inferior to chicken')
            self.send_message(
                room,
                '{} has selected: famine'.format(display_name)
            )
            return
        if meal not in self.menu:
            self.send_message(room, 'I did not understand meal choice of {}'.format(meal))
            return
        else:
            meal_name, price, spicy_flag = self.menu[meal]

        args, *comment = args.split('-note ')
        order_args = {
            key: None if not val else val[0]
            for key, *val in [
                arg.split('=')
                for arg in args.strip().split(' ')
            ]
        }

        spicy = None
        if spicy_flag:
            spicy = '-s' in order_args

        if '-no_wings' in order_args:
            wings = 0
        else:
            wings = 3
            price += 1

        drink = order_args.get('-d', 'pepsi')

        try:
            extra = float(order_args.get('-extra', '0'))
        except ValueError:
            self.send_message(
                room,
                'I didn\'t understand {} as an extra amount of money'.format(order_args['-extra'])
            )
        else:
            price += extra

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
                display_name,
                'spicy ' if spicy else '',
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
        money = defaultdict(float)
        for person, order in self.orders:
            money[person] -= order['price']

        for person, amount in self.money.items():
            money[person] += amount

        credit = [
            '{} is owed £{:0.2f}'.format(
                get_display_name(person),
                amount,
            )
            for person, amount in money.items()
            if amount > 0
        ]
        debt = [
            '{} owes £{:0.2f}'.format(
                get_display_name(person),
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
        if not self.orders:
            self.send_message(
                kwargs.get('room'),
                'No orders have been made'
            )
            return
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
                    '{}{}'.format(
                        'spicy ' if order['spicy'] else '',
                        order['meal']
                    )
                ] += 1
            all_drinks[order['drink']] += 1
            min_wings += order['wings']
            if order['notes']:
                comments.append('{} requested "{}"'.format(
                    get_display_name(person),

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
            '{}\n\n{}\n\n{}{}'.format(
                ', '.join('**{}** {}'.format(v, k) for k, v in dict(all_meals).items()),
                '**{}** wings'.format(all_wings),
                ', '.join('**{}** {}'.format(v, k) for k, v in dict(all_drinks).items()),
                '' if not comments else '\n\n{}'.format('\n\n'.join(comments)),
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
            self.money['rfc'] += order['price']
        self.send_message(kwargs.get('room'), 'Placing the following order:\n\n')

        # must be given matching regex to propagate command
        self.show_order('show order', **kwargs)
        self.clear_order('clear order', **kwargs)

    @cmd('(?i)clear order')
    def clear_order(self, room, **kwargs):
        self.orders = []
        self.save_state()
        self.send_message(room, 'done')

    @cmd('(?i)i paid( [\d\.]+)? for chicken')
    def paid_rfc(self, amount, room, sender, **kwargs):
        if self.orders:
            self.send_message(kwargs.get('room'), 'placing outstanding orders first')
            for person, order in self.orders:
                self.money[person] -= order['price']
                self.money['rfc'] += order['price']
            self.orders = []
            self.save_state()
        try:
            money = float(amount)
        except TypeError:
            # No amount given is paying off all the money
            if amount is None:
                money = self.money['rfc']
            else:
                return
        except ValueError:
            self.send_message(room, '{} is not a valid amount of money'.format(
                amount,
            ))
            return
        self.money[sender] += money
        self.money['rfc'] -= money
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

    @cmd('(?i)load state')
    def real_time_load_state(self, room, sender, **kwargs):
        if sender != os.environ['ADMIN_ID']:
            self.send_message(room, 'Sorry, this is an admin only command')
            return
        self.load_state()
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
                'money': dict(self.money),
                'defaults': self.default_orders,
                'menu': self.menu,
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
                self.default_orders = state.get('defaults', {})
                self.menu = state.get('menu', {})

                # load money back into default dict
                self.money = defaultdict(float)
                for person, amount in state.get('money', {}).items():
                    self.money[person] = round(amount, 2)
                break
        else:
            print('No state found - carrying on regardless')
