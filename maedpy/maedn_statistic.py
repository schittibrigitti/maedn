import os
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import filedialog

STATISTIC_OUTPUT_DIR = Path(__file__).resolve().parent / 'output' / 'statistic'


def statistic_output_directory(input_directory, output_root=None):
    source_name = Path(input_directory).name or 'selected_data'
    root = Path(output_root) if output_root is not None else STATISTIC_OUTPUT_DIR
    return root / source_name


def _resolve_output_path(filepath, default_name):
    path = Path(filepath) if filepath is not None else STATISTIC_OUTPUT_DIR / default_name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def open_folder_dialog():
    # Erstelle ein verstecktes Tkinter-Fenster
    root = tk.Tk()
    root.withdraw()  # Verstecke das Hauptfenster
    
    # Setze das Fenster in den Vordergrund
    root.attributes("-topmost", True)
    
    # Öffne den Ordnerauswahldialog
    folder_path = filedialog.askdirectory(title="Select a Folder", parent=root)
    
    # Gib den Pfad des ausgewählten Ordners zurück
    return folder_path

def read_json_files(directory):
    game_data = []
    # Liste von Dateien, die ausgeschlossen werden sollen
    exclude_files = {"game_end.json", "time_dep.json"}
    
    for filename in os.listdir(directory):
        if filename.endswith(".json") and filename not in exclude_files:
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r') as file:
                # Lade die JSON-Daten und füge sie zur Liste hinzu
                game_data.append(json.load(file))
    
    return game_data

def process_game_data(game_data, filepath=None):
    results = []
    
    for game in game_data:
        turn_counter = 1
        last_turn = {}
        game_result = []
        
        for entry in game:
            round_num = entry['round']
            player = entry['player']
            in_play = entry['in_play']
            in_house = entry['in_house']
            deliberate_moves = entry['deliberate_moves']
            
            # Store the last turn of each player
            last_turn[player] = {
                'round': round_num,
                'player': player,
                'in_play': in_play,
                'in_house': in_house,
                'deliberate_moves': deliberate_moves
            }
            
            # When a new player takes a turn, save the previous player's last turn
            if len(last_turn) > 1:
                for last_player, last_data in list(last_turn.items())[:-1]:  # Exclude the current player
                    game_result.append({
                        'turn': turn_counter,
                        'round': last_data['round'],
                        #'player': last_player,
                        'in_play': last_data['in_play'],
                        'in_house': last_data['in_house'],
                        'deliberate_moves': last_data['deliberate_moves']
                    })
                    turn_counter += 1
                last_turn = {player: last_turn[player]}  # Keep only the current player's turn in the dict
        
        # At the end, save the last turn of the current player
        for last_player, last_data in last_turn.items():
            game_result.append({
                'turn': turn_counter,
                'round': last_data['round'],
                #'player': last_player,
                'in_play': last_data['in_play'],
                'in_house': last_data['in_house'],
                'deliberate_moves': last_data['deliberate_moves']
            })
            turn_counter += 1
        
        results.append(game_result)
    
    data_to_save = []
    max_turns = max(len(game) for game in results)

    for turn in range(1, max_turns + 1):
        in_play_values = []
        in_house_values = []
        deliberate_moves_values = []
        games_completed = 0
        
        for game in results:
            if turn <= len(game):
                entry = game[turn - 1]
                in_play_values.append(entry['in_play'])
                in_house_values.append(entry['in_house'])
                deliberate_moves_values.append(entry['deliberate_moves'])
            else:
                games_completed += 1
        
        data_to_save.append({
            'turn': turn,
            'mean_in_play': np.mean(in_play_values) if in_play_values else None,
            'mean_in_house': np.mean(in_house_values) if in_house_values else None,
            'games_completed': games_completed
        })
    
    filepath = _resolve_output_path(filepath, 'time_dep.json')
    with filepath.open('w', encoding='utf-8') as file:
        json.dump(data_to_save, file)

def analyze_game_states(game_data, filepath=None):
    end_data = []

    for game in game_data:
        last_entry = game[-1]  # Get the last entry of the game
        
        # Extract the necessary data from the last entry
        turns = len(game)
        rolls = last_entry['roll number']
        winning_player = last_entry['player']
        deliberate_moves = last_entry['deliberate_moves']
        in_house = last_entry['in_house']
        
        first_piece_in_house_turn = None
        for i,entry in enumerate(game):
            player_positions = entry['positions'][winning_player]
            if any(
                p == 'house' or (isinstance(p, str) and p.startswith('house_'))
                for p in player_positions
            ):
                first_piece_in_house_turn = entry['roll number']
                break
        
        end_data.append({
            'turns': turns,
            'rolls': rolls,
            'winning_player': winning_player,
            'deliberate_moves': deliberate_moves,
            'pieces_in_house': in_house,
            'first_piece_in_house_roll': first_piece_in_house_turn
        })

    filepath = _resolve_output_path(filepath, 'game_end.json')
    with filepath.open('w', encoding='utf-8') as file:
        json.dump(end_data, file)


