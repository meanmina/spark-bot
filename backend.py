#!/usr/bin/python3
'''
    Main backend where spark messages land and are parsed
'''
import os
import re
from random import choice
from bot_helpers import MENTION_REGEX, PERSON_ID, send_message, list_memberships
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


def cmd(regex, tag=False, turn=False):
    def cmd_decorator(fn):
        def inner(obj, text, **kwargs):
            if tag:
                if PERSON_ID not in text:
                    return
            room = kwargs['room']
            sender = kwargs['sender']
            game = obj.games.get(room)
            kwargs['game'] = game
            text = re.sub(PERSON_ID, '', text).strip()
            match = re.match(regex, text)
            if not match:
                print('no match with {}'.format(regex))
                return
            if turn:
                if game is None:
                    return
                if game.state != 'progress':
                    return
                if sender != game.turn.id:
                    send_message('It\'s not your turn')
                    return
                if game.waiting_actions:
                    send_message(room, 'Waiting for: {}'.format(
                        ', '.join(
                            '{p_name} to {description}'.format(**action)
                            for action in game.waiting_actions
                        )
                    ))
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
        print('sid-debug - {}'.format(self.admin_room))
        send_message(self.admin_room, 'Hello')

        self.db_cur = db_conn.cursor()
        self.games = {}

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
                send_message(self.admin_room, exc)

    @cmd('(?i)help', tag=True)
    def send_help(self, room, **kwargs):
        send_message(room, self.help_text, markdown=True)

    # Setup commands
    @cmd('(?i)new(?: as )?(\w+)?', tag=True)
    def create_game(self, nickname, room, sender, **kwargs):
        if room in self.games:
            send_message(room, 'Game already in {}'.format(self.games[room].state))
        else:
            self.games[room] = Dominion(admin=sender, room=room)
            self.games[room].add_player(sender, nickname)
            send_message(room, 'Created game, waiting for more people to join')

    @cmd('(?i)join(?: as )?(\w+)?', tag=True)
    def join_game(self, nickname, room, sender, **kwargs):
        if room not in self.games:
            send_message(room, 'No games are active in this room')
        elif self.games[room].state == 'setup':
            self.games[room].add_player(sender, nickname)
            send_message(room, 'Added new player to game. Players are {}'.format(
                self.games[room].players
            ))
        else:
            send_message(room, 'Can\'t join the game right now')

    @cmd('(?i)start', tag=True)
    def start_game(self, room, sender, **kwargs):
        if room not in self.games:
            send_message(room, 'No games are active in this room')
        elif self.games[room].state == 'setup':
            game = self.games[room]
            if sender == game.admin:
                game.start()
            else:
                send_message(room, 'Only the game creator can start')
        else:
            send_message(room, 'Can\'t start the game right now')

    @cmd('(?i)call me (\w+)', tag=True)
    def nickname(self, nickname, room, sender, **kwargs):
        if room in self.games:
            for player in self.games[room].players:
                if player.id == sender:
                    player.nickname = nickname

    # chat commands
    @cmd('(?i)smack (.+)')
    def smack(self, target, room, **kwargs):
        people = list_memberships(room)
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
        card = game.identify_card(card)
        if card is not None:
            game.play(card)

    @cmd('(?i)buy (\w+)', turn=True)
    def buy(self, card, game, **kwargs):
        card = game.identify_card(card)
        if card is not None:
            game.buy(card)

    @cmd('(?i)(\w+)')
    def select(self, card, game, sender, **kwargs):
        # private (or at least not in game) message
        if game is None:
            # should probably sort these by time at some point
            for game in self.games.values():
                for action in game.waiting_actions:
                    if action['public']:
                        continue
                    if sender == action['p_id']:
                        card = game.identify_card(card)
                        if action['function'](card):
                            action['count'] -= 1
                            if action['count'] <= 0:
                                game.waiting_actions.remove(action)
                            return
        # in a game
        else:
            for action in game.waiting_actions:
                if not action['public']:
                    continue
                if sender == action['p_id']:
                    card = game.identify_card(card)
                    if action['function'](card):
                        action['count'] -= 1
                        if action['count'] <= 0:
                            game.waiting_actions.remove(action)
                        return

    @cmd('(?i)(\w+), ?([\w ,]+)')
    def select_multiple(self, card, other_cards, **kwargs):
        ''' If it looks like a mutliple command split and send separately'''
        self.select(card, **kwargs)
        if ',' in other_cards:
            self.select_multiple(other_cards, **kwargs)
        else:
            self.select(other_cards, **kwargs)

    @cmd('(?i)pass (\w+)', turn=True)
    def done(self, game, **kwargs):
        game.done()
