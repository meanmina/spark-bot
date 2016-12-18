from bot_helpers import send_message


# Parent card classes
class Card:
    ''' Card object '''
    def __repr__(self):
        return self.name


class Victory(Card):
    ''' victory card '''
    pass


class Treasure(Card):
    ''' Treasure card '''
    pass


class Action(Card):
    ''' Action card '''

    def __init__(self):
        self.name = type(self).__name__.lower()
        self.actions = 0
        self.cards = 0
        self.buys = 0
        self.treasure = 0

    def action(self, game):
        player = game.turn
        player.in_play.append(self)
        player.hand.remove(self)
        player.actions += self.actions
        player.buys += self.buys
        player.action_treasure += self.treasure
        for _ in range(self.cards):
            player.draw_card()


# Treasure
class Copper(Treasure):
    name = 'copper'
    num_in_game = 60
    cost = 0
    value = 1


class Silver(Treasure):
    name = 'silver'
    num_in_game = 40
    cost = 3
    value = 2


class Gold(Treasure):
    name = 'gold'
    num_in_game = 30
    cost = 6
    value = 3


# Victory
class Estate(Victory):
    name = 'estate'
    cost = 2
    points = 1


class Duchy(Victory):
    name = 'duchy'
    cost = 5
    points = 3


class Province(Victory):
    name = 'province'
    cost = 8
    points = 6


class Curse(Victory):
    name = 'curse'
    cost = float('inf')
    points = -1


# Action
class Malitia(Action):

    name = 'malitia'
    cost = 4

    def __init__(self):
        super().__init__()
        self.treasure = 2

    def action(self, game):
        super().action(game)
        attacked_player = next(game.turn_order)
        while attacked_player != game.turn:
            if attacked_player.protected:
                continue
            num_to_discard = len(attacked_player.hand) - 3
            if num_to_discard <= 0:
                continue
            send_message(
                attacked_player.id,
                'You have been attacked by a malitia! Currently you have {} but '
                'you must discard {} card(s) to get down to three. Discard publicly by '
                'typing the name of a card in the group room'.format(
                    attacked_player.hand,
                    num_to_discard,
                ),
                direct=True
            )
            game.waiting_public.append([
                attacked_player.id,
                attacked_player.discard
            ])


class Witch(Action):

    name = 'witch'
    cost = 5

    def __init__(self):
        super().__init__()
        self.cards = 2

    def action(self, game):
        super().action(game)
        attacked_player = next(game.turn_order)
        while attacked_player != game.turn:
            if attacked_player.protected:
                continue
            try:
                attacked_player.gain_card(game.take_card(Curse))
            except IndexError:
                pass  # If they run out then don't worry


STARTING_CARDS = [Estate()] * 3 + [Copper()] * 7
VICTORY_CARDS = [Estate, Duchy, Province]
TREASURE_CARDS = [Copper, Silver, Gold]
KINGDOM_CARDS = [
    Malitia,
    Witch
]
