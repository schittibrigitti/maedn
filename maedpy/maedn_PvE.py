import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from datetime import datetime

PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in __import__('sys').path:
    __import__('sys').path.insert(0, str(PACKAGE_DIR))

try:
    from .bin.Game_class import Game_Mode
    from .bin.Simulate_Game import GameSession, HumanAgent, RandomAgent
    from .board_view import BoardView
    from .sound import VolumeButton, play_ping
except ImportError:
    from bin.Game_class import Game_Mode
    from bin.Simulate_Game import GameSession, HumanAgent, RandomAgent
    from board_view import BoardView
    from sound import VolumeButton, play_ping


CLASSIC_DEFAULTS = {
    'n_players': 4,
    'n_pieces': 4,
    'n_pieces_to_win': 4,
    'n_dice_sides': 6,
    'start_to_start_distance': 10,
    'n_rerolls': 3,
    'clear_start_on_non_six': True,
    'knock_duty': True
}
GAME_RESTART_DELAY_MS = 5000
BANNER_STEP_MS = 30
DEFAULT_VOLUME_LEVEL = 2
FRAME_SPEEDS = {
    'Skip': None,
    'Manual': None,
    'normal': 500,
    'fast': 100
}
ACTION_KEYS = ('d', 'w', 'a', 's')
GAME_MODES_PATH = PACKAGE_DIR / 'game_mode.json'


def action_labels(count):
    keys = [key.upper() for key in ACTION_KEYS[:count]]
    return keys + [str(index + 1) for index in range(len(keys), count)]


def create_game(parameters=None):
    values = dict(CLASSIC_DEFAULTS)
    if parameters:
        values.update(parameters)
    return Game_Mode(values)


def parameters_for_game(game):
    return {
        'n_players': game.n_players,
        'n_pieces': game.n_pieces,
        'n_pieces_to_win': game.n_pieces_to_win,
        'n_dice_sides': game.n_dice_sides,
        'start_to_start_distance': game.start_to_start_distance,
        'n_rerolls': game.n_rerolls,
        'clear_start_on_non_six': game.clear_start_on_non_six,
        'knock_duty': game.knock_duty
    }


def load_game_modes(filepath=GAME_MODES_PATH):
    with Path(filepath).open(encoding='utf-8') as modes_file:
        modes = json.load(modes_file)
    if not isinstance(modes, list) or not modes:
        raise ValueError('game_mode.json must contain a non-empty list.')

    names = set()
    for mode in modes:
        if not isinstance(mode, dict) or not isinstance(mode.get('name'), str) or not mode['name'].strip():
            raise ValueError('Every game mode must have a non-empty name.')
        if mode['name'] != mode['name'].strip() or Path(mode['name']).name != mode['name']:
            raise ValueError(f"Game mode name is not a valid folder name: {mode['name']}")
        if mode['name'] in names:
            raise ValueError(f"Duplicate game mode name: {mode['name']}")
        if not isinstance(mode.get('parameters'), dict):
            raise ValueError(f"Game mode {mode['name']} must contain a parameters object.")
        names.add(mode['name'])
    return modes


def create_agents(n_players):
    if n_players < 1:
        raise ValueError('The game must have at least one player.')
    return [HumanAgent()] + [RandomAgent() for _ in range(n_players - 1)]


def pve_output_directory(game=None, mode_name=None):
    directory = PACKAGE_DIR / 'output' / 'pve'
    if game is not None:
        directory /= mode_name or Path(game.out_folder).name
    return directory


def save_pve_game(game_log, game=None, output_dir=None, mode_name=None):
    if not game_log:
        raise ValueError('There is no completed game to save.')

    directory = Path(output_dir) if output_dir is not None else pve_output_directory(game, mode_name)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"pve_game_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')}.json"
    filepath = directory / filename
    with filepath.open('w', encoding='utf-8') as game_file:
        json.dump(game_log, game_file, indent=4)
    return filepath


