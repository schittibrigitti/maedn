import sys
sys.path.append('../bin/')
from Game_class import Game_Mode
from Simulate_Game import simulate_game

def main():
    
    ' The first player rolls twice until he gets a 6 and then rolls a 3 and moves away from start '
    ' Tthe second player rolls 3 times and gets no 6. Player 1 gets a 6 again and then a 1 to move away'
    ' Player 2 now has a 6 after the third trial. And then a 1 to move away'
    
    # Game setup and manually change parameters
    game_setup = Game_Mode("test_setup.json")  
    
    # Define a starting position for the player 
    starting_positions = {
        0: [-1, -1, -1, -1],  # Player 1 has one piece on the start position
        1: [-1, -1, -1, -1]
    }
    
    #  consecutive rolls of a 6 
    dice_rolls = [1, 6, 3, 2, 1, 5, 6, 1, 1, 2, 6, 1]

      # run game
    game_log = simulate_game(game_setup, dice_rolls, starting_positions)
    
    # expected outcome
    result1 = [3, 1, -1, -1]
    result2 = [11, -1, -1, -1]

    
    if game_log[6]['positions']['Player 1'] == result1 and game_log[6]['positions']['Player 2'] == result2:
        print("Test tripple roll PASSED")
    else: 
        print("Test tripple roll FAILED")
    
if __name__ == "__main__":
    main()