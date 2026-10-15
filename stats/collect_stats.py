"""Sammelt Kennzahlen aus den EvE- (output/statistic) und PvE-Spielen (output/pve).

Schreibt in stats/generated/:
  lengths.csv  Spiellänge (Würfe, Runden, Züge) je Modus und Quelle
  wins.csv     Siege je Spieler, Modus und Quelle
  pies.tex     Kuchendiagramme (links EvE, rechts PvE, Modi untereinander)
"""
import csv
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / 'maedpy'
GAME_MODES_PATH = PACKAGE_DIR / 'game_mode.json'
SOURCES = {
    'EvE': (PACKAGE_DIR / 'output' / 'statistic', 'game_log_*.json'),
    'PvE': (PACKAGE_DIR / 'output' / 'pve', 'pve_game_*.json'),
}
GENERATED = Path(__file__).resolve().parent / 'generated'
PIE_COLORS = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'yellow!80!orange', 'teal']
METRICS = ('rolls', 'rounds', 'moves', 'rolls_per_move', 'decision_share', 'opponent_house')


def load_modes():
    with GAME_MODES_PATH.open(encoding='utf-8') as modes_file:
        return json.load(modes_file)


def opponent_house_average(last, winner):
    counts = [
        sum(1 for piece in pieces if isinstance(piece, str) and piece.startswith('house'))
        for name, pieces in last['positions'].items() if name != winner
    ]
    return statistics.fmean(counts) if counts else 0.0


def game_metrics(game):
    last = game[-1]
    moves = len(game)
    return {
        'rolls': last['roll number'],
        'rounds': last['round'],
        'moves': moves,
        'rolls_per_move': last['roll number'] / moves,
        'decision_share': 100 * last['deliberate_moves'] / moves,
        'opponent_house': opponent_house_average(last, last['player']),
        'winner': last['player'],
    }

def read_games(directory, pattern):
    games = []
    for filepath in sorted(Path(directory).glob(pattern)):
        try:
            game = json.loads(filepath.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(game, list) and game and isinstance(game[-1], dict) and 'roll number' in game[-1]:
            games.append(game_metrics(game))
    return games


def collect(modes):
    data = {}
    for mode in modes:
        for source, (root, pattern) in SOURCES.items():
            data[(mode['name'], source)] = read_games(root / mode['name'], pattern)
    return data


def mean_std(values):
    if not values:
        return 0.0, 0.0
    return statistics.fmean(values), statistics.pstdev(values) if len(values) > 1 else 0.0


def tex_escape(text):
    return text.replace('&', r'\&').replace('_', r'\_').replace('%', r'\%')


def write_lengths(modes, data):
    with (GENERATED / 'lengths.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        header = ['mode']
        for source in SOURCES:
            header.append(f'{source}_n')
            for metric in METRICS:
                header += [f'{source}_{metric}_{field}' for field in ('mean', 'std', 'top', 'label')]
        writer.writerow(header)
        for mode in modes:
            row = [mode['name']]
            for source in SOURCES:
                games = data[(mode['name'], source)]
                row.append(len(games))
                for metric in METRICS:
                    mean, std = mean_std([g[metric] for g in games])
                    digits = 0 if metric in ('rolls', 'rounds', 'moves') else 1 if metric == 'decision_share' else 2
                    label = f'{mean:.{digits}f} (n={len(games)})' if games else 'n=0'
                    row += [f'{mean:.3f}', f'{std:.3f}', f'{mean + std:.3f}', label]
            writer.writerow(row)

def win_counts(games, n_players):
    counts = [0] * n_players
    for game in games:
        match = re.fullmatch(r'Player (\d+)', game['winner'])
        if match and 1 <= int(match.group(1)) <= n_players:
            counts[int(match.group(1)) - 1] += 1
    return counts


def write_wins(modes, data):
    with (GENERATED / 'wins.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['mode', 'source', 'n', 'player', 'wins'])
        for mode in modes:
            n_players = mode['parameters']['n_players']
            for source in SOURCES:
                games = data[(mode['name'], source)]
                for index, wins in enumerate(win_counts(games, n_players), start=1):
                    writer.writerow([mode['name'], source, len(games), index, wins])


def pie_cell(mode, games):
    n_players = mode['parameters']['n_players']
    counts = win_counts(games, n_players)
    total = sum(counts)
    if total == 0:
        return r'\emph{keine Daten}'
    slices = ', '.join(
        f'{100 * count / total:.1f}/{index}' for index, count in enumerate(counts, start=1)
    )
    colors = ','.join(PIE_COLORS[i % len(PIE_COLORS)] for i in range(n_players))
    return (
        r'\begin{tikzpicture}'
        rf'\pie[radius=1.6, color={{{colors}}}, text=legend, rotate=90, '
        rf'after number=\%]{{{slices}}}'
        r'\end{tikzpicture}'
        rf'\\[0.2em] {{\small $n={total}$}}'
    )


def write_pies(modes, data):
    lines = []
    for mode in modes:
        params = mode['parameters']
        nominal = params.get('nominal_players', params['n_players'])
        seats = params.get('player_positions')
        info = f"{params['n_players']} Spieler"
        if nominal != params['n_players']:
            info += f", Brett für {nominal}, Sitze {', '.join(map(str, seats))}"
        lines.append(rf'\subsection*{{{tex_escape(mode["name"])}}}')
        lines.append(rf'{{\small {info}; erwarteter Anteil je Spieler: ${100 / params["n_players"]:.1f}\,\%$}}\par')
        lines.append(r'\begin{center}')
        lines.append(r'\begin{tabular}{c@{\hspace{2cm}}c}')
        lines.append(r'\textbf{EvE} & \textbf{PvE} \\')
        eve, pve = (pie_cell(mode, data[(mode['name'], source)]) for source in SOURCES)
        lines.append(rf'\begin{{tabular}}[t]{{@{{}}c@{{}}}}{eve}\end{{tabular}} &')
        lines.append(rf'\begin{{tabular}}[t]{{@{{}}c@{{}}}}{pve}\end{{tabular}} \\')
        lines.append(r'\end{tabular}')
        lines.append(r'\end{center}')
        lines.append('')
    (GENERATED / 'pies.tex').write_text('\n'.join(lines), encoding='utf-8')


def main():
    GENERATED.mkdir(parents=True, exist_ok=True)
    modes = load_modes()
    data = collect(modes)
    write_lengths(modes, data)
    names = ','.join('{' + tex_escape(mode['name']) + '}' for mode in modes)
    (GENERATED / 'modes.tex').write_text(
        rf'\def\modelist{{{names}}}' + '\n' + rf'\def\modelast{{{len(modes) - 1}}}' + '\n',
        encoding='utf-8'
    )
    write_wins(modes, data)
    write_pies(modes, data)
    for (name, source), games in data.items():
        print(f'{name} [{source}]: n={len(games)}')


if __name__ == '__main__':
    sys.exit(main())
