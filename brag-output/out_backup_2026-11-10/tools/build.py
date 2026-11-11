"""Write the Hyperframes composition (index.html + compositions/*.html) from tools/timing.json.

Animated demo: the learner (tools/person.py) uses each feature in rebuilt SpeechMate screens. The
screens use the app's real labels; the interview plan, the deck insights and the Q&A question are
real outputs of the app's AI (see brag-plan.md). Scores and feedback on the results screens are
illustrative and carry an on-screen tag saying so.
Every element is anchored to a caption chunk of the voiceover, so it lands on the word that says it.
Run: python3 tools/build.py   (from brag-output/), after tools/build_voice.py
"""
import json, math, subprocess
from functools import cache
from pathlib import Path

from person import person, HOODIE, HOODIE_SHADE, HAIR, SKIN_SHADE

HERE = Path(__file__).parent
COMP = HERE.parent / "composition"
T = json.loads((HERE / "timing.json").read_text())

# Brand: frontend/app/globals.css + frontend/DESIGN.md
BG, INK, ACCENT_INK, MUTED = "#FFFAF0", "#0A0A0A", "#1A3A3A", "#5C6766"
PINK, PINK_INK, TEAL, TEAL_INK = "#FF4D8B", "#C21E57", "#1A3A3A", "#1F6F6B"
LAVENDER, LAV_INK, PEACH, OCHRE, MINT = "#B8A4ED", "#4B2FA8", "#FFB084", "#E8B94A", "#A4D4C5"
NIGHT, NIGHT2 = "#0A1A1A", "#13201F"

LEAD = {"s01-mirror": 1.6, "s03-intro": 0.8}
TAIL = {"s10-close": 3.2, "s07-present": 1.2, "s05-interview": 1.2}
REVEAL = 1.35   # s03: wordmark lands on vol-1's strong cue at 17.02 s

# Real AI output, captured from the running app (see brag-plan.md)
PLAN = json.loads((HERE / "real_outputs.json").read_text())

BASE_CSS = """
#root{position:absolute;inset:0;overflow:hidden;background:%(BG)s;font-family:Inter,sans-serif;color:%(INK)s}
.h{opacity:0}
.abs{position:absolute}
.disp{font-weight:600;letter-spacing:-0.035em;line-height:1.04}
.card{position:absolute;border-radius:28px;box-shadow:inset 0 3px 0 rgba(255,255,255,.45),inset 0 -7px 0 rgba(0,0,0,.12),0 22px 44px rgba(10,26,26,.16)}
.chip{position:absolute;display:inline-flex;align-items:center;gap:12px;padding:12px 24px;border-radius:999px;font-size:30px;font-weight:600;white-space:nowrap;box-shadow:inset 0 2px 0 rgba(255,255,255,.4),inset 0 -4px 0 rgba(0,0,0,.1),0 10px 22px rgba(10,26,26,.12)}
.bot{position:absolute}
.bot img{position:absolute;inset:0;width:100%%;height:100%%}
.row{position:absolute;display:flex;align-items:center;gap:16px;font-size:29px;font-weight:500}
.row i{flex:none;width:15px;height:15px;border-radius:50%%}
.win{position:absolute;border-radius:22px;background:%(BG)s;overflow:hidden;box-shadow:0 30px 70px rgba(10,26,26,.24),0 0 0 1px rgba(10,26,26,.08)}
.win .bar{position:absolute;left:0;right:0;top:0;height:46px;display:flex;align-items:center;gap:9px;padding:0 18px;background:#F3EEE3;border-bottom:1px solid rgba(10,26,26,.08);z-index:5}
.win .bar b{width:13px;height:13px;border-radius:50%%;background:#D9D2C3}
.win .bar span{margin-left:16px;padding:4px 16px;border-radius:999px;background:#fff;font-size:20px;color:%(MUTED)s}
.wc{position:absolute;left:0;right:0;top:46px;bottom:0;overflow:hidden}
.nav{position:absolute;left:0;right:0;top:0;height:62px;display:flex;align-items:center;gap:30px;padding:0 34px;border-bottom:1px solid rgba(10,26,26,.07);font-size:19px;color:%(MUTED)s}
.nav .wm{font-weight:600;letter-spacing:-0.03em;font-size:23px;color:%(INK)s;margin-right:26px;display:flex;align-items:center;gap:10px}
.nav .wm i{width:22px;height:22px;border-radius:50%%;background:%(PEACH)s;box-shadow:inset 0 -3px 0 rgba(0,0,0,.12)}
.nav .on{color:%(INK)s;font-weight:600}
.lbl{position:absolute;font-size:19px;font-weight:600;color:%(INK)s}
.inp{position:absolute;height:50px;border-radius:12px;background:#fff;border:1.5px solid rgba(10,26,26,.14);font-size:20px;padding:12px 16px;color:%(INK)s;white-space:nowrap;overflow:hidden}
.ta{position:absolute;border-radius:12px;background:#fff;border:1.5px solid rgba(10,26,26,.14);font-size:19px;line-height:1.45;padding:12px 16px;color:%(INK)s}
.typ{display:inline-block;white-space:nowrap;clip-path:inset(0 100%% 0 0)}
.opt{position:absolute;padding:9px 18px;border-radius:999px;font-size:18px;font-weight:600;background:#fff;color:%(INK)s;border:1.5px solid rgba(10,26,26,.14);white-space:nowrap}
.btn{position:absolute;padding:14px 26px;border-radius:12px;font-size:20px;font-weight:600;background:%(INK)s;color:#fff;white-space:nowrap}
.pane{position:absolute;border-radius:18px;background:#fff;box-shadow:0 8px 24px rgba(10,26,26,.08),0 0 0 1px rgba(10,26,26,.06)}
.dark{background:%(NIGHT)s;color:#FFFAF0}
.dpane{position:absolute;border-radius:18px;background:%(NIGHT2)s;color:#FFFAF0}
.turn{position:absolute;display:flex;align-items:center;gap:12px;padding:12px 22px;border-radius:14px;font-size:20px;font-weight:600}
.illus{position:absolute;right:20px;top:78px;padding:6px 14px;border-radius:999px;background:%(OCHRE)s;color:%(INK)s;font-size:16px;font-weight:700;letter-spacing:.06em;z-index:6}
.cur{position:absolute;left:0;top:0;width:40px;height:48px;z-index:40;pointer-events:none}
.bubble{position:absolute;padding:16px 22px;border-radius:20px;font-size:22px;line-height:1.35}
""" % dict(BG=BG, INK=INK, MUTED=MUTED, PEACH=PEACH, OCHRE=OCHRE, NIGHT=NIGHT, NIGHT2=NIGHT2)

CURSOR = ('<svg viewBox="0 0 40 48"><path d="M4 3 L4 38 L13 30 L19 44 L26 41 L20 27 L32 27 Z" fill="#fff" '
          'stroke="#0A0A0A" stroke-width="3" stroke-linejoin="round"/></svg>')
NAV_ITEMS = ["Home", "Conversation", "Interview", "Presentations", "Progress"]


def nav(active):
    items = "".join(f'<span class="{"on" if n == active else ""}">{n}</span>' for n in NAV_ITEMS)
    return f'<div class="nav"><span class="wm"><i></i>SpeechMate</span>{items}</div>'


def person_back(pid, hoodie=HOODIE, shade=HOODIE_SHADE):
    """the learner seen from behind (viewBox 0 0 400 600)"""
    return f"""<g id="{pid}" class="pbody">
  <path d="M70 600 C70 446 120 386 200 386 C280 386 330 446 330 600 Z" fill="{hoodie}"/>
  <path d="M120 420 C140 470 260 470 280 420 C260 396 140 396 120 420 Z" fill="{shade}"/>
  <rect x="180" y="326" width="40" height="70" rx="14" fill="{SKIN_SHADE}"/>
  <g class="phead"><circle cx="120" cy="262" r="15" fill="{SKIN_SHADE}"/><circle cx="280" cy="262" r="15" fill="{SKIN_SHADE}"/>
  <ellipse cx="200" cy="250" rx="82" ry="94" fill="{HAIR}"/></g>
</g>"""


