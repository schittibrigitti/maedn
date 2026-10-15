import json
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_DIR / 'bin'))
from Game_class import Game_Mode
from Simulate_Game import simulate_game

GAME_MODES_PATH = PACKAGE_DIR / 'game_mode.json'
STATISTIC_ROOT = PACKAGE_DIR / 'output' / 'statistic'


def run_all_modes(repetitions=1000, output_root=STATISTIC_ROOT, modes_path=GAME_MODES_PATH):
    with Path(modes_path).open(encoding='utf-8') as modes_file:
        modes = json.load(modes_file)

    for mode in modes:
        directory = Path(output_root) / mode['name']
        directory.mkdir(parents=True, exist_ok=True)
        game = Game_Mode(mode['parameters'])
        for index in range(repetitions):
            log = simulate_game(game)
            with (directory / f'game_log_{index:05d}.json').open('w', encoding='utf-8') as log_file:
                json.dump(log, log_file)
        print(f"{mode['name']}: {repetitions} games saved to {directory}")


if __name__ == '__main__':
    run_all_modes(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
