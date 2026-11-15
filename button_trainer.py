"""
Button Trainer  (Xbox / PlayStation)
------------------------------------
Practice pressing controller buttons like the prompts in Phantom Blade Zero / Black Myth.

MENU
  - Pick a preset: Xbox or PlayStation
  - Tick which buttons you want to practice (LB LT RB RT / X Y B A) - at least 1
  - Tick "Mash" if you want spam prompts (A/B/X/Y only)
  - Press START (click it, Enter, or the START / OPTIONS button on your pad)
  Move with D-pad / left stick / arrow keys / WASD / mouse.  A (Cross) / Enter / click = toggle.

GAME
  - A ring drains COUNTER-CLOCKWISE around the button.
  - Press the right button -> ring turns full white, expands and vanishes,
    "NICE!" + your reaction time (ms) shows up, then the next button appears.
  - Ring runs out -> MISS.  Wrong button -> screen shake (target stays).
  - START / ESC = back to menu, R = reset stats

Install:   pip install pygame
Run:       python button_trainer.py

Keyboard fallback (no pad):  Z=A  X=B  C=X  V=Y  Q=LB  E=RB  1=LT  3=RT
(For PlayStation: A=Cross  B=Circle  X=Square  Y=Triangle, LB/RB/LT/RT = L1/R1/L2/R2)
"""
import math
import random
import sys
import time

import pygame

# ----------------------------------------------------------------- settings
W, H = 1000, 640
FPS = 60

SINGLE_LIMIT = 2.0          # seconds to press a single button
SPAM_CHANCE = 0.35          # chance that an enabled A/B/X/Y becomes a "mash" prompt
SPAM_MIN, SPAM_MAX = 6, 12  # how many presses for a mash prompt
SPAM_BASE_TIME = 1.2        # mash time limit = base + presses * per_press
SPAM_TIME_PER_PRESS = 0.32
GAP_MIN, GAP_MAX = 0.45, 0.9  # pause between prompts
TRIGGER_THRESHOLD = 0.3

LINUX = sys.platform.startswith("linux")

# Controller mappings (pygame 2 / SDL2).  Logical names are always
#   A B X Y LB RB LT RT   (for PlayStation: Cross Circle Square Triangle L1 R1 L2 R2)
# If a button on your pad is wrong, edit the numbers here.
PRESETS = {
    "Xbox": dict(
        buttons={0: "A", 1: "B", 2: "X", 3: "Y", 4: "LB", 5: "RB"},
        lt_axis=2 if LINUX else 4, rt_axis=5, start_button=7,
    ),
    "PlayStation": dict(
        buttons=({0: "A", 1: "B", 2: "Y", 3: "X", 4: "LB", 5: "RB"} if LINUX
                 else {0: "A", 1: "B", 2: "X", 3: "Y", 9: "LB", 10: "RB"}),
        lt_axis=2 if LINUX else 4, rt_axis=5, start_button=9 if LINUX else 6,
    ),
}
PS_NAME_HINTS = ("ps4", "ps5", "dualshock", "dualsense", "playstation", "wireless controller", "sony")

KEYS = {
    pygame.K_z: "A", pygame.K_x: "B", pygame.K_c: "X", pygame.K_v: "Y",
    pygame.K_q: "LB", pygame.K_e: "RB", pygame.K_1: "LT", pygame.K_3: "RT",
}

FACE = ["A", "B", "X", "Y"]
SHOULDER = ["LB", "RB", "LT", "RT"]
ALL = FACE + SHOULDER

LABELS = {
    "Xbox": {n: n for n in ALL},
    "PlayStation": {"A": "Cross", "B": "Circle", "X": "Square", "Y": "Triangle",
                    "LB": "L1", "RB": "R1", "LT": "L2", "RT": "R2"},
}
_SHOULDER_COL = (210, 215, 230)
PRESET_COLORS = {
    "Xbox": {"A": (88, 214, 110), "B": (240, 80, 80), "X": (80, 150, 255), "Y": (255, 205, 60)},
    "PlayStation": {"A": (110, 160, 255), "B": (245, 85, 90), "X": (240, 140, 205), "Y": (90, 220, 150)},
}
for _p in PRESET_COLORS.values():
    for _n in SHOULDER:
        _p[_n] = _SHOULDER_COL

