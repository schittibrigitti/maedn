import itertools
from collections import Counter

def generate_combinations(total, n):
    """Generiert alle Kombinationen von `n` Ganzzahlen, die zusammen `total` ergeben,
    wobei einige Ganzzahlen 0 sein können."""
    def helper(remaining, n, start):
        if n == 1:
            yield [remaining]
        else:
            for i in range(start, remaining + 1):
                for result in helper(remaining - i, n - 1, 0):  # start bei 0, um 0 zu erlauben
                    yield [i] + result

    return list(helper(total, n, 0))  # start bei 0, um 0 zu erlauben

def brute_force_probability(n_player, pieces2win, pieces):
    # Spezielle Fälle: Wenn die Bedingungen nicht erfüllt werden können, gib 0 zurück
    if n_player < 1 or pieces < pieces2win or pieces > pieces2win + (n_player - 1) * (pieces2win - 1):
        return 0

    # Alle möglichen Verteilungen von `pieces` auf `n_player` Spieler
    combinations = generate_combinations(pieces, n_player)
    
    total_permutations = set()
    for combination in combinations:
        # Alle Permutationen der Kombinationen hinzufügen
        perms = itertools.permutations(combination)
        total_permutations.update(perms)
    
    total_combinations = len(total_permutations)
    valid_combinations = 0
    invalid_combinations = 0

    for combination in total_permutations:
        counts = Counter(combination)
        count_values = list(counts.values())
        
        # Prüfen, ob genau ein Spieler z Figuren hat und alle anderen maximal z-1 Figuren
        if combination.count(pieces2win) == 1 and all(x <= pieces2win for x in combination):
            valid_combinations += 1
        
        # Prüfen, ob mehr als ein Spieler z Figuren hat oder ob jemand mehr als z Figuren hat
        if combination.count(pieces2win) > 1 or any(x > pieces2win for x in combination):
            invalid_combinations += 1

    # Berechnung der Wahrscheinlichkeit
    if total_combinations - invalid_combinations == 0:
        probability = 0
    else:
        probability = valid_combinations / (total_combinations - invalid_combinations)
    
    return probability

# Beispiel: 4 Figuren, 4 Spieler, z = 2
n_player = 8
pieces2win = 4
pieces = 12

# result = brute_force_probability(n_player, pieces2win, pieces)
# print(f"Die Wahrscheinlichkeit, dass einer von {n_player} Spielern genau {pieces2win} von {pieces} Figuren erhält und die anderen höchstens {pieces2win-1}, beträgt: {result*100:.4f}%")


for pieces in range(pieces2win,pieces2win+(pieces2win-1)*(n_player-1)):
    result = brute_force_probability(n_player, pieces2win, pieces)
    print(f"Die Wahrscheinlichkeit, dass einer von {n_player} Spielern genau {pieces2win} von {pieces} Figuren erhält und die anderen höchstens {pieces2win-1}, beträgt: {result*100:.4f}%")