class Scene:
    def __init__(self, sid, bg=BG):
        self.sid, self.bg = sid, bg
        t = T[sid]
        self.L, self.Tl = LEAD.get(sid, 0.6), TAIL.get(sid, 0.9)
        self.cs = [self.L + c["start"] for c in t["chunks"]]
        self.ce = [self.L + c["end"] for c in t["chunks"]]
        self.D = round(self.L + t["dur"] + self.Tl, 3)
        self.html, self.js, self.sfx, self.css = [], [], [], ""

    def id(self, name):
        return f"{self.sid.split('-')[0]}-{name}"

    def at(self, i, frac=0.0):
        return round(self.cs[i] + frac * (self.ce[i] - self.cs[i]), 3)

    # ---------- elements ----------
    def add(self, h):
        self.html.append(h)

    def el(self, name, cls, style, inner="", hidden=True, attrs=""):
        h = " h" if hidden else ""
        self.html.append(f'<div id="{self.id(name)}" class="{cls}{h}" style="{style}" {attrs}>{inner}</div>')
        return name

    def e(self, name, cls, style, inner="", hidden=True):
        """an element as a string (to nest inside a window)"""
        h = " h" if hidden else ""
        return f'<div id="{self.id(name)}" class="{cls}{h}" style="{style}">{inner}</div>'

    def bot(self, name, who, x, y, size, states=("default",), hidden=True):
        imgs = "".join(f'<img id="{self.id(name)}-{st}" src="assets/bots/{who}-{st}.png" alt="" style="opacity:{1 if i == 0 else 0}">'
                       for i, st in enumerate(states))
        return self.el(name, "bot", f"left:{x}px;top:{y}px;width:{size}px;height:{size}px", imgs, hidden)

    def chip(self, name, text, x, y, bg, fg=INK, dot=None, size=30):
        d = f'<i style="width:14px;height:14px;border-radius:50%;background:{dot}"></i>' if dot else ""
        return self.el(name, "chip", f"left:{x}px;top:{y}px;background:{bg};color:{fg};font-size:{size}px", d + text)

    def rows(self, name, items, x, y, dot, gap=60, size=29, color=INK, width=470):
        for k, txt in enumerate(items):
            self.el(f"{name}{k}", "row", f"left:{x}px;top:{y + k * gap}px;width:{width}px;font-size:{size}px;color:{color}",
                    f'<i style="background:{dot}"></i><span>{txt}</span>')
        return [f"{name}{k}" for k in range(len(items))]

    def text(self, name, html, x, y, w, size, weight=600, color=INK, align="left", extra="", hidden=True):
        return self.el(name, "abs disp" if weight >= 600 else "abs",
                       f"left:{x}px;top:{y}px;width:{w}px;font-size:{size}px;font-weight:{weight};color:{color};text-align:{align};{extra}",
                       html, hidden)

    def win(self, name, x, y, w, h, url, inner, dark=False, hidden=True):
        self.W = (x, y + 46)   # content origin, for cursor targets
        bar = f'<div class="bar"><b></b><b></b><b></b><span>{url}</span></div>'
        return self.el(name, "win", f"left:{x}px;top:{y}px;width:{w}px;height:{h}px",
                       f'{bar}<div class="wc{" dark" if dark else ""}">{inner}</div>', hidden)

    # ---------- motion ----------
    def tw(self, js):
        self.js.append(js)

    def show(self, name, t, how="rise", sfx=None):
        s = f"#{self.id(name)}"
        f = {
            "rise": '{opacity:0,y:34},{opacity:1,y:0,duration:0.7,ease:"expo.out"}',
            "blur": '{opacity:0,filter:"blur(10px)"},{opacity:1,filter:"blur(0px)",duration:0.22,ease:"power4.out"}',
            "pop": '{opacity:0,scale:0.55},{opacity:1,scale:1,duration:0.75,ease:"back.out(1.5)"}',
            "left": '{opacity:0,x:-60,filter:"blur(8px)"},{opacity:1,x:0,filter:"blur(0px)",duration:0.6,ease:"expo.out"}',
            "right": '{opacity:0,x:90,filter:"blur(10px)"},{opacity:1,x:0,filter:"blur(0px)",duration:0.7,ease:"expo.out"}',
            "fade": '{opacity:0},{opacity:1,duration:0.45,ease:"power2.out"}',
            "drop": '{opacity:0,y:-24},{opacity:1,y:0,duration:0.45,ease:"expo.out"}',
        }[how]
        self.tw(f'tl.fromTo("{s}",{f},{t});')
        if sfx:
            self.sfx.append((sfx, t))
        return t

    def hide(self, name, t, d=0.25):
        self.tw(f'tl.to("#{self.id(name)}",{{opacity:0,filter:"blur(8px)",duration:{d},ease:"power2.in"}},{round(t - d, 3)});')

    def cut(self, name, t):
        self.tw(f'tl.set("#{self.id(name)}",{{opacity:0}},{t});')

    def hop(self, name, t):
        s = f"#{self.id(name)}"
        self.tw(f'tl.to("{s}",{{y:-46,duration:0.22,ease:"power2.out"}},{t});tl.to("{s}",{{y:0,duration:0.5,ease:"bounce.out"}},{round(t + 0.22, 3)});')

    def swap(self, name, a, b, t, hop=True):
        self.tw(f'tl.to("#{self.id(name)}-{a}",{{opacity:0,duration:0.25}},{t});tl.to("#{self.id(name)}-{b}",{{opacity:1,duration:0.25}},{t});')
        if hop:
            self.hop(name, t)

    def typ(self, name, t, d=None, keys=True):
        """reveal a .typ span left to right like typing"""
        n = 24 if d is None else max(6, int(d * 22))
        d = d or 1.0
        self.tw(f'tl.fromTo("#{self.id(name)}",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:{d},ease:"steps({n})"}},{t});')
        if keys:
            self.sfx.append(("keypress-003", t)); self.sfx.append(("keypress-007", round(t + d * 0.5, 3)))

    def pick(self, name, t, bg=ACCENT_INK, fg="#fff"):
        self.tw(f'tl.to("#{self.id(name)}",{{backgroundColor:"{bg}",color:"{fg}",borderColor:"{bg}",duration:0.15}},{t});')

    # cursor (scene coordinates); targets inside the last window use self.W
    def cursor(self, t_in, x, y):
        if not getattr(self, "has_cur", False):
            self.el("cur", "cur", "", CURSOR); self.has_cur = True
        self.tw(f'tl.fromTo("#{self.id("cur")}",{{opacity:0,x:{x + 120},y:{y + 80}}},{{opacity:1,x:{x},y:{y},duration:0.6,ease:"power3.out"}},{t_in});')

    def move(self, t, x, y, d=0.55, win=True):
        if win:
            x, y = x + self.W[0], y + self.W[1]
        self.tw(f'tl.to("#{self.id("cur")}",{{x:{x},y:{y},duration:{d},ease:"power2.inOut"}},{t});')

    def click(self, t):
        c = f"#{self.id('cur')}"
        self.tw(f'tl.to("{c}",{{scale:0.82,duration:0.08,ease:"power2.out"}},{t});tl.to("{c}",{{scale:1,duration:0.14,ease:"power2.out"}},{round(t + 0.08, 3)});')
        self.sfx.append(("mouseclick1", t))

    def press(self, t, x, y, target=None, d=0.55):
        """move to a point in the window, then click (and select an option)"""
        self.move(t, x, y, d)
        self.click(round(t + d, 3))
        if target:
            self.pick(target, round(t + d + 0.04, 3))
        return round(t + d, 3)

    def zoom(self, name, t, k, ox, oy, d=0.8, right=None):
        """right: the window's width, to keep its right edge in place instead of its left"""
        if right:
            self.tw(f'tl.set("#{self.id(name)}",{{transformOrigin:"{ox}px {oy}px"}},{t});'
                    f'tl.to("#{self.id(name)}",{{scale:{k},x:{-round((right - ox) * (k - 1))},duration:{d},ease:"power2.inOut"}},{t});')
            return
        self._zoom_left(name, t, k, ox, oy, d)

    def _zoom_left(self, name, t, k, ox, oy, d=0.8):
        """punch in on a window: (ox, oy) is the window-local point that stays put"""
        self.tw(f'tl.set("#{self.id(name)}",{{transformOrigin:"{ox}px {oy}px"}},{t});'
                f'tl.to("#{self.id(name)}",{{scale:{k},x:{round(ox * (k - 1))},duration:{d},ease:"power2.inOut"}},{t});')

    def unzoom(self, name, t, d=0.7):
        self.tw(f'tl.to("#{self.id(name)}",{{scale:1,x:0,duration:{d},ease:"power2.inOut"}},{t});')

    # the learner's actions
    def talk(self, pid, t, d):
        n = max(1, int(d / 0.2))
        self.tw(f'tl.to("#{pid} .pmouth",{{scaleY:2.4,transformOrigin:"50% 50%",duration:0.1,yoyo:true,repeat:{2 * n - 1},ease:"sine.inOut"}},{t});')

    def blink(self, pid, t):
        self.tw(f'tl.to("#{pid} .peyes",{{scaleY:0.1,transformOrigin:"50% 50%",duration:0.07,yoyo:true,repeat:1}},{t});')

    def gesture(self, pid, t, n=2, deg=-24):
        self.tw(f'tl.to("#{pid} .parm",{{rotation:{deg},svgOrigin:"292 452",duration:0.35,yoyo:true,repeat:{2 * n - 1},ease:"sine.inOut"}},{t});')

    def nod(self, pid, t, deg=4, n=1):
        self.tw(f'tl.to("#{pid} .phead",{{rotation:{deg},svgOrigin:"200 350",duration:0.4,yoyo:true,repeat:{2 * n - 1},ease:"sine.inOut"}},{t});')

    def flood(self, color, who, num, title, t_in, t_out, sub):
        self.el("flood", "abs", f"inset:0;background:{color};clip-path:circle(0% at 50% 50%)", hidden=False)
        fg = "#fff" if color in (TEAL, PINK) else INK
        self.bot("fbot", who, 250, 250, 520)
        self.text("fnum", num, 860, 300, 900, 64, 600, fg, extra="opacity:.7")
        self.text("ftitle", title, 860, 370, 980, 112, 600, fg)
        self.text("fsub", sub, 864, 640, 900, 36, 500, fg, extra="opacity:.85")
        f = f"#{self.id('flood')}"
        self.tw(f'tl.fromTo("{f}",{{clipPath:"circle(0% at 50% 50%)"}},{{clipPath:"circle(75% at 50% 50%)",duration:0.6,ease:"power2.inOut"}},{t_in});')
        self.sfx.append(("card-slide-1", t_in))
        self.show("fbot", t_in + 0.25, "pop")
        self.show("fnum", t_in + 0.35, "blur"); self.show("ftitle", t_in + 0.42, "blur"); self.show("fsub", t_in + 0.6, "blur")
        self.hop("fbot", t_in + 1.3)
        ids = ",".join(f'"#{self.id(n)}"' for n in ("fbot", "fnum", "ftitle", "fsub"))
        self.tw(f'tl.to(["{f}",{ids}],{{y:-1150,duration:0.55,ease:"power3.in"}},{round(t_out - 0.55, 3)});tl.set(["{f}",{ids}],{{opacity:0}},{t_out});')
        self.sfx.append(("card-slide-3", round(t_out - 0.5, 3)))

    def left_col(self, who, states, label, color, fg):
        self.bot("b", who, 130, 96, 250, states)
        self.chip("lab", label, 120, 360, color, fg, size=28)

    def write(self):
        cid = self.sid
        doc = f"""<template>
  <style>{BASE_CSS}
#root{{background:{self.bg}}}
{self.css}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="1920" data-height="1080">
{chr(10).join('    ' + h for h in self.html)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join('    ' + j for j in self.js)}
    tl.set({{}}, {{}}, {self.D});
    window.__timelines["{cid}"] = tl;
  </script>
</template>
"""
        (COMP / "compositions" / f"{cid}.html").write_text(doc)


def svg_person(pid, w, h, mouth="closed", hoodie=HOODIE, shade=HOODIE_SHADE, extra_style=""):
    return (f'<svg viewBox="0 0 400 600" style="position:absolute;width:{w}px;height:{h}px;overflow:visible;{extra_style}">'
            f'{person(pid, hoodie, shade, mouth)}</svg>')


def camera_view(s, pid, w, h, mouth="closed"):
    """the learner's camera feed inside a session window: a warm room, the learner at the desk"""
    ph = h * 0.92
    return (f'<div style="position:absolute;inset:0;background:linear-gradient(#E6DAC8,#D9CBB5)">'
            f'<div style="position:absolute;left:{w * 0.08}px;top:{h * 0.14}px;width:{w * 0.22}px;height:{h * 0.34}px;border-radius:10px;background:#C9D9DA;box-shadow:inset 0 0 0 8px #EFE6D8"></div>'
            f'<div style="position:absolute;right:{w * 0.07}px;top:{h * 0.2}px;width:{w * 0.2}px;height:10px;border-radius:5px;background:#B89B74"></div>'
            f'<div style="position:absolute;right:{w * 0.1}px;top:{h * 0.2 - 46}px;width:40px;height:46px;border-radius:20px 20px 6px 6px;background:#7FA88E"></div>'
            f'<div style="position:absolute;right:{w * 0.16}px;top:{h * 0.2 - 30}px;width:26px;height:30px;border-radius:4px;background:{PEACH}"></div>'
            f'{svg_person(pid, ph * 2 / 3, ph, mouth, extra_style=f"left:{(w - ph * 2 / 3) / 2}px;bottom:-{h * 0.08}px")}'
            f'</div>')


# ================================ real life ================================
def mirror_room(s, pid_back, pid_ref, mouth="closed"):
    """a bedroom wall, a tall mirror, the learner from behind, the reflection facing us"""
    s.add(f'<div class="abs" style="inset:0;background:linear-gradient(#F4EADB 0 72%,#E3D2B8 72%)"></div>')
    s.add('<div class="abs" style="left:120px;top:120px;width:300px;height:230px;border-radius:14px;background:#D6E6E8;box-shadow:inset 0 0 0 14px #FBF5EA"></div>')
    s.add('<div class="abs" style="left:255px;top:120px;width:14px;height:230px;background:#FBF5EA"></div>')
    s.add('<div class="abs" style="left:1560px;top:520px;width:200px;height:250px;border-radius:16px;background:#C9A77A"></div>'
          '<div class="abs" style="left:1600px;top:420px;width:110px;height:110px;border-radius:50%;background:#7FA88E"></div>')
    # the mirror: frame, glass, reflection, sheen
    s.add(f'<div class="abs" style="left:800px;top:50px;width:600px;height:860px;border-radius:300px 300px 26px 26px;background:#B98F55;'
          f'box-shadow:inset 0 4px 0 rgba(255,255,255,.35),0 26px 50px rgba(60,40,10,.25)"></div>')
    s.add(f'<div id="{s.id("glass")}" class="abs" style="left:826px;top:76px;width:548px;height:808px;border-radius:274px 274px 16px 16px;overflow:hidden;'
          f'background:radial-gradient(120% 90% at 50% 30%,#E7F1F2,#BFD5D9)">'
          f'<div class="abs" style="left:0;right:0;bottom:0;height:200px;background:#D1C3AB;opacity:.55"></div>'
          f'<svg viewBox="0 0 400 600" style="position:absolute;left:64px;top:170px;width:420px;height:630px;overflow:visible;opacity:.95">{person(pid_ref, mouth=mouth)}</svg>'
          f'<div class="abs" style="left:-80px;top:0;width:90px;height:1000px;background:rgba(255,255,255,.35);transform:rotate(18deg)"></div>'
          f'<div class="abs" style="left:60px;top:0;width:30px;height:1000px;background:rgba(255,255,255,.28);transform:rotate(18deg)"></div></div>')
    s.add(f'<svg viewBox="0 0 400 600" class="abs" style="left:430px;top:420px;width:470px;height:705px;overflow:visible">{person_back(pid_back)}</svg>')


