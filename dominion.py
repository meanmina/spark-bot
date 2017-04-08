from itertools import cycle
from random import shuffle
from copy import copy
from bot_helpers import send_message
from cards import Action, Treasure, STARTING_CARDS, VICTORY_CARDS, TREASURE_CARDS, KINGDOM_CARDS, \
                  Curse, Witch


class EndGameException(Exception):
    pass


class Player:
    ''' player class '''

    def __init__(self, person_id, group_room):
        ''' new player '''
        # TODO set up 1 on 1 room with player
        # TODO set up player name
        self.group_room = group_room
        self.id = person_id
        self.hand = []
        self.discards = []
        self.in_play = []
        self.deck = STARTING_CARDS
        shuffle(self.deck)
        self.new_hand()

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
        return [False, 'You Don\'t have a {}'.format(card.name)]

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

    @property
    def treasure(self):
        in_hand = sum([card.value for card in self.hand if isinstance(card, Treasure)])
        return in_hand + self.action_treasure - self.spent

    @property
    def hand_as_message(self):
        return 'Bugger all'


class Dominion:
    ''' Dominion card game '''

    def __init__(self, admin, room):
        ''' create new game '''
        self.room = room
        self.admin_id = admin
        self.players = [Player(admin, self.room)]
        self.board = {}
        self.empty_stacks = set()
        self.state = 'setup'

    def add_player(self, player_id):
        ''' add a new player to game in setup '''
        if player_id in [player.id for player in self.players]:
            send_message(self.room, 'You are already in this game')
        else:
            self.players.append(Player(player_id, self.room))

    def start(self):
        ''' Start the game '''
        self.state = 'progress'
        shuffle(self.players)
        send_message(self.room, 'Turn order is: {}'.format(', '.join(
            player.name for player in self.players
        )))
        self.turn_order = cycle(self.players)
        self.turn = next(self.turn_order)
        self.make_board(len(self.players))

    def take_card(self, card_type):
        cards_left = self.board[card_type]
        if cards_left == 0:
            raise IndexError('No cards left on stack')
        elif cards_left == 1:
            self.empty_stacks.add(card_type)
            send_message(self.room, 'The last {} has been taken'.format(card_type.name))
        self.board[card_type] -= 1
        return card_type()

    def next_turn(self):
        if len(self.empty_stacks) >= 3 or self.board['province'][1] == 0:
            # Do end game stuff here
            return
        self.turn.end_turn()
        self.turn = next(self.turn_order)
        send_message(self.room, '{} it\'s your turn, you have:'.format(self.turn.id))
        send_message(self.room, '{}'.format(self.turn.hand_as_message))

    def make_board(self, num_players):
        # Add base cards
        for card_type in VICTORY_CARDS:
            self.board[card_type] = 8 if num_players == 2 else 12
        for card_type in TREASURE_CARDS:
            in_hand = 3 * num_players if card_type.name == 'copper' else 0
            self.board[card_type] = card_type.num_in_game - in_hand
        # add kingdom cards
        kingdom_cards = copy(KINGDOM_CARDS)
        shuffle(kingdom_cards)
        for card_type in kingdom_cards[:10]:
            self.board[card_type] = 10
            if card_type == Witch:  # special case to add curses
                self.board[Curse] = (num_players - 1) * 10
        self.trash = []

    def select_card(self, card):
        ''' take a string card input and return a card object '''
        pass

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
        self.buys -= 1
        if self.turn.buys == 0:
            self.next_turn()

    def done(self):
        ''' player is done with theit turn '''
        self.next_turn()

    def select(self, card):
        ''' when the game is expecting player to select a card '''
        pass
