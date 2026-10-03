#!/usr/bin/env python3
"""Renders the profile as one animated terminal session, with live GitHub stats.

usage: GITHUB_TOKEN=... python3 assets/gen_terminal.py [OUT_DIR]   (default OUT_DIR: ./out)
Writes OUT_DIR/terminal.svg plus one OUT_DIR/link-<name>.svg button per contact link.
Run daily by .github/workflows/terminal.yml, which publishes OUT_DIR to the `output` branch.
"""
import json
import os
import re
import sys
import textwrap
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER = "walidozich"
W = 900
PAD = 24
TOP = 58          # first text baseline
LH = 21           # line height
FS = 14           # font size
CW = 8.4          # char advance (forced via textLength, so it is exact)
FONT = "'JetBrains Mono','Fira Code','Cascadia Code',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

C = dict(bg="#0d1117", bar="#161b22", fg="#c9d1d9", dim="#6e7681", green="#39d353",
         cyan="#58a6ff", yellow="#e3b341", red="#f85149", magenta="#bc8cff", border="#30363d")
HEAT = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

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

ABOUT = [
    "I build secure, scalable backend systems with a focus on clean architecture,",
    "API design, distributed workflows, and database-driven applications.",
    "",
    "My work spans .NET Core, NestJS, FastAPI, Kafka/NATS messaging, Redis caching,",
    "and Dockerized environments, plus modern frontend stacks when the product needs",
    "a complete end-to-end build.",
]

LINKS = [  # (key, label shown in the listing, url)
    ("portfolio", "portfolio-walidozich.netlify.app", "https://portfolio-walidozich.netlify.app"),
    ("linkedin", "in/mohamed-walid-cherchali", "https://www.linkedin.com/in/mohamed-walid-cherchali-204771217/"),
    ("github", "github.com/walidozich", "https://github.com/walidozich"),
    ("email", "cherchalimohamedwalid@gmail.com", "mailto:cherchalimohamedwalid@gmail.com"),
    ("instagram", "@walidozich", "https://instagram.com/walidozich"),
]

STACK = [
    ("languages/", "C  C#  C++  Java  JavaScript  Python  HTML5  CSS3"),
    ("backend/", ".NET Core  NestJS  FastAPI  Express.js  Django  Node.js  OpenAPI"),
    ("distributed/", "Apache Kafka  NATS  Redis  BullMQ"),
    ("databases/", "PostgreSQL  MySQL  MongoDB  Prisma  Entity Framework"),
    ("frontend/", "Next.js  React Native  TailwindCSS"),
    ("devops+sec/", "Docker  Docker Compose  Linux  Git  GitHub  JWT  OAuth2  RBAC"),
]
ICONS = ["c", "cs", "cpp", "java", "js", "py", "html", "css", "dotnet", "nestjs", "fastapi", "express",
         "django", "nodejs", "kafka", "redis", "postgres", "mysql", "mongodb", "prisma", "nextjs", "react",
         "tailwind", "docker", "linux", "git", "github"]

