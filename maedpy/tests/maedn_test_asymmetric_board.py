import sys
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))
sys.path.insert(0, str(PACKAGE_DIR / 'bin'))

from Game_class import Game_Mode
from Simulate_Game import GameSession, simulate_game
from board_view import BoardView
from maedn_PvE import create_agents, create_game, load_game_modes

PARAMETERS = {'nominal_players': 4, 'n_players': 3, 'player_positions': [1, 2, 4]}


class FakeCanvas:
    def __init__(self):
        self.ovals = []
        self.texts = []

    def delete(self, *args):
        self.ovals.clear()
        self.texts.clear()

    def create_oval(self, *args, **kwargs):
        self.ovals.append(args)

    def create_text(self, *args, **kwargs):
        self.texts.append(kwargs.get('text'))

    def create_rectangle(self, *args, **kwargs):
        pass

    def create_line(self, *args, **kwargs):
        pass

    def tag_bind(self, *args):
        pass

    def winfo_width(self):
        return 800

    def winfo_height(self):
        return 800


def test_example_json_defines_uneven_board():
    game = Game_Mode(str(PACKAGE_DIR / 'input' / 'three_players_on_four_player_field.json'))
    assert (game.nominal_players, game.n_players) == (4, 3)
    assert game.size == 40
    assert game.start_positions == [0, 10, 30]
    assert game.end_positions == [39, 9, 29]


def test_default_positions_are_consecutive():
    game = Game_Mode({'n_players': 3})
    assert game.nominal_players == 3
    assert game.player_positions == [1, 2, 3]
    assert game.start_positions == [0, 10, 20]
    assert game.size == 30


@pytest.mark.parametrize('overrides', [
    {'player_positions': [1, 2]},
    {'player_positions': [1, 2, 2]},
    {'player_positions': [1, 2, 5]},
    {'player_positions': [0, 1, 2]},
    {'nominal_players': 2},
])
def test_invalid_configuration_is_rejected(overrides):
    with pytest.raises(ValueError):
        Game_Mode({**PARAMETERS, **overrides})


def test_player_at_seat_four_walks_the_long_way():
    game = Game_Mode(PARAMETERS)
    session = GameSession(game, dice_rolls=[1], agents=create_agents(3))
    third = session.players[2]
    assert (third.start_pos, third.end_pos) == (30, 29)
    # Player 2 (start 10) has 20 fields to its own home entrance; Player 3 only 10 before Player 1
    assert (game.start_positions[0] - game.start_positions[2]) % game.size == 10
    assert (game.start_positions[2] - game.start_positions[1]) % game.size == 20


def test_full_game_runs_on_uneven_board():
    game = Game_Mode(PARAMETERS)
    log = simulate_game(game, seed=3)
    assert log
    assert set(log[-1]['positions']) == {'Player 1', 'Player 2', 'Player 3'}


def test_game_mode_json_contains_uneven_board():
    modes = {mode['name']: mode['parameters'] for mode in load_game_modes()}
    parameters = modes['3 Players on classic 4 Player Field']
    game = create_game(parameters)
    assert game.start_positions == [0, 10, 30]
    assert game.size == 40
    assert len(create_agents(game.n_players)) == 3


def test_board_view_places_starts_on_uneven_board():
    game = create_game(PARAMETERS)
    view = BoardView(FakeCanvas(), game=game)
    assert [view.players[f'Player {i}']['start_pos'] for i in (1, 2, 3)] == [0, 10, 30]
    view.render({'player': 'Player 3', 'positions': {
        'Player 1': [-1] * 4, 'Player 2': [-1] * 4, 'Player 3': [5, 'house_1', -1, -1]}})
    assert view.size == 40
    assert view._track_coordinates(30) != view._track_coordinates(20)