WHITE = (255, 255, 255)
ACCENT = (110, 190, 255)
GOOD = (80, 205, 125)
BAD = (255, 95, 95)
BG_TOP, BG_BOTTOM = (22, 26, 40), (8, 9, 15)

CENTER = (W // 2, 330)
RING_R = 112
RING_W = 12


# ------------------------------------------------------------------ helpers
def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_out_back(t):
    t = max(0.0, min(1.0, t))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def get_font(size):
    return pygame.font.SysFont("segoeui,helveticaneue,arial,dejavusans", size, bold=True)


def ring_surface(radius, thickness, start, stop, color, alpha=255, ss=2):
    """Anti-aliased arc from angle `start` to `stop` (radians, counter-clockwise)."""
    size = int((radius + thickness) * 2 + 6)
    S = size * ss
    surf = pygame.Surface((S, S), pygame.SRCALPHA)
    c = S / 2
    ro = (radius + thickness / 2) * ss
    ri = (radius - thickness / 2) * ss
    span = stop - start
    if span >= math.tau - 1e-3:
        pygame.draw.circle(surf, color, (c, c), ro, max(1, int(ro - ri)))
    elif span > 1e-3:
        steps = max(3, int(span / math.tau * 160))
        outer, inner = [], []
        for i in range(steps + 1):
            a = start + span * i / steps
            outer.append((c + ro * math.cos(a), c - ro * math.sin(a)))
            inner.append((c + ri * math.cos(a), c - ri * math.sin(a)))
        pygame.draw.polygon(surf, color, outer + inner[::-1])
        mid = (ro + ri) / 2
        for a in (start, stop):  # round caps
            pygame.draw.circle(surf, color, (c + mid * math.cos(a), c - mid * math.sin(a)),
                               (ro - ri) / 2)
    else:
        return None
    surf = pygame.transform.smoothscale(surf, (size, size))
    if alpha < 255:
        surf.set_alpha(max(0, int(alpha)))
    return surf


def blit_center(dst, img, pos):
    if img is not None:
        dst.blit(img, img.get_rect(center=(int(pos[0]), int(pos[1]))))


def draw_text(dst, text, font, color, center, alpha=255):
    img = font.render(text, True, color)
    if alpha < 255:
        img.set_alpha(max(0, int(alpha)))
    dst.blit(img, img.get_rect(center=(int(center[0]), int(center[1]))))


def make_icon(name, preset, font_big, font_mid):
    """Pre-render a nice button icon (200x200, anti-aliased)."""
    ss = 2
    size = 200 * ss
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    col = PRESET_COLORS[preset][name]
    label = LABELS[preset][name]
    if name in FACE:
        if preset == "Xbox":
            pygame.draw.circle(surf, lerp_color(col, (0, 0, 0), 0.55), (c, c + 4 * ss), 58 * ss)
            pygame.draw.circle(surf, col, (c, c), 58 * ss)
            pygame.draw.circle(surf, lerp_color(col, WHITE, 0.45), (c, c), 58 * ss, 4 * ss)
            txt = font_big.render(label, True, WHITE)
            txt = pygame.transform.smoothscale(txt, (txt.get_width() * ss, txt.get_height() * ss))
            surf.blit(txt, txt.get_rect(center=(c, c)))
        else:  # PlayStation symbols
            pygame.draw.circle(surf, (14, 16, 24), (c, c + 4 * ss), 58 * ss)
            pygame.draw.circle(surf, (44, 48, 68), (c, c), 58 * ss)
            pygame.draw.circle(surf, lerp_color(col, (0, 0, 0), 0.25), (c, c), 58 * ss, 3 * ss)
            w = 8 * ss
            if name == "A":      # cross
                d = 22 * ss
                pygame.draw.line(surf, col, (c - d, c - d), (c + d, c + d), w)
                pygame.draw.line(surf, col, (c - d, c + d), (c + d, c - d), w)
            elif name == "B":    # circle
                pygame.draw.circle(surf, col, (c, c), 25 * ss, w)
            elif name == "X":    # square
                pygame.draw.rect(surf, col, pygame.Rect(c - 23 * ss, c - 23 * ss, 46 * ss, 46 * ss),
                                 w, border_radius=2 * ss)
            else:                # triangle
                pts = [(c, c - 28 * ss), (c - 28 * ss, c + 20 * ss), (c + 28 * ss, c + 20 * ss)]
                pygame.draw.lines(surf, col, True, pts, w)
                for p in pts:
                    pygame.draw.circle(surf, col, p, w // 2)
    else:
        if name in ("LB", "RB"):
            w, h = 140 * ss, 56 * ss
        else:
            w, h = 108 * ss, 96 * ss
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (c, c)
        pygame.draw.rect(surf, (20, 22, 32), rect.move(0, 5 * ss), border_radius=22 * ss)
        pygame.draw.rect(surf, (62, 67, 88), rect, border_radius=22 * ss)
        pygame.draw.rect(surf, col, rect, width=4 * ss, border_radius=22 * ss)
        txt = font_mid.render(label, True, WHITE)
        txt = pygame.transform.smoothscale(txt, (txt.get_width() * ss, txt.get_height() * ss))
        surf.blit(txt, txt.get_rect(center=(c, c)))
    return pygame.transform.smoothscale(surf, (200, 200))


def make_background():
    bg = pygame.Surface((W, H))
    for y in range(H):
        bg.fill(lerp_color(BG_TOP, BG_BOTTOM, y / H), (0, y, W, 1))
    glow = pygame.Surface((W, H), pygame.SRCALPHA)
    for r, a in ((320, 10), (240, 14), (160, 18)):
        pygame.draw.circle(glow, (120, 150, 255, a), CENTER, r)
    bg.blit(glow, (0, 0))
    return bg


# --------------------------------------------------------------------- game
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Button Trainer")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()

        self.f_title = get_font(54)
        self.f_huge = get_font(72)
        self.f_big = get_font(54)
        self.f_start = get_font(40)
        self.f_mid = get_font(34)
        self.f_label = get_font(26)
        self.f_small = get_font(22)
        self.f_tiny = get_font(18)

        self.bg = make_background()
        self.icons = {p: {n: make_icon(n, p, self.f_big, self.f_mid) for n in ALL}
                      for p in PRESETS}
        self.menu_icons = {}
        for p in PRESETS:
            self.menu_icons[p] = {}
            for n in ALL:
                on = pygame.transform.smoothscale(self.icons[p][n], (100, 100))
                off = on.copy()
                off.set_alpha(70)
                self.menu_icons[p][n] = (on, off)

        pygame.joystick.init()
        self.joy = None
        if pygame.joystick.get_count() > 0:
            self.joy = pygame.joystick.Joystick(0)
        self.preset = "Xbox"
        self.auto_preset()

        # settings chosen in the menu
        self.enabled = {n: True for n in ALL}
        self.mash = True

        # menu state
        self.mode = "menu"
        self.error_until = 0.0
        self.stick_dir = {"l": False, "r": False, "u": False, "d": False}
        self.build_layout()
        self.focus = (4, 0)  # START

        # game state
        self.trig_down = {"LT": False, "RT": False}
        self.reset_stats()
        self.target = None
        self.last_name = None
        self.effects = []
        self.shake = 0.0
        self.spawn_at = 0.0

    # ------------------------------------------------------------ settings
    def auto_preset(self):
        if self.joy is not None:
            name = self.joy.get_name().lower()
            if any(h in name for h in PS_NAME_HINTS):
                self.preset = "PlayStation"
            else:
                self.preset = "Xbox"

    def col(self, name):
        return PRESET_COLORS[self.preset][name]

    # ---------------------------------------------------------------- menu
    def build_layout(self):
        self.rows = []
        self.rects = {}

        # row 0: preset
        pw, ph, gap = 210, 50, 16
        left = W // 2 - pw - gap // 2
        r0 = []
        for i, p in enumerate(PRESETS):
            self.rects[(0, i)] = pygame.Rect(left + i * (pw + gap), 95, pw, ph)
            r0.append(("preset", p))
        self.rows.append(r0)

        # rows 1-2: buttons
        cw, ch, cgap = 190, 80, 20
        x0 = (W - (4 * cw + 3 * cgap)) // 2
        for row, (names, top) in enumerate((
                (["LB", "LT", "RB", "RT"], 185),
                (["X", "Y", "B", "A"], 305)), start=1):
            items = []
            for i, n in enumerate(names):
                self.rects[(row, i)] = pygame.Rect(x0 + i * (cw + cgap), top, cw, ch)
                items.append(("btn", n))
            self.rows.append(items)

        # row 3: mash
        self.rects[(3, 0)] = pygame.Rect(0, 0, 600, 56)
        self.rects[(3, 0)].midtop = (W // 2, 412)
        self.rows.append([("mash", None)])

        # row 4: start
        self.rects[(4, 0)] = pygame.Rect(0, 0, 320, 62)
        self.rects[(4, 0)].midtop = (W // 2, 505)
        self.rows.append([("start", None)])

    def move_focus(self, dr, dc):
        r, c = self.focus
        if dr:
            r = max(0, min(len(self.rows) - 1, r + dr))
            c = min(c, len(self.rows[r]) - 1)
        if dc:
            c = max(0, min(len(self.rows[r]) - 1, c + dc))
            if r == 0:  # moving left/right on the preset row picks it right away
                self.preset = self.rows[0][c][1]
        self.focus = (r, c)

    def activate(self, pos, now):
        kind, val = self.rows[pos[0]][pos[1]]
        self.focus = pos
        if kind == "preset":
            self.preset = val
        elif kind == "btn":
            self.enabled[val] = not self.enabled[val]
        elif kind == "mash":
            self.mash = not self.mash
        elif kind == "start":
            self.start_game(now)

    def start_game(self, now):
        if not any(self.enabled.values()):
            self.error_until = now + 2.2
            return
        self.mode = "play"
        self.reset_stats()
        self.target = None
        self.last_name = None
        self.effects = []
        self.shake = 0.0
        self.trig_down = {"LT": False, "RT": False}
        self.spawn_at = now + 0.8

    def hit_test(self, pos):
        for key, rect in self.rects.items():
            if rect.collidepoint(pos):
                return key
        return None

    # --------------------------------------------------------------- stats
    def reset_stats(self):
        self.hits = 0
        self.misses = 0
        self.wrong = 0
        self.streak = 0
        self.best_streak = 0
        self.times = []

    # ---------------------------------------------------------- target flow
    def spawn(self, now):
        pool = [n for n in ALL if self.enabled[n]]
        if len(pool) > 1 and self.last_name in pool:
            pool.remove(self.last_name)
        name = random.choice(pool)
        kind, need = "single", 1
        limit = SINGLE_LIMIT
        if self.mash and name in FACE and random.random() < SPAM_CHANCE:
            kind = "spam"
            need = random.randint(SPAM_MIN, SPAM_MAX)
            limit = SPAM_BASE_TIME + need * SPAM_TIME_PER_PRESS
        self.target = dict(name=name, kind=kind, need=need, count=0,
                           t0=now, limit=limit, pulse=0.0)
        self.last_name = name

    def press(self, name, now):
        t = self.target
        if t is None:
            return
        if name == t["name"]:
            t["count"] += 1
            t["pulse"] = 1.0
            if t["count"] >= t["need"]:
                self.on_hit(now)
        else:
            self.wrong += 1
            self.shake = 0.35

    def on_hit(self, now):
        t = self.target
        ms = int((now - t["t0"]) * 1000)
        self.hits += 1
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        self.times.append(ms)
        self.effects.append(dict(type="hit", t0=now, name=t["name"], ms=ms))
        self.target = None
        self.spawn_at = now + random.uniform(GAP_MIN, GAP_MAX)

    def on_miss(self, now):
        t = self.target
        self.misses += 1
        self.streak = 0
        self.effects.append(dict(type="miss", t0=now, name=t["name"]))
        self.target = None
        self.spawn_at = now + random.uniform(GAP_MIN, GAP_MAX)

    # --------------------------------------------------------------- input
    def handle_events(self, now):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.JOYDEVICEADDED:
                self.joy = pygame.joystick.Joystick(e.device_index)
                if self.mode == "menu":
                    self.auto_preset()
                continue
            if e.type == pygame.JOYDEVICEREMOVED:
                self.joy = None
                continue
            if self.mode == "menu":
                if not self.menu_event(e, now):
                    return False
            else:
                self.play_event(e, now)

        if self.mode == "menu":
            self.poll_stick()
        else:
            self.poll_triggers(now)
        return True

    def menu_event(self, e, now):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                return False
            moves = {pygame.K_UP: (-1, 0), pygame.K_w: (-1, 0), pygame.K_DOWN: (1, 0),
                     pygame.K_s: (1, 0), pygame.K_LEFT: (0, -1), pygame.K_a: (0, -1),
                     pygame.K_RIGHT: (0, 1), pygame.K_d: (0, 1)}
            if e.key in moves:
                self.move_focus(*moves[e.key])
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.start_game(now)
            elif e.key == pygame.K_SPACE:
                self.activate(self.focus, now)
        elif e.type == pygame.MOUSEMOTION:
            hit = self.hit_test(e.pos)
            if hit:
                self.focus = hit
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            hit = self.hit_test(e.pos)
            if hit:
                self.activate(hit, now)
        elif e.type == pygame.JOYHATMOTION:
            x, y = e.value
            if y == 1:
                self.move_focus(-1, 0)
            elif y == -1:
                self.move_focus(1, 0)
            elif x == -1:
                self.move_focus(0, -1)
            elif x == 1:
                self.move_focus(0, 1)
        elif e.type == pygame.JOYBUTTONDOWN:
            if e.button == PRESETS[self.preset]["start_button"]:
                self.start_game(now)
            elif e.button == 0:
                self.activate(self.focus, now)
            elif self.joy is not None and self.joy.get_numhats() == 0 and 11 <= e.button <= 14:
                dr, dc = {11: (-1, 0), 12: (1, 0), 13: (0, -1), 14: (0, 1)}[e.button]
                self.move_focus(dr, dc)
        return True

    def poll_stick(self):
        if self.joy is None or self.joy.get_numaxes() < 2:
            return
        ax, ay = self.joy.get_axis(0), self.joy.get_axis(1)
        for key, cond, mv in (("l", ax < -0.6, (0, -1)), ("r", ax > 0.6, (0, 1)),
                              ("u", ay < -0.6, (-1, 0)), ("d", ay > 0.6, (1, 0))):
            if cond and not self.stick_dir[key]:
                self.move_focus(*mv)
            self.stick_dir[key] = cond

    def play_event(self, e, now):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.mode = "menu"
            elif e.key == pygame.K_r:
                self.reset_stats()
            elif e.key in KEYS:
                self.press(KEYS[e.key], now)
        elif e.type == pygame.JOYBUTTONDOWN:
            cfg = PRESETS[self.preset]
            if e.button == cfg["start_button"]:
                self.mode = "menu"
                return
            name = cfg["buttons"].get(e.button)
            if name:
                self.press(name, now)

    def poll_triggers(self, now):
        # triggers are analog axes -> detect the press edge ourselves
        if self.joy is None:
            return
        cfg = PRESETS[self.preset]
        for name, axis in (("LT", cfg["lt_axis"]), ("RT", cfg["rt_axis"])):
            if axis < self.joy.get_numaxes():
                down = self.joy.get_axis(axis) > TRIGGER_THRESHOLD
                if down and not self.trig_down[name]:
                    self.press(name, now)
                self.trig_down[name] = down

    # -------------------------------------------------------------- update
    def update(self, now, dt):
        if self.mode != "play":
            return
        self.shake = max(0.0, self.shake - dt)
        if self.target is None:
            if now >= self.spawn_at:
                self.spawn(now)
        else:
            t = self.target
            t["pulse"] = max(0.0, t["pulse"] - dt * 6)
            if now - t["t0"] >= t["limit"]:
                self.on_miss(now)
        self.effects = [fx for fx in self.effects if now - fx["t0"] < 1.1]

    # ------------------------------------------------------- drawing: menu
    def draw_checkbox(self, center, checked, accent):
        box = pygame.Rect(0, 0, 30, 30)
        box.center = center
        if checked:
            pygame.draw.rect(self.screen, accent, box, border_radius=8)
            x, y = box.x, box.y
            pygame.draw.lines(self.screen, (10, 14, 24), False,
                              [(x + 7, y + 16), (x + 13, y + 22), (x + 23, y + 9)], 4)
        else:
            pygame.draw.rect(self.screen, (90, 98, 130), box, width=2, border_radius=8)

    def draw_card(self, rect, checked, focused, accent):
        bgc = (32, 38, 60) if checked else (22, 26, 42)
        pygame.draw.rect(self.screen, bgc, rect, border_radius=16)
        pygame.draw.rect(self.screen, accent if checked else (58, 64, 92), rect,
                         width=2, border_radius=16)
        if focused:
            pygame.draw.rect(self.screen, WHITE, rect.inflate(10, 10), width=2, border_radius=20)

    def draw_menu(self, now):
        s = self.screen
        draw_text(s, "BUTTON TRAINER", self.f_title, WHITE, (W // 2, 48))

        # preset segmented control
        for i, p in enumerate(PRESETS):
            rect = self.rects[(0, i)]
            sel = (p == self.preset)
            pygame.draw.rect(s, ACCENT if sel else (26, 31, 50), rect, border_radius=25)
            if not sel:
                pygame.draw.rect(s, (62, 68, 98), rect, width=2, border_radius=25)
            draw_text(s, p, self.f_label, (10, 14, 24) if sel else (170, 178, 205), rect.center)
            if self.focus == (0, i):
                pygame.draw.rect(s, WHITE, rect.inflate(10, 10), width=2, border_radius=30)

        # sections
        draw_text(s, "SHOULDERS & TRIGGERS", self.f_tiny, (120, 130, 165), (W // 2, 168))
        draw_text(s, "FACE BUTTONS", self.f_tiny, (120, 130, 165), (W // 2, 288))
        for row in (1, 2):
            for i, (_, n) in enumerate(self.rows[row]):
                rect = self.rects[(row, i)]
                on = self.enabled[n]
                self.draw_card(rect, on, self.focus == (row, i), self.col(n))
                self.draw_checkbox((rect.x + 32, rect.centery), on, self.col(n))
                icon = self.menu_icons[self.preset][n][0 if on else 1]
                blit_center(s, icon, (rect.x + 122, rect.centery))

        # mash
        rect = self.rects[(3, 0)]
        face_on = any(self.enabled[n] for n in FACE)
        self.draw_card(rect, self.mash and face_on, self.focus == (3, 0), ACCENT)
        self.draw_checkbox((rect.x + 32, rect.centery), self.mash, ACCENT)
        label = ("MASH prompts  (spam the face buttons)" if face_on
                 else "MASH prompts  (needs a face button ticked)")
        tcol = (225, 230, 245) if face_on else (110, 118, 145)
        img = self.f_label.render(label, True, tcol)
        s.blit(img, img.get_rect(midleft=(rect.x + 62, rect.centery)))

        # start
        rect = self.rects[(4, 0)]
        ok = any(self.enabled.values())
        pygame.draw.rect(s, GOOD if ok else (60, 66, 90), rect, border_radius=31)
        draw_text(s, "START", self.f_start, (8, 24, 14) if ok else (150, 158, 185), rect.center)
        if self.focus == (4, 0):
            pygame.draw.rect(s, WHITE, rect.inflate(12, 12), width=2, border_radius=37)

        if now < self.error_until:
            fade = min(1.0, (self.error_until - now) / 0.5) * 255
            draw_text(s, "Tick at least 1 button first!", self.f_mid, BAD,
                      (W // 2, 488), alpha=fade)

        hint = ("D-pad / stick / arrows / mouse = move     A (Cross) / Enter / click = tick     "
                "START = go")
        draw_text(s, hint, self.f_tiny, (110, 118, 145), (W // 2, H - 22))

    # ------------------------------------------------------- drawing: game
    def draw_target(self, now, center):
        t = self.target
        name = t["name"]
        col = self.col(name)
        age = now - t["t0"]
        appear = ease_out_back(age / 0.18)
        frac = max(0.0, 1.0 - age / t["limit"])  # time left

        blit_center(self.screen, ring_surface(RING_R, RING_W, 0, math.tau, WHITE, alpha=28), center)

        # time ring: drains COUNTER-CLOCKWISE (the eaten end travels ccw from the top)
        start = math.pi / 2 + (1 - frac) * math.tau
        stop = math.pi / 2 + math.tau
        base = (235, 240, 255) if name in SHOULDER else col
        ring_col = lerp_color(base, (255, 70, 70), max(0.0, (0.3 - frac) / 0.3))
        blit_center(self.screen, ring_surface(RING_R, RING_W, start, stop, ring_col), center)

        if t["kind"] == "spam":
            p = t["count"] / t["need"]
            blit_center(self.screen,
                        ring_surface(RING_R - 28, 6, math.pi / 2 - p * math.tau, math.pi / 2,
                                     lerp_color(col, WHITE, 0.3)), center)
            draw_text(self.screen, f"MASH!  {t['count']}/{t['need']}", self.f_mid, col,
                      (center[0], center[1] + RING_R + 48))

        scale = (0.55 + 0.45 * appear) * (1 + 0.16 * t["pulse"])
        sz = max(2, int(200 * scale))
        icon = pygame.transform.smoothscale(self.icons[self.preset][name], (sz, sz))
        blit_center(self.screen, icon, center)

    def draw_effects(self, now, center):
        for fx in self.effects:
            a = now - fx["t0"]
            if fx["type"] == "hit":
                p = ease_out(a / 0.5)
                if a < 0.5:
                    radius = RING_R * (1 + 0.35 * p)
                    thick = RING_W * (1 - 0.5 * p)
                    blit_center(self.screen,
                                ring_surface(radius, thick, 0, math.tau, WHITE, alpha=255 * (1 - p)),
                                center)
                    sz = int(200 * (1 + 0.45 * p))
                    icon = pygame.transform.smoothscale(self.icons[self.preset][fx["name"]], (sz, sz))
                    icon.set_alpha(int(255 * (1 - p)))
                    blit_center(self.screen, icon, center)
                tp = ease_out(a / 0.25)
                fade = 255 if a < 0.7 else 255 * (1 - (a - 0.7) / 0.4)
                ytxt = center[1] - RING_R - 70 - 14 * tp
                ms = fx["ms"]
                tcol = (120, 255, 190) if ms < 350 else (255, 225, 110) if ms < 700 else (255, 255, 255)
                sc = 0.7 + 0.3 * ease_out_back(a / 0.25)
                img = self.f_huge.render("NICE!", True, tcol)
                img = pygame.transform.smoothscale(
                    img, (max(2, int(img.get_width() * sc)), max(2, int(img.get_height() * sc))))
                img.set_alpha(max(0, int(fade)))
                self.screen.blit(img, img.get_rect(center=(center[0], int(ytxt))))
                draw_text(self.screen, f"{ms} ms", self.f_mid, WHITE,
                          (center[0], ytxt + 46), alpha=fade)
            else:  # miss
                if a < 0.5:
                    p = ease_out(a / 0.5)
                    blit_center(self.screen,
                                ring_surface(RING_R * (1 - 0.1 * p), RING_W, 0, math.tau,
                                             (255, 70, 70), alpha=220 * (1 - p)), center)
                fade = 255 if a < 0.7 else 255 * (1 - (a - 0.7) / 0.4)
                draw_text(self.screen, "MISS", self.f_huge, (255, 90, 90),
                          (center[0], center[1] - RING_R - 70), alpha=fade)

    def draw_hud(self):
        avg = sum(self.times) / len(self.times) if self.times else 0
        best = min(self.times) if self.times else 0
        lines = [
            f"Hits {self.hits}    Miss {self.misses}    Wrong {self.wrong}",
            f"Streak {self.streak}  (best {self.best_streak})",
            f"Avg {avg:.0f} ms    Best {best} ms",
        ]
        for i, s in enumerate(lines):
            img = self.f_small.render(s, True, (190, 198, 220))
            self.screen.blit(img, (24, 20 + i * 28))

        if self.joy:
            status, col = f"Controller connected  ({self.preset} preset)", (120, 230, 150)
        else:
            status, col = "No controller - using keyboard (Z X C V Q E 1 3)", (255, 190, 90)
        img = self.f_tiny.render(status, True, col)
        self.screen.blit(img, img.get_rect(bottomleft=(24, H - 18)))
        img = self.f_tiny.render("START / ESC = menu    R = reset stats", True, (120, 128, 150))
        self.screen.blit(img, img.get_rect(bottomright=(W - 24, H - 18)))

    def draw_play(self, now):
        cx = CENTER[0] + (math.sin(now * 70) * self.shake * 26 if self.shake > 0 else 0)
        center = (cx, CENTER[1])
        self.draw_effects(now, center)
        if self.target:
            self.draw_target(now, center)
        elif not self.effects:
            draw_text(self.screen, "get ready...", self.f_mid, (120, 128, 150), center)
        self.draw_hud()

    def draw(self, now):
        self.screen.blit(self.bg, (0, 0))
        if self.mode == "menu":
            self.draw_menu(now)
        else:
            self.draw_play(now)
        pygame.display.flip()

    # ----------------------------------------------------------- main loop
    def run(self):
        prev = time.perf_counter()
        running = True
        while running:
            now = time.perf_counter()
            dt = now - prev
            prev = now
            running = self.handle_events(now)
            self.update(now, dt)
            self.draw(now)
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    Game().run()