def plot_time_data(filepath=None):
    filepath = Path(filepath) if filepath is not None else STATISTIC_OUTPUT_DIR / 'time_dep.json'
    with filepath.open('r', encoding='utf-8') as file:
        saved_data = json.load(file)
    
    turns = [entry['turn'] for entry in saved_data]
    mean_in_play = [entry['mean_in_play'] for entry in saved_data]
    mean_in_house = [entry['mean_in_house'] for entry in saved_data]
    games_completed = [entry['games_completed'] for entry in saved_data]

    plt.figure(figsize=(12, 8))

    # Plot mean_in_play
    plt.subplot(3, 1, 1)
    plt.plot(turns, mean_in_play, linestyle='-')
    plt.title('Mean number of pieces in play')
    plt.xlabel('# Turns')
    plt.ylabel('# pieces')
    plt.grid(True)
    
    # Plot the model function
    x_values = np.linspace(1, max(turns), 500)
    tanh_values = .155*40*np.tanh(x_values/31) # Adjust the scaling factors as needed
    plt.plot(x_values, tanh_values, color='red', linestyle='-', label='model')
    plt.legend()

    # Plot mean_in_house and games_completed on the same plot
    plt.subplot(3, 1, 2)
    plt.plot(turns, mean_in_house, linestyle='-', label='Mean In House')
    plt.title('Mean number of pieces in the house')
    plt.xlabel('# Turns')
    plt.ylabel('# pieces')
    plt.grid(True)

    # Plot mean_in_house and games_completed on the same plot
    plt.subplot(3, 1, 3)
    plt.plot(turns, [x / games_completed[-1]*100 for x in games_completed], linestyle='-', label='Games Completed')
    plt.title(' Games Completed')
    plt.xlabel('# Turns')
    plt.ylabel('Games Completed in %')
    plt.grid(True)

    plt.tight_layout()
    plt.show()

def plot_game_data(filepath=None):
    filepath = Path(filepath) if filepath is not None else STATISTIC_OUTPUT_DIR / 'game_end.json'
    with filepath.open('r', encoding='utf-8') as file:
        end_data = json.load(file)
    
    # Extracting the required data
    player_wins = {}
    turns_to_end = []
    rolls_to_first_house = []
    pieces_in_house_at_end = []
    total_rolls = 0
    total_deliberate_moves = 0
    
    for game in end_data:
        winning_player = game['winning_player']
        turns = game['turns']
        rolls = game['rolls']
        deliberate_moves = game['deliberate_moves']
        #rolls_to_first_house = game['first_piece_in_house_roll']
        
        if winning_player not in player_wins:
            player_wins[winning_player] = 0
        player_wins[winning_player] += 1
        
        turns_to_end.append(turns)
        rolls_to_first_house.append(game['first_piece_in_house_roll'])
        pieces_in_house_at_end.append(game['pieces_in_house'])
        total_rolls += rolls
        total_deliberate_moves += deliberate_moves
    
    # Calculating statistics
    num_games = len(end_data)
    median_turns = np.median(turns_to_end)
    median_rolls = np.median([game['rolls'] for game in end_data])
    deliberate_moves_per_roll = (total_deliberate_moves / total_rolls) * 100
    
    # Plotting the data
    plt.figure(figsize=(12, 8))
    
    # Pie chart for player wins
    plt.subplot(2, 2, 1)
    plt.pie(player_wins.values(), labels=player_wins.keys(), autopct='%1.1f%%', startangle=140)
    plt.title('Distribution of Wins by Player')
    
    # Adding statistics text to the pie chart
    plt.subplot(2, 2, 2)
    plt.text(0.05, 0.8, f'No. of Games: {num_games}', fontsize=12, bbox=dict(facecolor='white', alpha=0.8))
    plt.text(0.05, 0.5, f'Median Game Length: {median_turns:.0f} Turns / {median_rolls:.0f} Rolls', fontsize=12, bbox=dict(facecolor='white', alpha=0.8))
    plt.text(0.05, 0.2, f'Deliberate Moves: {deliberate_moves_per_roll:.2f}% of Rolls', fontsize=12, bbox=dict(facecolor='white', alpha=0.8))
    
    # Histogram for turns to end the game
    plt.subplot(2, 2, 3)
    plt.hist(turns_to_end, bins=20, edgecolor='black')
    plt.title('Turns played until a player wins')
    plt.xlabel('# Turns')
    plt.ylabel('Frequency')
    

    # Histogram for turns to end the game
    plt.subplot(2, 2, 4)
    predefined_bins = [3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5]
    plt.hist(pieces_in_house_at_end, bins=predefined_bins, edgecolor='black')
    plt.title('Total pieces in the house at game end')
    plt.xlabel('# Pieces')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    plt.show()

def main():
    #read data
    print("read data")
    directory = open_folder_dialog()
    if not directory:
        return
    print(directory)
    game_data = read_json_files(directory)
    output_directory = statistic_output_directory(directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    time_data_path = output_directory / 'time_dep.json'
    game_data_path = output_directory / 'game_end.json'
    
    # process data
    print("process data")
    # TODO skip if wanted
    process_game_data(game_data, time_data_path)
    analyze_game_states(game_data, game_data_path)

    # Plot the saved data
    print("plot data")
    plot_time_data(time_data_path)
    plot_game_data(game_data_path)
    
    return

if __name__ == "__main__":
    main()