class PvEWindow:
    def __init__(self, root=None):
        self.root = root or tk.Tk()
        self.root.title('Mensch ärgere Dich nicht - PvE')
        self.root.geometry('1040x940')
        self.root.minsize(620, 640)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.after_id = None
        self.game = None
        self.session = None
        self.board = None
        self.frame_delay = 1000
        self.skip_animation = False
        self.is_paused = False
        self.manual_mode = False
        self.waiting_to_start = False
        self.animation_frames = []
        self.animation_index = 0
        self.display_state = None
        self.pending_actions = []
        self.pending_player = None
        self.pending_action_labels = []
        self.game_modes = load_game_modes()
        self.game_modes_by_name = {mode['name']: mode for mode in self.game_modes}
        self.selected_mode_name = None
        self.saved_path = None
        self.game_end_handled = False
        self.games_finished = 0
        self.volume_level = DEFAULT_VOLUME_LEVEL
        self._build_game_panel()
        self.status_var.set('Select a game mode to start')
        if self.game_modes:
            self.start_game(self.game_modes[0]['name'])

    def start_game(self, mode_name=None):
        mode_name = mode_name or self.mode_var.get()
        if mode_name not in self.game_modes_by_name:
            return
        self._cancel_pending_callback()
        try:
            parameters = dict(self.game_modes_by_name[mode_name]['parameters'])
            if parameters['n_pieces_to_win'] > parameters['n_pieces']:
                raise ValueError('Pieces needed to win cannot exceed pieces per player.')
            self.game = create_game(parameters)
            self.game_parameters = parameters
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror('Invalid game mode', str(error), parent=self.root)
            return

        self.selected_mode_name = mode_name
        self.session = GameSession(
            self.game,
            agents=create_agents(self.game.n_players)
        )
        self.saved_path = None
        self.game_end_handled = False
        self.pending_actions = []
        self.pending_action_labels = []
        self.pending_player = None
        self.animation_frames = []
        self.animation_index = 0
        self.display_state = None
        self.manual_mode = False
        self.waiting_to_start = True
        self.board = BoardView(self.canvas, game=self.game)
        self.skip_animation = self.speed_var.get() == 'Skip'
        self.manual_mode = self.speed_var.get() == 'Manual'
        self.frame_delay = FRAME_SPEEDS[self.speed_var.get()] or 0
        self.is_paused = True
        self.pause_button.configure(text='Play', state='normal')
        self.step_button.configure(state='disabled')
        self.mode_var.set(mode_name)
        self.status_var.set(f'{mode_name} - Paused - press Play to start')
        self._render_state(self.session.snapshot())
        if self.games_finished > 0:
            self.toggle_pause()

    def _build_game_panel(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.game_frame = ttk.Frame(self.root, padding=(12, 8))
        self.game_frame.grid(row=0, column=0, sticky='nsew')
        self.game_frame.grid_columnconfigure(0, weight=1)
        self.game_frame.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(self.game_frame)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        header.grid_columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value='Select a game mode to start')
        ttk.Label(header, textvariable=self.status_var, font=('Segoe UI', 12, 'bold')).grid(
            row=0, column=0, sticky='w'
        )

        self.mode_var = tk.StringVar(value='')
        self.mode_menu = ttk.Combobox(
            header,
            values=tuple(self.game_modes_by_name),
            textvariable=self.mode_var,
            state='readonly',
            width=max(16, max(map(len, self.game_modes_by_name), default=0) + 2)
        )
        self.mode_menu.grid(row=0, column=1, sticky='e', padx=(8, 8))
        self.mode_menu.bind('<<ComboboxSelected>>', self._on_mode_selected)

        speed_controls = ttk.Frame(header)
        speed_controls.grid(row=0, column=2, sticky='e')
        ttk.Label(speed_controls, text='Frame speed').pack(side='left', padx=(0, 8))
        self.speed_var = tk.StringVar(value='Skip')
        self.speed_menu = ttk.Combobox(
            speed_controls,
            values=tuple(FRAME_SPEEDS),
            textvariable=self.speed_var,
            state='readonly',
            width=7
        )
        self.speed_menu.pack(side='left')
        self.speed_menu.bind('<<ComboboxSelected>>', self._update_speed)
        self.pause_button = ttk.Button(
            speed_controls,
            text='Pause',
            command=self.toggle_pause,
            state='disabled'
        )
        self.pause_button.pack(side='left', padx=(10, 4))
        self.step_button = ttk.Button(
            speed_controls,
            text='Next frame',
            command=self.step_frame,
            state='disabled'
        )
        self.step_button.pack(side='left', padx=4)
        self.volume_button = VolumeButton(speed_controls, level=self.volume_level)
        self.volume_button.pack(side='left', padx=(10, 0))
        self.canvas = tk.Canvas(self.game_frame, background='white', highlightthickness=1, highlightbackground='#cbd5e1')
        self.canvas.grid(row=1, column=0, sticky='nsew')
        self.board = BoardView(self.canvas)
        self.canvas.bind('<Configure>', self._on_canvas_resize)
        self.root.bind_all('<KeyPress>', self._handle_action_key)

    def _on_mode_selected(self, event=None):
        self.start_game(self.mode_var.get())

    def _update_speed(self, event=None):
        selected_speed = self.speed_var.get()
        self.skip_animation = selected_speed == 'Skip'
        self.manual_mode = selected_speed == 'Manual'
        self.frame_delay = FRAME_SPEEDS[selected_speed] or 0

        if self.waiting_to_start:
            return

        if self.skip_animation and (self.after_id is not None or self.is_paused):
            self._cancel_pending_callback()
            self.animation_frames = []
            self.animation_index = 0
            self.is_paused = False
            self.manual_mode = False
            self.pause_button.configure(text='Pause', state='disabled')
            self.step_button.configure(state='disabled')
            self._render_state(self.session.snapshot())
            self.after_id = self.root.after_idle(self._advance_game)
        elif self.manual_mode:
            if self.after_id is not None:
                self._cancel_pending_callback()
                self.is_paused = True
            if self.is_paused or not self.pending_actions:
                self.pause_button.configure(text='Play', state='normal')
                self.step_button.configure(state='normal')
        elif self.after_id is not None or self.is_paused:
            self._cancel_pending_callback()
            self.is_paused = False
            self.pause_button.configure(text='Pause', state='normal')
            self.step_button.configure(state='disabled')
            if self.animation_frames and self.animation_index < len(self.animation_frames):
                self.after_id = self.root.after(self.frame_delay, self._render_next_frame)
            else:
                self.after_id = self.root.after_idle(self._advance_game)

    def _on_canvas_resize(self, event):
        if self.board is None or self.display_state is None:
            return
        self._render_state(self.display_state)
        if self.pending_actions:
            self.board.draw_action_arrows(
                self.pending_player,
                self.pending_actions,
                self._choose_action,
                self.pending_action_labels
            )

    def _is_animating(self):
        return self.after_id is not None

    def _advance_game(self):
        self.after_id = None
        if self.session.finished:
            self._handle_game_end()
            return

        result = self.session.advance()
        if result['type'] == 'decision_required':
            display_state = dict(result['state'])
            display_state.update({
                'player': result['player'],
                'roll number': self.session.roll_num,
                'rolls': result['rolls']
            })
            self._render_state(display_state)
            if self.manual_mode:
                self.is_paused = True
                self.pause_button.configure(text='Manual', state='disabled')
            else:
                self.pause_button.configure(text='Pause', state='disabled')
            self.step_button.configure(state='disabled')
            self._show_decisions(result['player'], result['actions'], result['roll'])
            return

        if result['type'] == 'finished':
            self._handle_game_end()
            return

        if result['type'] == 'input_exhausted':
            self.status_var.set('Dice input exhausted')
            return

        self._play_house_sound(result)
        self.status_var.set(f"{result['player']} rolled {', '.join(map(str, result['rolls']))}")
        if self.skip_animation:
            self.manual_mode = False
            self.pause_button.configure(state='disabled')
            self.step_button.configure(state='disabled')
            self.after_id = self.root.after_idle(self._advance_game)
            return

        frames = self._build_animation_frames(result)
        if self.manual_mode:
            self.animation_frames = frames
            self.animation_index = 0
            self.is_paused = True
            self.pause_button.configure(text='Manual', state='disabled')
            self.step_button.configure(state='normal')
            if not frames:
                display_state = dict(result['state'])
                display_state.update({
                    'player': result['player'],
                    'rolls': result['rolls']
                })
                self._render_state(display_state)
            return

        if frames:
            self._play_frames(frames, 0)
        else:
            self._render_state(result['state'])
            self.after_id = self.root.after(self.frame_delay, self._finish_animated_turn)

    def _build_animation_frames(self, event):
        actor_moves = [
            move for move in event['moves']
            if move['player'] == event['player'] and move['to'] != -1
        ]
        if not actor_moves:
            return []

        move = actor_moves[0]
        player_index = next(
            index for index, player in enumerate(self.session.players)
            if player.name == move['player']
        )
        player = self.session.players[player_index]
        path = self._piece_path(move['from'], move['to'], player.end_pos)
        if not path:
            return []

        before_positions = {
            name: list(pieces)
            for name, pieces in event['previous_state']['positions'].items()
        }
        positions = {name: list(pieces) for name, pieces in before_positions.items()}
        positions[move['player']][move['piece_index']] = path[-1]
        frame = dict(event['state'])
        frame.update({
            'player': event['player'],
            'rolls': event['rolls'],
            'positions': positions
        })
        return [frame]

    def _piece_path(self, start, destination, end_position):
        if start == -1 or not isinstance(start, (int, str)):
            return [destination]

        if isinstance(start, str) and start.startswith('house_'):
            start_slot = int(start.split('_', 1)[1])
            end_slot = int(destination.split('_', 1)[1])
            return [f'house_{slot}' for slot in range(start_slot + 1, end_slot + 1)]

        if not isinstance(start, int):
            return [destination]

        if isinstance(destination, int):
            distance = (destination - start) % self.game.size
            if distance == 0:
                return [destination]
            return [(start + step) % self.game.size for step in range(1, distance + 1)]

        if isinstance(destination, str) and destination.startswith('house_'):
            steps_to_house = (end_position - start) % self.game.size + 1
            path = [(start + step) % self.game.size for step in range(1, steps_to_house)]
            target_slot = int(destination.split('_', 1)[1])
            path.extend(f'house_{slot}' for slot in range(1, target_slot + 1))
            return path

        return [destination]

    def _play_frames(self, frames, index):
        self.animation_frames = frames
        self.animation_index = index
        self.is_paused = False
        self.manual_mode = False
        self.pause_button.configure(text='Pause', state='normal')
        self.step_button.configure(state='disabled')
        self._render_next_frame()

    def _render_next_frame(self):
        self.after_id = None
        if self.is_paused:
            return
        if self.animation_index >= len(self.animation_frames):
            self.animation_frames = []
            self.pause_button.configure(text='Pause', state='disabled')
            self.step_button.configure(state='disabled')
            self.after_id = None
            self._finish_animated_turn()
            return

        frame = self.animation_frames[self.animation_index]
        self.animation_index += 1
        self._render_state(frame)
        self.after_id = self.root.after(
            self.frame_delay,
            self._render_next_frame
        )

    def toggle_pause(self):
        if self.waiting_to_start:
            self.waiting_to_start = False
            if self.manual_mode:
                self.is_paused = True
                self.pause_button.configure(text='Manual', state='disabled')
                self.step_button.configure(state='normal')
                self.status_var.set('Manual - click Next frame to continue')
            elif self.skip_animation:
                self.is_paused = False
                self.pause_button.configure(state='disabled')
                self.after_id = self.root.after_idle(self._advance_game)
            else:
                self.is_paused = False
                self.pause_button.configure(text='Pause', state='normal')
                self.after_id = self.root.after(self.frame_delay, self._advance_game)
            return

        if self.skip_animation:
            return

        if self.is_paused:
            self.is_paused = False
            self.manual_mode = False
            self.pause_button.configure(text='Pause', state='normal')
            self.step_button.configure(state='disabled')
            if self.animation_index < len(self.animation_frames):
                self.after_id = self.root.after(self.frame_delay, self._render_next_frame)
            else:
                self.after_id = self.root.after_idle(self._advance_game)
            return

        if not self.animation_frames:
            return
        self._cancel_pending_callback()
        self.is_paused = True
        self.pause_button.configure(text='Play', state='normal')
        self.step_button.configure(state='normal')
        self.status_var.set('Paused')

    def step_frame(self):
        if not self.is_paused:
            self.step_button.configure(state='disabled')
            return

        self.manual_mode = True
        if self.animation_index >= len(self.animation_frames):
            self.animation_frames = []
            self.animation_index = 0
            self._advance_game()
            if self.pending_actions or not self.is_paused:
                return
            if not self.animation_frames:
                self.step_button.configure(state='normal')
                return

        frame = self.animation_frames[self.animation_index]
        self.animation_index += 1
        self._render_state(frame)
        self.step_button.configure(state='normal')
        if self.animation_index >= len(self.animation_frames):
            self.animation_frames = []
            self.animation_index = 0

    def _finish_animated_turn(self):
        self.after_id = None
        self.animation_frames = []
        self.is_paused = False
        self.pause_button.configure(text='Pause', state='disabled')
        self.step_button.configure(state='disabled')
        self._advance_game()

    def _show_decisions(self, player, actions, roll):
        self.pending_player = player
        player_state = next(item for item in self.session.players if item.name == player)

        def progress(action):
            destination = action['to']
            if isinstance(destination, str) and destination.startswith('house_'):
                return self.game.size + int(destination.split('_', 1)[1])
            if destination == 'house':
                return self.game.size + 1
            if isinstance(destination, int):
                return (destination - player_state.start_pos) % self.game.size
            return -1

        actions = sorted(actions, key=progress, reverse=True)
        self.pending_actions = actions
        self.pending_action_labels = action_labels(len(actions))
        letters = self.board.draw_action_arrows(
            player,
            actions,
            self._choose_action,
            self.pending_action_labels
        )
        choices = ', '.join(letters)
        keyboard_choices = ', '.join(
            f'{key.upper()} (Figur {index + 1})'
            for index, key in enumerate(ACTION_KEYS[:len(actions)])
        )
        self.status_var.set(
            f'{player} rolled {roll} - click {choices} or press {keyboard_choices}'
        )

    def _handle_action_key(self, event):
        key = event.char.lower()
        if key not in ACTION_KEYS:
            return
        action_index = ACTION_KEYS.index(key)
        if action_index < len(self.pending_actions):
            self._choose_action(self.pending_actions[action_index])

    def _choose_action(self, action):
        result = self.session.choose_action(action)
        self.pending_player = None
        self.pending_actions = []
        self.pending_action_labels = []
        self._play_house_sound(result)
        self.status_var.set(f"{result['player']} selected a move")
        if self.skip_animation:
            self._render_state(result['state'])
            self.after_id = self.root.after_idle(self._advance_game)
            return

        frames = self._build_animation_frames(result)
        if self.manual_mode:
            self.animation_frames = frames
            self.animation_index = 0
            self.is_paused = True
            self.pause_button.configure(text='Manual', state='disabled')
            self.step_button.configure(state='normal')
            if not frames:
                self._render_state(result['state'])
            return

        if frames:
            self._play_frames(frames, 0)
        else:
            self._render_state(result['state'])
            self.after_id = self.root.after(self.frame_delay, self._finish_animated_turn)

    def _play_house_sound(self, result):
        entered_house = any(
            isinstance(move['to'], str) and move['to'].startswith('house')
            and not (isinstance(move['from'], str) and move['from'].startswith('house'))
            for move in result.get('moves', [])
        )
        if entered_house:
            play_ping(self.volume_button.level)

    def _render_state(self, state):
        self.display_state = state
        self.board.render(state)

    def _handle_game_end(self):
        if self.game_end_handled:
            return
        self.game_end_handled = True
        self.games_finished += 1
        self._render_state(self.session.snapshot())
        human_won = self.session.winner == self.session.players[0].name
        message = 'YOU WIN! CONGRATULATIONS' if human_won else f"{self.session.winner} wins"
        self.status_var.set(message)
        self._scroll_banner(message)
        self.pause_button.configure(state='disabled')
        self.step_button.configure(state='disabled')

        try:
            self.saved_path = save_pve_game(
                self.session.log,
                game=self.game,
                mode_name=self.selected_mode_name
            )
        except OSError as error:
            self.saved_path = None
            messagebox.showerror('Could not save game', str(error), parent=self.root)
        self.after_id = self.root.after(GAME_RESTART_DELAY_MS, self._restart_after_game_end)

    def _restart_after_game_end(self):
        self.after_id = None
        self.start_game(self.selected_mode_name)

    def _scroll_banner(self, text):
        # Text läuft einmal von rechts nach links über das Spielfeld
        self.canvas.update_idletasks()
        width = max(self.canvas.winfo_width(), 1)
        item = self.canvas.create_text(
            width, self.canvas.winfo_height() / 2, text=text, anchor='w',
            font=('Segoe UI', 40, 'bold'), fill='#c0392b'
        )
        end_x = -(self.canvas.bbox(item)[2] - self.canvas.bbox(item)[0])
        steps = max(1, (GAME_RESTART_DELAY_MS - 200) // BANNER_STEP_MS)
        dx = (end_x - width) / steps
        self._banner_step(item, dx, steps)

    def _banner_step(self, item, dx, steps_left):
        self.banner_id = None
        if steps_left <= 0:
            self.canvas.delete(item)
            return
        self.canvas.move(item, dx, 0)
        self.banner_id = self.root.after(
            BANNER_STEP_MS, self._banner_step, item, dx, steps_left - 1
        )

    def _cancel_pending_callback(self):
        banner_id = getattr(self, 'banner_id', None)
        if banner_id is not None:
            try:
                self.root.after_cancel(banner_id)
            except tk.TclError:
                pass
            self.banner_id = None
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

    @staticmethod
    def _position_label(position):
        if isinstance(position, int):
            return f'Field {position}'
        if isinstance(position, str) and position.startswith('house_'):
            return f'House slot {position.split("_", 1)[1]}'
        return str(position)

    @staticmethod
    def _action_label(kind):
        return {
            'capture': 'capture',
            'house_entry': 'enter house',
            'house_advance': 'advance in house',
            'move': 'move'
        }.get(kind, kind)

    def close(self):
        self._cancel_pending_callback()
        self.root.destroy()


def main():
    root = tk.Tk()
    PvEWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
