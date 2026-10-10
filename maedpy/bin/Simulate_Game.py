# import libraries
import random
import json
import os
from datetime import datetime

try:
    from .Player_class import Player
except ImportError:
    from Player_class import Player

class RandomAgent:
    """Random baseline with the configured move priorities."""
    requires_input = False

    def choose_action(self, observation, actions, rng):
        house_entries = [action for action in actions if action['kind'] == 'house_entry']
        house_advances = [action for action in actions if action['kind'] == 'house_advance']
        preferred = house_entries or house_advances or actions
        return preferred[rng.randint(0, len(preferred) - 1)]['piece_index']


class HumanAgent:
    """Marks decisions that must be supplied through GameSession.choose_action."""
    requires_input = True


class GameSession:
    """Incremental game runner that pauses when a controller must choose a move."""
    def __init__(
        self,
        game,
        agents=None,
        dice_rolls=None,
        start_positions=None,
        seed=None,
        rng=None
    ):
        self.game = game
        self.agents = list(agents) if agents is not None else [
            RandomAgent() for _ in range(game.n_players)
        ]
        if len(self.agents) != game.n_players:
            raise ValueError('An agent must be provided for each player.')

        self.rng = rng or (random.Random(seed) if seed is not None else random)
        self.dice_rolls = dice_rolls
        self.roll_index = 0
        self.players = [Player(game, index) for index in range(game.n_players)]
        self.current_player_index = 0
        self.round_num = 1
        self.roll_num = 0
        self.log = []
        self.pending_decision = None

        if start_positions is not None:
            for player_index, positions in start_positions.items():
                player = self.players[player_index]
                player.pieces = positions[:]
                player.finished_pieces = player.count_in_house()

        self.winner = self._find_winner()

    @property
    def finished(self):
        return self.winner is not None

    def snapshot(self):
        return {
            'round': self.round_num,
            'roll number': self.roll_num,
            'active_player': None if self.finished else self.players[self.current_player_index].name,
            'positions': {player.name: player.get_pieces() for player in self.players},
            'in_play': sum(player.count_in_play() for player in self.players),
            'in_house': sum(player.count_in_house() for player in self.players),
            'winner': self.winner
        }

    def advance(self):
        if self.pending_decision is not None:
            return self.pending_decision['response']
        if self.finished:
            return {'type': 'finished', 'winner': self.winner, 'state': self.snapshot()}

        actor_index = self.current_player_index
        player = self.players[actor_index]
        before = self.snapshot()
        max_rolls = self.game.n_rerolls if player.count_in_play() == 0 else 1
        rolls = []
        roll = None

        while len(rolls) < max_rolls:
            self.roll_num += 1
            if self.dice_rolls:
                if self.roll_index >= len(self.dice_rolls):
                    return {'type': 'input_exhausted', 'log': self.log}
                roll = self.dice_rolls[self.roll_index]
                self.roll_index += 1
            else:
                roll = self.rng.randint(1, self.game.n_dice_sides)

            rolls.append(roll)
            if roll == self.game.n_dice_sides:
                break

        if roll is None:
            return {'type': 'input_exhausted', 'log': self.log}

        if roll == self.game.n_dice_sides:
            if not player.can_enter():
                decision = self._resolve_regular_move(actor_index, roll, rolls, before)
                if decision is not None:
                    return decision
            elif not player.start_free():
                moved_piece = player.move_away(self.players, roll, self.game)
                if moved_piece is None:
                    decision = self._resolve_regular_move(actor_index, roll, rolls, before)
                    if decision is not None:
                        return decision
            else:
                player.enter_piece(self.players, self.game)
        elif (
            self.game.clear_start_on_non_six
            and not player.start_free()
            and player.can_enter()
        ):
            moved_piece = player.move_away(self.players, roll, self.game)
            if moved_piece is None:
                decision = self._resolve_regular_move(actor_index, roll, rolls, before)
                if decision is not None:
                    return decision
        else:
            decision = self._resolve_regular_move(actor_index, roll, rolls, before)
            if decision is not None:
                return decision

        return self._complete_turn(actor_index, roll, rolls, before)

    def choose_action(self, action):
        if self.pending_decision is None:
            raise RuntimeError('There is no pending player decision.')

        piece_index = action.get('piece_index') if isinstance(action, dict) else action
        pending = self.pending_decision
        if piece_index not in pending['legal_moves']:
            raise ValueError('The selected action is not legal in the current state.')

        player = self.players[pending['player_index']]
        if len(pending['legal_moves']) > 1:
            player.deliberate_moves += 1
        player.move_piece(self.players, piece_index, pending['roll'], self.game)
        self.pending_decision = None
        return self._complete_turn(
            pending['player_index'],
            pending['roll'],
            pending['rolls'],
            pending['before']
        )

    def _resolve_regular_move(self, actor_index, roll, rolls, before):
        player = self.players[actor_index]
        legal_moves = player.get_legal_moves(self.players, roll, self.game)
        if not legal_moves:
            return None

        actions = [self._make_action(player, piece_index, roll) for piece_index in legal_moves]
        agent = self.agents[actor_index]
        if getattr(agent, 'requires_input', False) and len(actions) > 1:
            response = {
                'type': 'decision_required',
                'player': player.name,
                'player_index': actor_index,
                'roll': roll,
                'rolls': list(rolls),
                'actions': actions,
                'state': before
            }
            self.pending_decision = {
                'response': response,
                'player_index': actor_index,
                'roll': roll,
                'rolls': list(rolls),
                'legal_moves': legal_moves,
                'before': before
            }
            return response

        if getattr(agent, 'requires_input', False):
            piece_index = legal_moves[0]
        else:
            observation = self.snapshot()
            observation['roll'] = roll
            observation['rolls'] = list(rolls)
            observation['player_index'] = actor_index
            piece_index = agent.choose_action(observation, actions, self.rng)
            if isinstance(piece_index, dict):
                piece_index = piece_index.get('piece_index')
            if piece_index not in legal_moves:
                raise ValueError('The selected action is not legal in the current state.')

            if isinstance(agent, RandomAgent):
                preferred = player.get_preferred_moves(legal_moves, roll, self.game)
                if len(preferred) > 1:
                    player.deliberate_moves += 1
            elif len(legal_moves) > 1:
                player.deliberate_moves += 1

        player.move_piece(self.players, piece_index, roll, self.game)
        return None

    def _make_action(self, player, piece_index, roll):
        start = player.pieces[piece_index]
        destination = player._get_destination(start, roll, self.game)
        if player.check_collision(self.players, piece_index, roll, self.game):
            kind = 'capture'
        elif player._house_slot(destination) is not None:
            kind = 'house_entry' if player._house_slot(start) is None else 'house_advance'
        else:
            kind = 'move'
        return {
            'id': piece_index,
            'piece_index': piece_index,
            'from': start,
            'to': destination,
            'kind': kind
        }

    def _complete_turn(self, actor_index, roll, rolls, before):
        actor = self.players[actor_index]
        if roll != self.game.n_dice_sides:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            if self.current_player_index == 0:
                self.round_num += 1

        self.winner = self._find_winner()
        after = self.snapshot()
        in_play = after['in_play']
        in_house = after['in_house']
        deliberate = sum(player.deliberate_moves for player in self.players)
        log_entry = {
            'round': self.round_num,
            'player': actor.name,
            'roll number': self.roll_num,
            'rolls': list(rolls),
            'positions': after['positions'],
            'in_play': in_play,
            'in_house': in_house,
            'deliberate_moves': deliberate
        }
        self.log.append(log_entry)

        moves = []
        for player_name, old_positions in before['positions'].items():
            new_positions = after['positions'][player_name]
            for piece_index, (old_position, new_position) in enumerate(zip(old_positions, new_positions)):
                if old_position != new_position:
                    moves.append({
                        'player': player_name,
                        'piece_index': piece_index,
                        'from': old_position,
                        'to': new_position
                    })

        return {
            'type': 'turn_completed',
            'player': actor.name,
            'rolls': list(rolls),
            'moves': moves,
            'previous_state': before,
            'state': after,
            'log_entry': log_entry,
            'winner': self.winner
        }

    def _find_winner(self):
        for player in self.players:
            if player.finished_pieces >= self.game.n_pieces_to_win:
                return player.name
        return None