def s01():
    s = Scene("s01-mirror")
    mirror_room(s, "p01b", "p01r")
    # rehearsing: the reflection talks and gestures
    for k, (w, bg, x) in enumerate([("Presentation", LAVENDER, 140), ("Job interview", MINT, 140)]):
        s.chip(f"c{k}", w, x, 430 + k * 90, bg, size=32)
        s.show(f"c{k}", s.at(k, 0.15), "pop", "drop_001")
    s.talk("p01r", s.at(0, 0.1), s.ce[2] - s.cs[0])
    s.gesture("p01r", s.at(1, 0.2), 3)
    s.tw('tl.to("#p01b .phead",{rotation:-3,svgOrigin:"200 380",duration:0.5,yoyo:true,repeat:5,ease:"sine.inOut"},' + str(s.at(0, 0.2)) + ');')
    for t in (s.at(0, 0.6), s.at(2, 0.3), s.at(4, 0.5), s.at(6, 0.3)):
        s.blink("p01r", t)
    for k in range(2):
        s.hide(f"c{k}", s.at(3))
    # ...nothing
    s.el("dim", "abs", "inset:0;background:#0A1A1A")
    s.tw(f'tl.fromTo("#{s.id("dim")}",{{opacity:0}},{{opacity:0.18,duration:0.8,ease:"power2.inOut"}},{s.at(3, 0.3)});')
    s.el("tb", "bubble", f"left:150px;top:200px;background:#fff;color:{INK};font-size:40px;font-weight:600;box-shadow:0 14px 30px rgba(10,26,26,.15);border-radius:30px;padding:22px 34px",
         "…so how did I do?")
    s.show("tb", s.at(3, 0.75), "pop", "drop_002")
    s.hide("tb", s.at(4, 0.45))
    qs = ["Did my answer make sense?", "Did I sound nervous?", "What should I work on?"]
    for k, q in enumerate(qs):
        s.el(f"q{k}", "bubble", f"left:110px;top:{170 + k * 120}px;background:#fff;color:{INK};font-size:31px;font-weight:600;box-shadow:0 12px 26px rgba(10,26,26,.14)",
             f'{q} <span style="color:{PINK_INK};margin-left:10px">?</span>')
        s.show(f"q{k}", [s.at(4, 0.55), s.at(5, 0.1), s.at(5, 0.6)][k], "pop", "drop_001" if k != 1 else "drop_002")
        s.tw(f'tl.to("#{s.id(f"q{k}")}",{{opacity:0.35,duration:0.6}},{s.at(6, 0.1)});')
    # slump
    s.tw(f'tl.to("#p01r .phead",{{rotation:6,y:14,svgOrigin:"200 350",duration:0.9,ease:"power2.inOut"}},{s.at(6, 0.3)});')
    s.tw(f'tl.to("#p01b .phead",{{y:16,duration:0.9,ease:"power2.inOut"}},{s.at(6, 0.3)});')
    s.tw(f'tl.to("#p01r .pbrow",{{y:6,duration:0.6}},{s.at(6, 0.3)});')
    return s


def s02():
    s = Scene("s02-problem")
    s.text("t", 'And I\'m <span style="color:#C21E57">not the only one</span>.', 160, 90, 1600, 84, hidden=True)
    s.show("t", s.at(0), "blur")
    # three people, each practising alone
    vign = [("At the mirror", HOODIE, HOODIE_SHADE, "mirror"), ("At the laptop", "#C2416C", "#9E3358", "laptop"), ("With note cards", "#6A4FC9", "#553DA6", "cards")]
    for k, (cap, hc, hs, kind) in enumerate(vign):
        x = 160 + k * 545
        prop = {
            "mirror": '<div class="abs" style="right:34px;top:70px;width:150px;height:260px;border-radius:75px 75px 10px 10px;background:#B98F55"></div>'
                      '<div class="abs" style="right:44px;top:80px;width:130px;height:240px;border-radius:65px 65px 6px 6px;background:#D4E6E8"></div>',
            "laptop": '<div class="abs" style="left:150px;bottom:0;width:220px;height:120px;border-radius:10px 10px 0 0;background:#3B4A49"></div>'
                      '<div class="abs" style="left:160px;bottom:0;width:200px;height:104px;border-radius:6px;background:#9FC3C6"></div>',
            "cards": '',
        }[kind]
        px = {"mirror": 40, "laptop": 0, "cards": 120}[kind]
        extra = ('<div class="abs" style="left:300px;top:250px;width:90px;height:120px;border-radius:8px;background:#fff;transform:rotate(12deg);'
                 'box-shadow:0 6px 14px rgba(0,0,0,.15)"></div>') if kind == "cards" else ""
        s.el(f"v{k}", "card", f"left:{x}px;top:200px;width:505px;height:420px;background:#F4EADB;overflow:hidden",
             f'{prop}{svg_person(f"p02{k}", 260, 390, hoodie=hc, shade=hs, extra_style=f"left:{px}px;bottom:-40px")}{extra}'
             f'<div class="abs" style="left:24px;top:22px;padding:8px 18px;border-radius:999px;background:#fff;font-size:24px;font-weight:600">{cap}</div>')
        s.show(f"v{k}", [s.at(1, 0.1), s.at(2, 0.1), s.at(2, 0.6)][k], "rise", "card-place-1" if k % 2 == 0 else "card-place-2")
        s.talk(f"p02{k}", s.at(1, 0.3) + k * 0.4, 3.0)
    for k, (w, bg) in enumerate([("Fresh graduates", MINT), ("Anxiety", PEACH), ("Stage fright", LAVENDER), ("Practising alone", OCHRE)]):
        s.chip(f"c{k}", w, 160 + [0, 300, 530, 820][k], 660, bg, size=30)
        s.show(f"c{k}", s.at([1, 2, 2, 3][k], [0.1, 0.25, 0.65, 0.2][k]), "pop", "drop_001" if k % 2 == 0 else "drop_002")
    for k in range(3):
        s.blink(f"p02{k}", s.at(3, 0.5) + k * 0.2)
        s.tw(f'tl.to("#p02{k} .phead",{{rotation:5,y:10,svgOrigin:"200 350",duration:0.7}},{s.at(3, 0.4)});')
    gone = ["t"] + [f"v{k}" for k in range(3)] + [f"c{k}" for k in range(4)]
    for n in gone:
        s.hide(n, s.at(4))
    for k, (num, label, src, bg) in enumerate([
            ("64", "of employers say poor English is why graduates fail interviews", "JobStreet Malaysia, Graduate Employability Survey 2025", OCHRE),
            ("53", "cite weak communication &amp; presentation skills", "JobStreet Malaysia × Malaysian Employers Federation, 2025", PEACH)]):
        x = 160 + k * 820
        s.el(f"k{k}", "card", f"left:{x}px;top:170px;width:780px;height:470px;background:{bg}",
             f'<div class="disp" style="position:absolute;left:52px;top:40px;font-size:190px"><span id="{s.id(f"n{k}")}">0</span>%</div>'
             f'<div style="position:absolute;left:56px;top:270px;width:660px;font-size:36px;font-weight:600;line-height:1.25">{label}</div>'
             f'<div style="position:absolute;left:56px;bottom:30px;font-size:24px;opacity:.75">{src}</div>')
        t = s.at(4 + k, 0.1)
        s.show(f"k{k}", t, "rise", "card-place-1" if k == 0 else "card-place-2")
        s.tw(f'tl.fromTo({{v:0}},{{v:0}},{{v:{num},duration:1.1,ease:"power2.out",onUpdate:function(){{document.getElementById("{s.id(f"n{k}")}").textContent=Math.round(this.targets()[0].v)}}}},{t + 0.1});')
        s.hide(f"k{k}", s.at(6))
    for k, w in enumerate(["Practise safely", "See where to improve", "Keep getting better"]):
        s.text(f"w{k}", w, 160, 200 + k * 170, 1600, 104, 600, [ACCENT_INK, PINK_INK, TEAL_INK][k])
        s.show(f"w{k}", s.at(6, 0.6) if k == 0 else s.at(7, 0.05 + 0.5 * (k - 1)), "left")
        s.hide(f"w{k}", s.D)
    s.html[-1] = s.html[-1].replace('class="abs disp h"', 'class="abs disp h" data-hold')
    return s


# ================================ SpeechMate ================================
def s03():
    s = Scene("s03-intro")
    s.text("logo", "SpeechMate", 200, 250, 1240, 210, 600, INK)
    s.show("logo", REVEAL, "blur", "impactBell_heavy_000")   # beat-locked: vol-1 strong cue 17.02 s
    s.text("sub", "An AI speaking coach built for Malaysian speakers", 210, 500, 1200, 44, 500, ACCENT_INK)
    s.show("sub", s.at(0, 0.45), "blur")
    s.bot("mate", "mate", 1460, 110, 330, ("sleeping", "default"))
    s.show("mate", s.at(1), "pop", "card-place-1")
    s.swap("mate", "sleeping", "default", s.at(1, 0.4))
    s.chip("matel", "Mate · your companion", 1470, 440, MINT, size=28)
    s.show("matel", s.at(1, 0.55), "pop")
    s.el("say", "bubble", f"left:1500px;top:40px;background:#fff;font-size:26px;font-weight:600;box-shadow:0 10px 22px rgba(10,26,26,.14)", "Nice one!")
    s.show("say", s.at(1, 0.8), "pop", "drop_002"); s.hide("say", s.at(2, 0.4))
    for k, (w, bg) in enumerate([("English", MINT), ("Bahasa Malaysia", PEACH), ("Manglish", LAVENDER)]):
        s.chip(f"l{k}", w, [210, 450, 800][k], 620, bg, size=32)
        s.show(f"l{k}", s.at(2, [0.2, 0.42, 0.85][k]), "pop", "drop_001")
    s.chip("acc", "A Malaysian accent is not a mistake", 210, 720, "#fff", ACCENT_INK, dot=TEAL_INK, size=30)
    s.show("acc", s.at(3, 0.3), "rise")
    t_out = s.at(4)
    for n in ["logo", "sub", "matel", "l0", "l1", "l2", "acc", "mate"]:
        s.hide(n, t_out)
    s.text("h", "Three ways to practise, each with its own AI partner", 0, 90, 1920, 56, 600, INK, "center")
    s.show("h", s.at(4, 0.1), "blur")
    for k, (name, who, bg, fg, t) in enumerate([
            ("Mock interview", "interviewer", TEAL, "#fff", s.at(5)),
            ("Presentation practice", "presenter", LAVENDER, INK, s.at(5, 0.6)),
            ("Daily conversation", "chat", PINK, "#fff", s.at(6, 0.25))]):
        x = 210 + k * 520
        s.el(f"f{k}", "card", f"left:{x}px;top:210px;width:460px;height:470px;background:{bg}",
             f'<img id="{s.id(f"fb{k}")}" src="assets/bots/{who}-default.png" alt="" style="position:absolute;left:70px;top:-10px;width:320px;height:320px">'
             f'<div class="disp" style="position:absolute;left:36px;bottom:40px;font-size:40px;color:{fg}">{name}</div>')
        s.show(f"f{k}", t, "rise", "card-place-1" if k != 1 else "card-place-2")
        s.tw(f'tl.to("#{s.id(f"fb{k}")}",{{y:-30,duration:0.2,ease:"power2.out"}},{t + 0.5});tl.to("#{s.id(f"fb{k}")}",{{y:0,duration:0.45,ease:"bounce.out"}},{t + 0.7});')
    s.chip("ni", "Never interrupts you while you speak", 650, 735, "#fff", ACCENT_INK, dot=PINK, size=30)
    s.show("ni", s.at(7, 0.1), "rise")
    for n in ["h", "f0", "f1", "f2", "ni"]:
        s.hide(n, s.D)
    return s


WX, WY, WW, WH = 600, 70, 1224, 760


