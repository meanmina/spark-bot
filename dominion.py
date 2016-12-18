import re
from itertools import cycle
from random import shuffle
from copy import copy
from bot_helpers import send_message, get_person_info
from cards import Action, Treasure, Victory, STARTING_CARDS, VICTORY_CARDS, TREASURE_CARDS, \
                  KINGDOM_CARDS, Curse, Province


class EndGameException(Exception):
    pass


class Player:
    ''' player class '''

    def __init__(self, person_id, nickname, group_room):
        ''' new player '''
        if nickname is None:
            person_info = get_person_info(person_id)
            nickname = person_info['displayName']
        self.nickname = nickname
        self.group_room = group_room
        self.id = person_id
        self.hand = []
        self.discards = []
        self.in_play = []
        self.deck = copy(STARTING_CARDS)
        shuffle(self.deck)
        self.new_hand()

    def __repr__(self):
        return self.nickname

    def new_hand(self):
        for _ in range(5):
            self.draw_card()
        self.bought = False
        self.actions = 1
        self.buys = 1
        self.spent = 0
        self.action_treasure = 0

    def draw_card(self):
        try:
            self.hand.append(self.deck.pop())
        except IndexError:
            if len(self.discards) < 1:
                # Technically possible if lots of pick up cards - just no more cards are drawn
                send_message(self.group_room, 'No more cards available')
                return
            self.deck = self.discards
            shuffle(self.deck)
            self.discards = []
            self.hand.append(self.deck.pop())

    def can_play_card(self, card):
        if self.actions < 1:
            return [False, 'You have no more actions left']
        if not issubclass(card, Action):
            return [False, 'Only action cards can be played']
        if self.bought:
            return [False, 'You can\'t play an action card after buying a card']
        for owned_card in self.hand:
            if isinstance(owned_card, card):
                return [True, owned_card]
        return [False, 'You Don\'t have a {}'.format(card)]

    def end_turn(self):
        while self.in_play:
            self.discards.append(self.in_play.pop())
        while self.hand:
            self.discards.append(self.hand.pop())
        self.new_hand()

    def gain_card(self, card, place='discard'):
        if place == 'discard':
            self.discards.append(card)
        elif place == 'hand':
            self.hand.append(card)
        elif place == 'deck':
            self.deck.append(card)

    def discard(self, card):
        for i, owned_card in enumerate(self.hand):
            if isinstance(owned_card, card):
                self.discards.append(self.hand.pop(i))
                return True

    @property
    def treasure(self):
        in_hand = sum([card.value for card in self.hand if isinstance(card, Treasure)])
        return in_hand + self.action_treasure - self.spent

    @property
    def hand_as_message(self):
        actions = [card.name for card in self.hand if isinstance(card, Action)]
        treasures = [card.name for card in self.hand if isinstance(card, Treasure)]
        victories = [card.name for card in self.hand if isinstance(card, Victory)]
        message = ''
        if actions:
            message += '**Actions**: {}\n\n'.format(', '.join(actions))
        if treasures:
            message += '**Treasures**: {}\n\n'.format(', '.join(treasures))
        if victories:
            message += '**Victories**: {}\n\n'.format(', '.join(victories))
        message += '**actions** {} - **treasure** {} - **buys** {}'.format(
            self.actions,
            self.treasure,
            self.buys,
        )
        return message

    @property
    def protected(self):
        # TODO check for moats
        return False


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
        self.waiting_public = []
        self.waiting_private = []

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
            repr(player) for player in self.players
        )))
        self.turn_order = cycle(self.players)
        self.turn = next(self.turn_order)
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
