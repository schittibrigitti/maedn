import sys
from unittest.mock import patch
sys.path.append('../bin/')
from Game_class import Game_Mode
from Simulate_Game import GameSession, HumanAgent, RandomAgent, simulate_game

def test_game_session(game_setup):
    first_seeded_session = GameSession(game_setup, seed=814)
    second_seeded_session = GameSession(game_setup, seed=814)
    assert first_seeded_session.advance() == second_seeded_session.advance()

    session = GameSession(
        game_setup,
        agents=[HumanAgent(), RandomAgent()],
        dice_rolls=[1],
        start_positions={
            0: [1, 30, -1, -1],
            1: [-1, -1, -1, -1]
        }
    )

    decision = session.advance()
    assert decision['type'] == 'decision_required'
    assert decision['player'] == 'Player 1'
    assert [action['piece_index'] for action in decision['actions']] == [0, 1]
    assert session.log == []

    event = session.choose_action(1)
    assert event['type'] == 'turn_completed'
    assert event['log_entry']['positions']['Player 1'] == [1, 'house_1', -1, -1]
    assert list(event['log_entry']) == [
        'round', 'player', 'roll number', 'rolls', 'positions',
        'in_play', 'in_house', 'deliberate_moves'
    ]

    shared_session = GameSession(
        game_setup,
        agents=[HumanAgent(), HumanAgent()],
        dice_rolls=[1, 1],
        start_positions={
            0: [1, 30, -1, -1],
            1: [11, 20, -1, -1]
        }
    )
    first_decision = shared_session.advance()
    shared_session.choose_action(1)
    second_decision = shared_session.advance()
    assert second_decision['type'] == 'decision_required'
    assert second_decision['player'] == 'Player 2'
    shared_session.choose_action(1)
    assert len(shared_session.log) == 2

def test_move_priorities(game_setup):
    game_setup.clear_start_on_non_six = True

    with patch('Player_class.random.randint', return_value=0):
        house_entry_log = simulate_game(
            game_setup,
            dice_rolls=[1],
            start_positions={
                0: [1, 30, -1, -1],
                1: [-1, -1, -1, -1]
            }
        )
    assert house_entry_log[0]['positions']['Player 1'] == [1, 'house_1', -1, -1]

    with patch('Player_class.random.randint', return_value=0):
        house_advance_log = simulate_game(
            game_setup,
            dice_rolls=[1],
            start_positions={
                0: [1, 'house_1', -1, -1],
                1: [-1, -1, -1, -1]
            }
        )
    assert house_advance_log[0]['positions']['Player 1'] == [1, 'house_2', -1, -1]

    with patch('Player_class.random.randint', return_value=0):
        capture_log = simulate_game(
            game_setup,
            dice_rolls=[1],
            start_positions={
                0: [30, 1, -1, -1],
                1: [2, -1, -1, -1]
            }
        )
    assert capture_log[0]['positions']['Player 1'] == [30, 2, -1, -1]
    assert capture_log[0]['positions']['Player 2'] == [-1, -1, -1, -1]

    with patch('Player_class.random.randint', return_value=1):
        regular_move_log = simulate_game(
            game_setup,
            dice_rolls=[1],
            start_positions={
                0: [1, 5, -1, -1],
                1: [-1, -1, -1, -1]
            }
        )
    assert regular_move_log[0]['positions']['Player 1'] == [1, 6, -1, -1]

def main():
    
    ' The player must always chose moving away from home over beating another '
    ' figure. This is tested independelty of the figure position'
    
    # Game setup and manually change parameters
    game_setup = Game_Mode("test_setup.json")
    
    # Define a starting position for the player 
    starting_positions = {
        0: [0, 10, -1, -1],  # Player 1 has one piece on the start position
        1: [11, -1, -1, -1]
    }
    dice_rolls = [1]

    if not game_setup.clear_start_on_non_six:
        raise AssertionError("The start-field rule was not loaded from test_setup.json")
    
    # run game
    game_log = simulate_game(game_setup, dice_rolls, starting_positions)
    
    # expected outcome
    result = [1, 10, -1, -1]
    
    
    if game_log[0]['positions']['Player 1'] != result:
        raise AssertionError(
            f"Clear-start rule failed: {game_log[0]['positions']['Player 1']}"
        )
    print("Test Case clear start on non-six PASSED")

    game_setup.clear_start_on_non_six = False
    game_log = simulate_game(game_setup, dice_rolls, starting_positions)
    expected_player = [0, 11, -1, -1]
    expected_opponent = [-1, -1, -1, -1]
    if (
        game_log[0]['positions']['Player 1'] != expected_player
        or game_log[0]['positions']['Player 2'] != expected_opponent
    ):
        raise AssertionError(
            "Standard start-field behavior failed: "
            f"{game_log[0]['positions']}"
        )
    print("Test Case standard start-field behavior PASSED")
        
        
    # Define a starting position for the player 
    game_setup.clear_start_on_non_six = True
    starting_positions = {
        0: [10, 0, -1, -1],  # Player 1 has one piece on the start position
        1: [11, -1, -1, -1]
    }
    dice_rolls = [1]
    
    # run game
    game_log = simulate_game(game_setup, dice_rolls, starting_positions)
    
    # expected outcome
    result = [10, 1, -1, -1]
    
    if game_log[0]['positions']['Player 1'] != result:
        print("Test Case priorities FAILED")
    else: 
        print("Test Case priorities PASSED")

    starting_positions = {
        0: [1, 3, -1, -1],
        1: [11, -1, -1, -1]
    }
    dice_rolls = [2]

    with patch('Player_class.random.randint', return_value=0):
        game_log = simulate_game(game_setup, dice_rolls, starting_positions)

    result = [1, 5, -1, -1]
    if game_log[0]['positions']['Player 1'] != result:
        raise AssertionError(
            f"A piece moved onto an occupied own field: {game_log[0]['positions']['Player 1']}"
        )
    print("Test Case own occupied destination PASSED")

    test_move_priorities(game_setup)
    print("Test Case move priorities PASSED")

    test_game_session(game_setup)
    print("Test Case game session PASSED")
    
if __name__ == "__main__":
    main()