def s04():
    s = Scene("s04-profile")
    s.left_col("mate", ("default",), "Your profile", MINT, INK)
    s.show("b", s.at(0), "pop", "card-place-1"); s.show("lab", s.at(0, 0.3), "pop")

    def opts(prefix, items, x, y, sel=None):
        out, cx = "", x
        for k, o in enumerate(items):
            out += s.e(f"{prefix}{k}", "opt", f"left:{cx}px;top:{y}px", o, hidden=False)
            cx += int(len(o) * 10.2 + 46)
        return out

    brief = ("They are an undergraduate student, in Computer Science. Self-rated speaking level: Intermediate. "
             "Use natural, everyday-professional language and ask for reasons and examples. Their goal: Do well in job interviews. "
             "They are working on: Filler Words, Confidence. Feedback style they asked for: Balance strengths and improvements, specific and kind.")
    inner = (nav("") + '<div class="disp" style="position:absolute;left:48px;top:88px;font-size:40px">Profile</div>'
             + '<div class="lbl" style="left:48px;top:160px">Level of study</div>'
             + opts("st", ["Secondary", "Pre-university", "Undergraduate", "Postgraduate"], 48, 192)
             + '<div class="lbl" style="left:48px;top:262px">Field of study or work</div>'
             + f'<div class="inp" style="left:48px;top:292px;width:560px"><span id="{s.id("fld")}" class="typ">Computer Science</span></div>'
             + '<div class="lbl" style="left:48px;top:372px">Skill level</div>'
             + opts("sk", ["Beginner", "Intermediate", "Advanced"], 48, 404)
             + '<div class="lbl" style="left:48px;top:472px">What you want to work on</div>'
             + opts("ch", ["Filler Words", "Pronunciation", "Eye Contact", "Confidence"], 48, 504)
             + '<div class="lbl" style="left:48px;top:572px">How should feedback sound?</div>'
             + opts("fb", ["Encouraging", "Balanced", "Direct"], 48, 604)
             + s.e("card", "pane", f"left:700px;top:150px;width:480px;height:470px;background:#F1ECFD",
                   f'<div style="position:absolute;left:28px;top:24px;font-size:22px;font-weight:700">How your coach uses this</div>'
                   f'<div id="{s.id("brief")}" style="position:absolute;left:28px;top:70px;width:424px;font-size:19px;line-height:1.5;color:#2A2A2A;clip-path:inset(0 0 100% 0)">'
                   f'<b>About the learner:</b> {brief}</div>', hidden=False)
             + '<img src="assets/bots/mate-default.png" alt="" style="position:absolute;right:14px;bottom:8px;width:84px;height:84px">')
    s.win("w", WX, WY, WW, WH, "speechmate · /profile", inner)
    s.show("w", s.at(0, 0.15), "right")
    s.cursor(s.at(0, 0.6), WX + 700, WY + 600)
    t = s.press(s.at(1, 0.0), 360, 210, "st2", 0.45)
    s.move(t + 0.15, 300, 316, 0.35); s.click(t + 0.5); s.typ("fld", t + 0.6, 0.8)
    t = s.press(s.at(1, 0.55), 175, 422, "sk1", 0.45)
    s.press(s.at(1, 0.85), 80, 522, "ch0", 0.35)
    s.press(s.at(2, 0.05), 420, 522, "ch3", 0.4)
    s.press(s.at(2, 0.5), 205, 622, "fb1", 0.4)
    s.tw(f'tl.to("#{s.id("brief")}",{{clipPath:"inset(0 0 0% 0)",duration:2.2,ease:"steps(9)"}},{s.at(2, 0.6)});')
    s.zoom("w", s.at(3, 0.0), 1.1, 940, 380)
    s.hop("b", s.at(3, 0.2))
    s.rows("r", ["Your field", "Your speaking level", "What you find hard", "How blunt the feedback is"], 130, 450, TEAL_INK)
    for k, tt in enumerate([s.at(1, 0.05), s.at(1, 0.5), s.at(1, 0.8), s.at(2, 0.45)]):
        s.show(f"r{k}", tt, "left")
    for n in ["b", "lab", "w", "cur"] + [f"r{k}" for k in range(4)]:
        s.hide(n, s.D)
    return s


def session_win(s, name, url, mode_color, bot_who, bot_state_a, bot_state_b, partner, question, pid, x=WX, y=WY, w=WW, h=WH, follow=None):
    """the live session page: big camera view, the partner bot, the turn banner, the current question"""
    cw, ch = 740, 470
    turns = {
        "ai": (f"{partner} is talking", "var(--x)", "#1E2E2D", "#FFFAF0"),
        "you": ("Your turn: speak now", "", mode_color, "#fff"),
        "listen": ("Listening… keep going", "", mode_color, "#fff"),
        "think": (f"{partner} is thinking…", "", "#2A3A39", "#FFFAF0"),
    }
    banners = "".join(s.e(f"{name}-t{k}", "turn", f"left:40px;top:{40 + ch + 34}px;background:{bg};color:{fg}",
                          f'<span style="width:12px;height:12px;border-radius:50%;background:{fg};opacity:.8"></span>{txt}')
                      for k, (txt, _, bg, fg) in turns.items())
    inner = (f'<div style="position:absolute;left:40px;top:34px;width:{cw}px;height:{ch}px;border-radius:18px;overflow:hidden">{camera_view(s, pid, cw, ch)}</div>'
             f'<div style="position:absolute;left:56px;top:50px;padding:6px 14px;border-radius:999px;background:rgba(10,26,26,.7);font-size:16px;color:#fff">● REC</div>'
             + banners
             + f'<div class="dpane" style="left:{cw + 70}px;top:34px;width:{w - cw - 110}px;height:300px">'
             f'<img id="{s.id(name + "-bot-" + bot_state_a)}" src="assets/bots/{bot_who}-{bot_state_a}.png" alt="" style="position:absolute;left:50%;top:10px;width:240px;height:240px;margin-left:-120px">'
             f'<img id="{s.id(name + "-bot-" + bot_state_b)}" src="assets/bots/{bot_who}-{bot_state_b}.png" alt="" style="position:absolute;left:50%;top:10px;width:240px;height:240px;margin-left:-120px;opacity:0">'
             f'<div style="position:absolute;left:0;right:0;bottom:16px;text-align:center;font-size:20px;font-weight:600">{partner}</div></div>'
             + f'<div class="dpane" style="left:{cw + 70}px;top:354px;width:{w - cw - 110}px;height:{h - 46 - 390}px">'
             f'<div style="position:absolute;left:22px;top:18px;font-size:14px;font-weight:700;letter-spacing:.12em;opacity:.6">CURRENT QUESTION</div>'
             f'<div id="{s.id(name + "-q")}" style="position:absolute;left:22px;top:46px;right:22px;font-size:19px;line-height:1.45">{question}</div>'
             f'<div id="{s.id(name + "-q2")}" class="h" style="position:absolute;left:22px;top:46px;right:22px;font-size:21px;line-height:1.45;font-weight:600;color:{MINT}">{follow or ""}</div></div>')
    return s.win(name, x, y, w, h, url, inner, dark=True)


def banner(s, name, which, t):
    for k in ("ai", "you", "listen", "think"):
        s.tw(f'tl.set("#{s.id(f"{name}-t{k}")}",{{opacity:{1 if k == which else 0}}},{t});')


def s05():
    s = Scene("s05-interview")
    s.flood(TEAL, "interviewer", "01", "Mock interview", 0.05, s.at(1), "Questions for YOUR interview")
    s.text("gh", "General questions everyone gets", 0, 150, 1920, 40, 600, "#7A8584", "center")
    s.show("gh", s.at(1, 0.1), "blur")
    for k, q in enumerate(["“Tell me about yourself.”", "“What are your strengths?”", "“Where do you see yourself in five years?”"]):
        s.text(f"g{k}", q, 0, 260 + k * 120, 1920, 58, 600, "#9AA3A2", "center")
        s.show(f"g{k}", s.at(1, 0.3) + k * 0.25, "blur")
    s.tw(f'tl.set(["#{s.id("g0")}","#{s.id("g1")}","#{s.id("g2")}"],{{textDecoration:"line-through",opacity:0.55}},{s.at(2, 0.7)});')
    for n in ["gh", "g0", "g1", "g2"]:
        s.hide(n, s.at(3))

    s.left_col("interviewer", ("sleeping", "working"), "Mock interview", TEAL, "#fff")
    s.show("b", s.at(3), "pop", "card-place-1"); s.show("lab", s.at(3, 0.2), "pop")
    # --- the form
    def opts(prefix, items, x, y):
        out, cx = "", x
        for k, o in enumerate(items):
            out += s.e(f"{prefix}{k}", "opt", f"left:{cx}px;top:{y}px", o, hidden=False)
            cx += int(len(o) * 10.2 + 46)
        return out
    form = (nav("Interview")
            + f'<div style="position:absolute;left:48px;top:84px;font-size:15px;font-weight:700;letter-spacing:.14em;color:{TEAL_INK}">MOCK INTERVIEW</div>'
            + '<div class="disp" style="position:absolute;left:48px;top:108px;font-size:36px">Tell us about the interview</div>'
            + '<div style="position:absolute;left:48px;top:170px;font-size:21px;font-weight:700">1 · The role</div>'
            + '<div class="lbl" style="left:48px;top:208px">Position you applied for</div>'
            + f'<div class="inp" style="left:48px;top:236px;width:520px"><span id="{s.id("pos")}" class="typ">Graduate Data Analyst</span></div>'
            + '<div class="lbl" style="left:610px;top:208px">Company</div>'
            + f'<div class="inp" style="left:610px;top:236px;width:540px"><span id="{s.id("co")}" class="typ">Nusantara Retail Group</span></div>'
            + '<div class="lbl" style="left:48px;top:306px">Level</div>' + opts("lv", ["Internship", "Graduate", "Junior", "Mid"], 48, 336)
            + '<div class="lbl" style="left:610px;top:306px">Interview type</div>' + opts("it", ["Behavioural", "Technical", "Mixed"], 610, 336)
            + '<div style="position:absolute;left:48px;top:404px;font-size:21px;font-weight:700">2 · About you</div>'
            + '<div class="lbl" style="left:48px;top:442px">Your background</div>'
            + f'<div class="ta" style="left:48px;top:470px;width:520px;height:118px"><span id="{s.id("bg1")}" class="typ">Final-year Computer Science student.</span><br>'
              f'<span id="{s.id("bg2")}" class="typ">Internship: weekly sales dashboards,</span><br><span id="{s.id("bg3")}" class="typ">data cleaning in Python.</span></div>'
            + '<div class="lbl" style="left:610px;top:442px">Job description</div>'
            + f'<div class="ta" style="left:610px;top:470px;width:540px;height:118px"><span id="{s.id("jd1")}" class="typ">Analyse sales and customer data, build</span><br>'
              f'<span id="{s.id("jd2")}" class="typ">dashboards, present insights to</span><br><span id="{s.id("jd3")}" class="typ">non-technical managers. SQL, Python.</span></div>'
            + '<div style="position:absolute;left:48px;top:606px;width:520px;height:58px;border-radius:12px;border:2px dashed rgba(10,26,26,.25)"></div>'
            + s.e("res", "abs", f"left:62px;top:616px;padding:8px 16px;border-radius:10px;background:{MINT};font-size:19px;font-weight:600", "📄 resume.pdf · read")
            + s.e("pv", "btn", "left:930px;top:612px", "Preview questions", hidden=False)
            + s.e("pv2", "btn", f"left:930px;top:612px;background:{TEAL_INK}", "Preparing questions…"))
    s.win("w", WX, WY, WW, WH, "speechmate · /interview", form)
    s.show("w", s.at(3, 0.1), "right")
    s.cursor(s.at(3, 0.5), WX + 400, WY + 300)
    t = s.at(4, 0.0)
    s.move(t, 200, 260, 0.35); s.click(t + 0.35); s.typ("pos", t + 0.45, 0.9)
    s.move(t + 1.0, 760, 260, 0.4); s.click(t + 1.4); s.typ("co", t + 1.5, 0.9)
    s.press(s.at(4, 0.75), 190, 352, "lv1", 0.4)
    s.press(s.at(4, 0.92), 870, 352, "it2", 0.3)
    t = s.at(5, 0.0)
    for k, d in enumerate((0.55, 0.55, 0.45)):
        s.typ(f"bg{k + 1}", t + k * 0.5, d, keys=k == 0)
        s.typ(f"jd{k + 1}", t + 0.25 + k * 0.5, d, keys=False)
    s.show("res", s.at(5, 0.75), "pop", "drop_001")
    t = s.press(s.at(6, 0.0), 1040, 636, None, 0.5)
    s.show("pv2", t + 0.1, "fade"); s.cut("pv", t + 0.1)
    s.rows("r", ["Position", "Company", "Level", "Job description", "Your resume"], 130, 450, TEAL_INK, gap=54)
    for k, tt in enumerate([s.at(4, 0.05), s.at(4, 0.35), s.at(4, 0.7), s.at(5, 0.1), s.at(5, 0.7)]):
        s.show(f"r{k}", tt, "left", "drop_001" if k == 4 else None)
    for k in range(5):
        s.hide(f"r{k}", s.at(7))
    s.hide("w", s.at(7, 0.05)); s.hide("cur", s.at(7, 0.05))

    # --- the real plan
    qs = PLAN["interview"]
    rows = ""
    for k, (qi, tag) in enumerate([(1, None), (2, None), (3, None), (5, None)]):
        q = qs[qi]
        rows += (f'<div id="{s.id(f"pq{k}")}" class="pane h" style="left:48px;top:{150 + k * 140}px;width:1120px;height:128px">'
                 f'<div style="position:absolute;left:22px;top:14px;font-size:15px;font-weight:700;color:{TEAL_INK};letter-spacing:.1em">QUESTION {qi + 1}</div>'
                 f'<div style="position:absolute;left:22px;top:38px;right:320px;font-size:19px;line-height:1.38;font-weight:500">{q["question"]}</div></div>')
    plan = (nav("Interview")
            + '<div style="position:absolute;left:48px;top:86px;font-size:21px;font-weight:700">3 · Your questions</div>'
            + f'<div style="position:absolute;left:48px;top:114px;font-size:18px;color:{MUTED}">Curated for Graduate Data Analyst at Nusantara Retail Group · 7 questions</div>'
            + rows)
    s.win("p", WX, WY, WW, WH, "speechmate · /interview · your questions", plan)
    s.show("p", s.at(7, 0.0), "right")
    for k in range(4):
        s.show(f"pq{k}", s.at(7, 0.1) + k * 0.18, "drop", "card-place-1" if k == 0 else None)
    # callouts: where each question came from
    for k, (txt, row, chunk, col, fg) in enumerate([("the job description", 1, 8, PEACH, INK), ("your resume", 0, 9, MINT, INK), ("your project", 2, 9.5, LAVENDER, INK)]):
        y = WY + 46 + 150 + row * 140 + 40
        s.chip(f"co{k}", f"from {txt}", WX + WW - 320, y, col, fg, size=22)
        ci = int(chunk); fr = 0.6 if chunk % 1 else 0.15
        s.show(f"co{k}", s.at(ci, fr), "pop", "drop_002")
    s.rows("q", ["For <b>this</b> job, <b>this</b> candidate", "Skills the role needs", "Experience on your resume", "Questions you should expect", "Preview before you start"],
           130, 450, PINK_INK, gap=54, size=27)
    for k, (i, f) in enumerate([(7, 0.0), (8, 0.0), (9, 0.0), (10, 0.0), (11, 0.0)]):
        s.show(f"q{k}", s.at(i, f), "left")
    for k in range(3):
        s.hide(f"co{k}", s.at(11, 0.1))
    s.zoom("p", s.at(11, 0.1), 1.18, 600, 300)
    for n in ["p"] + [f"q{k}" for k in range(5)]:
        s.hide(n, s.at(13))

    # --- the live interview
    q2 = qs[1]["question"]
    session_win(s, "live", "speechmate · /session", TEAL, "interviewer", "default", "working", "Alex", q2, "p05",
                follow="Follow-up: could you give one specific example from your internship?")
    s.show("live", s.at(13, 0.05), "right")
    s.swap("b", "sleeping", "working", s.at(13, 0.6))
    banner(s, "live", "ai", s.at(13, 0.05))
    s.swap("live-bot", "default", "working", s.at(13, 0.6), hop=False)
    banner(s, "live", "you", s.at(14, 0.45))
    s.swap("live-bot", "working", "default", s.at(14, 0.45), hop=False)
    banner(s, "live", "listen", s.at(14, 0.7))
    s.talk("p05", s.at(14, 0.7), 1.6)
    s.gesture("p05", s.at(14, 0.75), 1)
    s.chip("w2", "Waits until you've finished", 120, 470, "#fff", ACCENT_INK, dot=TEAL_INK, size=27)
    s.show("w2", s.at(14, 0.5), "rise")
    banner(s, "live", "think", s.at(15, 0.15))
    banner(s, "live", "ai", s.at(15, 0.55))
    s.swap("live-bot", "default", "working", s.at(15, 0.55), hop=False)
    s.hide("live-q", s.at(15, 0.55), 0.2)
    s.show("live-q2", s.at(15, 0.6), "blur", "drop_002")
    s.chip("fuc", "Short answer → one follow-up", 120, 550, "#fff", ACCENT_INK, dot=PINK, size=27)
    s.show("fuc", s.at(15, 0.3), "rise")
    banner(s, "live", "you", s.at(16, 0.6))
    s.blink("p05", s.at(13, 0.9)); s.blink("p05", s.at(16, 0.3))
    s.nod("p05", s.at(16, 0.1))
    for n in ["live", "w2", "fuc", "b", "lab"]:
        s.hide(n, s.D)
    return s


