import sys
sys.path.append('../bin/')
from Game_class import Game_Mode
from Simulate_Game import simulate_game

def main():
    
    ' One Player starts the game with a 6, and then rolls another four 6s. '
    ' The player must first insert the piece on position 0 and then move it '
    ' by 6 steps to position 6. Then the third roll of a 6 means that another '
    ' piece is put in position 0. Then the first piece has to be moved, then the second'
    ' and then a new piece can be inserted'
    
    # Game setup and manually change parameters
    game_setup = Game_Mode("test_setup.json")
    
    # Define a starting position for the player 
    starting_positions = {
        0: [-1, -1, -1, -1],  # Player 1 has one piece on the start position
        1: [-1, -1, -1, -1]
    }
    
    #  consecutive rolls of a 6 
    dice_rolls = [6, 6, 6, 6, 6]

    # run game
    game_log = simulate_game(game_setup, dice_rolls, starting_positions)
    
    # expected outcome
    result = [12, 6, -1, -1]
    
    
    if game_log[4]['positions']['Player 1'] != result:
        print("Test Case 5 times 6 FAILED")
    else: 
        print("Test Case 5 times 6 PASSED")
    
if __name__ == "__main__":
    main()
