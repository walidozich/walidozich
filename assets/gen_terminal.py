#!/usr/bin/env python3
"""Generates assets/terminal.svg (run: python3 assets/gen_terminal.py): an animated terminal session for the profile README."""
from html import escape
from pathlib import Path

W = 900
PAD = 24
TOP = 58          # first text baseline
LH = 21           # line height
FS = 14           # font size
CW = 8.4          # char advance (forced via textLength, so it is exact)
FONT = "'JetBrains Mono','Fira Code','Cascadia Code',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

C = dict(bg="#0d1117", bar="#161b22", fg="#c9d1d9", dim="#6e7681", green="#39d353",
         cyan="#58a6ff", yellow="#e3b341", red="#f85149", magenta="#bc8cff", border="#30363d")

BANNER = {
    "W": ["██╗    ██╗", "██║    ██║", "██║ █╗ ██║", "██║███╗██║", "╚███╔███╔╝", " ╚══╝╚══╝ "],
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "Z": ["███████╗", "╚══███╔╝", "  ███╔╝ ", " ███╔╝  ", "███████╗", "╚══════╝"],
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "H": ["██╗  ██╗", "██║  ██║", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
}

out = []          # body elements
keyframes = []    # per-line typing keyframes
y = TOP
t = 0.6           # running clock (seconds)


def text(x, y, s, color, delay, weight=None):
    """One line segment, revealed at `delay`. textLength pins the monospace grid."""
    fw = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x:.1f}" y="{y}" fill="{color}" textLength="{len(s) * CW:.1f}" '
            f'lengthAdjust="spacingAndGlyphs"{fw} class="r" style="animation-delay:{delay:.2f}s">'
            f'{escape(s)}</text>')


def prompt(cmd, delay, speed=0.055):
    """Prompt appears at `delay`, then `cmd` is typed. Returns the time typing ends."""
    global y
    user, path = "walid@usthb", ":~$ "
    x = PAD
    out.append(text(x, y, user, C["green"], delay, "700"))
    x += len(user) * CW
    out.append(text(x, y, path, C["cyan"], delay, "700"))
    x += len(path) * CW
    out.append(text(x, y, cmd, C["fg"], delay))
    n = len(cmd)
    dur = n * speed
    k = f"k{len(keyframes)}"
    keyframes.append(f"@keyframes {k}{{to{{transform:translateX({n * CW:.1f}px)}}}}")
    # Cover slides right in n steps (typing), cursor rides its left edge, then both vanish.
    end = delay + 0.35 + dur
    out.append(
        f'<g class="r" style="animation-delay:{delay:.2f}s">'
        f'<g style="animation:{k} {dur:.2f}s steps({n}) {delay + 0.35:.2f}s forwards">'
        f'<rect x="{x:.1f}" y="{y - FS}" width="{n * CW + 12:.1f}" height="{LH}" fill="{C["bg"]}"/>'
        f'<rect x="{x:.1f}" y="{y - FS + 1}" width="{CW:.1f}" height="{FS + 3}" fill="{C["green"]}" '
        f'class="h" style="animation-delay:{end + 0.25:.2f}s"/>'
        f'</g></g>')
    y += LH
    return end + 0.3


# ---- boot ----------------------------------------------------------------
t = prompt("./boot.sh --profile", t)
boot = [
    ("[  OK  ]", C["green"], "Loaded kernel module: fullstack.ko"),
    ("[  OK  ]", C["green"], "Started kafka.service, nats.service, redis.service"),
    ("[  OK  ]", C["green"], "Mounted /dev/postgres on /var/lib/data"),
    ("[  OK  ]", C["green"], "Reached target: clean-architecture.target"),
    ("[ WARN ]", C["yellow"], "coffee.service: levels low, continuing anyway"),
]
for tag, col, msg in boot:
    out.append(text(PAD, y, tag, col, t, "700"))
    out.append(text(PAD + 9 * CW, y, msg, C["dim"] if col == C["green"] else C["fg"], t))
    y += LH
    t += 0.18
y += 6
t += 0.3

# ---- banner --------------------------------------------------------------
t = prompt("figlet -f ansi_shadow walidozich", t)
y += 4
rows = ["".join(BANNER[ch][r] for ch in "WALIDOZICH") for r in range(6)]
bw, bh = 7.2, 13
bx0 = (W - len(rows[0]) * bw) / 2
by0 = y - FS + 2
glyphs = []
for r, row in enumerate(rows):
    blocks, lines = [], []
    for c, ch in enumerate(row):
        x0, y0 = bx0 + c * bw, by0 + r * bh
        cx, cy = x0 + bw / 2, y0 + bh / 2
        x1, y1 = x0 + bw, y0 + bh
        if ch == "█":
            blocks.append(f"M{x0:.1f} {y0:.1f}h{bw:.1f}v{bh}h-{bw:.1f}z")
        elif ch == "═":
            lines.append(f"M{x0:.1f} {cy - 1.5:.1f}H{x1:.1f}M{x0:.1f} {cy + 1.5:.1f}H{x1:.1f}")
        elif ch == "║":
            lines.append(f"M{cx - 1.5:.1f} {y0:.1f}V{y1:.1f}M{cx + 1.5:.1f} {y0:.1f}V{y1:.1f}")
        elif ch == "╗":
            lines.append(f"M{x0:.1f} {cy - 1.5:.1f}H{cx + 1.5:.1f}V{y1:.1f}M{x0:.1f} {cy + 1.5:.1f}H{cx - 1.5:.1f}V{y1:.1f}")
        elif ch == "╔":
            lines.append(f"M{x1:.1f} {cy - 1.5:.1f}H{cx - 1.5:.1f}V{y1:.1f}M{x1:.1f} {cy + 1.5:.1f}H{cx + 1.5:.1f}V{y1:.1f}")
        elif ch == "╝":
            lines.append(f"M{x0:.1f} {cy + 1.5:.1f}H{cx + 1.5:.1f}V{y0:.1f}M{x0:.1f} {cy - 1.5:.1f}H{cx - 1.5:.1f}V{y0:.1f}")
        elif ch == "╚":
            lines.append(f"M{x1:.1f} {cy + 1.5:.1f}H{cx - 1.5:.1f}V{y0:.1f}M{x1:.1f} {cy - 1.5:.1f}H{cx + 1.5:.1f}V{y0:.1f}")
    glyphs.append(
        f'<g class="r" style="animation-delay:{t + r * 0.07:.2f}s">'
        f'<path d="{"".join(lines)}" stroke="url(#shade)" stroke-width="1" fill="none"/>'
        f'<path d="{"".join(blocks)}" fill="url(#grad)"/></g>')
