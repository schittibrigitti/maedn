"""Gym-aehnliche Umgebung (ohne Zusatzabhaengigkeiten) zum Trainieren von Spieler-KIs.

Ein Aufruf von ``step`` entspricht einer Entscheidung eines gesteuerten Sitzes.
Zuege ohne Wahlmoeglichkeit (kein oder genau ein legaler Zug) und Zuege der
Gegner werden automatisch gespielt.
"""
try:
    from .bin.Simulate_Game import GameSession, HumanAgent, RandomAgent
except ImportError:
    from bin.Simulate_Game import GameSession, HumanAgent, RandomAgent

try:
    from .bin.Game_class import Game_Mode
except ImportError:
    from bin.Game_class import Game_Mode


class MaednEnv:
    """Turn-basierte Umgebung.

    controlled: Sitzindizes, die von aussen gesteuert werden (Default: [0]).
        Mehrere Sitze ermoeglichen Self-Play; ``info['player_index']`` nennt
        den Sitz, der gerade entscheiden muss.
    opponents: Agent-Objekte fuer die uebrigen Sitze (Liste in Sitzreihenfolge
        ohne die gesteuerten Sitze oder Dict {sitz: agent}); Default RandomAgent.
    max_rounds: Rundenlimit; danach ``truncated=True``.

    Beobachtung (dict, alles Python-Listen/Zahlen):
        player_index: Sitz der entscheidenden Figur-Gruppe
        roll: gewuerfelter Wert
        pieces: n_players*n_pieces Werte, aus Sicht des entscheidenden Sitzes
            (eigene Figuren zuerst, dann die Gegner in Sitzreihenfolge).
            0 = nicht im Spiel, 1..size = Ringfeld relativ zum eigenen Startfeld
            (1 = Startfeld), size+k = Hausplatz k des jeweiligen Besitzers.
        action_mask: n_pieces Werte, 1 wenn die eigene Figur ziehen darf
        n_values: Anzahl moeglicher Werte pro Eintrag in ``pieces``
    Aktion: Figurindex (int) des entscheidenden Sitzes; muss in action_mask 1 sein.
    Reward (fuer den Sitz, der gerade gezogen hat): +1 Sieg, -1 Niederlage, sonst 0.
    """

    def __init__(self, game=None, controlled=None, opponents=None, max_rounds=1000, seed=None):
        self.game = game if hasattr(game, 'n_players') else Game_Mode(game)
        self.controlled = list(controlled) if controlled is not None else [0]
        if not self.controlled or any(not 0 <= s < self.game.n_players for s in self.controlled):
            raise ValueError('controlled must contain valid seat indices.')
        free_seats = [s for s in range(self.game.n_players) if s not in self.controlled]
        if isinstance(opponents, dict):
            self.opponents = dict(opponents)
        elif opponents is not None:
            if len(opponents) != len(free_seats):
                raise ValueError('An opponent must be provided for each non-controlled seat.')
            self.opponents = dict(zip(free_seats, opponents))
        else:
            self.opponents = {}
        for seat in free_seats:
            self.opponents.setdefault(seat, RandomAgent())
        self.max_rounds = max_rounds
        self.seed = seed
        self.session = None
        self._event = None
        self.n_values = self.game.size + self.game.n_pieces + 1

    def reset(self, seed=None):
        seed = seed if seed is not None else self.seed
        agents = [
            HumanAgent() if seat in self.controlled else self.opponents[seat]
            for seat in range(self.game.n_players)
        ]
        self.session = GameSession(self.game, agents=agents, seed=seed)
        self._event = None
        self._advance()
        return self._observation(), self._info()

    def step(self, action):
        if self.session is None or self._event is None or self._event['type'] != 'decision_required':
            raise RuntimeError('Call reset() first; the episode may be over.')
        actor = self._event['player_index']
        self._event = self.session.choose_action(int(action))
        self._advance()

        terminated = self.session.finished
        truncated = not terminated and self.session.round_num > self.max_rounds
        reward = 0.0
        if terminated:
            reward = 1.0 if self.session.winner == self.session.players[actor].name else -1.0
        observation = None if terminated or truncated else self._observation()
        return observation, reward, terminated, truncated, self._info()

    def legal_actions(self):
        if self._event is None or self._event['type'] != 'decision_required':
            return []
        return [action['piece_index'] for action in self._event['actions']]

    def _advance(self):
        while True:
            if self._event is not None and self._event['type'] == 'decision_required':
                return
            if self.session.finished or self.session.round_num > self.max_rounds:
                return
            self._event = self.session.advance()

    def _observation(self):
        event = self._event
        if event is None or event['type'] != 'decision_required':
            return None
        game = self.game
        seat = event['player_index']
        players = self.session.players
        own_start = players[seat].start_pos
        order = [seat] + [i for i in range(game.n_players) if i != seat]
        pieces = []
        for index in order:
            for position in players[index].pieces:
                if position == -1:
                    pieces.append(0)
                elif isinstance(position, int):
                    pieces.append((position - own_start) % game.size + 1)
                else:
                    pieces.append(game.size + int(position.split('_', 1)[1]))
        mask = [0] * game.n_pieces
        for action in event['actions']:
            mask[action['piece_index']] = 1
        return {
            'player_index': seat,
            'roll': event['roll'],
            'pieces': pieces,
            'action_mask': mask,
            'n_values': self.n_values,
        }

    def _info(self):
        session = self.session
        winner = session.winner
        return {
            'player_index': self._event['player_index'] if self._event and self._event['type'] == 'decision_required' else None,
            'winner': winner,
            'winner_index': next((i for i, p in enumerate(session.players) if p.name == winner), None),
            'round': session.round_num,
        }