def simulate_game(game, dice_rolls=None, start_positions=None, agents=None, seed=None):
    session = GameSession(
        game,
        agents=agents,
        dice_rolls=dice_rolls,
        start_positions=start_positions,
        seed=seed
    )
    while not session.finished:
        result = session.advance()
        if result['type'] == 'input_exhausted':
            return session.log
        if result['type'] == 'decision_required':
            raise RuntimeError('simulate_game cannot pause for a HumanAgent; use GameSession.')
    return session.log

def output_results(game, log):
    # calculate deliverables 
    total_deliberate_moves = log[-1]['deliberate_moves']
    total_rounds = log[-1]['round']
    total_rolls = log[-1]['roll number']
    winner = log[-1]['player']
    
    # Save the log to a file
    # Generate the filename with current date and time
    filename = os.path.join(
        game.out_folder,
        datetime.now().strftime('game_log_%Y-%m-%d_%H-%M-%S_%f')[:-4] + '.json'
    )
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(log, f, indent=4)

    # Print log for verification
    for entry in log:
        rolls = ", ".join(map(str, entry["rolls"]))
        print(f"Round: {entry['round']}, Player: {entry['player']}, Rolls: {rolls}, In Play: {entry['in_play']}, In House: {entry['in_house']}, deliberate Actions: {entry['deliberate_moves']}")

    # Print total rounds and rolls
    print(f"Total Rounds: {total_rounds}")
    print(f"Total Rolls: {total_rolls}")
    print(f"Rolls per round: {round(total_rolls/total_rounds/game.n_players,2)}")
    print(f"Deliberate actions per roll: {round(total_deliberate_moves/total_rolls*100,1)}%")
    print(f"Winner: {winner}!")

