import json
import re
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge

try:
    from .board_view import PLAYER_COLORS
except ImportError:
    from board_view import PLAYER_COLORS


PVE_OUTPUT_ROOT = Path(__file__).resolve().parent / 'output' / 'pve'


def _number_of_players(directory):
    match = re.match(r'^(\d+)(?:_|$)', directory.name)
    if match is None:
        return None
    return int(match.group(1))


def _winner_counts(directory, number_of_players):
    counts = [0] * number_of_players
    total_games = 0

    for filepath in sorted(directory.glob('pve_game_*.json')):
        try:
            with filepath.open(encoding='utf-8') as game_file:
                game = json.load(game_file)
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(game, list) or not game:
            continue
        winner = game[-1].get('player') if isinstance(game[-1], dict) else None
        match = re.fullmatch(r'Player (\d+)', str(winner))
        if match is None:
            continue
        player_index = int(match.group(1)) - 1
        if 0 <= player_index < number_of_players:
            counts[player_index] += 1
            total_games += 1

    return counts, total_games


def create_winner_distribution(directory, number_of_players=None, output_root=None):
    directory = Path(directory)
    number_of_players = number_of_players or _number_of_players(directory)
    if number_of_players is None or number_of_players < 1:
        raise ValueError(f'Could not determine the player count for {directory}.')

    counts, total_games = _winner_counts(directory, number_of_players)
    colors = [PLAYER_COLORS[index % len(PLAYER_COLORS)] for index in range(number_of_players)]

    figure, axis = plt.subplots(figsize=(6, 6))
    axis.pie(
        counts,
        colors=colors,
        startangle=90,
        counterclock=False,
        autopct='%1.1f%%',
        wedgeprops={'linewidth': 0, 'edgecolor': 'none'},
    )

    expected_angle = 360 / number_of_players
    axis.add_patch(
        Wedge(
            (0, 0),
            1,
            90 - expected_angle,
            90,
            facecolor='none',
            edgecolor='black',
            linewidth=1.5,
        )
    )
    axis.set(aspect='equal')
    axis.axis('off')
    figure.text(0.5, 0.03, f'n={total_games}', ha='center', va='bottom')
    output_directory = Path(output_root) if output_root is not None else directory.parent
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f'{directory.name}_statistic.png'
    figure.savefig(output_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(figure)
    return output_path, counts, total_games


def create_all_winner_distributions(output_root=PVE_OUTPUT_ROOT):
    output_root = Path(output_root)
    created = []
    if not output_root.is_dir():
        return created

    for directory in sorted(path for path in output_root.iterdir() if path.is_dir()):
        if _number_of_players(directory) is None:
            continue
        created.append(create_winner_distribution(directory, output_root=output_root))
    return created


if __name__ == '__main__':
    create_all_winner_distributions()