def s06():
    s = Scene("s06-results")
    s.left_col("mate", ("working", "default"), "Your results", MINT, INK)
    s.show("b", s.at(0), "pop"); s.show("lab", s.at(0, 0.3), "pop")
    s.swap("b", "working", "default", s.at(0, 0.8))
    pills = [("Voice &amp; delivery", 74, OCHRE), ("Language &amp; clarity", 70, MINT), ("Body language", 66, PEACH), ("Confidence &amp; presence", 68, LAVENDER)]
    cards = "".join(s.e(f"pc{k}", "pane", f"left:{48 + k * 284}px;top:300px;width:262px;height:150px",
                        f'<div style="position:absolute;left:20px;top:18px;font-size:18px;font-weight:700;width:220px">{n}</div>'
                        f'<div class="disp" style="position:absolute;left:20px;top:58px;font-size:44px">{v}</div>'
                        f'<div style="position:absolute;left:20px;right:20px;bottom:22px;height:12px;border-radius:6px;background:#EEE8DC">'
                        f'<div id="{s.id(f"pb{k}")}" style="width:{v}%;height:100%;border-radius:6px;background:{c};transform-origin:0 50%"></div></div>')
                    for k, (n, v, c) in enumerate(pills))
    q3 = PLAN["interview"][2]["question"]
    fb = s.e("ans", "pane", "left:48px;top:480px;width:1120px;height:330px",
             f'<div style="position:absolute;left:24px;top:18px;font-size:15px;font-weight:700;letter-spacing:.1em;color:{TEAL_INK}">WHAT YOU SAID · QUESTION 3</div>'
             f'<div style="position:absolute;left:24px;top:44px;right:24px;font-size:18px;color:{MUTED}">{q3[:118]}…</div>'
             + "".join(s.e(f"sc{k}", "abs", f"left:{24 + k * 300}px;top:96px;padding:8px 16px;border-radius:10px;background:#F3EEE3;font-size:19px;font-weight:600", f"{lab} <b>{v}/5</b>")
                       for k, (lab, v) in enumerate([("Answered the question", 4), ("Easy to follow (STAR)", 3), ("Real details", 3)]))
             + s.e("str", "abs", f"left:24px;top:150px;right:24px;padding:16px 20px;border-radius:14px;background:#E3F3EE;font-size:19px;line-height:1.5",
                   '<b>Stronger answer, from your own facts:</b> “In my internship I built weekly sales dashboards. When a store manager asked why sales dipped, '
                   'I showed one chart, explained the cause in plain words, and suggested what to check next.”'), hidden=False)
    inner = (nav("Progress")
             + '<div class="illus">ILLUSTRATIVE VALUES</div>'
             + f'<div style="position:absolute;left:48px;top:84px;font-size:15px;font-weight:700;letter-spacing:.14em;color:{TEAL_INK}">MOCK INTERVIEW · RESULTS</div>'
             + f'<div id="{s.id("scroll")}" style="position:absolute;left:0;right:0;top:0;height:1400px">'
             + '<svg viewBox="0 0 120 120" style="position:absolute;left:48px;top:120px;width:150px;height:150px"><circle cx="60" cy="60" r="50" fill="none" stroke="#EEE8DC" stroke-width="12"/>'
               f'<circle id="{s.id("ring")}" cx="60" cy="60" r="50" fill="none" stroke="{TEAL_INK}" stroke-width="12" stroke-linecap="butt" pathLength="100" stroke-dasharray="100 100" stroke-dashoffset="100" transform="rotate(-90 60 60)"/></svg>'
             + f'<div class="disp" style="position:absolute;left:48px;top:168px;width:150px;text-align:center;font-size:48px"><span id="{s.id("ov")}">0</span></div>'
             + '<div class="disp" style="position:absolute;left:230px;top:140px;font-size:28px">Overall</div>'
             + f'<div style="position:absolute;left:230px;top:184px;width:900px;font-size:20px;line-height:1.45;color:#2A2A2A">You answered every question with relevant points. Next time, add one number to each answer and finish with the result.</div>'
             + f'{cards}{fb}'
             + s.e("dr", "pane", "left:48px;top:840px;width:1120px;height:230px",
                   f'<div style="position:absolute;left:24px;top:18px;font-size:15px;font-weight:700;letter-spacing:.1em;color:{PINK_INK}">YOUR #1 FOCUS FOR NEXT TIME · 3 DRILLS</div>'
                   + "".join(f'<div style="position:absolute;left:{24 + k * 360}px;top:56px;width:340px;height:100px;border-radius:14px;background:{c};padding:16px;font-size:20px;font-weight:600">{d}</div>'
                             for k, (d, c) in enumerate([("Finish with the result (STAR)", "#F1ECFD"), ("Add one real number", "#FFF0E6"), ("Fewer filler words", "#E3F3EE")]))
                   + f'<div id="{s.id("go")}" class="btn" style="left:24px;top:168px">Practise this now</div>', hidden=False)
             + '</div>')
    s.win("w", WX, WY, WW, WH, "speechmate · /results", inner)
    s.show("w", s.at(0, 0.15), "right")
    s.tw(f'tl.to("#{s.id("ring")}",{{strokeDashoffset:28,duration:1.2,ease:"power2.out"}},{s.at(0, 0.5)});')
    s.tw(f'tl.fromTo({{v:0}},{{v:0}},{{v:72,duration:1.2,ease:"power2.out",onUpdate:function(){{document.getElementById("{s.id("ov")}").textContent=Math.round(this.targets()[0].v)}}}},{s.at(0, 0.5)});')
    for k in range(4):
        s.show(f"pc{k}", s.at(1, k * 0.22), "drop", "drop_001" if k == 0 else None)
        s.tw(f'tl.fromTo("#{s.id(f"pb{k}")}",{{scaleX:0}},{{scaleX:1,duration:0.8,ease:"power2.out"}},{s.at(1, k * 0.22) + 0.2});')
    s.rows("p", [p[0] for p in pills], 130, 450, OCHRE, gap=54, size=27)
    for k in range(4):
        s.show(f"p{k}", s.at(1, k * 0.22), "left")
    for k in range(4):
        s.hide(f"p{k}", s.at(3))
    s.tw(f'tl.to("#{s.id("scroll")}",{{y:-250,duration:0.9,ease:"power2.inOut"}},{s.at(3, 0.0)});')
    s.tw(f'tl.fromTo("#{s.id("ans")}",{{opacity:0}},{{opacity:1,duration:0.4}},{s.at(3, 0.1)});')
    s.html  # (ans is visible inside scroll; fade handled above)
    for k, tt in enumerate([s.at(4, 0.2), s.at(5, 0.2), s.at(5, 0.7)]):
        s.tw(f'tl.fromTo("#{s.id(f"sc{k}")}",{{opacity:0,scale:0.8}},{{opacity:1,scale:1,duration:0.4,ease:"back.out(1.6)"}},{tt});')
    s.tw(f'tl.fromTo("#{s.id("str")}",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.6,ease:"expo.out"}},{s.at(6, 0.1)});')
    s.zoom("w", s.at(6, 0.3), 1.12, 600, 420)
    s.unzoom("w", s.at(8, 0.0))
    s.tw(f'tl.to("#{s.id("scroll")}",{{y:-610,duration:0.9,ease:"power2.inOut"}},{s.at(8, 0.0)});')
    s.rows("f", ["Did I answer the question?", "Clear structure (STAR)", "A stronger version, only my facts"], 130, 450, PINK_INK, gap=54, size=27)
    for k, (i, f) in enumerate([(4, 0.0), (5, 0.0), (6, 0.2)]):
        s.show(f"f{k}", s.at(i, f), "left")
    for k in range(3):
        s.hide(f"f{k}", s.at(8))
    s.chip("d", "3 drills · Practise this now", 120, 450, ACCENT_INK, "#fff", size=27)
    s.show("d", s.at(8, 0.3), "pop", "drop_002")
    s.cursor(s.at(8, 0.2), WX + 600, WY + 500)
    s.press(s.at(8, 0.4), 170, 422, None, 0.5)
    s.hop("b", s.at(8, 0.6))
    for n in ["w", "b", "lab", "d", "cur"]:
        s.hide(n, s.D)
    # the ans pane starts visible inside the window; hide it until scrolled
    s.tw(f'tl.set("#{s.id("ans")}",{{opacity:0}},0);')
    for k in range(3):
        s.tw(f'tl.set("#{s.id(f"sc{k}")}",{{opacity:0}},0);')
    s.tw(f'tl.set("#{s.id("str")}",{{opacity:0}},0);')
    return s


