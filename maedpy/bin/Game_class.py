import json
from pathlib import Path

class Game_Mode:
    def __init__(self, file_name=None):
        # Standardwerte für die Parameter
        self.n_players = 4
        self.n_dice_sides = 6
        self.start_to_start_distance = 10
        self.n_rerolls = 3
        self.n_pieces_to_win = 4
        self.knock_duty = True
        self.n_pieces = 4
        self.clear_start_on_non_six = True

        # Berechne die Größe basierend auf der Anzahl der Spieler und der Startdistanz (vor dem Einlesen)
        self.size = self.n_players * self.start_to_start_distance

        # Initialisiere Start- und Endpositionen sowie Spielernamen erneut
        self.player_names = [f"Player {i+1}" for i in range(self.n_players)]
        self.start_positions = [i * self.start_to_start_distance for i in range(self.n_players)]
        self.end_positions = [(i * self.start_to_start_distance - 1) % self.size for i in range(self.n_players)]

        if isinstance(file_name, dict):
            data = file_name
        elif file_name:
            with open(file_name, 'r') as file:
                data = json.load(file)
        else:
            data = None

        if data is not None:
            self.n_players = data.get('n_players', self.n_players)
            self.n_dice_sides = data.get('n_dice_sides', self.n_dice_sides)
            self.start_to_start_distance = data.get('start_to_start_distance', self.start_to_start_distance)
            self.n_rerolls = data.get('n_rerolls', self.n_rerolls)
            self.n_pieces_to_win = data.get('n_pieces_to_win', self.n_pieces_to_win)
            self.knock_duty = data.get('knock_duty', self.knock_duty)
            self.clear_start_on_non_six = data.get('clear_start_on_non_six', self.clear_start_on_non_six)
            self.n_pieces = data.get('n_pieces', self.n_pieces)

            self.size = self.n_players * self.start_to_start_distance
            self.player_names = [f"Player {i+1}" for i in range(self.n_players)]
            self.start_positions = [i * self.start_to_start_distance for i in range(self.n_players)]
            self.end_positions = [(i * self.start_to_start_distance - 1) % self.size for i in range(self.n_players)]

            self.player_names = data.get('player_names', self.player_names)
            self.start_positions = data.get('start_positions', self.start_positions)
            self.end_positions = data.get('end_positions', self.end_positions)

            temp_size = data.get('size')
            if temp_size is not None and temp_size > self.size:
                self.size = temp_size

        # In- und Output-Parameter
        parameters = [
            self.n_players, self.size, self.n_dice_sides,
            self.start_to_start_distance, self.n_rerolls,
            self.n_pieces_to_win, self.n_pieces, self.knock_duty,
            self.clear_start_on_non_six
        ]
        output_folder = Path(__file__).resolve().parents[1] / 'output'
        self.out_folder = str(output_folder / "_".join(str(i) for i in parameters))
