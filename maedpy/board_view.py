from math import cos, pi, sin


PLAYER_COLORS = [
    'red', 'blue', 'green', 'orange', 'purple', 'brown',
    'cyan', 'magenta', 'gold', 'turquoise'
]


def is_house_position(position):
    return position == 'house' or (
        isinstance(position, str) and position.startswith('house_')
    )


class BoardView:
    """Reusable Tk canvas renderer for game snapshots and replay log entries."""

    def __init__(self, canvas, game=None, start_positions=None, width=800, height=800):
        self.canvas = canvas
        self.game = game
        self.width = width
        self.height = height
        self.default_width = width
        self.default_height = height
        self.size = getattr(game, 'size', 40)
        self.n_pieces = getattr(game, 'n_pieces', 4)
        self.center_x = width / 2
        self.center_y = height / 2
        self.radius = min(width, height) * 0.33

        if start_positions is None and game is not None:
            start_positions = {
                name: {'start_pos': game.start_positions[index]}
                for index, name in enumerate(game.player_names)
            }
        elif start_positions is None:
            start_positions = {
                'Player 1': {'start_pos': 0},
                'Player 2': {'start_pos': 10},
                'Player 3': {'start_pos': 20},
                'Player 4': {'start_pos': 30}
            }

        self.players = {}
        for index, (name, value) in enumerate(start_positions.items()):
            default_start = index * self.size // max(1, len(start_positions))
            if isinstance(value, dict):
                start_pos = value.get('start_pos', default_start)
                color = value.get('color', PLAYER_COLORS[index % len(PLAYER_COLORS)])
            else:
                start_pos = value
                color = PLAYER_COLORS[index % len(PLAYER_COLORS)]
            self.players[name] = {'start_pos': start_pos, 'color': color}

    def render(self, state, move_from=None, move_to=None, knocked_piece=None, move_player=None):
        self._update_dimensions()
        self.canvas.delete('all')
        positions = state.get('positions', {})
        active_player = state.get('player', state.get('active_player', ''))
        point_radius = max(5, min(12, self.radius * 0.04))
        self.canvas.create_oval(
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius,
            outline='black',
            width=3
        )

        for position in range(self.size):
            x, y = self._track_coordinates(position)
            self.canvas.create_oval(
                x - point_radius, y - point_radius,
                x + point_radius, y + point_radius,
                outline='black', fill='white', width=2
            )

        for player_name, player in self.players.items():
            start_pos = player['start_pos'] % self.size
            x, y = self._track_coordinates(start_pos)
            self.canvas.create_oval(
                x - point_radius * 1.35, y - point_radius * 1.35,
                x + point_radius * 1.35, y + point_radius * 1.35,
                outline=player['color'], width=3
            )
            house_spacing = min(24, self.radius * 0.09)
            inner_house_radius = max(
                30,
                self.radius * 0.72 - (self.n_pieces - 1) * house_spacing
            )
            label_radius = max(18, inner_house_radius - 24)
            label_x, label_y = self._radial_coordinates(
                (start_pos / self.size) * 2 * pi,
                label_radius
            )
            anchor = 'e' if label_x > self.center_x + 10 else 'w' if label_x < self.center_x - 10 else 'center'
            self.canvas.create_text(
                label_x, label_y, text=player_name,
                fill=player['color'],
                font=('Arial', 10, 'bold', 'underline') if player_name == active_player else ('Arial', 10, 'bold'),
                anchor=anchor
            )
            pieces = positions.get(player_name, [])
            self._draw_house(player_name, player['color'], start_pos)
            waiting_count = sum(1 for piece in pieces if piece == -1)
            for waiting_index in range(waiting_count):
                waiting_x, waiting_y = self._waiting_piece_coordinates(
                    start_pos, waiting_count, waiting_index
                )
                waiting_radius = max(6, min(10, self.radius * 0.035))
                self.canvas.create_oval(
                    waiting_x - waiting_radius, waiting_y - waiting_radius,
                    waiting_x + waiting_radius, waiting_y + waiting_radius,
                    outline=player['color'], fill=player['color'], width=2
                )

        for player_name, pieces in positions.items():
            player = self.players.get(player_name)
            if player is None:
                continue
            color = player['color']
            legacy_slot = 1
            occupied_slots = {
                self._house_slot(piece)
                for piece in pieces
                if self._house_slot(piece) is not None
            }
            for piece in pieces:
                if isinstance(piece, int) and piece >= 0:
                    x, y = self._track_coordinates(piece % self.size)
                    self._draw_piece(x, y, color)
                elif piece == 'house':
                    while legacy_slot in occupied_slots:
                        legacy_slot += 1
                    self._draw_house_piece(player_name, legacy_slot, color)
                    occupied_slots.add(legacy_slot)
                    legacy_slot += 1
                else:
                    slot = self._house_slot(piece)
                    if slot is not None:
                        self._draw_house_piece(player_name, slot, color)

        if knocked_piece:
            player_name, position = knocked_piece
            player = self.players.get(player_name)
            if player is not None:
                x, y = self._track_coordinates(position % self.size)
                self._draw_piece(x + 8, y + 8, player['color'], outline='black')

        round_num = state.get('round', 0)
        roll_num = state.get('roll number', state.get('roll_number', 0))
        rolls = state.get('rolls', [])
        self.canvas.create_text(
            self.center_x, 20,
            text=f'Round: {round_num}, Roll: {roll_num}',
            font=('Arial', 16, 'bold')
        )
        self._draw_dice(rolls)

        if move_from is not None and move_to is not None:
            player_name = move_player or active_player
            player = self.players.get(player_name)
            if player is not None:
                start = self._position_coordinates(player_name, move_from)
                end = self._position_coordinates(player_name, move_to)
                if start is not None and end is not None:
                    self.canvas.create_line(
                        *start, *end,
                        fill=player['color'], arrow='last', width=2
                    )

        return state

    def draw_action_arrows(self, player_name, actions, on_select):
        player = self.players.get(player_name)
        if player is None:
            return []

        drawn_letters = []
        color = player['color']
        for index, action in enumerate(actions):
            start = self._position_coordinates(player_name, action['from'])
            destination = self._position_coordinates(player_name, action['to'])
            if start is None or destination is None:
                continue

            letter = chr(ord('A') + index)
            tag = f'pve-action-{index}'
            self.canvas.create_line(
                *start, *destination,
                fill=color, arrow='last', width=3, tags=(tag,)
            )

            delta_x = destination[0] - self.center_x
            delta_y = destination[1] - self.center_y
            length = max(1, (delta_x ** 2 + delta_y ** 2) ** 0.5)
            label_x = destination[0] + delta_x / length * 22
            label_y = destination[1] + delta_y / length * 22
            label_radius = max(12, min(18, self.radius * 0.055))
            self.canvas.create_oval(
                label_x - label_radius, label_y - label_radius,
                label_x + label_radius, label_y + label_radius,
                fill='white', outline=color, width=2, tags=(tag,)
            )
            self.canvas.create_text(
                label_x, label_y, text=letter,
                fill=color, font=('Arial', max(10, int(label_radius))),
                tags=(tag,)
            )
            self.canvas.tag_bind(
                tag, '<Button-1>',
                lambda event, selected=action: on_select(selected)
            )
            drawn_letters.append(letter)

        return drawn_letters

    def _draw_house(self, player_name, color, start_pos):
        spacing = min(24, self.radius * 0.09)
        first_radius = self.radius * 0.72
        for slot in range(1, self.n_pieces + 1):
            radius = max(30, first_radius - (slot - 1) * spacing)
            angle = (start_pos / self.size) * 2 * pi
            x, y = self._radial_coordinates(angle, radius)
            self.canvas.create_oval(
                x - 13, y - 13, x + 13, y + 13,
                outline=color, fill='white', width=2
            )
            self.canvas.create_text(x, y, text=str(slot), fill=color, font=('Arial', 8))

    def _draw_house_piece(self, player_name, slot, color):
        if not 1 <= slot <= self.n_pieces:
            return
        start_pos = self.players[player_name]['start_pos']
        spacing = min(24, self.radius * 0.09)
        radius = max(30, self.radius * 0.72 - (slot - 1) * spacing)
        angle = (start_pos / self.size) * 2 * pi
        x, y = self._radial_coordinates(angle, radius)
        self._draw_piece(x, y, color)

    def _position_coordinates(self, player_name, position):
        if isinstance(position, int) and position >= 0:
            return self._track_coordinates(position % self.size)
        slot = self._house_slot(position)
        if slot is not None:
            start_pos = self.players[player_name]['start_pos']
            spacing = min(24, self.radius * 0.09)
            radius = max(30, self.radius * 0.72 - (slot - 1) * spacing)
            angle = (start_pos / self.size) * 2 * pi
            return self._radial_coordinates(angle, radius)
        return None

    def _track_coordinates(self, position):
        angle = (position / self.size) * 2 * pi
        return self._radial_coordinates(angle, self.radius)

    def _waiting_piece_coordinates(self, start_pos, count, index):
        angle = (start_pos / self.size) * 2 * pi
        group_radius = self.radius + min(55, self.height * 0.11)
        center_x, center_y = self._radial_coordinates(angle, group_radius)

        if count == 1:
            return center_x, center_y

        orbit_radius = min(14, self.height * 0.03)
        if count == 2:
            offset = (index - 0.5) * orbit_radius * 1.4
            return center_x - int(sin(angle) * offset), center_y + int(cos(angle) * offset)

        piece_angle = (index / count) * 2 * pi - pi / 2
        return (
            center_x + int(orbit_radius * cos(piece_angle)),
            center_y + int(orbit_radius * sin(piece_angle))
        )

    def _draw_dice(self, rolls):
        if not rolls:
            return

        size = max(24, min(44, self.radius * 0.17))
        gap = max(6, size * 0.18)
        total_width = len(rolls) * size + max(0, len(rolls) - 1) * gap
        left = self.center_x - total_width / 2
        top = self.center_y - size / 2 + self.radius * 0.08
        for index, roll in enumerate(rolls):
            self._draw_die(roll, left + index * (size + gap), top, size)

    def _draw_die(self, roll, x, y, size):
        self.canvas.create_rectangle(
            x, y, x + size, y + size,
            outline='black', fill='white', width=2
        )
        pips = {
            1: [(1, 1)],
            2: [(0, 0), (2, 2)],
            3: [(0, 0), (1, 1), (2, 2)],
            4: [(0, 0), (2, 0), (0, 2), (2, 2)],
            5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
            6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)]
        }
        if roll not in pips:
            self.canvas.create_text(x + size / 2, y + size / 2, text=str(roll))
            return

        step = size / 4
        pip_radius = max(2, size * 0.055)
        for column, row in pips[roll]:
            center_x = x + step * (column + 1)
            center_y = y + step * (row + 1)
            self.canvas.create_oval(
                center_x - pip_radius, center_y - pip_radius,
                center_x + pip_radius, center_y + pip_radius,
                fill='black'
            )

    def _update_dimensions(self):
        get_width = getattr(self.canvas, 'winfo_width', None)
        get_height = getattr(self.canvas, 'winfo_height', None)
        width = get_width() if get_width is not None else self.default_width
        height = get_height() if get_height is not None else self.default_height
        self.width = width if width > 1 else self.default_width
        self.height = height if height > 1 else self.default_height
        self.center_x = self.width / 2
        self.center_y = self.height / 2
        self.radius = min(self.width, self.height) * 0.33

    def _radial_coordinates(self, angle, radius):
        return (
            self.center_x + int(radius * cos(angle)),
            self.center_y + int(radius * sin(angle))
        )

    @staticmethod
    def _house_slot(position):
        if isinstance(position, str) and position.startswith('house_'):
            try:
                return int(position[len('house_'):])
            except ValueError:
                return None
        return None

    def _draw_piece(self, x, y, color, outline='black'):
        size = 9
        self.canvas.create_oval(
            x - size, y - size, x + size, y + size,
            fill=color, outline=outline, width=2
        )