QUOTES = [
    ("Simplicity is prerequisite for reliability.", "Edsger W. Dijkstra"),
    ("Programs must be written for people to read, and only incidentally for machines to execute.", "Harold Abelson"),
    ("Premature optimization is the root of all evil.", "Donald Knuth"),
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("The best way to predict the future is to invent it.", "Alan Kay"),
    ("Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "Martin Fowler"),
    ("There are only two hard things in Computer Science: cache invalidation and naming things.", "Phil Karlton"),
    ("Debugging is twice as hard as writing the code in the first place.", "Brian Kernighan"),
    ("Walking on water and developing software from a specification are easy if both are frozen.", "Edward V. Berard"),
    ("A distributed system is one in which the failure of a computer you didn't even know existed can render your own computer unusable.", "Leslie Lamport"),
    ("The only way for errors to occur in a program is by being put there by the author. No other mechanisms are known.", "Harlan Mills"),
    ("Controlling complexity is the essence of computer programming.", "Brian Kernighan"),
    ("Deleted code is debugged code.", "Jeff Sickel"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Code never lies, comments sometimes do.", "Ron Jeffries"),
    ("Everything should be made as simple as possible, but not simpler.", "Albert Einstein"),
    ("The most damaging phrase in the language is: it's always been done this way.", "Grace Hopper"),
    ("If debugging is the process of removing bugs, then programming must be the process of putting them in.", "Edsger W. Dijkstra"),
    ("Weeks of coding can save you hours of planning.", "Unknown"),
]


# ---- data ------------------------------------------------------------------
def http(url, body=None):
    headers = {"User-Agent": f"{USER}-profile-terminal"}
    if body is not None:
        headers["Authorization"] = f"bearer {TOKEN}"
        body = json.dumps(body).encode()
    with urllib.request.urlopen(urllib.request.Request(url, body, headers), timeout=30) as r:
        return r.read().decode()


def gql(query):
    res = json.loads(http("https://api.github.com/graphql", {"query": query}))
    if res.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {res['errors']}")
    return res["data"]


def fetch_stats(now):
    u = gql(f'''{{ user(login: "{USER}") {{
        createdAt
        contributionsCollection {{ contributionCalendar {{ totalContributions
            weeks {{ contributionDays {{ date contributionCount weekday }} }} }} }}
        repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {{
            totalCount nodes {{ stargazerCount
                languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{ edges {{ size node {{ name color }} }} }} }} }}
    }} }}''')["user"]
    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))

    # One calendar per year since signup gives lifetime totals and streaks.
    parts = []
    for y in range(created.year, now.year + 1):
        start = max(created, datetime(y, 1, 1, tzinfo=timezone.utc))
        end = min(now, datetime(y, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        parts.append(f'y{y}: contributionsCollection(from: "{start.isoformat()}", to: "{end.isoformat()}") '
                     '{ contributionCalendar { weeks { contributionDays { date contributionCount } } } }')
    years = gql(f'{{ user(login: "{USER}") {{ {" ".join(parts)} }} }}')["user"]
    days = {}
    for col in years.values():
        for w in col["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    today = now.date()
    cur, day = 0, today if days.get(today.isoformat(), 0) else today - timedelta(days=1)
    while days.get(day.isoformat(), 0):
        cur, day = cur + 1, day - timedelta(days=1)
    best, best_end, run = 0, None, 0
    for ds in sorted(days):
        run = run + 1 if days[ds] else 0
        if run > best:
            best, best_end = run, date.fromisoformat(ds)

    langs = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            langs[n] = (langs.get(n, (0, e["node"]["color"]))[0] + e["size"], e["node"]["color"] or C["dim"])
    total = sum(s for s, _ in langs.values())
    top = sorted(((n, s * 100 / total, col) for n, (s, col) in langs.items()), key=lambda x: -x[1])[:6]

    cal = u["contributionsCollection"]["contributionCalendar"]
    badge = http(f"https://user-badge.committers.top/algeria_private/{USER}.svg")
    rank = re.search(r"Algeria #(\d+)", badge)
    if not rank:
        raise RuntimeError("committers.top badge no longer contains 'Algeria #<rank>'")
    return dict(
        year_total=cal["totalContributions"], weeks=cal["weeks"], lifetime=sum(days.values()),
        since=created.strftime("%b %Y"), current=cur, longest=best,
        longest_span=(best_end - timedelta(days=best - 1), best_end) if best else None,
        repos=u["repositories"]["totalCount"], stars=sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        langs=top, rank=int(rank.group(1)),
    )


def fetch_icon(name):
    svg = http(f"https://skillicons.dev/icons?i={name}&theme=dark")
    m = re.search(r'<g transform="translate\(0, 0\)">\s*(<svg[\s\S]*</svg>)\s*</g>\s*</svg>\s*$', svg)
    if not m:
        raise RuntimeError(f"unexpected skillicons response for {name!r}")
    return m.group(1)


# ---- drawing ---------------------------------------------------------------
class Term:
    def __init__(self):
        self.out, self.keyframes = [], []
        self.y, self.t = TOP, 0.6

    def text(self, x, s, color, delay, weight=None, y=None):
        """One run of text, revealed at `delay`. textLength pins the monospace grid."""
        if not s:
            return
        fw = f' font-weight="{weight}"' if weight else ""
        self.out.append(
            f'<text x="{x:.1f}" y="{self.y if y is None else y}" fill="{color}" textLength="{len(s) * CW:.1f}" '
            f'lengthAdjust="spacingAndGlyphs"{fw} class="r" style="animation-delay:{delay:.2f}s">{escape(s)}</text>')

    def line(self, runs, step=0.06, indent=0):
        """Print a line made of (text, color[, weight]) runs, then advance the clock by `step`."""
        x = PAD + indent * CW
        for run in runs:
            s, col, *w = run
            self.text(x, s, col, self.t, *w)
            x += len(s) * CW
        self.y += LH
        self.t += step

    def prompt(self, cmd, speed=0.045):
        """Prompt appears, then `cmd` is typed under a sliding cover with a riding cursor.

        The cover is also hidden once typing ends: Chrome can stop a steps() animation one step
        short of its end value, which would leave the last character covered."""
        d = self.t
        self.text(PAD, "walid@usthb", C["green"], d, "700")
        self.text(PAD + 11 * CW, ":~$ ", C["cyan"], d, "700")
        x = PAD + 15 * CW
        self.text(x, cmd, C["fg"], d)
        n, dur = len(cmd), len(cmd) * speed
        k = f"k{len(self.keyframes)}"
        self.keyframes.append(f"@keyframes {k}{{to{{transform:translateX({n * CW:.1f}px)}}}}")
        end = d + 0.3 + dur
        self.out.append(
            f'<g class="r" style="animation-delay:{d:.2f}s">'
            f'<g style="animation:{k} {dur:.2f}s steps({n}) {d + 0.3:.2f}s forwards">'
            f'<rect x="{x:.1f}" y="{self.y - FS}" width="{n * CW + 12:.1f}" height="{LH}" fill="{C["bg"]}" '
            f'class="h" style="animation-delay:{end + 0.2:.2f}s"/>'
            f'<rect x="{x:.1f}" y="{self.y - FS + 1}" width="{CW:.1f}" height="{FS + 3}" fill="{C["green"]}" '
            f'class="h" style="animation-delay:{end + 0.2:.2f}s"/></g></g>')
        self.y += LH
        self.t = end + 0.25

    def gap(self, px=8, secs=0.25):
        self.y += px
        self.t += secs


def banner(T):
    rows = ["".join(BANNER[ch][r] for ch in "WALIDOZICH") for r in range(6)]
    bw, bh = 7.2, 13
    bx0, by0 = (W - len(rows[0]) * bw) / 2, T.y - FS + 6
    glyphs = []
    for r, row in enumerate(rows):
        blocks, lines = [], []
        for c, ch in enumerate(row):
            x0, y0 = bx0 + c * bw, by0 + r * bh
            cx, cy, x1, y1 = x0 + bw / 2, y0 + bh / 2, x0 + bw, y0 + bh
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
            f'<g class="r" style="animation-delay:{T.t + r * 0.07:.2f}s">'
            f'<path d="{"".join(lines)}" stroke="url(#shade)" stroke-width="1" fill="none"/>'
            f'<path d="{"".join(blocks)}" fill="url(#grad)"/></g>')
    T.out.append(f'<g filter="url(#glow)">{"".join(glyphs)}</g>')
    T.y = int(by0 + 6 * bh + LH + 4)
    T.t += 6 * 0.07 + 0.3


def heatmap(T, weeks):
    cell, step = 11, 14
    x0 = PAD + 4 * CW
    top = T.y - FS + 2
    for wi, w in enumerate(weeks):
        cells = []
        for d in w["contributionDays"]:
            n = d["contributionCount"]
            lvl = 0 if n == 0 else 1 if n < 3 else 2 if n < 6 else 3 if n < 10 else 4
            cells.append(f'<rect x="{x0 + wi * step}" y="{top + d["weekday"] * step}" width="{cell}" height="{cell}" '
                         f'rx="2" fill="{HEAT[lvl]}"/>')
        if w["contributionDays"][0]["date"][8:] <= "07":
            T.text(x0 + wi * step, date.fromisoformat(w["contributionDays"][0]["date"]).strftime("%b"),
                   C["dim"], T.t, y=top - 6)
        T.out.append(f'<g class="r" style="animation-delay:{T.t + wi * 0.015:.2f}s">{"".join(cells)}</g>')
    for i, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        T.text(PAD, lab, C["dim"], T.t, y=top + i * step + 10)
    T.y = top + 7 * step + LH
    T.t += len(weeks) * 0.015 + 0.2


def cowsay(T, quote, who):
    body = textwrap.wrap(quote, 44) + [f"  - {who}"]
    wd = max(len(s) for s in body)
    bubble = [" " + "_" * (wd + 2)]
    for i, s in enumerate(body):
        l, r = ("<", ">") if len(body) == 1 else ("/", "\\") if i == 0 else ("\\", "/") if i == len(body) - 1 else ("|", "|")
        bubble.append(f"{l} {s.ljust(wd)} {r}")
    bubble.append(" " + "-" * (wd + 2))
    cow = ["        \\   ^__^", "         \\  (oo)\\_______", "            (__)\\       )\\/\\",
           "                ||----w |", "                ||     ||"]
    for s in bubble:
        T.line([(s, C["fg"])], 0.05, indent=2)
    for s in cow:
        T.line([(s, C["green"])], 0.05, indent=2)


def render(stats, icons, now):
    T = Term()

    T.prompt("./boot.sh --profile")
    for tag, col, msg in [
        ("[  OK  ]", C["green"], "Loaded kernel module: fullstack.ko"),
        ("[  OK  ]", C["green"], "Started kafka.service, nats.service, redis.service"),
        ("[  OK  ]", C["green"], "Mounted /dev/postgres on /var/lib/data"),
        ("[  OK  ]", C["green"], "Reached target: clean-architecture.target"),
        ("[ WARN ]", C["yellow"], "coffee.service: levels low, continuing anyway"),
    ]:
        T.line([(tag, col, "700"), (" " + msg, C["dim"] if col == C["green"] else C["fg"])], 0.16)
    T.gap()

    T.prompt("figlet -f ansi_shadow walidozich")
    banner(T)

    T.prompt("whoami --verbose")
    for k, v in [
        ("name", "Cherchali Mohamed Walid"), ("role", "Fullstack Developer"),
        ("focus", "Distributed Systems & API Design"), ("study", "Bioinformatics @ USTHB, Algiers"),
        ("shell", "zsh on Linux, inside Docker more often than not"), ("uptime", "always shipping"),
    ]:
        T.line([(k.ljust(10), C["magenta"], "700"), (v, C["fg"])], 0.08, indent=2)
    for i, col in enumerate([C["dim"], C["red"], C["green"], C["yellow"], C["cyan"], C["magenta"], C["fg"]]):
        T.out.append(f'<rect x="{PAD + 2 * CW + i * 30}" y="{T.y - FS + 4}" width="26" height="12" rx="2" '
                     f'fill="{col}" class="r" style="animation-delay:{T.t:.2f}s"/>')
    T.gap(LH + 4)

    T.prompt("cat about.txt")
    for s in ABOUT:
        T.line([(s, C["fg"])], 0.07)
    T.gap()

    T.prompt("committers --rank --country algeria")
    T.line([("rank      ", C["magenta"], "700"), (f"#{stats['rank']}", C["green"], "700"),
            ("  in Algeria on committers.top (all contributions)", C["dim"])], 0.1, indent=2)
    T.gap()

    T.prompt("./connect.sh --list")
    for i, (key, label, _) in enumerate(LINKS, 1):
        T.line([(f"[{i}]", C["green"], "700"), (f" {key.ljust(11)} ", C["fg"]), ("->  ", C["dim"]),
                (label, C["cyan"])], 0.09, indent=2)
    T.line([("5 channels open. the buttons under this window are clickable.", C["dim"])], 0.1, indent=2)
    T.gap()

    T.prompt("tree ~/stack --noreport")
    T.line([("/home/walid/stack", C["cyan"], "700")], 0.07)
    for i, (d, items) in enumerate(STACK):
        T.line([("└── " if i == len(STACK) - 1 else "├── ", C["dim"]), (d.ljust(16), C["cyan"], "700"),
                (items, C["fg"])], 0.07)
    T.gap()

    T.prompt("ls ~/stack --icons")
    size, step, per = 40, 48, 14
    for i, svg in enumerate(icons):
        x = PAD + (i % per) * step
        y = T.y - FS + (i // per) * step
        T.out.append(f'<g class="r" style="animation-delay:{T.t + i * 0.04:.2f}s">'
                     f'<g transform="translate({x:.1f} {y}) scale({size / 256})">{svg}</g></g>')
    T.y += 2 * step
    T.t += len(icons) * 0.04 + 0.2
    T.gap(4)

    T.prompt(f"gh stats --user {USER}")
    d = T.t
    T.text(PAD, "fetching contributions from api.github.com ", C["dim"], d)
    for i in range(3):
        T.text(PAD + (43 + i) * CW, ".", C["dim"], d + 0.2 * (i + 1))
    T.text(PAD + 47 * CW, "done", C["green"], d + 0.8, "700")
    T.y += LH
    T.t = d + 1.0
    span = stats["longest_span"]
    rows = [
        ("contributions", f"{stats['year_total']:,} in the last year", f"  ({stats['lifetime']:,} since {stats['since']})"),
        ("current streak", f"{stats['current']} day{'s' if stats['current'] != 1 else ''}", ""),
        ("longest streak", f"{stats['longest']} days",
         f"  ({span[0]:%b %d} - {span[1]:%b %d, %Y})" if span else ""),
        ("public repos", f"{stats['repos']}", f"  ({stats['stars']} stars)"),
    ]
    for k, v, extra in rows:
        T.line([(k.ljust(16), C["magenta"], "700"), (v, C["green"], "700"), (extra, C["dim"])], 0.1, indent=2)
    T.gap(LH)
    heatmap(T, stats["weeks"])
    T.line([("top languages", C["magenta"], "700"), (" (public repos, by bytes)", C["dim"])], 0.1, indent=2)
    maxp = stats["langs"][0][1]
    for name, pct, col in stats["langs"]:
        bx = PAD + 16 * CW
        T.text(PAD + 2 * CW, name[:13].ljust(13), C["fg"], T.t)
        T.out.append(f'<rect x="{bx:.1f}" y="{T.y - FS + 3}" width="{max(3, 420 * pct / maxp):.1f}" height="12" rx="2" '
                     f'fill="{col}" class="r g" style="animation-delay:{T.t:.2f}s"/>')
        T.text(bx + 432, f"{pct:5.1f}%", C["dim"], T.t)
        T.y += LH
        T.t += 0.12
    T.line([(f"# synced {now:%Y-%m-%d %H:%M} UTC by .github/workflows/terminal.yml", C["dim"])], 0.1)
    T.gap()

    T.prompt("fortune -s dev | cowsay")
    quote, who = QUOTES[now.date().toordinal() % len(QUOTES)]
    cowsay(T, quote, who)
    T.gap()

    T.prompt("exit")
    T.line([("logout", C["fg"])], 0.15)
    T.line([("Connection to github.com closed.", C["fg"])], 0.4)
    T.gap(LH)
    T.line([("[Process completed]", C["dim"])], 0)

    H = T.y + 4
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="ttl">
<title id="ttl">walidozich: Cherchali Mohamed Walid, Fullstack Developer focused on distributed systems and API design. {stats['year_total']} contributions in the last year.</title>
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
.g{{transform-box:fill-box;transform-origin:left;animation:show 0s forwards,grow .6s ease-out forwards}}
@keyframes show{{to{{opacity:1}}}}
@keyframes hide{{to{{opacity:0}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
{chr(10).join(T.keyframes)}
</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{C["bg"]}" stroke="{C["border"]}"/>
<path d="M.5 10.5a10 10 0 0 1 10-10h{W - 21}a10 10 0 0 1 10 10v22H.5z" fill="{C["bar"]}"/>
<path d="M.5 32.5H{W - .5}" stroke="{C["border"]}"/>
<circle cx="22" cy="17" r="6" fill="#ff5f57"/><circle cx="42" cy="17" r="6" fill="#febc2e"/><circle cx="62" cy="17" r="6" fill="#28c840"/>
<text x="{W / 2}" y="21.5" fill="{C["dim"]}" text-anchor="middle" style="font-size:12px">walid@usthb: ~ (zsh) 120x40</text>
{chr(10).join(T.out)}
<rect x="1" y="33" width="{W - 2}" height="{H - 34}" fill="url(#scan)" pointer-events="none"/>
</svg>
'''


def button(i, key):
    label = f"[{i}] {key}"
    w = int(len(label) * CW + 28)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="32" viewBox="0 0 {w} 32" role="img" aria-label="{key}">
<rect x=".5" y=".5" width="{w - 1}" height="31" rx="6" fill="{C["bar"]}" stroke="{C["border"]}"/>
<text x="14" y="21" font-family="{FONT}" font-size="{FS}" textLength="{3 * CW:.1f}" lengthAdjust="spacingAndGlyphs" fill="{C["green"]}" font-weight="700">[{i}]</text>
<text x="{14 + 4 * CW:.1f}" y="21" font-family="{FONT}" font-size="{FS}" textLength="{len(key) * CW:.1f}" lengthAdjust="spacingAndGlyphs" fill="{C["fg"]}">{key}</text>
</svg>
'''


if __name__ == "__main__":
    TOKEN = os.environ.get("GITHUB_TOKEN")
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is not set (locally: GITHUB_TOKEN=$(gh auth token) python3 assets/gen_terminal.py)")
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    stats = fetch_stats(now)
    icons = [fetch_icon(n) for n in ICONS]
    (out / "terminal.svg").write_text(render(stats, icons, now))
    for i, (key, _, _) in enumerate(LINKS, 1):
        (out / f"link-{key}.svg").write_text(button(i, key))
    print(f"wrote {out}/terminal.svg and {len(LINKS)} link buttons "
          f"(rank #{stats['rank']}, {stats['year_total']} contributions this year, streak {stats['current']})")