def slide_html(n, title, body):
    return (f'<div style="position:absolute;inset:0;background:#fff">'
            f'<div style="position:absolute;left:44px;top:34px;font-size:34px;font-weight:700;letter-spacing:-0.02em;color:{INK}">{title}</div>'
            f'<div style="position:absolute;left:44px;top:96px;width:120px;height:6px;border-radius:3px;background:{LAVENDER}"></div>{body}'
            f'<div style="position:absolute;right:24px;bottom:18px;font-size:16px;color:{MUTED}">{n} / 3</div></div>')


def s07():
    s = Scene("s07-present")
    s.flood(LAVENDER, "presenter", "02", "Presentation practice", 0.05, s.at(1), "Does your talk match your slides?")
    s.left_col("presenter", ("default", "sleeping"), "Presentation practice", LAVENDER, INK)
    s.show("b", s.at(1), "pop", "card-place-2"); s.show("lab", s.at(1, 0.2), "pop")
    d = PLAN["deck"]
    # --- upload, then the deck page
    up = (nav("Presentations") + f'<div id="{s.id("upv")}">'
          + f'<div style="position:absolute;left:48px;top:84px;font-size:15px;font-weight:700;letter-spacing:.14em;color:{LAV_INK}">PRESENTATION PRACTICE</div>'
          + '<div class="disp" style="position:absolute;left:48px;top:108px;font-size:36px">Practise your talk and your Q&amp;A</div>'
          + '<div style="position:absolute;left:48px;top:190px;width:1120px;height:250px;border-radius:20px;border:2.5px dashed rgba(75,47,168,.4);background:#F6F2FE"></div>'
          + f'<div style="position:absolute;left:48px;top:290px;width:1120px;text-align:center;font-size:22px;color:{LAV_INK};font-weight:600">New presentation · drop a .pptx or .pdf</div>'
          + s.e("bar0", "abs", "left:300px;top:380px;width:620px;height:14px;border-radius:7px;background:#E6DEFB")
          + f'<div id="{s.id("bar1")}" style="position:absolute;left:300px;top:380px;width:620px;height:14px;border-radius:7px;background:{LAV_INK};transform-origin:0 50%"></div></div>'
          # the deck page, built over the upload view
          + s.e("deck", "abs", f"left:0;right:0;top:62px;bottom:0;background:{BG}",
                f'<div class="disp" style="position:absolute;left:48px;top:22px;font-size:32px">{d["title"]}</div>'
                f'<div style="position:absolute;left:48px;top:72px;width:1120px;font-size:18px;line-height:1.5;color:#2A2A2A">{d["summary"]}</div>'
                + s.e("mm", "pane", "left:48px;top:170px;width:640px;height:110px;background:#F1ECFD",
                      f'<div style="position:absolute;left:20px;top:14px;font-size:15px;font-weight:700;letter-spacing:.1em;color:{LAV_INK}">MAIN MESSAGE</div>'
                      f'<div style="position:absolute;left:20px;top:40px;right:20px;font-size:19px;line-height:1.4;font-weight:600">{d["main_message"]}</div>')
                + s.e("stc", "pane", "left:712px;top:170px;width:456px;height:110px",
                      f'<div style="position:absolute;left:20px;top:14px;font-size:15px;font-weight:700;letter-spacing:.1em;color:{LAV_INK}">STRUCTURE</div>'
                      + "".join(f'<div style="position:absolute;left:20px;top:{44 + k * 30}px;font-size:18px"><b>{sec["section"]}</b> · slide{"s" if len(sec["slides"]) > 1 else ""} {"–".join(str(x) for x in (sec["slides"][0], sec["slides"][-1])) if len(sec["slides"]) > 1 else sec["slides"][0]}</div>'
                                for k, sec in enumerate(d["structure"])))
                + s.e("rd", "abs", f"left:48px;top:186px;padding:10px 18px;border-radius:999px;background:#F1ECFD;color:{LAV_INK};font-size:19px;font-weight:600", "Reading your deck · 3 slides…")
                + '<div style="position:absolute;left:48px;top:300px;font-size:20px;font-weight:700">Step 1 · What each slide should say</div>'
                + "".join(s.e(f"kp{k}", "pane", f"left:48px;top:{340 + k * 82}px;width:1120px;height:70px",
                              f'<div style="position:absolute;left:20px;top:12px;font-size:15px;font-weight:700;color:{LAV_INK}">SLIDE {k + 1} · {sl["title"]}</div>'
                              f'<div style="position:absolute;left:20px;top:36px;font-size:18px">{sl["key_point"]}</div>')
                          for k, sl in enumerate(d["slides"]))
                + s.e("pres", "btn", f"left:48px;top:600px;background:{LAV_INK}", "Present it", hidden=False)
                + s.e("qa", "btn", "left:220px;top:600px;background:#fff;color:#0A0A0A;border:1.5px solid rgba(10,26,26,.2)", "Rehearse the Q&amp;A", hidden=False)))
    s.win("u", WX, WY, WW, WH, "speechmate · /presentations", up)
    s.show("u", s.at(1, 0.05), "right")
    s.el("file", "abs", f"left:{WX + 900}px;top:{WY + 600}px;padding:14px 20px;border-radius:14px;background:#fff;font-size:21px;font-weight:600;box-shadow:0 14px 30px rgba(10,26,26,.2)",
         "📊 Time management.pptx")
    s.show("file", s.at(1, 0.2), "pop")
    s.tw(f'tl.to("#{s.id("file")}",{{x:-420,y:-310,duration:0.8,ease:"power2.inOut"}},{s.at(1, 0.45)});')
    s.tw(f'tl.to("#{s.id("file")}",{{opacity:0,scale:0.7,duration:0.25}},{s.at(1, 0.45) + 0.85});')
    s.sfx.append(("drop_001", s.at(1, 0.45) + 0.8))
    s.show("bar0", s.at(1, 0.45) + 0.85, "fade")
    s.tw(f'tl.fromTo("#{s.id("bar1")}",{{scaleX:0}},{{scaleX:1,duration:1.4,ease:"power1.inOut"}},{s.at(1, 0.45) + 0.9});')
    s.show("deck", s.at(2, 0.55), "fade", "card-place-2"); s.cut("upv", s.at(2, 0.55) + 0.45)
    s.tw(f'tl.set(["#{s.id("mm")}","#{s.id("stc")}","#{s.id("kp0")}","#{s.id("kp1")}","#{s.id("kp2")}"],{{opacity:0}},0);')
    s.tw(f'tl.set("#{s.id("rd")}",{{opacity:1}},{s.at(2, 0.6)});tl.to("#{s.id("rd")}",{{opacity:0.45,duration:0.35,yoyo:true,repeat:5,ease:"sine.inOut"}},{s.at(2, 0.7)});tl.set("#{s.id("rd")}",{{opacity:0}},{s.at(4, 0.02)});')
    s.show("mm", s.at(4, 0.05), "drop", "drop_001"); s.show("stc", s.at(4, 0.55), "drop", "drop_002")
    for k in range(3):
        s.show(f"kp{k}", s.at(5, 0.05) + k * 0.25, "drop")
    s.text("un", "The AI reads the deck <b>first</b>", 120, 450, 460, 32, 600, INK)
    s.show("un", s.at(2, 0.3), "blur")
    ins = s.rows("i", ["Main message", "Structure", "Key point of every slide"], 130, 520, LAV_INK, gap=54, size=27)
    for k, (i, f) in enumerate([(4, 0.05), (4, 0.55), (5, 0.3)]):
        s.show(ins[k], s.at(i, f), "left")
    s.cursor(s.at(5, 0.6), WX + 500, WY + 500)
    s.press(s.at(5, 0.75), 110, 62 + 624, None, 0.45)
    for n in ["u", "un", "cur"] + ins:
        s.hide(n, s.at(6, 0.1))
    # --- presenting
    slides = [
        slide_html(1, d["slides"][0]["title"], "".join(f'<div style="position:absolute;left:44px;top:{140 + k * 54}px;width:{[420, 360, 400][k]}px;height:22px;border-radius:11px;background:#EDE7DA"></div>' for k in range(3))),
        slide_html(2, d["slides"][1]["title"], "".join(f'<div style="position:absolute;left:{44 + (k % 2) * 190}px;top:{130 + (k // 2) * 110}px;width:176px;height:96px;border-radius:12px;background:{c};font-size:15px;font-weight:700;padding:10px">{t}</div>'
                                                      for k, (t, c) in enumerate([("Urgent · important", PEACH), ("Important", MINT), ("Urgent", OCHRE), ("Neither", "#EDE7DA")]))),
        slide_html(3, d["slides"][2]["title"], "".join(f'<div style="position:absolute;left:{44 + k * 120}px;top:150px;width:100px;height:{60 + k * 30}px;border-radius:10px;background:{LAVENDER};opacity:{0.5 + k * 0.15}"></div>' for k in range(4))),
    ]
    stage = "".join(f'<div id="{s.id(f"sl{k}")}" style="position:absolute;inset:0;opacity:{1 if k == 0 else 0}">{h}</div>' for k, h in enumerate(slides))
    talk = (f'<div style="position:absolute;left:40px;top:34px;width:760px;height:430px;border-radius:16px;overflow:hidden">{stage}</div>'
            f'<div style="position:absolute;left:830px;top:34px;width:354px;height:250px;border-radius:16px;overflow:hidden">{camera_view(s, "p07", 354, 250)}</div>'
            f'<div class="dpane" style="left:830px;top:300px;width:354px;height:250px">'
            f'<img src="assets/bots/presenter-sleeping.png" alt="" style="position:absolute;left:50%;top:6px;width:190px;height:190px;margin-left:-95px">'
            f'<div style="position:absolute;left:0;right:0;bottom:16px;text-align:center;font-size:19px;font-weight:600">Listening quietly</div></div>'
            f'<div class="turn" style="left:40px;top:486px;background:{LAV_INK};color:#fff">Presenting</div>'
            + s.e("nx", "btn", "left:660px;top:486px;background:#2A3A39", "Next slide →", hidden=False))
    s.win("v", WX, WY, WW, WH, "speechmate · /session", talk, dark=True)
    s.show("v", s.at(6, 0.05), "right")
    s.talk("p07", s.at(6, 0.4), s.ce[8] - s.cs[6])
    s.gesture("p07", s.at(7, 0.1), 2)
    s.cursor(s.at(7, 0.0), WX + 900, WY + 600)
    for k, tt in enumerate([s.at(7, 0.25), s.at(8, 0.2)]):
        t = s.press(tt, 740, 508, None, 0.4)
        s.tw(f'tl.to("#{s.id(f"sl{k}")}",{{opacity:0,duration:0.2}},{t + 0.05});tl.to("#{s.id(f"sl{k + 1}")}",{{opacity:1,duration:0.2}},{t + 0.05});')
    s.swap("b", "default", "sleeping", s.at(8))
    s.chip("q", "Your audience just listens", 120, 450, "#fff", ACCENT_INK, dot=LAV_INK, size=27)
    s.show("q", s.at(8, 0.1), "rise")
    for n in ["q", "v", "cur"]:
        s.hide(n, s.at(9))
    # --- per-slide results
    res = [(1, "Covered", 5, MINT, "You introduced all five strategies and why they matter."),
           (2, "Left out", 2, PEACH, "Left out: the Eisenhower matrix, the slide's main tool."),
           (3, "Covered", 4, MINT, "Time-blocking and short work sprints, explained with an example.")]
    rr = (nav("Presentations") + '<div class="illus">ILLUSTRATIVE VALUES</div>'
          + '<div class="disp" style="position:absolute;left:48px;top:96px;font-size:34px">Did your talk match your slides?</div>'
          + "".join(s.e(f"rs{k}", "pane", f"left:48px;top:{170 + k * 150}px;width:1120px;height:132px",
                        f'<div style="position:absolute;left:22px;top:16px;font-size:15px;font-weight:700;color:{LAV_INK};letter-spacing:.1em">SLIDE {n} · {d["slides"][n - 1]["title"].upper()}</div>'
                        f'<div style="position:absolute;right:22px;top:14px;padding:6px 14px;border-radius:999px;background:{c};font-size:17px;font-weight:700">{tag} · match {m}/5</div>'
                        f'<div style="position:absolute;left:22px;top:46px;font-size:17px;color:{MUTED}">The slide\'s point: {d["slides"][n - 1]["key_point"]}</div>'
                        f'<div style="position:absolute;left:22px;top:82px;font-size:19px;font-weight:600">{txt}</div>')
                    for k, (n, tag, m, c, txt) in enumerate(res)))
    s.win("r", WX, WY, WW, WH, "speechmate · /results", rr)
    s.show("r", s.at(9, 0.05), "right")
    s.swap("b", "sleeping", "default", s.at(9, 0.1))
    for k in range(3):
        s.show(f"rs{k}", s.at(10, 0.0) + k * 0.35, "drop", "card-place-1" if k == 0 else None)
    s.zoom("r", s.at(12, 0.2), 1.3, 600, 400)
    s.sfx.append(("drop_002", s.at(12, 0.55)))
    s.unzoom("r", s.at(13, 0.6))
    resr = s.rows("c", ["What you covered", "What you left out", "How well it matched (1–5)"], 130, 450, LAV_INK, gap=54, size=27)
    for k, (i, f) in enumerate([(12, 0.1), (12, 0.6), (13, 0.2)]):
        s.show(resr[k], s.at(i, f), "left")
    for n in ["r", "b", "lab"] + resr:
        s.hide(n, s.at(14))
    # --- the point, in big type
    s.el("bg2", "abs", f"inset:0;background:{LAVENDER}")
    s.show("bg2", s.at(14) - 0.1, "fade")
    s.text("m0", "When you present in your second language…", 160, 150, 1600, 48, 500, INK)
    s.show("m0", s.at(14, 0.15), "blur")
    s.text("m1", "Knowing the content", 160, 270, 1600, 96, 600, INK)
    s.text("m2", "≠ saying what it means.", 160, 390, 1600, 96, 600, LAV_INK)
    s.show("m1", s.at(16, 0.1), "blur"); s.show("m2", s.at(17, 0.2), "blur", "impactSoft_medium_001")
    s.text("m3", "SpeechMate checks your audience hears what your slides really say.", 160, 590, 1500, 48, 500, INK)
    s.show("m3", s.at(18, 0.2), "blur")
    s.bot("pb", "presenter", 1450, 560, 300, ("default",))
    s.show("pb", s.at(18, 0.4), "pop", "card-place-1"); s.hop("pb", s.at(19, 0.4))
    for n in ["m0", "m1", "m2", "m3", "bg2", "pb"]:
        s.hide(n, s.D)
    return s


