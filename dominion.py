import re
from random import shuffle
from itertools import cycle
from copy import copy
from bot_helpers import send_message
from cards import VICTORY_CARDS, TREASURE_CARDS, KINGDOM_CARDS, Curse, Province
from player import Player


class EndGameException(Exception):
    pass


class Dominion:
    ''' Dominion card game '''

    def __init__(self, admin, room):
        ''' create new game '''
        self.room = room
        self.admin = admin
        self.players = []
        self.board = {}
        self.empty_stacks = set()
        self.state = 'setup'
        self.waiting_actions = []

    def add_player(self, player_id, nickname):
        ''' add a new player to game in setup '''
        if player_id in [player.id for player in self.players]:
            send_message(self.room, 'You are already in this game')
        else:
            self.players.append(Player(player_id, nickname, self.room))

    def start(self):
        ''' Start the game '''
        self.state = 'progress'
        shuffle(self.players)
        send_message(self.room, 'Turn order is: {}'.format(', '.join(
            player for player in self.players
        )))
        self.turn_order = cycle(self.players)
        self.make_board(len(self.players))
        self.next_turn()

    def take_card(self, card):
        cards_left = self.board[card]
        if cards_left == 0:
            raise IndexError('No cards left on stack')
        elif cards_left == 1:
            self.empty_stacks.add(card)
            send_message(self.room, 'The last {} has been taken'.format(card))
        self.board[card] -= 1
        return card()

    def next_turn(self):
        if len(self.empty_stacks) >= 3 or self.board[Province] == 0:
            # TODO end game stuff here
            return
        self.turn = next(self.turn_order)
        send_message(self.room, '{} it\'s your turn, you have:'.format(self.turn))
        send_message(self.room, self.turn.hand_as_message, markdown=True)

    def make_board(self, num_players):
        # Add base cards
        for card in VICTORY_CARDS:
            self.board[card] = 8 if num_players == 2 else 12
        for card in TREASURE_CARDS:
            in_hand = 3 * num_players if repr(card) == 'copper' else 0
            self.board[card] = card.num_in_game - in_hand
        # add kingdom cards
        kingdom_cards = copy(KINGDOM_CARDS)
        shuffle(kingdom_cards)
        for card in kingdom_cards[:2]:
            self.board[card] = 10
            if repr(card) == 'witch':  # special case to add curses
                self.board[Curse] = (num_players - 1) * 10
        self.trash = []

    def identify_card(self, card_search):
        ''' take a string card input and return a card object '''
        regex = re.compile('(?i){}'.format(card_search))
        matches = [card for card in self.board if regex.match(card.name)]
        if len(matches) > 1:
            send_message(self.room, '{} matches any of: {}'.format(card_search, matches))
        elif len(matches) == 0:
            send_message(self.room, '{} does not match any cards'.format(card_search))
        else:
            return matches[0]

    def play(self, card):
        ''' player plays and action card '''
        success, result = self.turn.can_play_card(card)
        if not success:
            send_message(self.room, result)
        else:
            result.action(self)

    def buy(self, card):
        ''' player buys a card '''
        if card == Curse:
            send_message(self.room, 'You can\'t buy curses silly')
            return
        if self.turn.treasure < card.cost:
            send_message(self.room, 'You can\'t afford that card')
            return
        try:
            self.turn.gain_card(self.take_card(card))
        except IndexError:
            send_message(self.room, 'Sorry, there are none left')
            return
        self.turn.spent += card.cost
        self.turn.buys -= 1
        if self.turn.buys == 0:
            self.turn.end_turn()
            self.next_turn()

    def done(self):
        ''' player is done with their turn '''
        self.turn.end_turn()
        self.next_turn()
