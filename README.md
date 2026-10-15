# Mensch ärgere Dich nicht (MÄDN) – Simulation, PvE-GUI & Statistik

Parametrisierbare Python-Implementierung von *Mensch ärgere Dich nicht*
(englisch: Ludo). Das Projekt bietet:

- eine **Spiel-Engine** (beliebig viele Spieler, Figuren, Würfelseiten, Feldgrößen),
- **Simulation** vieler Bot-gegen-Bot-Partien mit JSON-Logs,
- ein **PvE-Spiel mit Tkinter-GUI** (ein Mensch gegen Zufalls-Bots),
- **Replay-Viewer** und **Statistik-Auswertungen** (matplotlib),
- analytische/numerische **Nebenrechnungen** zur Gewinnwahrscheinlichkeit und Spieldynamik.

> Dieses README richtet sich an Menschen **und** an KI-Assistenten/Chatbots.
> Der Abschnitt [Hinweise für KI-Assistenten](#hinweise-für-ki-assistenten) fasst die
> wichtigsten Konventionen und Stolperfallen zusammen.

---

## Inhaltsverzeichnis

1. [Schnellstart](#schnellstart)
2. [Projektstruktur](#projektstruktur)
3. [Spielregeln & Parameter](#spielregeln--parameter)
4. [Datenmodell](#datenmodell)
5. [Architektur](#architektur)
6. [Module im Detail](#module-im-detail)
7. [Ausgabedateien & Log-Format](#ausgabedateien--log-format)
8. [Backend nutzen: Spieler-KIs entwickeln & trainieren](#backend-nutzen-spieler-kis-entwickeln--trainieren)
9. [Tests](#tests)
10. [Hinweise für KI-Assistenten](#hinweise-für-ki-assistenten)
11. [Bekannte Einschränkungen / TODO](#bekannte-einschränkungen--todo)
12. [Repository-Hygiene](#repository-hygiene)

---

## Schnellstart

### Voraussetzungen

- Python 3.12 (entwickelt und getestet mit 3.12.4)
- Pakete laut [requirements.txt](requirements.txt): `matplotlib`, `numpy`, `scipy` (`scipy` nur für `MADN.py`)
- `tkinter` (bei Windows/macOS-Python enthalten; unter Linux z. B. `sudo apt install python3-tk`) – nur für GUI, Replay und Dateidialoge; die Engine selbst braucht es nicht

```bash
pip install -r requirements.txt
```

Optional als Paket installieren (für `import maedpy` aus anderen Projekten; Engine und `MaednEnv` haben keine Abhängigkeiten, `analysis` bringt die Plot-Pakete mit):

```bash
pip install -e .            # oder: pip install -e .[analysis]
```

### Typische Aufrufe

Alle Befehle aus dem Ordner `maedpy/` ausführen:

```bash
cd maedpy

# 1) Eine Bot-Partie simulieren (Standardregeln), Log nach output/<Parameter>/ schreiben
python main.py

# 2) Mensch gegen Bots (GUI)
python maedn_PvE.py

# 3) Gespeichertes Spiel als Replay ansehen (öffnet Dateidialog)
python maedn_visualization.py

# 4) Statistik über viele Logs (öffnet Ordnerdialog)
python maedn_statistic.py

# 5) Siegverteilung (Tortendiagramme) für alle PvE-Ordner erzeugen
python maedn_PvE_statistic.py
```

Eigene Regeln per JSON (siehe [Parameter](#spielregeln--parameter)) und mehrere Wiederholungen:

```python
# in Python (aus maedpy/)
from main import main
main(file_name="input/test.json", repetitions=100)
```

---

## Projektstruktur

```
MÄDN/
├── MADN.py                  # Kontinuumsmodell: Figurendichte/Schlagwahrscheinlichkeit (scipy-Fit)
├── Win_probability.py       # Brute-Force: Gewinnwahrscheinlichkeit bei Figurenverteilung
├── requirements.txt         # Python-Abhängigkeiten
├── pyproject.toml           # Paketdefinition (pip install -e .)
├── .gitignore               # schließt output/, Literatur/, *.docx, *.xlsx etc. aus
├── MÄDN.xlsx, MÄDN.docx,    # lokale Notizen/Auswertungen (NICHT im Repo, per .gitignore)
│   Würfel.docx, Literatur/  # und Literatur (PDF) – ebenfalls nicht versioniert
└── maedpy/                  # Hauptpaket
    ├── __init__.py          # exportiert Game_Mode, GameSession, Agents, simulate_game, MaednEnv
    ├── env.py               # MaednEnv: reset()/step()-Umgebung für KI-Training
    ├── main.py              # CLI-Einstieg: Bot-Simulation
    ├── maedn_PvE.py         # Tkinter-GUI: Mensch vs. Bots
    ├── game_mode.json       # benannte PvE-Spielmodi mit Parametern
    ├── board_view.py        # BoardView: Zeichnen des Spielfelds (Canvas)
    ├── maedn_visualization.py  # Replay-Fenster für gespeicherte Logs
    ├── maedn_statistic.py   # Statistiken/Plots über Log-Ordner
    ├── maedn_PvE_statistic.py  # Siegverteilung der PvE-Partien (PNG)
    ├── bin/
    │   ├── Game_class.py    # Game_Mode: Regel-/Brettparameter
    │   ├── Player_class.py  # Player: Figuren, Züge, Schlagen, Haus
    │   └── Simulate_Game.py # GameSession, Agents, simulate_game, output_results
    ├── input/               # Beispiel-Konfigurationen (JSON)
    ├── output/              # Erzeugte Logs/Statistiken – wird automatisch angelegt, nicht versioniert
    ├── output_test/         # lokal/optional, nicht versioniert (vom Code nicht benötigt)
    ├── tests/               # Test-Skripte (siehe Abschnitt Tests)
    └── todo.txt             # Offene Punkte
```

---

## Spielregeln & Parameter

Das Brett ist ein Ring mit `size = n_players * start_to_start_distance` Feldern.
Jeder Spieler hat ein Startfeld, ein Endfeld (letztes Feld vor dem Start) und ein „Haus“
mit Slots `house_1 … house_n`.

Konfigurierbar über [Game_Mode](maedpy/bin/Game_class.py) (Dict oder JSON-Datei):

| Parameter                 | Default | Bedeutung |
|---------------------------|---------|-----------|
| `n_players`               | 4       | Anzahl Spieler |
| `n_pieces`                | 4       | Figuren pro Spieler |
| `n_pieces_to_win`         | 4       | Figuren im Haus, die zum Sieg nötig sind |
| `n_dice_sides`            | 6       | Würfelseiten; die höchste Zahl ist die „Sechs“ (Herausbringen + nochmal würfeln) |
| `start_to_start_distance` | 10      | Felder zwischen zwei Startfeldern |
| `n_rerolls`               | 3       | Würfelversuche, solange keine Figur im Spiel ist |
| `knock_duty`              | `true`  | Schlagzwang: ist Schlagen möglich, sind nur schlagende Züge legal (per JSON oder PvE-Modusdefinition) |
| `clear_start_on_non_six`  | `true`  | Startfeld freimachen, auch wenn keine Sechs fällt (sofern noch Figuren draußen) |
| `size`                    | berechnet | Wird nur übernommen, wenn größer als `n_players*start_to_start_distance` |
| `player_names`            | `Player 1…n` | Spielernamen |
| `start_positions`         | `i*distance` | Startfelder |
| `end_positions`           | `(start-1) % size` | Endfelder |

Beispiel (`input/test.json`):

```json
{ "n_players": 6, "start_to_start_distance": 8 }
```

Regelumsetzung (Kurzfassung, siehe [Simulate_Game.py](maedpy/bin/Simulate_Game.py) und [Player_class.py](maedpy/bin/Player_class.py)):

- Ohne Figur im Spiel: bis zu `n_rerolls` Würfe; bei einer „Sechs“ wird abgebrochen.
- Bei einer „Sechs“: Figur herausbringen; ist das Startfeld belegt, wird zuerst eine Figur weggezogen (`move_away`); der Spieler ist danach noch einmal dran.
- Schlagen: Landet eine Figur auf einem besetzten Feld, wird die dortige Figur zurück auf `-1` gesetzt (auch eigene Figuren, siehe `check_and_handle_collision`).
- Schlagzwang (`knock_duty=true`): `get_legal_moves` liefert nur schlagende Züge, wenn welche existieren; mit `false` sind alle möglichen Züge erlaubt.
- Haus: Figuren dürfen nur bis ins Haus ziehen, wenn das Ziel nicht überschritten wird; Überspringen im Haus ist laut `todo.txt` noch zu prüfen.
- Zugpriorität des `RandomAgent`: Haus-Einzug > Haus-Vorrücken > beliebiger legaler Zug (zufällig).
- Sieg: Sobald ein Spieler `n_pieces_to_win` Figuren im Haus hat.

---

## Datenmodell

**Positionen einer Figur** (`Player.pieces`, Liste der Länge `n_pieces`):

| Wert            | Bedeutung |
|-----------------|-----------|
| `-1`            | noch nicht im Spiel („im Topf“) |
| `int` 0…size-1  | Feld auf dem Ring |
| `"house_k"`     | Slot `k` im Haus des Spielers (ab 1) |

**Spieler-Namen** sind `"Player 1"`, `"Player 2"`, … (Index = Nummer − 1). Der Mensch im PvE ist immer Spieler 1.

**Action** (Dict, von `GameSession` erzeugt):

```python
{"id": i, "piece_index": i, "from": <Position>, "to": <Position>,
 "kind": "capture" | "house_entry" | "house_advance" | "move"}
```

---

## Architektur

```
Game_Mode (Parameter)
     │
     ▼
GameSession ──────────────► Player (je Spieler: Figuren, Zuglogik)
  advance()  ── würfelt, führt Zug aus, gibt Event-Dict zurück
  choose_action(piece_index)  ── setzt wartende Mensch-Entscheidung fort
     ▲
     │ Agents: RandomAgent (entscheidet selbst) / HumanAgent (requires_input=True)
     │
Frontends: main.py (Bots, headless) │ maedn_PvE.py (Tkinter) │ Replay/Statistik (lesen JSON-Logs)
```

Wichtiges Prinzip: `GameSession.advance()` ist **inkrementell**. Muss ein `HumanAgent`
zwischen mehreren legalen Zügen wählen, liefert `advance()` ein Event
`{"type": "decision_required", ...}` und pausiert, bis `choose_action(piece_index)` aufgerufen wird.
Gibt es nur einen legalen Zug, wird er automatisch gespielt.

Event-Typen von `advance()` / `choose_action()`:

| `type`              | Bedeutung |
|---------------------|-----------|
| `turn_completed`    | Zug beendet; enthält `player`, `rolls`, `moves`, `previous_state`, `state`, `log_entry`, `winner` |
| `decision_required` | Mensch muss wählen; enthält `player`, `roll`, `rolls`, `actions`, `state` |
| `finished`          | Spiel bereits vorbei |
| `input_exhausted`   | Vorgegebene `dice_rolls` aufgebraucht (für deterministische Tests) |

---

## Module im Detail

### `maedpy/bin/Game_class.py` – `Game_Mode`
Liest Defaults, überschreibt sie mit einem Dict oder einer JSON-Datei und berechnet
`size`, `start_positions`, `end_positions`, `player_names`. Setzt außerdem `out_folder`:
`maedpy/output/<n_players>_<size>_<n_dice_sides>_<distance>_<n_rerolls>_<n_pieces_to_win>_<n_pieces>_<knock_duty>_<clear_start_on_non_six>`
(z. B. `4_40_6_10_3_4_4_True_True`). Dieser Ordnername kodiert die Parametrisierung und wird von den
Statistikskripten wieder ausgewertet (die erste Zahl = Spieleranzahl).

### `maedpy/bin/Player_class.py` – `Player`
Zustand und Zuglogik eines Spielers: `can_enter`, `enter_piece`, `move_piece`, `get_legal_moves`,
`get_preferred_moves`, `move_away`, `can_move`, `_get_destination`, Kollisionsbehandlung.

### `maedpy/bin/Simulate_Game.py`
- `RandomAgent`, `HumanAgent` – Entscheider.
- `GameSession` – Spielablauf (siehe Architektur). Optionen: `dice_rolls` (feste Würfe),
  `start_positions` (`{spielerindex: [positionen]}`), `seed`/`rng`.
- `simulate_game(game, ...)` – läuft bis Spielende, gibt das Log (Liste von Dicts) zurück.
- `output_results(game, log)` – schreibt das Log nach `game.out_folder` und druckt Kennzahlen.

### `maedpy/main.py`
`main(file_name=None, repetitions=1)`: Game_Mode laden → `simulate_game` → `output_results`, `repetitions`-mal.

### `maedpy/maedn_PvE.py`
Tkinter-GUI (`PvEWindow`): dauerhafte Modusauswahl aus `game_mode.json`, Spielfeld (`BoardView`), Geschwindigkeitsmodi
(`Skip`, `Manual`, `normal`, `fast`), Pause/Play/„Next frame“, Pfeile zur Zugauswahl
(Zugoptionen mit `D`, `W`, `A`, `S` per Tastatur oder Klick auswählbar),
Kein Endedialog: Nach Spielende erscheint in der Statuszeile YOU WIN! CONGRATULATIONS (läuft einmal quer über das Spielfeld; bei Sieg des Menschen, sonst Player N wins) und nach 5 s startet automatisch ein neues Spiel im selben Modus (läuft ohne erneutes Play los). Ein anderer Modus wird über das Dropdown gewählt. Beendete Spiele werden automatisch nach
`output/pve/<Modusname>/pve_game_<Zeitstempel>.json` gespeichert. Die PvE-Spielmodi stehen in
[`maedpy/game_mode.json`](maedpy/game_mode.json); das Dropdown bleibt sichtbar und beim Auswählen
eines Namens startet direkt ein Spiel mit diesen Parametern.
Neue Modi werden als Einträge mit `name` und `parameters` in der JSON-Liste ergänzt; Änderungen
werden beim nächsten Programmstart eingelesen.

| Name | Spieler | Abstand Startfelder | Bereits gespeicherte Partien |
|------|--------:|--------------------:|-----------------------------:|
| `Classic 4 Player Field` | 4 | 10 | 53 |
| `Classic 6 Player Field` | 6 | 8 | 3 |
| `2 Players on classic 4 Player Field` | 2 | 20 | 14 |
| `2 Players on 24 Tiles` | 2 | 12 | 26 |

Die übrigen Modi in `game_mode.json` haben noch keine Logs. PvE-Logs und Siegstatistiken verwenden den Modusnamen als Ordnernamen; ältere Ordner (Parameterstring, `modusN`) wurden zusammengeführt. Ältere Ordner mit höchstens zwei Partien bleiben unverändert.
Hilfsfunktionen: `create_game`, `parameters_for_game`, `create_agents`, `save_pve_game`.

### `maedpy/board_view.py` – `BoardView`
Zeichnet Ring, Häuser, Figuren, Würfel und Zugpfeile auf einem `tk.Canvas`; enthält
`PLAYER_COLORS` (auch von der Statistik genutzt).

### `maedpy/maedn_visualization.py`
Replay-Fenster (`ReplayWindow`) für Log-Dateien: vor/zurück, Sprung zu Runde.

### `maedpy/maedn_statistic.py`
Liest alle Logs eines Ordners (`game_end.json`, `time_dep.json` werden ignoriert), erzeugt
Plots (Spielende-/Zeitverläufe) und schreibt nach `output/statistic/<Ordnername>/`.

### `maedpy/maedn_PvE_statistic.py`
`create_all_winner_distributions()` – für jeden Modusordner in `output/pve/` ein Tortendiagramm
der Siege je Spieler (`<Modusname>_statistic.png`); die Spielerzahl wird aus `game_mode.json`
ermittelt; die schwarze Umrandung markiert den
Erwartungswert (1/n_players, d. h. Fairness).

### `MADN.py` (Repo-Wurzel)
Eigenständiges Skript: iteratives Kontinuumsmodell für die Figurendichte `n/D` und die
Schlagwahrscheinlichkeit `p_K`, Fit mit `scipy.optimize.curve_fit` (`rho_0 * tanh(t/t_0)`),
Vergleich mit Näherungsformeln. Parameter oben im Skript (`P`, `D_0`, `F`, `W`, `A`).
Gibt Ergebnisse auf der Konsole aus.

### `Win_probability.py` (Repo-Wurzel)
Brute-Force-Kombinatorik: Wahrscheinlichkeit, dass bei `pieces` im Haus befindlichen Figuren
genau ein Spieler `pieces2win` besitzt und alle anderen weniger. Parameter stehen im Skriptkörper.

---

## Ausgabedateien & Log-Format

Ein Log ist eine JSON-Liste mit einem Eintrag pro Zug:

```json
{
  "round": 1,
  "player": "Player 1",
  "roll number": 3,
  "rolls": [5, 5, 3],
  "positions": { "Player 1": [-1, -1, -1, -1], "Player 2": [...] },
  "in_play": 0,
  "in_house": 0,
  "deliberate_moves": 0
}
```

- `roll number` ist die laufende Gesamt-Wurfnummer, `deliberate_moves` die kumulierte Zahl echter Entscheidungen.
- Der **letzte Eintrag** eines Logs gehört dem Gewinner (`player`); `maedn_PvE_statistic.py` wertet genau das aus.
- Bot-Logs: `output/<Parameter>/game_log_<Zeit>.json`; PvE-Logs: `output/pve/<Modusname>/pve_game_<Zeit>.json`.

---

## Backend nutzen: Spieler-KIs entwickeln & trainieren

Die Engine in `maedpy/bin/` ist unabhängig von Tkinter und kann headless (ohne GUI, ohne Dateiausgabe)
als Simulationsumgebung für Bots, Reinforcement Learning oder Evolutionsverfahren genutzt werden.
Im Folgenden `maedpy/` als Arbeitsverzeichnis bzw. auf `sys.path`:

```python
import sys; sys.path.insert(0, "bin")
from Game_class import Game_Mode
from Simulate_Game import GameSession, RandomAgent, HumanAgent, simulate_game
```

### Variante A: Agent-Klasse (einfachster Weg)

Ein Agent ist ein beliebiges Objekt mit `requires_input = False` und der Methode
`choose_action(observation, actions, rng) -> piece_index`. Die Engine ruft sie nur auf, wenn der Spieler nach dem
Würfeln mindestens einen legalen Zug hat, und prüft, dass der zurückgegebene Index legal ist (sonst `ValueError`).

```python
class GreedyAgent:
    requires_input = False

    def choose_action(self, observation, actions, rng):
        # observation = GameSession.snapshot() + roll, rolls, player_index:
        #               round, roll number, active_player, positions {name: [pos,...]},
        #               in_play, in_house, winner
        # actions     = legale Züge: [{piece_index, from, to, kind}, ...]
        best = max(actions, key=lambda a: a["kind"] == "capture")
        return best["piece_index"]          # alternativ: das ganze Action-Dict

game = Game_Mode({"n_players": 4})
log = simulate_game(game, agents=[GreedyAgent(), RandomAgent(), RandomAgent(), RandomAgent()], seed=42)
winner = log[-1]["player"]                  # z. B. "Player 1"
```

- Es werden **keine Dateien geschrieben** (nur `output_results` schreibt Logs) – ideal für Massensimulationen.
- `seed=` macht Partien reproduzierbar; alternativ eigenes `rng=random.Random(...)` an `GameSession`.
- Die Anzahl der Agenten muss `n_players` entsprechen; der Agent mit Index `i` spielt `"Player i+1"`.
- Die `observation` enthält zusätzlich zum Snapshot `roll`, `rolls` (alle Würfe des Zugs) und `player_index` (eigener Sitz).

### Variante B: Umgebung `MaednEnv` (gym-ähnlich, für RL)

[maedpy/env.py](maedpy/env.py) kapselt `GameSession` als `reset()` / `step()`-Umgebung ohne Zusatzabhängigkeiten
(Python-Listen statt numpy; in `gymnasium` o. Ä. leicht zu wrappen). Ein `step` entspricht **einer Entscheidung**
(mehr als ein legaler Zug). Züge ohne Wahl sowie Züge der Gegner werden automatisch gespielt.

```python
from maedpy import MaednEnv

env = MaednEnv({"n_players": 4}, controlled=[0], max_rounds=500)   # Gegner: RandomAgent
obs, info = env.reset(seed=1)
done = False
while not done:
    legal = [i for i, ok in enumerate(obs["action_mask"]) if ok]
    action = my_policy(obs, legal)                  # Figurindex
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated
```

| Element | Bedeutung |
|---------|-----------|
| `obs["player_index"]`, `obs["roll"]` | entscheidender Sitz und gewürfelter Wert |
| `obs["pieces"]` | `n_players*n_pieces` Ganzzahlen aus Sicht des Entscheiders (eigene Figuren zuerst, dann die Gegner): `0` = nicht im Spiel, `1…size` = Ringfeld relativ zum eigenen Startfeld, `size+k` = Hausplatz `k` |
| `obs["action_mask"]` | `n_pieces` Werte, `1` = Figur darf ziehen |
| `obs["n_values"]` | Wertebereich der `pieces`-Einträge (`size + n_pieces + 1`) |
| Aktion | Figurindex des Entscheiders (muss in der Maske `1` sein) |
| Reward | für den zuletzt entscheidenden Sitz: `+1` Sieg, `-1` Niederlage (auch durch Gegnerzug), sonst `0` |
| `terminated` / `truncated` | Spielende / Rundenlimit `max_rounds` überschritten |
| `info` | `player_index`, `winner`, `winner_index`, `round` |

- **Self-Play:** `controlled=[0,1,2,3]` – dann liefert jedes Observation den Sitz im Feld `player_index`; dieselbe Policy kann alle Sitze spielen (Observation ist bereits sitzrelativ).
- **Eigene Gegner:** `opponents=[agent, ...]` (Reihenfolge der nicht gesteuerten Sitze) oder `{sitz: agent}`; Agents wie in Variante A.
- `reset()` kann ausnahmsweise `obs=None` liefern, wenn die Episode schon vor der ersten Entscheidung endet (nur bei sehr kleinem `max_rounds`).
- `env.legal_actions()` liefert die erlaubten Figurindizes; `env.session` gibt Zugriff auf die zugrunde liegende `GameSession`.
- Reproduzierbar über `reset(seed=...)`.

### Variante C: Direkte Schrittsteuerung mit `GameSession`

Mit `HumanAgent` (`requires_input = True`) pausiert `GameSession.advance()` bei jeder echten Entscheidung
und liefert `decision_required`; fortgesetzt wird mit `choose_action(piece_index)`.

```python
session = GameSession(game, agents=[HumanAgent()] + [RandomAgent() for _ in range(3)], seed=1)
while not session.finished:
    event = session.advance()
    while event["type"] == "decision_required":
        piece = my_policy(event["state"], event["roll"], event["actions"])
        event = session.choose_action(piece)
```
Zusammengefasst (Ebene `GameSession`; `MaednEnv` bietet dazu das Äquivalent in `obs`/`info`):

| Wunsch | Mittel |
|--------|--------|
| Zustand lesen | `session.snapshot()` bzw. `event["state"]` / `event["previous_state"]` |
| Legale Züge | `event["actions"]` (`kind`: `capture`, `house_entry`, `house_advance`, `move`) |
| Spielende / Sieger | `session.finished`, `session.winner` |
| Zugverlauf für Reward-Shaping | `event["moves"]` (alle bewegten Figuren inkl. geschlagener, `to == -1`) |
| Reproduzierbarkeit | `seed=` / `rng=`; Würfel erzwingen mit `dice_rolls=[...]` |
| Beliebige Startsituation | `start_positions={spielerindex: [positionen]}` |
| Andere Regeln/Brettgrößen | `Game_Mode({...})` (z. B. `n_players`, `n_pieces`, `knock_duty`, `n_dice_sides`) |
| Spiel für Training mehrfach starten | `env.reset(seed=...)` bzw. pro Partie neue `GameSession`; `Game_Mode` kann wiederverwendet werden |

### Typische Trainings-Setups

- **Turnier/Evaluierung:** viele Seeds durchlaufen, Siege je Spieler zählen. Wegen fester Sitzreihenfolge (Spieler 1 beginnt)
  die Plätze rotieren, um Positionsvorteile auszugleichen. Fairness-Referenz: Siegquote ≈ 1/`n_players`.
- **Self-Play / RL:** `MaednEnv(controlled=[0,1,2,3])` mit derselben Policy für alle Sitze; die Beobachtung ist bereits sitzrelativ kodiert.
- **Evolution/Parameteroptimierung:** Agent mit Gewichten parametrisieren (z. B. Bewertung von `capture`,
  `house_entry`, Abstand zu Gegnern) und per Turnier bewerten.
- **Daten sammeln:** `output_results(game, log)` oder `json.dump(log, ...)` speichert Logs im
  [Log-Format](#ausgabedateien--log-format); `output/` wird dabei automatisch angelegt.

### Performance & Stolperfallen

- Reine Python-Simulation; für sehr viele Partien mit `multiprocessing` parallelisieren (jede Partie unabhängig, eigener Seed).
- `GameSession.snapshot()` kopiert die Positionen (Deep Copy) – bei jedem Aufruf Kosten; nicht unnötig oft aufrufen.
- `deliberate_moves` wird nur für Statistik gezählt; bei eigenen Agents zählt jede Wahl mit > 1 legalem Zug.
- Positionen in Logs/Snapshots sind gemischt typisiert (`-1`, `int`, `"house_k"`); `MaednEnv` liefert sie bereits numerisch.
- Das Spiel kann theoretisch sehr lange dauern; `MaednEnv` hat dafür `max_rounds` (`truncated`), bei `GameSession` selbst `session.round_num` prüfen.
- Nicht lernbar sind Entscheidungen, die nach den Regeln automatisch ablaufen (Herausbringen bei Sechs, Startfeld freimachen, Zug bei nur einer Möglichkeit).
- Einen eigenen Agent im PvE-Fenster einzusetzen erfordert eine Änderung in `create_agents` in `maedn_PvE.py`
  (aktuell `[HumanAgent()] + [RandomAgent() ...]`).

---

## Tests

Die Tests liegen in `maedpy/tests/` und sind **eigenständige Skripte** (keine pytest-Konfiguration).
Sie fügen `../bin/` bzw. `..` per `sys.path` hinzu und lesen `test_setup.json` relativ zum
Arbeitsverzeichnis. Deshalb **aus `maedpy/tests/` heraus** starten:

```bash
cd maedpy/tests
python maedn_test_priorities.py
python maedn_test_double_6_intro.py
python maedn_test_triple_roll_intro.py
python maedn_test_env.py                # MaednEnv und Agent-Observation
python maedn_knock_and_house_test.py   # benötigt Tkinter/Display (GUI-/Canvas-Tests)
```

Mit festen `dice_rolls` und `start_positions` lassen sich Spielsituationen deterministisch nachstellen
(`GameSession(game, dice_rolls=[...], start_positions={0: [...]})`) – das ist die bevorzugte Methode für neue Tests.

---

## Hinweise für KI-Assistenten

- **Arbeitsverzeichnis:** Skripte in `maedpy/` nutzen teils relative und teils absolute Pfade
  (`Path(__file__)`). Imports funktionieren per `try: from .bin... except ImportError: from bin...`
  bzw. `sys.path`-Manipulation. Neue Module sollten dieses Muster beibehalten.
- **Engine und GUI sind getrennt.** Spiellogik gehört nach `bin/` (`Player_class.py`, `Simulate_Game.py`);
  Darstellung nach `board_view.py` / `maedn_PvE.py` / `maedn_visualization.py`. Keine Tkinter-Imports in `bin/`.
- **Neuer Agent (z. B. bessere KI):** Klasse mit `requires_input = False` und
  `choose_action(observation, actions, rng) -> piece_index` anlegen (Vorbild: `RandomAgent`),
  dann an `GameSession(game, agents=[...])` übergeben. Die Zuglegalität wird in `GameSession` geprüft.
  Beachte, dass die `deliberate_moves`-Zählung in `_resolve_regular_move` aktuell `RandomAgent` gesondert behandelt.
- **Neuer Parameter:** in `Game_Mode.__init__` (Default + JSON-Lesen), in die `parameters`-Liste für `out_folder`
  aufnehmen (Achtung: ändert Ordnernamen und die Auswertungs-Annahme „erste Zahl = Spielerzahl“), in
  `CLASSIC_DEFAULTS` / `parameters_for_game` und die gewünschten Spielmodi in `game_mode.json` ergänzen.
- **Positionen sind gemischt typisiert** (`-1`, `int`, `"house_k"`). Immer mit `isinstance` bzw.
  `Player._is_house_position` / `_house_slot` prüfen; nie numerisch vergleichen, ohne den Typ zu kennen.
- **Log-Schema stabil halten** – Replay und Statistik hängen daran
  (Reihenfolge der Schlüssel wird in `tests/maedn_test_priorities.py` geprüft).
- **Reproduzierbarkeit:** `seed=` (oder `rng=`) an `GameSession`/`simulate_game` übergeben; ohne Seed wird das globale `random`-Modul genutzt.
- **`Player.regular_move`** ist die ältere, direkte Zufallsvariante; die aktive Logik läuft über `GameSession._resolve_regular_move`.
- **Bekannte Eigenheiten:** Dateiname `maedn_PvE.py` und `MADN.py`/`MÄDN`-Ordner enthalten teils Umlaute;
  Code und Kommentare sind gemischt Deutsch/Englisch. Die generierten Ordner unter `output/` können tausende JSON-Dateien enthalten – nicht komplett einlesen oder in Prompts laden.
- Vor Änderungen die Tests aus `maedpy/tests/` ausführen und neue Regeln mit deterministischen Szenarien absichern.

---

## Bekannte Einschränkungen / TODO

Aus `maedpy/todo.txt`:

- Prüfen, ob Überspringen im Haus weiterhin verboten ist.
- Signal, wenn eine Figur ins Haus geht.

Weitere Beobachtungen:

- Es gibt keine automatisierte Test-Konfiguration (pytest/CI).
- Gegner im PvE sind ausschließlich `RandomAgent`.

---

## Repository-Hygiene

- [.gitignore](.gitignore) schließt aus: `maedpy/output/`, `maedpy/output_test/`, `maedpy/game_log.json`,
  `maedpy/game_end.json`, `maedpy/time_dep.json`, `Literatur/`, `*.docx`, `*.xlsx`, `__pycache__/`, `.vscode/`.
- **Ausgabeordner müssen nicht eingecheckt werden:** `output/…` (Bot-Logs, PvE-Logs, Statistik-PNGs) wird bei Bedarf
  automatisch angelegt (`os.makedirs` / `mkdir(parents=True)` in `output_results`, `save_pve_game`,
  `create_winner_distribution`, `maedn_statistic`). `output_test/` wird vom Code gar nicht verwendet.
- **Vor dem ersten Push prüfen**, dass die ausgeschlossenen Dateien nicht bereits in einer (privaten) Git-Historie stehen.
  Am sichersten: `MÄDN/` als Wurzel eines **neuen** Repos verwenden (`git init`), nicht den übergeordneten `github/`-Ordner,
  und ohne die alte Historie starten. Bereits getrackte Dateien werden von `.gitignore` nicht entfernt (`git rm -r --cached <pfad>`).
- Lizenz: [MIT](LICENSE) © 2026 Felix Schleifer. Frei nutzbar (auch kommerziell), aber der Copyright-Hinweis und der Lizenztext müssen in allen Kopien und wesentlichen Teilen des Codes erhalten bleiben (Namensnennung).