def s07b():
    s = Scene("s07b-qa", LAVENDER)
    s.bot("b", "presenter", 130, 96, 250, ("default", "working"))
    s.chip("lab", "Q&amp;A rehearsal", 120, 360, "#fff", INK, size=28)
    s.show("b", 0.05, "pop"); s.show("lab", 0.25, "pop")
    s.swap("b", "default", "working", s.at(0, 0.5))
    q = PLAN["deck"]["qa"][0]
    session_win(s, "a", "speechmate · /session", LAV_INK, "presenter", "default", "working", "The moderator", q, "p07b")
    s.show("a", 0.15, "right")
    banner(s, "a", "ai", 0.15)
    s.swap("a-bot", "default", "working", 0.3, hop=False)
    banner(s, "a", "you", s.at(2, 0.1))
    s.swap("a-bot", "working", "default", s.at(2, 0.1), hop=False)
    banner(s, "a", "listen", s.at(2, 0.6))
    s.talk("p07b", s.at(2, 0.6), s.D - s.at(2, 0.6) - 0.4)
    s.zoom("a", s.at(1, 0.0), 1.25, 1000, 520)
    s.unzoom("a", s.at(2, 0.2))
    r = s.rows("r", ["Questions from your own slides", "Feedback on every answer"], 130, 450, LAV_INK, gap=54, size=27)
    s.show(r[0], s.at(1), "left"); s.show(r[1], s.at(2, 0.2), "left")
    for n in ["a", "b", "lab"] + r:
        s.hide(n, s.D)
    return s


def s08():
    s = Scene("s08-convo")
    s.flood(PINK, "chat", "03", "Daily conversation", 0.05, s.at(1), "Talk the way you really talk")
    s.left_col("chat", ("default", "working"), "Daily conversation", PINK, "#fff")
    s.show("b", s.at(1), "pop", "card-place-1"); s.show("lab", s.at(1, 0.2), "pop")
    topics = ["Your week", "Small talk", "Studies &amp; work", "Making plans", "Malaysia", "Share an opinion"]
    cards = "".join(s.e(f"tp{k}", "pane", f"left:{48 + (k % 3) * 376}px;top:{180 + (k // 3) * 150}px;width:352px;height:128px",
                        f'<div style="position:absolute;left:22px;top:22px;width:40px;height:40px;border-radius:12px;background:{[PINK, MINT, LAVENDER, PEACH, OCHRE, "#C9D9DA"][k]}"></div>'
                        f'<div class="disp" style="position:absolute;left:22px;top:76px;font-size:24px">{t}</div>', hidden=False)
                    for k, t in enumerate(topics))
    pick = (nav("Conversation")
            + f'<div style="position:absolute;left:48px;top:84px;font-size:15px;font-weight:700;letter-spacing:.14em;color:{PINK_INK}">DAILY CONVERSATION</div>'
            + '<div class="disp" style="position:absolute;left:48px;top:108px;font-size:36px">What would you like to talk about?</div>'
            + cards + s.e("st", "btn", "left:48px;top:500px", "Start conversation", hidden=False))
    s.win("w", WX, WY, WW, WH, "speechmate · /conversation", pick)
    s.show("w", s.at(1, 0.05), "right")
    s.cursor(s.at(1, 0.2), WX + 700, WY + 600)
    s.press(s.at(1, 0.3), 200, 240, "tp0", 0.35)
    s.press(s.at(1, 0.75), 150, 520, None, 0.3)
    s.hide("w", s.at(2, 0.05)); s.hide("cur", s.at(2, 0.05))
    # the chat: transcript bubbles over the session page
    chat = (f'<div style="position:absolute;left:40px;top:34px;width:640px;height:400px;border-radius:16px;overflow:hidden">{camera_view(s, "p08", 640, 400)}</div>'
            f'<div class="dpane" style="left:710px;top:34px;width:474px;height:640px">'
            f'<img src="assets/bots/chat-working.png" alt="" style="position:absolute;left:20px;top:14px;width:110px;height:110px">'
            f'<div style="position:absolute;left:140px;top:52px;font-size:20px;font-weight:600">Your partner · Your week</div>'
            + s.e("m1", "bubble", "left:20px;top:140px;width:400px;background:#2A3A39;color:#FFFAF0;font-size:20px", "How was your week? Anything fun or stressful?")
            + s.e("m2", "bubble", f"left:54px;top:250px;width:400px;background:{PINK};color:#fff;font-size:20px", "This week quite busy lah, but okay. Got my final-year project demo, so macam a bit stressed.")
            + s.e("kept", "abs", f"left:54px;top:382px;padding:6px 14px;border-radius:999px;background:{MINT};color:{INK};font-size:16px;font-weight:700", "KEPT AS SPOKEN")
            + '</div>'
            + s.e("tips", "pane", "left:40px;top:456px;width:640px;height:218px;background:#FFFAF0;color:#0A0A0A",
                  '<div class="illus" style="top:14px">ILLUSTRATIVE</div>'
                  f'<div style="position:absolute;left:20px;top:18px;font-size:15px;font-weight:700;letter-spacing:.1em;color:{PINK_INK}">YOUR LANGUAGE</div>'
                  f'<div style="position:absolute;left:20px;top:52px;font-size:18px"><b style="color:{PINK_INK}">You said:</b> “This week quite busy lah, but okay.”</div>'
                  f'<div style="position:absolute;left:20px;top:96px;width:600px;font-size:18px;line-height:1.4"><b style="color:{TEAL_INK}">Try saying:</b> “This week has been quite busy, but it\'s been okay.” '
                  '<span style="color:#5C6766">For a formal setting; with friends, the original is fine.</span></div>'))
    s.win("c", WX, WY, WW, WH, "speechmate · /session", chat, dark=True)
    s.show("c", s.at(2, 0.05), "right")
    s.show("m1", s.at(2, 0.2), "pop", "drop_001")
    s.swap("b", "default", "working", s.at(2, 0.2))
    s.show("m2", s.at(2, 0.75), "pop", "drop_002")
    s.talk("p08", s.at(2, 0.5), 1.8)
    s.show("kept", s.at(3, 0.0), "pop")
    s.show("tips", s.at(3, 0.4), "rise", "card-place-2")
    s.zoom("c", s.at(4, 0.0), 1.12, 360, 600)
    s.chip("m", "English · Bahasa Malaysia · Manglish", 120, 450, "#fff", ACCENT_INK, dot=PINK, size=26)
    s.show("m", s.at(2, 0.2), "rise")
    for n in ["c", "b", "lab", "m"]:
        s.hide(n, s.D)
    return s


