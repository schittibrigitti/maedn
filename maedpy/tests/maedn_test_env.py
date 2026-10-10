import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from maedpy import MaednEnv, Game_Mode, GameSession, RandomAgent, simulate_game


def play_random(env, seed):
    observation, info = env.reset(seed=seed)
    steps = 0
    reward = 0.0
    terminated = env.session.finished
    truncated = observation is None and not terminated
    while not (terminated or truncated):
        legal = [i for i, ok in enumerate(observation['action_mask']) if ok]
        assert legal == env.legal_actions()
        assert len(observation['pieces']) == env.game.n_players * env.game.n_pieces
        assert all(0 <= value < observation['n_values'] for value in observation['pieces'])
        observation, reward, terminated, truncated, info = env.step(legal[0])
        steps += 1
    return steps, reward, terminated, truncated, info


def test_env_episode_and_determinism():
    first = play_random(MaednEnv(), seed=5)
    second = play_random(MaednEnv(), seed=5)
    assert first == second
    steps, reward, terminated, truncated, info = first
    assert terminated and not truncated
    assert reward == (1.0 if info['winner_index'] == 0 else -1.0)


def test_env_truncation_and_self_play():
    steps, reward, terminated, truncated, info = play_random(MaednEnv(max_rounds=3), seed=1)
    assert truncated and not terminated and reward == 0.0

    env = MaednEnv(controlled=[0, 1, 2, 3])
    observation, info = env.reset(seed=2)
    seats = set()
    done = False
    while not done:
        seats.add(observation['player_index'])
        action = observation['action_mask'].index(1)
        observation, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
    assert terminated and len(seats) > 1


def test_env_rejects_illegal_state():
    env = MaednEnv()
    try:
        env.step(0)
    except RuntimeError:
        pass
    else:
        raise AssertionError('step before reset must fail')


def test_agent_observation_has_roll_and_index():
    seen = []

    class Spy:
        requires_input = False

        def choose_action(self, observation, actions, rng):
            seen.append((observation['roll'], observation['player_index'], observation['active_player']))
            return actions[0]['piece_index']

    game = Game_Mode()
    simulate_game(game, agents=[Spy(), RandomAgent(), RandomAgent(), RandomAgent()], seed=3)
    assert seen and all(1 <= roll <= 6 and index == 0 for roll, index, _ in seen)


def main():
    test_env_episode_and_determinism()
    print('Test env episode PASSED')
    test_env_truncation_and_self_play()
    print('Test env truncation and self-play PASSED')
    test_env_rejects_illegal_state()
    print('Test env illegal state PASSED')
    test_agent_observation_has_roll_and_index()
    print('Test agent observation PASSED')


if __name__ == '__main__':
    main()
