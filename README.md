# Button Trainer

A small Python game for practicing controller button presses, inspired by the prompts in
Phantom Blade Zero / Black Myth. Works with **Xbox** and **PlayStation** controllers.

A ring drains **counter-clockwise** around a button. Press the right button in time and the
ring turns full white and vanishes, then **NICE!** and your reaction time in **ms** pop up and
the next button appears.

---

## Requirements

- Python 3.9+
- pygame

```bash
pip install pygame
```

## Run

```bash
python button_trainer.py
```

---

## How to use

### Menu

| Setting | What it does |
|---|---|
| **Xbox / PlayStation** | Chooses the preset (icons and button numbers). Auto-picked if your pad looks like a PS controller. |
| **LB LT RB RT** | Tick the shoulder buttons / triggers you want to practice. |
| **X Y B A** | Tick the face buttons you want to practice. |
| **MASH prompts** | If ticked, A/B/X/Y sometimes ask you to spam the button. If unticked, no mash prompts. |
| **START** | Starts the game. You must tick **at least 1 button** first. |

Menu controls:

- Move: D-pad / left stick / arrow keys / WASD / mouse
- Tick or select: **A** (Cross) / Enter / Space / click
- Start: click START, press Enter, or press **START** (Xbox) / **OPTIONS** (PlayStation) on the pad
- ESC: quit

### Game

- **Single press** - press the shown button before the ring runs out (2 seconds).
- **MASH!** - press the shown face button the required number of times (e.g. `MASH! 3/8`)
  before the ring runs out. The inner ring fills as you press.
- Wrong button -> the screen shakes and the target stays. Ring runs out -> **MISS**.
- Reaction time colors: green under 350 ms, yellow under 700 ms, white otherwise.
- **START** on the pad or **ESC** -> back to the menu
- **R** -> reset stats

### Keyboard fallback (no controller)

| Key | Button |
|---|---|
| Z | A (Cross) |
| X | B (Circle) |
| C | X (Square) |
| V | Y (Triangle) |
| Q / E | LB / RB (L1 / R1) |
| 1 / 3 | LT / RT (L2 / R2) |

---

## Settings you can change

At the top of `button_trainer.py`:

```python
SINGLE_LIMIT = 2.0          # seconds to press a single button
SPAM_CHANCE = 0.35          # chance a face button becomes a mash prompt
SPAM_MIN, SPAM_MAX = 6, 12  # presses needed for a mash prompt
GAP_MIN, GAP_MAX = 0.45, 0.9  # pause between prompts
```

If a button on your controller is wrong, edit the numbers in the `PRESETS` block
(PlayStation pads number their buttons differently on Windows and Linux).
If LT / RT don't register, change `lt_axis` / `rt_axis` there.

---

## Build a .exe (Windows)

You must build on Windows to get a Windows `.exe`.

1. Install PyInstaller:

   ```bash
   pip install pyinstaller
   ```

2. Build (run this in the folder that contains `button_trainer.py`):

   ```bash
   pyinstaller --onefile --windowed --name ButtonTrainer button_trainer.py
   ```

3. Your program is at:

   ```
   dist\ButtonTrainer.exe
   ```

   You can copy that single file anywhere and double-click it. The `build` folder,
   the `.spec` file and `__pycache__` can be deleted.

What the options mean:

| Option | Meaning |
|---|---|
| `--onefile` | Bundle everything into a single `.exe`. |
| `--windowed` | No black console window behind the game. |
| `--name ButtonTrainer` | Name of the output file. |
| `--icon icon.ico` | (optional) Give the `.exe` a custom icon. |

### Troubleshooting

- **`pyinstaller` is not recognized** -> use `python -m PyInstaller --onefile --windowed --name ButtonTrainer button_trainer.py`
- **The exe closes instantly** -> rebuild without `--windowed` and run it from a terminal to see the error.
- **Antivirus flags the exe** -> this is a common false positive with PyInstaller one-file builds. Add an exception, or build without `--onefile` (you get a folder instead).
- **Rebuilding after code changes** -> just run the same command again.