def s09():
    s = Scene("s09-agents")
    cx, cy, rx, ry = 960, 450, 560, 320
    s.css = f"#s09-ring{{left:{cx - rx}px;top:{cy - ry}px;width:{2 * rx}px;height:{2 * ry}px}}"
    s.add(f'<svg id="s09-ring" class="abs" viewBox="0 0 {2 * rx} {2 * ry}"><ellipse id="s09-ell" cx="{rx}" cy="{ry}" rx="{rx - 4}" ry="{ry - 4}" '
          f'fill="none" stroke="{ACCENT_INK}" stroke-opacity=".28" stroke-width="5" stroke-dasharray="14 14" pathLength="100"/></svg>')
    s.add(f'<svg id="s09-ring2" class="abs" viewBox="0 0 {2 * rx} {2 * ry}" style="left:{cx - rx}px;top:{cy - ry}px;width:{2 * rx}px;height:{2 * ry}px">'
          f'<ellipse id="s09-sweep" cx="{rx}" cy="{ry}" rx="{rx - 4}" ry="{ry - 4}" fill="none" stroke="#C21E57" stroke-width="7" '
          f'stroke-linecap="butt" stroke-dasharray="100 100" stroke-dashoffset="100" pathLength="100"/></svg>')
    s.tw(f'tl.fromTo("#s09-ell",{{strokeDashoffset:100,opacity:0}},{{strokeDashoffset:0,opacity:1,duration:1.6,ease:"power2.inOut"}},{s.at(0)});')
    s.bot("mate", "mate", cx - 120, cy - 150, 240, ("default", "working"))
    s.show("mate", s.at(0, 0.2), "pop", "card-place-1")
    s.text("ct", "A team of AI agents", cx - 300, cy + 90, 600, 38, 600, INK, "center")
    s.show("ct", s.at(1, 0.2), "blur")
    nodes = [(-90, "Know the learner", "Learner profile", "mate", MINT, (8, 0.0)),
             (-30, "Plan", "Question planner", "interviewer", TEAL, (2, 0.0)),
             (30, "Practise", "Interviewer", "interviewer", TEAL, (3, 0.0)),
             (90, "Check", "Deck reader", "presenter", LAVENDER, (4, 0.0)),
             (150, "Coach", "Measured issues only", "mate", OCHRE, (5, 0.0)),
             (210, "Practise again", "Progress", "chat", PINK, (10, 0.4))]
    for k, (ang, step, agent, who, col, (ci, cf)) in enumerate(nodes):
        x = round(cx + rx * math.cos(math.radians(ang)) - 210)
        y = round(cy + ry * math.sin(math.radians(ang)) - 70)
        fg = "#fff" if col == TEAL else INK
        s.el(f"n{k}", "card", f"left:{x}px;top:{y}px;width:420px;height:140px;background:{col}",
             f'<img id="{s.id(f"nb{k}")}" src="assets/bots/{who}-default.png" alt="" style="position:absolute;left:0;top:2px;width:136px;height:136px">'
             f'<div class="disp" style="position:absolute;left:140px;top:28px;width:272px;font-size:30px;white-space:nowrap;color:{fg}">{step}</div>'
             f'<div style="position:absolute;left:142px;top:78px;width:270px;font-size:24px;font-weight:500;color:{fg};opacity:.85">{agent}</div>')
        t = s.at(ci, cf)
        s.show(f"n{k}", t, "pop", "card-place-1" if k % 2 else "card-place-2")
        s.tw(f'tl.to("#{s.id(f"nb{k}")}",{{rotation:-8,duration:0.18,yoyo:true,repeat:3,ease:"sine.inOut"}},{t + 0.6});')
    s.chip("inv", "It can't invent a problem", cx - 200, cy + 160, "#fff", ACCENT_INK, dot=OCHRE, size=28)
    s.show("inv", s.at(7, 0.1), "rise")
    s.hide("inv", s.at(8, 0.6)); s.hide("ct", s.at(8))
    # Mate's chat (real suggestion chips from MateChat.tsx)
    s.el("chat", "pane", f"left:{cx - 230}px;top:{cy + 84}px;width:460px;height:128px",
         f'<div style="position:absolute;left:18px;top:14px;font-size:16px;font-weight:700;letter-spacing:.1em;color:{TEAL_INK}">ASK MATE</div>'
         f'<div style="position:absolute;right:18px;top:44px;padding:10px 16px;border-radius:16px 16px 4px 16px;background:{ACCENT_INK};color:#fff;font-size:21px">What should I practise next?</div>'
         f'<div id="{s.id("dots")}" style="position:absolute;left:18px;top:84px;padding:6px 16px;border-radius:16px 16px 16px 4px;background:#F3EEE3;font-size:22px;letter-spacing:4px">•••</div>')
    s.show("chat", s.at(9, 0.1), "rise", "drop_001")
    s.tw(f'tl.to("#{s.id("dots")}",{{opacity:0.3,duration:0.3,yoyo:true,repeat:5,ease:"sine.inOut"}},{s.at(9, 0.4)});')
    s.swap("mate", "default", "working", s.at(9, 0.2))
    s.hide("chat", s.at(10))
    s.tw(f'tl.fromTo("#s09-sweep",{{strokeDashoffset:100}},{{strokeDashoffset:0,duration:{round(s.ce[11] - s.cs[10] + 0.6, 2)},ease:"power1.inOut"}},{s.at(10)});')
    s.text("loop", "Practise → get coached → practise again", cx - 420, cy + 100, 840, 34, 600, PINK_INK, "center")
    s.show("loop", s.at(11, 0.1), "blur")
    s.swap("mate", "working", "default", s.at(12, 0.3))
    for n in ["mate", "loop"] + [f"n{k}" for k in range(6)]:
        s.hide(n, s.D)
    s.tw(f'tl.to(["#s09-ring","#s09-ring2"],{{opacity:0,duration:0.25}},{s.D - 0.25});')
    return s


def s10():
    s = Scene("s10-close")
    for k, (big, small, bg) in enumerate([
            ("4.9% · 7.3%", "word error rate on real English · Malay speech", MINT),
            ("Deleted", "your recordings, after analysis", PEACH),
            ("Explained", "every score, never guessed. See <b>How it's measured</b>", LAVENDER)]):
        s.el(f"t{k}", "card", f"left:{140 + k * 560}px;top:200px;width:520px;height:380px;background:{bg}",
             f'<div class="disp" style="position:absolute;left:40px;top:60px;font-size:{76 if k == 0 else 84}px">{big}</div>'
             f'<div style="position:absolute;left:42px;top:200px;width:440px;font-size:30px;font-weight:500;line-height:1.3">{small}</div>')
        s.show(f"t{k}", s.at(k, 0.1), "rise", "card-place-1" if k != 1 else "card-place-2")
        s.hide(f"t{k}", s.at(3))
    # the mirror again: the learner smiles, Mate is there
    s.el("room", "abs", "inset:0")
    room_start = len(s.html)
    mirror_room(s, "p10b", "p10r", mouth="smile")
    room = "".join(s.html[room_start:]); del s.html[room_start:]
    s.html[-1] = s.html[-1].replace("></div>", f">{room}</div>", 1) if s.html[-1].endswith("></div>") else s.html[-1]
    s.show("room", s.at(3) - 0.2, "fade")
    s.bot("mate", "mate", 110, 560, 280, ("default",))
    s.show("mate", s.at(3, 0.45), "pop", "card-place-1")
    s.el("say", "bubble", f"left:150px;top:470px;background:#fff;font-size:30px;font-weight:600;box-shadow:0 10px 22px rgba(10,26,26,.14)", "Nice one!")
    s.show("say", s.at(3, 0.7), "pop", "drop_002")
    s.tw(f'tl.to("#p10r .phead",{{rotation:-5,svgOrigin:"200 350",duration:0.4,yoyo:true,repeat:1,ease:"sine.inOut"}},{s.at(3, 0.5)});')
    s.tw(f'tl.to("#p10b .phead",{{rotation:5,svgOrigin:"200 380",duration:0.5,ease:"power2.out"}},{s.at(3, 0.6)});')
    for n in ["room", "say"]:
        s.hide(n, s.at(4))
    s.tw(f'tl.to("#{s.id("mate")}",{{x:810 - 110,y:130 - 560,scale:1.07,duration:0.7,ease:"power2.inOut"}},{s.at(4) - 0.4});')
    s.text("logo", "SpeechMate", 0, 470, 1920, 170, 600, INK, "center")
    s.show("logo", s.at(4, 0.05), "blur", "impactBell_heavy_003")
    s.text("tag", "Practise, and finally know what to improve.", 0, 680, 1920, 50, 500, ACCENT_INK, "center")
    s.show("tag", s.at(4, 0.35), "blur")
    s.tw(f'tl.to("#{s.id("mate")}",{{rotation:360,duration:0.8,ease:"power2.inOut"}},{s.ce[4] + 0.3});')
    return s


@cache
def fx_len(name):
    f = next((COMP / "assets" / "sfx").glob(f"{name}.*"))
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout
    return round(float(out) - 0.01, 3), f.name


def main():
    (COMP / "compositions").mkdir(exist_ok=True)
    scenes = [f() for f in (s01, s02, s03, s04, s05, s06, s07, s07b, s08, s09, s10)]
    starts, t = {}, 0.0
    for s in scenes:
        starts[s.sid] = round(t, 3); t += s.D
    total = round(t, 3)
    for s in scenes:
        s.write()

    hosts, audio, caps = [], [], []
    track = 20
    for k, s in enumerate(scenes):
        st = starts[s.sid]
        hosts.append(f'<div id="{s.sid}" data-composition-id="{s.sid}" data-composition-src="compositions/{s.sid}.html" '
                     f'data-start="{st}" data-duration="{s.D}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="1920" data-height="1080" style="z-index:{k + 1}"></div>')
        audio.append(f'<audio id="vo-{s.sid.split("-")[0]}" class="clip" data-start="{round(st + s.L, 3)}" data-duration="{T[s.sid]["dur"]}" '
                     f'data-track-index="3" data-volume="1" src="assets/voice/{s.sid}.wav"></audio>')
        for name, lt in sorted(s.sfx, key=lambda x: x[1]):
            track += 1
            ln, fname = fx_len(name)
            vol = 0.5 if name.startswith("impactBell") else 0.28 if name.startswith(("keypress", "mouseclick")) else 0.42
            audio.append(f'<audio id="fx{track}" class="clip" data-start="{round(st + lt, 3)}" data-duration="{ln}" '
                         f'data-track-index="{track}" data-volume="{vol}" src="assets/sfx/{fname}"></audio>')
        for c in T[s.sid]["chunks"]:
            caps.append((round(st + s.L + c["start"], 3), round(st + s.L + c["end"], 3), c["en"], c["ms"]))

    s3 = starts["s03-intro"]
    m2_media = round(17.02 - REVEAL, 3)                  # beat-locked: 17.02 s cue -> s03 + REVEAL
    m2_len = round(163.96 - m2_media - 1.0, 3)
    m3_start = round(s3 + m2_len - 3.0, 3)
    audio[:0] = [
        f'<audio id="m1" class="clip" data-start="0" data-duration="{round(s3 + 1.2, 3)}" data-track-index="10" data-volume="0.12" '
        f'data-fade-in="1.5" data-fade-out="1.6" src="assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3"></audio>',
        f'<audio id="m2" class="clip" data-start="{s3}" data-duration="{m2_len}" data-media-start="{m2_media}" data-track-index="11" '
        f'data-volume="0.14" data-fade-in="0.6" data-fade-out="3" src="assets/music/happy-beats-business-moves-vol-1-by-ende-dot-app.mp3"></audio>',
        f'<audio id="m3" class="clip" data-start="{m3_start}" data-duration="{round(total - m3_start, 3)}" data-track-index="12" '
        f'data-volume="0.14" data-fade-in="3" data-fade-out="3" src="assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3"></audio>',
    ]

    groups, js, prev_end = [], [], 0.0
    for k, (a, b, en, ms) in enumerate(caps):
        nxt = caps[k + 1][0] if k + 1 < len(caps) else total
        end = round(min(nxt - 0.02, b + 0.7), 3)
        start = round(max(a - 0.08, 0.15, prev_end), 3)
        prev_end = end
        groups.append(f'<div id="cap{k}" class="cap"><div class="box"><div class="en">{en}</div><div class="ms">{ms}</div></div></div>')
        js.append(f'tl.fromTo("#cap{k}",{{opacity:0}},{{opacity:1,duration:0.12,ease:"power2.out"}},{start});'
                  f'tl.to("#cap{k}",{{opacity:0,duration:0.12,ease:"power2.in"}},{round(end - 0.12, 3)});'
                  f'tl.set("#cap{k}",{{opacity:0,visibility:"hidden"}},{end});')
    (COMP / "compositions" / "captions.html").write_text(f"""<template>
  <style>
#root{{position:absolute;inset:0;pointer-events:none;font-family:Inter,sans-serif}}
.cap{{position:absolute;left:0;right:0;bottom:64px;text-align:center;opacity:0}}
.cap .box{{display:inline-block;max-width:1560px;padding:14px 34px 16px;border-radius:20px;background:rgba(10,26,26,.88)}}
.cap .en{{font-size:38px;font-weight:600;letter-spacing:-0.01em;color:#FFFAF0;line-height:1.25}}
.cap .ms{{margin-top:6px;font-size:28px;font-weight:500;color:{MINT};line-height:1.3}}
  </style>
  <div id="root" data-composition-id="captions" data-width="1920" data-height="1080">
{chr(10).join('    ' + g for g in groups)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join('    ' + j for j in js)}
    tl.set({{}}, {{}}, {total});
    window.__timelines["captions"] = tl;
  </script>
</template>
""")
    (COMP / "index.html").write_text(f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: {BG}; }}
      #root {{ width: 100%; height: 100%; font-family: Inter, sans-serif; }}
      #ground {{ position: absolute; inset: 0; background: {BG}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1920" data-height="1080">
      <div id="ground"></div>
{chr(10).join('      ' + h for h in hosts)}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total}"
        data-track-index="2" data-track-kind="captions" data-width="1920" data-height="1080" style="z-index:50"></div>
{chr(10).join('      ' + a for a in audio)}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
""")
    print(f"total {total:.1f}s ({int(total // 60)}:{total % 60:04.1f})")


if __name__ == "__main__":
    main()