out.append(f'<g filter="url(#glow)">{"".join(glyphs)}</g>')
y = int(by0 + 6 * bh + LH + 6)
t += 6 * 0.07 + 0.4

# ---- whoami --------------------------------------------------------------
t = prompt("whoami --verbose", t)
info = [
    ("name", "Cherchali Mohamed Walid"),
    ("role", "Fullstack Developer"),
    ("focus", "Distributed Systems & API Design"),
    ("study", "Bioinformatics @ USTHB, Algiers"),
    ("backend", ".NET Core | NestJS | FastAPI | Express | Django"),
    ("messaging", "Kafka | NATS | Redis | BullMQ"),
    ("data", "PostgreSQL | MySQL | MongoDB | Prisma | EF Core"),
    ("shell", "zsh on Linux, inside Docker more often than not"),
    ("uptime", "always shipping"),
]
for k, v in info:
    out.append(text(PAD + 2 * CW, y, k.ljust(10), C["magenta"], t, "700"))
    out.append(text(PAD + 12 * CW, y, v, C["fg"], t))
    y += LH
    t += 0.09
y += 4
for i, col in enumerate([C["dim"], C["red"], C["green"], C["yellow"], C["cyan"], C["magenta"], C["fg"]]):
    out.append(f'<rect x="{PAD + 2 * CW + i * 30}" y="{y - FS}" width="26" height="14" rx="2" fill="{col}" '
               f'class="r" style="animation-delay:{t:.2f}s"/>')
y += LH + 8
t += 0.4

# ---- idle prompt with blinking cursor -------------------------------------
out.append(text(PAD, y, "walid@usthb", C["green"], t, "700"))
out.append(text(PAD + 11 * CW, y, ":~$ ", C["cyan"], t, "700"))
out.append(f'<g class="r" style="animation-delay:{t:.2f}s"><rect x="{PAD + 15 * CW:.1f}" y="{y - FS + 1}" '
           f'width="{CW:.1f}" height="{FS + 3}" fill="{C["green"]}" class="b"/></g>')
H = y + 22

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="ttl">
<title id="ttl">walidozich: Cherchali Mohamed Walid, Fullstack Developer focused on distributed systems and API design</title>
<defs>
<linearGradient id="grad" x1="0" x2="1"><stop offset="0" stop-color="{C["green"]}"/><stop offset="1" stop-color="{C["cyan"]}"/></linearGradient>
<linearGradient id="shade" x1="0" x2="1"><stop offset="0" stop-color="#1a7f37"/><stop offset="1" stop-color="#1f6feb"/></linearGradient>
<filter id="glow" x="-5%" y="-20%" width="110%" height="140%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#ffffff" opacity=".018"/></pattern>
</defs>
<style>
text{{font-family:{FONT};font-size:{FS}px;white-space:pre}}
.r{{opacity:0;animation:show 0s forwards}}
.h{{animation:hide 0s forwards}}
.b{{animation:blink 1.05s steps(1) infinite}}
@keyframes show{{to{{opacity:1}}}}
@keyframes hide{{to{{opacity:0}}}}
@keyframes blink{{50%{{opacity:0}}}}
{chr(10).join(keyframes)}
</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{C["bg"]}" stroke="{C["border"]}"/>
<path d="M.5 10.5a10 10 0 0 1 10-10h{W - 21}a10 10 0 0 1 10 10v22H.5z" fill="{C["bar"]}"/>
<path d="M.5 32.5H{W - .5}" stroke="{C["border"]}"/>
<circle cx="22" cy="17" r="6" fill="#ff5f57"/><circle cx="42" cy="17" r="6" fill="#febc2e"/><circle cx="62" cy="17" r="6" fill="#28c840"/>
<text x="{W / 2}" y="21.5" fill="{C["dim"]}" text-anchor="middle" style="font-size:12px">walid@usthb: ~ (zsh) 120x40</text>
{chr(10).join(out)}
<rect x="1" y="33" width="{W - 2}" height="{H - 34}" fill="url(#scan)" pointer-events="none"/>
</svg>
'''
Path(__file__).with_name("terminal.svg").write_text(svg)
print(f"wrote assets/terminal.svg {W}x{H}, animation ends at ~{t:.1f}s")
