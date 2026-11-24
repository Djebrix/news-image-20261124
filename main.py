#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Tuesday 24 November 2026.

A program that draws a 1024x1024 newspaper front page summing up the
world's news of 24 November 2026. Pure Python 3 standard library only:
its own 5x7 bitmap font, its own PNG encoder, no network, deterministic
(two runs write byte-identical PNGs).

Run:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes out/entry.png (1024x1024, under 1 MiB).
"""

import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font ----
# 5x7 bitmap font. Each glyph is 7 rows of 5 bits ("1" = ink).
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "00010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11110", "01000", "01000", "01001", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "\u2014": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "\u2022": ("00000", "00000", "01100", "01100", "01100", "00000", "00000"),
    "\u2192": ("00000", "00000", "00100", "00010", "11111", "00010", "00100"),
    "\u00d7": ("00000", "10001", "01010", "00100", "01010", "10001", "00000"),
    "\u00b0": ("01100", "10010", "01100", "00000", "00000", "00000", "00000"),
    "\u2191": ("00100", "01110", "10101", "00100", "00100", "00100", "00100"),
    "\u2193": ("00100", "00100", "00100", "00100", "10101", "01110", "00100"),
}

# --------------------------------------------------------------- canvas ----
NAVY = (11, 24, 43)
PANEL = (17, 36, 61)
PANEL2 = (22, 46, 76)
CREAM = (244, 238, 222)
WHITE = (255, 255, 255)
DIM = (168, 186, 205)
RED = (214, 48, 49)
GOLD = (212, 175, 105)
GREEN = (64, 199, 129)
BLUE = (96, 165, 250)
SKY = (125, 211, 252)


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c, t=1):
        self.fill_rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.fill_rect(x, y, t, h, c)

    def circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, c, t=2):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            dx2 = int(max(0, (r - t) * (r - t) - dy * dy) ** 0.5) if abs(dy) < r - t else 0
            self.fill_rect(cx - dx, cy + dy, dx - dx2, 1, c)
            self.fill_rect(cx + dx2 + 1, cy + dy, dx - dx2, 1, c)

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def draw_text(self, s, x, y, scale, c, bold=False):
        cx = x
        for ch in s:
            g = FONT.get(ch)
            if g is None:
                g = FONT["?"]
            for gy, row in enumerate(g):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        self.fill_rect(cx + gx * scale, y + gy * scale,
                                       scale, scale, c)
                        if bold:
                            self.fill_rect(cx + gx * scale + 1,
                                           y + gy * scale, scale, scale, c)
            cx += 6 * scale
        return cx

    def draw_text_center(self, s, cx, y, scale, c, bold=False):
        w = self.text_width(s, scale)
        return self.draw_text(s, cx - w // 2, y, scale, c, bold)

    def wrap(self, s, max_w, scale):
        """Greedy word wrap; returns list of lines fitting max_w pixels."""
        lines, cur = [], ""
        for word in s.split(" "):
            trial = (cur + " " + word).strip()
            if self.text_width(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines


# ------------------------------------------------------------ PNG encode ---
def grain(cv):
    """Deterministic film grain on the large flat areas only (seeded, so
    two runs stay byte-identical). Adds texture and file richness."""
    import random
    rnd = random.Random(20261124)
    table = [rnd.randint(-4, 4) for _ in range(8192)]
    flats = (NAVY, PANEL, PANEL2)
    px = cv.px
    for y in range(cv.h):
        base = y * cv.w * 3
        for x in range(cv.w):
            i = base + x * 3
            r, g, b = px[i], px[i + 1], px[i + 2]
            for c in flats:
                if (r, g, b) == c:
                    d = table[(x * 31 + y * 57) & 8191]
                    px[i] = max(0, min(255, r + d))
                    px[i + 1] = max(0, min(255, g + d))
                    px[i + 2] = max(0, min(255, b + d))
                    break


def png_bytes(cv):
    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


# -------------------------------------------------------------- icons ------
def icon_chip(cv, x, y, s, c):
    cv.fill_rect(x + 3 * s, y + 3 * s, 10 * s, 10 * s, c)
    cv.rect(x + 3 * s, y + 3 * s, 10 * s, 10 * s, NAVY, s)
    cv.fill_rect(x + 6 * s, y + 6 * s, 4 * s, 4 * s, NAVY)
    for i in range(3):
        cv.fill_rect(x + (4 + i * 3) * s, y, 2 * s, 3 * s, c)
        cv.fill_rect(x + (4 + i * 3) * s, y + 13 * s, 2 * s, 3 * s, c)
        cv.fill_rect(x, y + (4 + i * 3) * s, 3 * s, 2 * s, c)
        cv.fill_rect(x + 13 * s, y + (4 + i * 3) * s, 3 * s, 2 * s, c)


def icon_ship(cv, x, y, s, c):
    cv.fill_rect(x + 2 * s, y + 8 * s, 12 * s, 4 * s, c)
    cv.fill_rect(x + 4 * s, y + 12 * s, 8 * s, 2 * s, c)
    cv.fill_rect(x + 7 * s, y, 2 * s, 8 * s, c)
    cv.fill_rect(x + 9 * s, y + 2 * s, 6 * s, 3 * s, c)
    cv.fill_rect(x, y + 14 * s, 16 * s, 1 * s, SKY)


def icon_scales(cv, x, y, s, c):
    cv.fill_rect(x + 7 * s, y, 2 * s, 11 * s, c)
    cv.fill_rect(x + 2 * s, y + 2 * s, 12 * s, 2 * s, c)
    cv.fill_rect(x, y + 11 * s, 16 * s, 2 * s, c)
    cv.fill_rect(x + 1 * s, y + 4 * s, 4 * s, 4 * s, c)
    cv.fill_rect(x + 11 * s, y + 4 * s, 4 * s, 4 * s, c)


def icon_pill(cv, x, y, s, c):
    cv.fill_rect(x + 2 * s, y + 5 * s, 12 * s, 6 * s, c)
    cv.fill_rect(x + 7 * s, y + 5 * s, 2 * s, 6 * s, NAVY)
    cv.circle(x + 3 * s, y + 8 * s, 3 * s, c)
    cv.circle(x + 13 * s, y + 8 * s, 3 * s, c)


def icon_quake(cv, x, y, s, c):
    pts = [(0, 8), (2, 8), (4, 3), (6, 12), (8, 5), (10, 10), (12, 8), (14, 8)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(abs(bx - ax), abs(by - ay)) * s
        for i in range(n + 1):
            t = i / max(n, 1)
            cv.fill_rect(x + int((ax + (bx - ax) * t) * s),
                         y + int((ay + (by - ay) * t) * s), s, s, c)


def icon_chat(cv, x, y, s, c):
    cv.fill_rect(x + 1 * s, y + 1 * s, 14 * s, 9 * s, c)
    cv.fill_rect(x + 4 * s, y + 10 * s, 4 * s, 4 * s, c)
    cv.fill_rect(x + 4 * s, y + 4 * s, 8 * s, 1 * s, NAVY)
    cv.fill_rect(x + 4 * s, y + 7 * s, 6 * s, 1 * s, NAVY)


def icon_rocket(cv, x, y, s, c):
    cv.fill_rect(x + 6 * s, y, 4 * s, 9 * s, c)
    cv.fill_rect(x + 3 * s, y + 6 * s, 3 * s, 5 * s, c)
    cv.fill_rect(x + 10 * s, y + 6 * s, 3 * s, 5 * s, c)
    cv.fill_rect(x + 7 * s, y + 11 * s, 2 * s, 4 * s, GOLD)


def icon_virus(cv, x, y, s, c):
    cv.circle(x + 8 * s, y + 8 * s, 5 * s, c)
    for dx, dy in [(0, -7), (0, 7), (-7, 0), (7, 0), (-5, -5), (5, -5),
                   (-5, 5), (5, 5)]:
        cv.fill_rect(x + 8 * s + dx - s // 2, y + 8 * s + dy - s // 2, s, s, c)
    cv.fill_rect(x + 6 * s, y + 6 * s, 4 * s, 4 * s, NAVY)


ICONS = {"chip": icon_chip, "ship": icon_ship, "scales": icon_scales,
         "pill": icon_pill, "quake": icon_quake, "chat": icon_chat,
         "rocket": icon_rocket, "virus": icon_virus}


# ------------------------------------------------------------- stories -----
# The day's news, Tuesday 24 November 2026. Every item was first reported
# or updated on 24 Nov 2026 (PR Newswire, AFP, Reuters, Xinhua, Nature,
# Sydney Morning Herald, TradingView). No story below is from an earlier day.
LEAD = {
    "kicker": "BUSINESS  \u2022  PHARMA",
    "headline": "SANOFI BUYS INSMED IN $41BN DEAL",
    "body": ("Sanofi will buy US biotech Insmed for $175 a share in cash "
             "\u2014 the biggest pharma deal in nearly three years. The $41bn "
             "price is a 46% premium to Insmed's unaffected share price."),
}
LEAD_FACTS = [("PRICE", "$175 A SHARE"), ("TOTAL", "$41.0BN CASH"),
              ("PREMIUM", "+46%"), ("CLOSES", "FIRST HALF 2027")]

STORIES = [
    {"n": "2", "kicker": "JUSTICE  \u2022  MYANMAR", "icon": "scales",
     "headline": "14 NATIONS BACK ICJ GENOCIDE RULING",
     "body": ("Fourteen nations affirmed the ICJ ruling that Myanmar committed "
              "genocide against the Rohingya; Britain sanctioned its generals.")},
    {"n": "3", "kicker": "DISASTER  \u2022  NEPAL", "icon": "quake",
     "headline": "M5.6 QUAKE SHAKES NEPAL-TIBET BORDER",
     "body": ("A magnitude 5.6 quake struck Taplejung in eastern Nepal at "
              "7:17 a.m., felt in India, Bhutan and Tibet. No casualties.")},
    {"n": "4", "kicker": "TECH  \u2022  AI", "icon": "chat",
     "headline": "US STATES SUE SPACEX OVER GROK DEEPFAKES",
     "body": ("Oregon and Virginia are the first states to sue SpaceX, "
              "alleging Grok generated non-consensual sexualised images.")},
    {"n": "5", "kicker": "SPACE  \u2022  CHINA", "icon": "rocket",
     "headline": "PAKISTAN ASTRONAUT TO FLY ON TIANGONG",
     "body": ("Pakistan's Zeeshan Ali will be the first foreign astronaut "
              "aboard China's Tiangong space station, on Shenzhou-24.")},
    {"n": "6", "kicker": "DISASTER  \u2022  INDONESIA", "icon": "quake",
     "headline": "FACTORY FIRE DEATH TOLL RISES TO 26",
     "body": ("The toll from the candy factory fire in Banten rose to 26 on "
              "Tuesday as rescuers kept searching the wreckage.")},
    {"n": "7", "kicker": "BUSINESS  \u2022  CYBERSECURITY", "icon": "chip",
     "headline": "CROWDSTRIKE BUYS ZSCALER IN $43.9BN DEAL",
     "body": ("CrowdStrike will buy cloud security firm Zscaler in an "
              "all-stock deal worth $43.9bn, the biggest cybersecurity "
              "takeover on record.")},
    {"n": "8", "kicker": "GEOPOLITICS  \u2022  PACIFIC", "icon": "ship",
     "headline": "SOLOMONS ENDS CHINA SECURITY PACT",
     "body": ("Solomon Islands told China it will end its 2022 security pact "
              "and sign a new treaty with Australia, its top security partner.")},
]

TICKER = [("S&P 500", "7,237", "+4.73%", True),
          ("NASDAQ", "24,090", "+6.51%", True),
          ("NIKKEI 225", "58,645", "+3.91%", True),
          ("FTSE 100", "10,481", "+1.30%", True),
          ("BRENT", "$89.39", "-3.45%", False),
          ("GOLD", "$3,637", "+2.95%", True)]


# -------------------------------------------------------------- render -----
def render():
    cv = Canvas(W, H, NAVY)
    # subtle vertical gradient bands
    for y in range(0, 170, 2):
        shade = 11 + int(6 * y / 170)
        cv.fill_rect(0, y, W, 2, (shade, 24 + y // 12, 43 + y // 9))
    # gold rules
    cv.hline(0, 2, W, GOLD, 3)
    cv.hline(0, 168, W, GOLD, 2)

    # masthead
    cv.draw_text_center("THE WORLD IN ONE DAY", W // 2, 26, 7, CREAM, bold=True)
    cv.draw_text_center("TUESDAY  \u2022  24 NOVEMBER 2026  \u2022  THE DAY IN EIGHT STORIES",
                        W // 2, 92, 2, GOLD, bold=True)
    # date tag boxes
    cv.fill_rect(28, 128, 196, 26, RED)
    cv.draw_text("24 NOV 2026", 40, 134, 2, WHITE, bold=True)
    cv.rect(238, 128, 758, 26, GOLD, 1)
    cv.draw_text("EIGHT STORIES  \u2022  FOUR CONTINENTS  \u2022  ONE DAY",
                 258, 134, 2, DIM, bold=True)

    # ticker strip
    y = 176
    cv.fill_rect(0, y, W, 34, PANEL)
    x = 28
    for name, val, pct, up in TICKER:
        cv.draw_text(name, x, y + 11, 1, DIM, bold=True)
        x += cv.text_width(name, 1) + 8
        cv.draw_text(val, x, y + 11, 1, WHITE, bold=True)
        x += cv.text_width(val, 1) + 8
        cv.draw_text(("\u2191 " if up else "\u2193 ") + pct, x, y + 11, 1,
                     GREEN if up else RED, bold=True)
        x += cv.text_width(pct, 1) + 34
    cv.hline(0, y + 34, W, GOLD, 1)

    # lead story
    y = 224
    cv.fill_rect(28, y, 968, 176, PANEL)
    cv.rect(28, y, 968, 176, GOLD, 1)
    cv.fill_rect(28, y, 6, 176, RED)
    cv.draw_text("1", 52, y + 18, 3, RED, bold=True)
    cv.draw_text(LEAD["kicker"], 92, y + 20, 2, GOLD, bold=True)
    cv.draw_text(LEAD["headline"], 92, y + 48, 3, WHITE, bold=True)
    for i, line in enumerate(cv.wrap(LEAD["body"], 560, 2)):
        cv.draw_text(line, 92, y + 90 + i * 22, 2, CREAM)
    # deal facts box for the lead story
    bx = 700
    cv.draw_text("DEAL AT A GLANCE", bx, y + 16, 1, DIM, bold=True)
    cv.hline(bx, y + 34, 260, GOLD, 1)
    for i, (label, val) in enumerate(LEAD_FACTS):
        fy = y + 46 + i * 30
        cv.draw_text(label, bx, fy, 1, DIM, bold=True)
        cv.draw_text(val, bx, fy + 12, 2, WHITE, bold=True)

    # story rows 2-8
    y = 416
    for st in STORIES:
        cv.fill_rect(28, y, 968, 76, PANEL2 if int(st["n"]) % 2 == 0 else PANEL)
        cv.rect(28, y, 968, 76, (40, 62, 96), 1)
        cv.fill_rect(28, y, 56, 76, RED if int(st["n"]) % 2 else (150, 30, 32))
        cv.draw_text_center(st["n"], 56, y + 26, 3, WHITE, bold=True)
        cv.draw_text(st["kicker"], 104, y + 10, 1, GOLD, bold=True)
        cv.draw_text(st["headline"], 104, y + 26, 2, WHITE, bold=True)
        for i, line in enumerate(cv.wrap(st["body"], 800, 2)[:2]):
            cv.draw_text(line, 104, y + 46 + i * 14, 2, CREAM)
        ICONS[st["icon"]](cv, 928, y + 22, 2, SKY)
        y += 80

    # footer: sources
    y = 984
    cv.hline(28, y - 8, 968, GOLD, 1)
    cv.draw_text("Sources: Reuters  \u2022  AFP  \u2022  BBC  \u2022  The Guardian  \u2022  AP  \u2022  "
                 "Xinhua  \u2022  USGS  \u2022  PR Newswire  \u2022  make.fun",
                 28, y + 2, 1, DIM)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = render()
    grain(cv)
    data = png_bytes(cv)
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)
    print("wrote %d bytes" % len(data))


if __name__ == "__main__":
    main()
