import json
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import patch
sys.path.append('../bin/')
sys.path.append('../')
from Game_class import Game_Mode
from Player_class import Player
from Simulate_Game import GameSession, simulate_game
from board_view import BoardView
import maedn_visualization
import maedn_PvE as pve_module
import maedn_statistic
from maedn_PvE import (
    PvEWindow,
    create_agents,
    create_game,
    load_game_modes,
    pve_output_directory,
    save_pve_game,
)

class FakeCanvas:
    def __init__(self, width=800, height=800):
        self.ovals = []
        self.oval_options = []
        self.rectangles = []
        self.lines = []
        self.bindings = {}
        self.texts = []
        self.text_items = []
        self.width = width
        self.height = height

    def delete(self, *args):
        self.ovals.clear()

    def create_oval(self, *args, **kwargs):
        self.ovals.append(args)
        self.oval_options.append(kwargs)

    def create_text(self, *args, **kwargs):
        self.texts.append(kwargs.get('text'))
        self.text_items.append((args, kwargs))

    def create_rectangle(self, *args, **kwargs):
        self.rectangles.append(args)

    def create_line(self, *args, **kwargs):
        self.lines.append(kwargs)

    def tag_bind(self, tag, event, callback):
        self.bindings[tag] = callback

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

def test_house_slots_are_drawn():
    game = Game_Mode("test_setup.json")
    canvas = FakeCanvas()
    view = BoardView(canvas, game=game)
    view.render({
        'round': 1,
        'rolls': [1],
        'player': 'Player 1',
        'positions': {
            'Player 1': ['house_1', 'house_2', -1, -1],
            'Player 2': [-1, -1, -1, -1]
        }
    })

    house_centers = [
        view._position_coordinates('Player 1', 'house_1'),
        view._position_coordinates('Player 1', 'house_2')
    ]
    drawn_centers = {
        ((oval[0] + oval[2]) // 2, (oval[1] + oval[3]) // 2)
        for oval in canvas.ovals
    }
    assert house_centers[0] != house_centers[1]
    assert all(center in drawn_centers for center in house_centers)
    player_labels = [
        (args, options)
        for args, options in canvas.text_items
        if options.get('text') == 'Player 1'
    ]
    assert len(player_labels) == 1
    label_args, label_options = player_labels[0]
    label_distance = (
        (label_args[0] - view.center_x) ** 2
        + (label_args[1] - view.center_y) ** 2
    ) ** 0.5
    assert label_distance < view.radius
    assert 'underline' in label_options['font']
    assert not any(
        options.get('text') == 'Player 1'
        and abs(args[0] - view.center_x) < 1
        and abs(args[1] - view.center_y) < 1
        for args, options in canvas.text_items
    )
    waiting_centers = [
        view._waiting_piece_coordinates(0, 2, index)
        for index in range(2)
    ]
    for center in waiting_centers:
        matching_options = [
            options
            for oval, options in zip(canvas.ovals, canvas.oval_options)
            if ((oval[0] + oval[2]) // 2, (oval[1] + oval[3]) // 2) == center
        ]
        assert matching_options and matching_options[-1]['fill'] == 'red'

    selected_actions = []
    actions = [
        {'piece_index': 0, 'from': 1, 'to': 2},
        {'piece_index': 1, 'from': 5, 'to': 6}
    ]
    letters = view.draw_action_arrows(
        'Player 1', actions, selected_actions.append, labels=['D', 'W']
    )
    assert letters == ['D', 'W']
    assert len(canvas.lines) == 2
    canvas.bindings['pve-action-1'](None)
    assert selected_actions == [actions[1]]
    dice_rectangles = canvas.rectangles
    assert len(dice_rectangles) == 1
    dice_center = (
        (dice_rectangles[0][0] + dice_rectangles[0][2]) / 2,
        (dice_rectangles[0][1] + dice_rectangles[0][3]) / 2
    )
    assert abs(dice_center[0] - view.center_x) < 1
    assert abs(dice_center[1] - view.center_y) < view.radius * 0.1

    canvas.width = 600
    canvas.height = 500
    view.render({'positions': {'Player 1': ['house_1', -1, -1, -1]}})
    first_track = canvas.ovals[1]
    assert ((first_track[0] + first_track[2]) // 2, (first_track[1] + first_track[3]) // 2) == (465, 250)

    ring_points = [view._waiting_piece_coordinates(0, 4, index) for index in range(4)]
    ring_center = (view.radius + min(55, view.height * 0.11) + view.center_x, view.center_y)
    ring_radii = [
        ((x - ring_center[0]) ** 2 + (y - ring_center[1]) ** 2) ** 0.5
        for x, y in ring_points
    ]
    assert max(ring_radii) - min(ring_radii) <= 1

def test_output_folder_and_dialog_cleanup():
    game = Game_Mode("test_setup.json")
    output_folder = Path(game.out_folder)
    assert output_folder.parent.name == 'output'
    assert output_folder.parent.parent.name == 'maedpy'

    class FakeRoot:
        destroyed = False

        def withdraw(self):
            pass

        def destroy(self):
            self.destroyed = True

    root = FakeRoot()
    with patch.object(maedn_visualization.tk, 'Tk', return_value=root):
        with patch.object(maedn_visualization.filedialog, 'askopenfilename', return_value=''):
            assert maedn_visualization.open_file_dialog() == ''
    assert root.destroyed

    class FakeWindowRoot:
        quit_called = False
        destroyed = False

        def quit(self):
            self.quit_called = True

        def destroy(self):
            self.destroyed = True

    window_root = FakeWindowRoot()
    replay_window = maedn_visualization.ReplayWindow.__new__(maedn_visualization.ReplayWindow)
    replay_window.root = window_root
    replay_window.close()
    assert window_root.quit_called and window_root.destroyed

def test_statistic_outputs_use_output_subfolder():
    log = [{
        'round': 1,
        'player': 'P',
        'roll number': 1,
        'in_play': 1,
        'in_house': 0,
        'deliberate_moves': 0,
        'positions': {'P': [0, -1]}
    }]
    with tempfile.TemporaryDirectory() as directory:
        output_root = Path(directory) / 'output' / 'statistic'
        target = maedn_statistic.statistic_output_directory(
            Path(directory) / 'selected_setup',
            output_root
        )
        maedn_statistic.process_game_data([log], target / 'time_dep.json')
        maedn_statistic.analyze_game_states([log], target / 'game_end.json')
        assert target == output_root / 'selected_setup'
        assert (target / 'time_dep.json').is_file()
        assert (target / 'game_end.json').is_file()

def test_pve_mode_and_animation_frames():
    game = create_game()
    assert game.n_players == 4 and game.size == 40
    agents = create_agents(game.n_players)
    assert agents[0].requires_input
    assert all(not agent.requires_input for agent in agents[1:])

    session = GameSession(
        game,
        agents=agents,
        dice_rolls=[3],
        start_positions={
            0: [1, 37, -1, -1],
            1: [-1, -1, -1, -1],
            2: [-1, -1, -1, -1],
            3: [-1, -1, -1, -1]
        }
    )
    decision = session.advance()
    assert decision['type'] == 'decision_required'
    house_action = next(action for action in decision['actions'] if action['kind'] == 'house_entry')
    event = session.choose_action(house_action)

    window = PvEWindow.__new__(PvEWindow)
    window.game = game
    window.session = session
    frames = window._build_animation_frames(event)
    assert len(frames) == 1
    assert frames[0]['positions']['Player 1'][1] == 'house_1'

    class FakeStatus:
        value = ''
        values = {}

        def set(self, value):
            self.value = value

        def configure(self, **kwargs):
            self.values.update(kwargs)

    class FakeRoot:
        callbacks = []

        def after_idle(self, callback):
            self.callbacks.append(callback)
            return len(self.callbacks)

        def after(self, delay, callback):
            self.callbacks.append(callback)
            return len(self.callbacks)

        def after_cancel(self, callback_id):
            pass

    class FakeSession:
        finished = False
        roll_num = 4
        calls = 0
        players = [type('FakePlayer', (), {'name': 'Player 1', 'start_pos': 0})()]

        def advance(self):
            self.calls += 1
            if self.calls == 1:
                return {'type': 'turn_completed', 'player': 'Player 2', 'rolls': [2]}
            return {
                'type': 'decision_required',
                'player': 'Player 1',
                'roll': 3,
                'rolls': [3],
                'actions': [{'piece_index': 0, 'from': 1, 'to': 4}],
                'state': {'positions': {'Player 1': [1, -1, -1, -1]}}
            }

    class FakeBoard:
        renders = 0
        actions = []

        def render(self, state):
            self.renders += 1

        def draw_action_arrows(self, player, actions, callback, labels=None):
            self.actions = actions
            return labels

    choice_window = PvEWindow.__new__(PvEWindow)
    choice_window.game = game
    choice_window.session = session
    choice_window.board = FakeBoard()
    choice_window.status_var = FakeStatus()
    choice_window.pending_actions = []
    ahead_action = {'piece_index': 0, 'from': 2, 'to': 7}
    behind_action = {'piece_index': 1, 'from': 25, 'to': 1}
    choice_window._show_decisions('Player 1', [behind_action, ahead_action], 5)
    assert choice_window.pending_actions == [ahead_action, behind_action]
    assert choice_window.pending_action_labels == ['D', 'W']
    selected_actions = []
    choice_window._choose_action = selected_actions.append
    choice_window._handle_action_key(SimpleNamespace(char='w'))
    assert selected_actions == [behind_action]

    skip_window = PvEWindow.__new__(PvEWindow)
    skip_window.session = FakeSession()
    skip_window.game = game
    skip_window.root = FakeRoot()
    skip_window.board = FakeBoard()
    skip_window.status_var = FakeStatus()
    skip_window.pause_button = FakeStatus()
    skip_window.step_button = FakeStatus()
    skip_window.after_id = None
    skip_window.skip_animation = True
    skip_window._advance_game()
    assert skip_window.session.calls == 1 and skip_window.board.renders == 0
    skip_window.root.callbacks.pop(0)()
    assert skip_window.session.calls == 2
    assert skip_window.board.renders == 1
    assert skip_window.board.actions[0]['piece_index'] == 0

def test_pause_resume_and_pve_save():
    class FakeRoot:
        cancelled = []
        scheduled = []

        def after_cancel(self, callback_id):
            self.cancelled.append(callback_id)

        def after(self, delay, callback):
            self.scheduled.append((delay, callback))
            return 22

    class FakeButton:
        values = {}

        def configure(self, **kwargs):
            self.values.update(kwargs)

    class FakeStatus:
        def set(self, value):
            self.value = value

    window = PvEWindow.__new__(PvEWindow)
    window.root = FakeRoot()
    window.pause_button = FakeButton()
    window.step_button = FakeButton()
    window.status_var = FakeStatus()
    window.animation_frames = [{}, {}, {}]
    window.animation_index = 1
    window.after_id = 17
    window.frame_delay = 300
    window.skip_animation = False
    window.is_paused = False
    window.waiting_to_start = False

    window.toggle_pause()
    assert window.is_paused and window.after_id is None
    assert window.animation_index == 1 and window.pause_button.values['text'] == 'Play'
    window.toggle_pause()
    assert not window.is_paused and window.after_id == 22
    assert window.root.scheduled[-1][0] == 300

    step_window = PvEWindow.__new__(PvEWindow)
    step_window.is_paused = True
    step_window.skip_animation = False
    step_window.animation_frames = [{'frame': 1}, {'frame': 2}]
    step_window.animation_index = 0
    step_window.step_button = FakeButton()
    rendered_frames = []
    step_window._render_state = rendered_frames.append
    step_window.step_frame()
    assert rendered_frames == [{'frame': 1}]
    assert step_window.animation_index == 1
    assert step_window.step_button.values['state'] == 'normal'
    step_window.step_frame()
    assert rendered_frames == [{'frame': 1}, {'frame': 2}]
    assert step_window.animation_index == 0
    assert step_window.animation_frames == []
    assert step_window.step_button.values['state'] == 'normal'

    step_window.pending_actions = []
    step_window._advance_game = lambda: (
        setattr(step_window, 'animation_frames', [{'frame': 3}]),
        setattr(step_window, 'animation_index', 0),
        setattr(step_window, 'is_paused', True)
    )
    step_window.step_frame()
    assert rendered_frames[-1] == {'frame': 3}

    log = [{'player': 'Player 1', 'rolls': [2], 'positions': {'Player 1': [1, -1]}}]
    assert pve_output_directory().parent.name == 'output'
    assert pve_output_directory().name == 'pve'
    setup_directory = pve_output_directory(create_game())
    assert setup_directory.parent.name == 'pve'
    assert setup_directory.name == Path(create_game().out_folder).name
    names = [mode['name'] for mode in load_game_modes()]
    assert len(names) >= 2 and len(set(names)) == len(names)
    assert pve_output_directory(create_game(), names[0]).name == names[0]
    modes = {mode['name']: mode['parameters'] for mode in load_game_modes()}
    assert all(mode['n_players'] >= 2 for mode in modes.values())
    with tempfile.TemporaryDirectory() as directory:
        filepath = save_pve_game(log, output_dir=directory)
        assert filepath.name.startswith('pve_game_')
        assert json.loads(filepath.read_text(encoding='utf-8')) == log

def test_game_end_auto_save_and_restart():
    root = tk.Tk()
    root.withdraw()
    window = PvEWindow(root)
    names = [mode['name'] for mode in load_game_modes()]
    assert window.selected_mode_name == names[0] and window.mode_var.get() == names[0]
    assert window.waiting_to_start
    modes_by_name = {m['name']: m['parameters'] for m in load_game_modes()}
    window.start_game(names[0])
    assert window.mode_menu.cget('values') == tuple(names)
    assert window.selected_mode_name == names[0]
    two_player = next(n for n in names if modes_by_name[n]['n_players'] == 2)
    window.start_game(two_player)
    assert window.game.n_players == 2
    assert window.mode_menu.winfo_exists()
    window.start_game(names[0])
    assert window.speed_var.get() == 'Skip'
    assert window.session.roll_num == 0
    assert window.waiting_to_start and window.is_paused
    assert window.pause_button.cget('text') == 'Play'
    window._cancel_pending_callback()
    window.session.winner = window.session.players[0].name
    window.session.log = [{
        'player': window.session.winner,
        'rolls': [1],
        'positions': window.session.snapshot()['positions']
    }]
    window.game_end_handled = False
    expected_path = Path('auto-saved-pve-game.json')

    with patch.object(pve_module, 'save_pve_game', return_value=expected_path) as save_game:
        window._handle_game_end()
        save_game.assert_called_once_with(
            window.session.log, game=window.game, mode_name=names[0]
        )

    root.update_idletasks()
    assert window.saved_path == expected_path
    assert window.status_var.get() == 'YOU WIN! CONGRATULATIONS'
    assert not hasattr(window, 'end_dialog')
    assert window.after_id is not None
    window._restart_after_game_end()
    assert window.selected_mode_name == names[0]
    assert window.session.winner is None and not window.waiting_to_start
    window._cancel_pending_callback()
    assert window.mode_menu.winfo_exists()
    root.destroy()

def test_house_slots():
    game = Game_Mode("test_setup.json")
    waiting_log = simulate_game(
        game,
        dice_rolls=[5],
        start_positions={
            0: [30, -1, -1, -1],
            1: [-1, -1, -1, -1]
        }
    )
    assert waiting_log[0]['positions']['Player 1'] == [30, -1, -1, -1]

    players = [Player(game, index) for index in range(game.n_players)]
    player = players[1]
    player.pieces = [9, 8, 7, 6]

    assert not player.can_move(9, 5, game)

    def move_piece(piece_index, roll):
        current_position = player.pieces[piece_index]
        assert player.can_move(current_position, roll, game)
        player.move_piece(players, piece_index, roll, game)

    move_piece(0, 1)
    assert player.pieces[0] == 'house_1'
    assert not player.can_move(8, 3, game)
    move_piece(0, 1)
    move_piece(1, 2)
    move_piece(0, 1)
    move_piece(1, 1)
    move_piece(2, 3)
    move_piece(0, 1)
    move_piece(1, 1)
    move_piece(2, 1)
    move_piece(3, 4)

    assert set(player.pieces) == {'house_1', 'house_2', 'house_3', 'house_4'}
    assert player.count_in_house() == 4
    assert player.finished_pieces == 4

def main():
    
    ' The first player knocks out the piece on 3 and then the second player'
    ' moves his piece in the house'
    
    # Game setup and manually change parameters
    game_setup = Game_Mode("test_setup.json")

    # Define a starting position for each player 
    starting_positions = {
        0: [0, -1, -1, -1],  # Player 1 has one piece on the start position
        1: [3, 8, -1, -1]
    }
    
    #  consecutive rolls of a 6 
    dice_rolls = [3, 2]

    # run game
    game_log = simulate_game(game_setup, dice_rolls, starting_positions)
    
    # expected outcome
    result = [-1, 'house_1', -1, -1]

    
    if game_log[1]['positions']['Player 2'] == result:
        print("Test knock and move PASSED")
    else: 
        print("Test knock and mov FAILED")

    test_house_slots()
    print("Test house slots PASSED")
    test_house_slots_are_drawn()
    print("Test house slot rendering PASSED")
    test_output_folder_and_dialog_cleanup()
    print("Test output folder and dialog cleanup PASSED")
    test_statistic_outputs_use_output_subfolder()
    print("Test statistic output folder PASSED")
    test_pve_mode_and_animation_frames()
    print("Test PvE mode and animation frames PASSED")
    test_pause_resume_and_pve_save()
    print("Test pause/resume and PvE save PASSED")
    test_game_end_auto_save_and_restart()
    print("Test game-end dialog and new game PASSED")
    
if __name__ == "__main__":
    main()