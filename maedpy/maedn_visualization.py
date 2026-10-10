import json
import tkinter as tk
from tkinter import filedialog
import numpy as np

try:
    from .board_view import BoardView, is_house_position
except ImportError:
    from board_view import BoardView, is_house_position

# Load the game log from a JSON file
def load_game_log(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def open_file_dialog():
    # Erstelle ein verstecktes Tkinter-Fenster
    root = tk.Tk()
    root.withdraw()  # Verstecke das Hauptfenster
    
    # Öffne den Dateiexplorer und filtere nach .json Dateien
    try:
        return filedialog.askopenfilename(
            title="Select a JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
    finally:
        root.destroy()

# Function to draw the board and update player status
def draw_board(canvas, log_entry, start_positions, move_from, move_to, knocked_piece):
    view = BoardView(canvas, start_positions=start_positions)
    return view.render(log_entry, move_from, move_to, knocked_piece)

def draw_piece(canvas, x, y, color):
    points = [x, y-15, x+10, y+15, x-10, y+15]
    canvas.create_polygon(points, fill=color, outline='black', width=4)
    canvas.create_oval(x-8, y-15, x+8, y+1, outline='black',  fill=color, width=4)

def draw_knocked_piece(canvas, x, y, color):
    points = [x-23, y+13, x+7, y+23, x+7, y+3]
    canvas.create_polygon(points, fill=color, outline='black', width=4)
    canvas.create_oval(x-31, y+6, x-15, y+21, outline='black',  fill=color, width=4)
    #canvas.create_oval(x-8, y-15, x+8, y+1, outline='black',  fill=color, width=4)
    
def draw_dice(canvas, rolls):
    dice_x = 310
    dice_y = 300
    dice_size = 50
    padding = 10
    for roll in rolls:
        draw_single_die(canvas, dice_x, dice_y, dice_size, roll)
        dice_x += dice_size + padding

def draw_single_die(canvas, x, y, size, roll):
    canvas.create_rectangle(x, y, x + size, y + size, outline='black', fill='white', width=2)
    spots = [(1, 1), (1, 3), (3, 1), (3, 3), (2, 2), (1, 2), (3, 2), (2, 1), (2, 3)]
    if roll == 1:
        draw_die_spot(canvas, x, y, size, spots[4])
    elif roll == 2:
        draw_die_spot(canvas, x, y, size, spots[0])
        draw_die_spot(canvas, x, y, size, spots[3])
    elif roll == 3:
        draw_die_spot(canvas, x, y, size, spots[0])
        draw_die_spot(canvas, x, y, size, spots[4])
        draw_die_spot(canvas, x, y, size, spots[3])
    elif roll == 4:
        draw_die_spot(canvas, x, y, size, spots[0])
        draw_die_spot(canvas, x, y, size, spots[1])
        draw_die_spot(canvas, x, y, size, spots[2])
        draw_die_spot(canvas, x, y, size, spots[3])
    elif roll == 5:
        draw_die_spot(canvas, x, y, size, spots[0])
        draw_die_spot(canvas, x, y, size, spots[1])
        draw_die_spot(canvas, x, y, size, spots[2])
        draw_die_spot(canvas, x, y, size, spots[3])
        draw_die_spot(canvas, x, y, size, spots[4])
    elif roll == 6:
        draw_die_spot(canvas, x, y, size, spots[0])
        draw_die_spot(canvas, x, y, size, spots[1])
        draw_die_spot(canvas, x, y, size, spots[2])
        draw_die_spot(canvas, x, y, size, spots[3])
        draw_die_spot(canvas, x, y, size, spots[5])
        draw_die_spot(canvas, x, y, size, spots[6])

def draw_die_spot(canvas, x, y, size, pos):
    offset = size // 4
    cx = x + pos[0] * offset
    cy = y + pos[1] * offset
    canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill='black')

def draw_move_arrow(canvas, move_from, move_to, color):
    angle_from = (move_from / 40) * 2 * np.pi
    x_from = 400 + int(300 * np.cos(angle_from))
    y_from = 400 + int(300 * np.sin(angle_from))
    
    angle_to = (move_to / 40) * 2 * np.pi
    x_to = 400 + int(300 * np.cos(angle_to))
    y_to = 400 + int(300 * np.sin(angle_to))
    
    canvas.create_line(x_from, y_from, x_to, y_to, fill=color, arrow=tk.LAST, width=2)

def initialize_canvas(game=None):
    root = tk.Tk()
    root.title("Mensch-Ärgere-Dich-Nicht")
    root.geometry('900x920')
    root.minsize(480, 560)
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    canvas = tk.Canvas(root, highlightthickness=0)
    canvas.grid(row=0, column=0, sticky='nsew')

    if game is None:
        start_positions = None
    else:
        start_positions = {
            name: {'start_pos': game.start_positions[index]}
            for index, name in enumerate(game.player_names)
        }

    return canvas, start_positions, root

class ReplayWindow:
    def __init__(self, game_log, game=None):
        if not game_log:
            raise ValueError('The game log is empty.')

        self.game_log = game_log
        self.frame_index = 0
        self.canvas, start_positions, self.root = initialize_canvas(game)
        self.board = BoardView(self.canvas, game=game, start_positions=start_positions)

        self.controls = tk.Frame(self.root)
        self.controls.grid(row=1, column=0, sticky='ew', pady=(4, 10))
        self.control_row = tk.Frame(self.controls)
        self.control_row.pack(anchor='center')
        self.prev_button = tk.Button(self.control_row, text="Previous", command=self.prev_frame)
        self.prev_button.pack(side='left', padx=4)
        self.turn_entry = tk.Entry(self.control_row, width=8, justify='center')
        self.turn_entry.pack(side='left', padx=4)
        self.go_button = tk.Button(self.control_row, text="Go to Turn", command=self.go_to_turn)
        self.go_button.pack(side='left', padx=4)
        self.next_button = tk.Button(self.control_row, text="Next", command=self.next_frame)
        self.next_button.pack(side='left', padx=4)

        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.canvas.bind('<Configure>', self.on_canvas_resize)
        self.render_current()

    def next_frame(self, event=None):
        if self.frame_index < len(self.game_log) - 1:
            self.frame_index += 1
            self.render_current()

    def prev_frame(self, event=None):
        if self.frame_index > 0:
            self.frame_index -= 1
            self.render_current()

    def go_to_turn(self):
        try:
            frame_num = int(self.turn_entry.get())
            if 0 <= frame_num < len(self.game_log):
                self.frame_index = frame_num
                self.render_current()
        except ValueError:
            pass

    def render_current(self):
        entry = self.game_log[self.frame_index]
        move_player = entry.get('player')
        move_from = None
        move_to = None
        knocked_piece = None

        if self.frame_index > 0:
            previous_entry = self.game_log[self.frame_index - 1]
            for player_name, pieces in entry['positions'].items():
                old_pieces = previous_entry['positions'].get(player_name, [])
                for old_piece, new_piece in zip(old_pieces, pieces):
                    if old_piece == new_piece:
                        continue
                    if new_piece == -1:
                        knocked_piece = (player_name, old_piece)
                    elif player_name == move_player:
                        move_from, move_to = old_piece, new_piece
                        break
                if move_from is not None:
                    break

        self.board.render(
            entry,
            move_from=move_from,
            move_to=move_to,
            knocked_piece=knocked_piece,
            move_player=move_player
        )

    def on_canvas_resize(self, event=None):
        if event is None or (event.width > 1 and event.height > 1):
            self.render_current()

    def run(self):
        self.root.mainloop()

    def close(self):
        self.root.quit()
        self.root.destroy()


def main(game_log=None, game=None, filename=None):
    if game_log is None:
        filename = filename or open_file_dialog()
        if not filename:
            return
        game_log = load_game_log(filename)

    if not game_log:
        return

    ReplayWindow(game_log, game=game).run()

if __name__ == "__main__":
    main()
