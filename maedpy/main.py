# import code
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'bin'))
from Game_class import Game_Mode
from Simulate_Game import simulate_game, output_results

#''''''''''''''''''''''''''''''''''''
#'''''''''''''Run Games '''''''''''''
#''''''''''''''''''''''''''''''''''''  

def main(file_name=None, repetitions=1):
    for i in range(repetitions):
        # read game set up
        game_setup = Game_Mode(file_name)
        
        # run game
        game_log = simulate_game(game_setup)
        
        # out put results
        output_results(game_setup, game_log)
    
if __name__ == "__main__":
     main()
