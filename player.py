from random import shuffle
from bot_helpers import send_message, get_person_info
from copy import copy
from cards import Action, Treasure, Victory, STARTING_CARDS


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
    def hand_as_message(self, hand_info=True, turn_info=True):
        if hand_info:
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
        if turn_info:
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
