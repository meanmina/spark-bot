#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import re
from random import choice
from bot_helpers import MENTION_REGEX, PERSON_ID, DEBUG_ROOM, send_message, list_memberships
from dominion import Dominion


cmd_list = []

INSULTS = [
    'You should be nicer to',
]
#     'has eyes like a pug\'s eyes - oversized, dry and susceptible to ulcers',
#     'has a spine like a pug\'s spine - rounded and likely to cause back pain',
#     'has a nose like a pugs\'s nose - barely able to allow air to pass through',
#     'has a brain like a pug\'s brain - likely to get encephalitis, have seizures and cause death',
# ]


def cmd(regex, tag=False, turn=False, waiting_turn=False):
    def cmd_decorator(fn):
        def inner(obj, text, **kwargs):
            if tag:
                if PERSON_ID not in text:
                    return
            room = kwargs.get('room')
            sender = kwargs.get('sender')
            if waiting_turn:
                game = obj.waiting_turns.get(sender)
                if game is None:
                    return
                kwargs['game'] = game
            if turn:
                game = obj.games.get(room)
                if room is None:
                    return
                if game.state != 'progress':
                    return
                if sender != game.turn.id:
                    return
                kwargs['game'] = game
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
        'Use the following commands for game setup by tagging me in the message\n'
        '* **help**: Show this message\n'
        '* **new**: Create a new game - currently does nothing\n\n'
        '####In Progress\n'
        'In play you no longer need to tag me\n'
        '* **smack** _tag_: Send and insult\n'
    )

    def __init__(self, db_conn):
        self.admin_room = os.environ['ADMIN_ROOM']
        self.send_message(self.admin_room, 'Hello')

        self.db_cur = db_conn.cursor()

        # people we are waiting for a 1:1 message from
        self.waiting_turns = {}

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
            try:
                func(self, text, room=room, sender=sender)
            except Exception as exc:
                send_message(DEBUG_ROOM, exc)

    @cmd('(?i)help', tag=True)
    def send_help(self, room, **kwargs):
        send_message(room, self.help_text, markdown=True)

    # Setup commands
    @cmd('(?i)new', tag=True)
    def create_game(self, room, sender):
        if room in self.games:
            send_message(room, 'Game already in {}'.format(self.games[room].state))
        else:
            self.games[room] = Dominion(admin=sender, room=room)

    @cmd('(?i)join', tag=True)
    def join_game(self, room, sender):
        if room not in self.games:
            send_message(room, 'No games are active in this room')
        elif self.games[room].state == 'setup':
            self.games[room].add_player(sender)
        else:
            send_message(room, 'Can\'t join the game right now')

    @cmd('(?i)start', tag=True)
    def start_game(self, room, sender):
        if room not in self.games:
            send_message(room, 'No games are active in this room')
        elif self.games[room].state == 'setup':
            game = self.games[room]
            if sender == game.admin:
                game.start()
            else:
                send_message(room, 'No games are active in this room')
        else:
            send_message(room, 'Can\'t start the game right now')

    # chat commands
    @cmd('(?i)smack ([\w ]*)')
    def smack(self, target, room, **kwargs):
        data = {'roomId': room}
        people = list_memberships(data=data)
        for person in people['items']:
            name = person.get('personDisplayName')
            print(name)
            print(person['personId'])
            if target == name or target == person['personId']:
                send_message(room, '{} {}'.format(choice(INSULTS), name))
                break
        else:
            send_message(room, 'It\'s rude to talk about people behind their back')

    # In-game commands
    @cmd('(?i)play (\w+)', turn=True)
    def action(self, card, game, **kwargs):
        card = game.select_card(card)
        if card is not None:
            game.play(card)

    @cmd('(?i)buy (\w+)', turn=True)
    def buy(self, card, game, **kwargs):
        card = game.select_card(card)
        if card is not None:
            game.buy(card)

    @cmd('(?i)(\w+)', waiting_turn=True)
    def select(self, card, game, **kwargs):
        card = game.select_card(card)
        if card is not None:
            game.select(card)

    @cmd('(?i)done (\w+)', turn=True)
    def done(self, game, **kwargs):
        game.done()
