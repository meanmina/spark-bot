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
        send_message(
            game.room,
            'You now have:\n\n' + player.hand_as_message,
            markdown=True,
        )


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
    cost = 0
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
        waiting_on = []
        for attacked_player in game.turn_order:
            if attacked_player == game.turn:
                break
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
            waiting_on.append('{} ({})'.format(attacked_player, num_to_discard))
            game.waiting_actions.append({
                'public': True,
                'p_id': attacked_player.id,
                'function': attacked_player.discard,
                'count': num_to_discard,
                'p_name': attacked_player.nickname,
                'description': 'discard after being attacked by a malitia'
            })
        if waiting_on:
            send_message(
                game.room,
                'Waiting for the following players to discard cards: {}'.format(
                    ', '.join(waiting_on)
                ),
            )
        else:
            send_message(game.room, 'Nobody has to discard')


class Witch(Action):

    name = 'witch'
    cost = 5

    def __init__(self):
        super().__init__()
        self.cards = 2

    def action(self, game):
        super().action(game)
        safe = []
        cursed = []
        no_more_curses = []
        for attacked_player in game.turn_order:
            if attacked_player == game.turn:
                break
            if attacked_player.protected:
                safe.append(attacked_player)
                continue
            try:
                attacked_player.gain_card(game.take_card(Curse))
                cursed.append(attacked_player)
            except IndexError:
                # If they run out then don't worry
                no_more_curses.append(attacked_player)
                pass
        if safe:
            send_message(game.room, 'Protected: {}'.format(', '.join(safe)))
        if cursed:
            send_message(game.room, 'Cursed: {}'.format(', '.join(safe)))
        if no_more_curses:
            send_message(
                game.room,
                'There are no curses left for: {}'.format(', '.join(no_more_curses))
            )


STARTING_CARDS = [Estate()] * 3 + [Copper()] * 7
VICTORY_CARDS = [Estate, Duchy, Province]
TREASURE_CARDS = [Copper, Silver, Gold]
KINGDOM_CARDS = [
    Malitia,
    Witch
]
