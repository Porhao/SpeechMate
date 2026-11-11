"""The SpeechMate demo video (concise version): story -> a continuous walkthrough of the app,
from the login page through every feature -> the agents -> close.

Pages are rebuilt from the real app (reference screenshots of the running app, 1440 px wide) and
drawn at 1.1x inside one browser window that stays on screen. Real app output is used where it
exists (tools/real_outputs.json); scores and feedback are illustrative and tagged on screen.
Run: python3 tools/demo.py   (from brag-output/), after tools/build_voice.py
"""
import json, math
from pathlib import Path

import build as B
from build import (BG, INK, ACCENT_INK, MUTED, PINK, PINK_INK, TEAL, TEAL_INK, LAVENDER, LAV_INK, PEACH, OCHRE, MINT,
                   NIGHT, NIGHT2, CURSOR, PLAN, REVEAL, COMP, T, page_caption, mirror_room, svg_person, camera_view, fx_len, person_back)
from person import HOODIE, HOODIE_SHADE
from life import Life, bot_html

SC = 1.1                                  # page px -> video px
PW, PH = 1440, 760                        # the page viewport
WW, WH = round(PW * SC), round(PH * SC) + 46
WX, WY = (1920 - WW) // 2, 18
CREAM2 = "#F4EBDD"
FOCUS_X, FOCUS_Y, CAP_TOP = 960, 450, 900   # where a zoom puts its focus; zoomed content stays above the captions


def zoom_xy(k, ox, oy):
    """translate for a window scaled by k about its top-left so (ox, oy) lands on the focus, clamped to the frame"""
    def axis(origin, o, size, focus, lo, hi):
        v = focus - origin - o * k
        if size * k <= hi - lo:                                   # smaller than the frame: centre it
            return round((lo + hi - size * k) / 2 - origin)
        return round(min(lo - origin, max(hi - origin - size * k, v)))   # edges stay outside the frame
    return axis(WX, ox, WW, FOCUS_X, 0, 1920), axis(WY, oy, WH, FOCUS_Y, 0, CAP_TOP)


def selftest_zoom():
    for k, ox, oy in [(1.25, 600, 430), (1.18, 1300, 420), (1.16, 330, 700), (1.12, 700, 500), (1.25, 0, 0), (1.25, WW, WH)]:
        x, y = zoom_xy(k, ox, oy)
        L, R, T_, B_ = WX + x, WX + x + WW * k, WY + y, WY + y + WH * k
        ok_x = abs(L + R - 1920) <= 1 if WW * k <= 1920 else (L <= 1 and R >= 1919)   # centred, or covers the width
        ok_y = abs(T_ + B_ - CAP_TOP) <= 1 if WH * k <= CAP_TOP else (T_ <= 1 and B_ >= CAP_TOP - 1)
        assert ok_x and ok_y, (k, ox, oy, L, R, T_, B_)


# what the viewer is looking at, shown as a badge in every app scene
STEPS = {
    "s04-login": ("Getting started", 1, 3, "Sign in", MINT), "s05-home": ("Getting started", 2, 3, "Home", MINT),
    "s06-profile": ("Getting started", 3, 3, "Your profile", MINT),
    "s07-form": ("Mock interview", 1, 5, "Describe the job", TEAL), "s08-plan": ("Mock interview", 2, 5, "Question plan", TEAL),
    "s09-live": ("Mock interview", 3, 5, "Live interview", TEAL), "s09b-analyse": ("Mock interview", 4, 5, "Analysis", TEAL),
    "s10-results": ("Mock interview", 5, 5, "Results", TEAL), "s10b-factcheck": ("Mock interview", 5, 5, "Results", TEAL),
    "s11-deck": ("Presentation", 1, 4, "Upload slides", LAVENDER), "s12-talk": ("Presentation", 2, 4, "Present", LAVENDER),
    "s13-match": ("Presentation", 3, 4, "Slide check", LAVENDER), "s14-qa": ("Presentation", 4, 4, "Q&amp;A", LAVENDER),
    "s15-convo": ("Daily conversation", 1, 2, "Chat", PINK), "s16-tips": ("Daily conversation", 2, 2, "Language tips", PINK),
    "s17-progress": ("After practice", 1, 3, "Progress", OCHRE), "s17b-mate": ("After practice", 2, 3, "Ask Mate", OCHRE),
    "s17c-measured": ("After practice", 3, 3, "How it's measured", OCHRE),
}


PAGE_CSS = """
.pg{position:absolute;left:0;top:0;width:1440px;height:760px;transform:scale(1.1);transform-origin:0 0;overflow:hidden;font-family:Inter,sans-serif;color:#0A0A0A}
.layer{position:absolute;inset:0}
.navp{position:absolute;z-index:8;left:30px;right:30px;top:10px;height:50px;border-radius:999px;background:#fff;box-shadow:0 6px 18px rgba(10,26,26,.08);display:flex;align-items:center;padding:0 14px 0 10px;gap:6px;font-size:15px}
.navp .lg{display:flex;align-items:center;gap:10px;font-weight:700;font-size:18px;margin-right:auto}
.navp .lg i{width:34px;height:34px;border-radius:50%;background:radial-gradient(circle at 40% 35%,#FFD9C2,#F5A27C)}
.navp .it{padding:8px 16px;border-radius:999px;color:#3A4645}
.navp .it.on{background:#0A0A0A;color:#fff;font-weight:600}
.navp .me{margin-left:auto;display:flex;align-items:center;gap:10px;font-size:14px}
.navp .me b{width:34px;height:34px;border-radius:50%;background:#0A0A0A;color:#fff;font-size:12px;display:grid;place-items:center}
.navp .bell{width:22px;height:22px;border-radius:6px;border:2px solid #3A4645;position:relative;margin-right:10px}
.navp .bell:after{content:"3";position:absolute;right:-9px;top:-9px;width:16px;height:16px;border-radius:50%;background:#E5484D;color:#fff;font-size:10px;display:grid;place-items:center}
.rail{position:absolute;z-index:8;left:10px;top:90px;width:42px;border-radius:999px;background:#fff;box-shadow:0 6px 18px rgba(10,26,26,.08);padding:8px 0;display:flex;flex-direction:column;align-items:center;gap:12px}
.rail i{width:24px;height:24px;border-radius:8px;background:#EDE6D8}
.rail i.dk{background:#0A0A0A;border-radius:50%}
.eb{position:absolute;font-size:13px;font-weight:700;letter-spacing:.14em}
.h1{position:absolute;font-size:42px;font-weight:700;letter-spacing:-0.03em;line-height:1.08}
.sub{position:absolute;font-size:16px;line-height:1.5;color:#3A4645}
.wcard{position:absolute;border-radius:18px;background:#fff;box-shadow:0 1px 0 rgba(10,26,26,.04),0 0 0 1px rgba(10,26,26,.07)}
.lb{position:absolute;font-size:15px;font-weight:600}
.lb em{font-style:normal;font-weight:400;color:#7A8584;margin-left:6px;font-size:13px}
.in{position:absolute;height:42px;border-radius:10px;background:#fff;border:1.5px solid rgba(10,26,26,.16);font-size:16px;padding:10px 14px;white-space:nowrap;overflow:hidden;color:#0A0A0A}
.in .ph{color:#9AA3A2}
.tile{position:absolute;border-radius:10px;background:#fff;border:1.5px solid rgba(10,26,26,.14);padding:9px 14px;font-size:15px;font-weight:600}
.tile small{display:block;font-weight:400;font-size:12px;color:#5C6766;margin-top:2px}
.tile.sel{border-color:#0A0A0A;background:#FBF4E6}
.pill{position:absolute;border-radius:10px;border:1.5px solid rgba(10,26,26,.14);background:#fff;padding:8px 13px;font-size:14px}
.bk{position:absolute;border-radius:12px;background:#0A0A0A;color:#fff;font-size:16px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:8px}
.wt{position:absolute;border-radius:12px;background:#fff;color:#0A0A0A;border:1.5px solid rgba(10,26,26,.15);font-size:16px;font-weight:600;display:flex;align-items:center;justify-content:center}
.typ{display:inline-block;white-space:nowrap;clip-path:inset(0 100% 0 0)}
.caret{position:absolute;width:2px;height:22px;background:#0A0A0A;opacity:0}
.mate{position:absolute;z-index:8;right:16px;bottom:10px;width:92px;height:92px}
.mate img{position:absolute;inset:0;width:100%;height:100%}
.mb{position:absolute;z-index:8;right:96px;bottom:70px;max-width:280px;padding:8px 14px;border-radius:14px 14px 4px 14px;background:#fff;font-size:15px;font-weight:600;box-shadow:0 8px 20px rgba(10,26,26,.15);opacity:0}
.illus{position:absolute;padding:5px 12px;border-radius:999px;background:#E8B94A;color:#0A0A0A;font-size:12px;font-weight:800;letter-spacing:.08em}
.dk{background:#0A1A1A;color:#FFFAF0}
.dp{position:absolute;border-radius:16px;background:#13201F;color:#FFFAF0}
.turn{position:absolute;display:flex;align-items:center;gap:10px;padding:10px 18px;border-radius:12px;font-size:16px;font-weight:600;opacity:0}
.bars{position:absolute;display:flex;gap:4px;align-items:flex-end;height:26px}
.bars i{width:5px;height:6px;border-radius:3px;background:#5EEAD4}
.load{position:absolute;left:0;top:0;height:3px;width:100%;background:#1F6F6B;transform-origin:0 50%;z-index:9}
.rip{position:absolute;width:56px;height:56px;margin:-28px 0 0 -28px;border-radius:50%;background:rgba(31,111,107,.28);border:2px solid rgba(31,111,107,.5);opacity:0;z-index:39;pointer-events:none}
.dots i{display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:4px}
"""


class S(B.Scene):
    def __init__(self, sid, bg=BG, lead=0.5):
        super().__init__(sid, bg)
        t = T[sid]
        self.L = lead
        self.cs = [lead + c["start"] for c in t["chunks"]]
        self.ce = [lead + c["end"] for c in t["chunks"]]
        self.D = round(max(t["min"], lead + t["dur"] + 0.8), 3)
        self.css = PAGE_CSS
        self.nrip = 0
        self.lives, self.talk_open = {}, {}

    def life(self, fid, seed=None, start="default"):
        if fid not in self.lives:
            self.lives[fid] = Life(fid, seed if seed is not None else sum(map(ord, fid)), start)
        return self.lives[fid]

    def lbot(self, name, who, x, y, size, start="default", hidden=True, idle=True, looks=None):
        """a living character: the outer element moves and fades, the inner one acts"""
        fid = f"{self.id(name)}-b"
        self.el(name, "abs", f"left:{x}px;top:{y}px;width:{size}px;height:{size}px", bot_html(fid, who, "inset:0", start), hidden)
        lf = self.life(fid, start=start)
        if idle:
            lf.idle(0.2, self.D, **({"looks": looks} if looks else {}))
        return lf

    def write(self):
        for lf in self.lives.values():
            self.js += lf.compile()
        if getattr(self, "has_win", False):
            # the whole scene sits on one camera that breathes slowly in and out (starts and ends at rest,
            # so cuts between scenes don't jump): the frame is never fully still while the voice talks
            self.html = [f'<div id="{self.id("cam")}" class="abs" style="left:0;top:0;width:1920px;height:1080px">'] + self.html + ["</div>"]
            self.tw(f'tl.fromTo("#{self.id("cam")}",{{scale:1}},{{scale:1.018,transformOrigin:"50% 42%",duration:{round(self.D / 2, 3)},'
                    f'ease:"sine.inOut",yoyo:true,repeat:1}},0);')
        super().write()

    def zoom(self, name, t, k, ox, oy, d=0.8, right=None):
        """punch in on the browser window: the window-local point (ox, oy) moves to the middle of the picture
        (above the captions), clamped so the window always fills the frame: no edge cut off half-way"""
        if name != "w":
            return super().zoom(name, t, k, ox, oy, d, right)
        x, y = zoom_xy(k, ox, oy)
        self.tw(f'tl.set("#{self.id(name)}",{{transformOrigin:"0px 0px"}},{t});'
                f'tl.to("#{self.id(name)}",{{scale:{k},x:{x},y:{y},duration:{d},ease:"power2.inOut"}},{t});')

    def unzoom(self, name, t, d=0.7):
        self.tw(f'tl.to("#{self.id(name)}",{{scale:1,x:0,y:0,duration:{d},ease:"power2.inOut"}},{t});')

    # page coordinates -> scene coordinates
    def P(self, x, y):
        return round(WX + x * SC), round(WY + 46 + y * SC)

    def cursor_at(self, t, x, y, fade=True):
        if not getattr(self, "has_cur", False):
            self.el("cur", "cur", "", CURSOR); self.has_cur = True
        X, Y = self.P(x, y)
        if fade:
            self.tw(f'tl.fromTo("#{self.id("cur")}",{{opacity:0,x:{X + 80},y:{Y + 60}}},{{opacity:1,x:{X},y:{Y},duration:0.5,ease:"power3.out"}},{t});')
        else:
            self.tw(f'tl.set("#{self.id("cur")}",{{opacity:1,x:{X},y:{Y}}},{t});')

    def go(self, t, x, y, d=0.5):
        X, Y = self.P(x, y)
        self.tw(f'tl.to("#{self.id("cur")}",{{x:{X},y:{Y},duration:{d},ease:"power2.inOut"}},{t});')
        return round(t + d, 3)

    def tap(self, t, x, y, target=None, d=0.5, sel=None, ring=False):
        """move, then click: cursor dips, a ripple opens, the target presses (and gets selected / focused)"""
        t = self.go(t, x, y, d)
        c = f"#{self.id('cur')}"
        self.tw(f'tl.to("{c}",{{scale:0.8,duration:0.07,ease:"power2.out"}},{t});tl.to("{c}",{{scale:1,duration:0.15,ease:"power2.out"}},{round(t + 0.07, 3)});')
        X, Y = self.P(x, y)
        r = f"rip{self.nrip}"; self.nrip += 1
        self.el(r, "rip", f"left:{X}px;top:{Y}px", hidden=False)
        self.tw(f'tl.fromTo("#{self.id(r)}",{{opacity:0.9,scale:0.3}},{{opacity:0,scale:1.5,duration:0.5,ease:"power2.out",immediateRender:false}},{t});')
        self.sfx.append(("mouseclick1", t))
        if target:
            g = f"#{self.id(target)}"
            self.tw(f'tl.to("{g}",{{scale:0.96,duration:0.07,ease:"power2.out"}},{t});tl.to("{g}",{{scale:1,duration:0.2,ease:"back.out(2)"}},{round(t + 0.07, 3)});')
            if sel == "tile":
                self.tw(f'tl.to("{g}",{{borderColor:"#0A0A0A",backgroundColor:"#FBF4E6",duration:0.15}},{t});')
            elif sel == "pill":
                self.tw(f'tl.to("{g}",{{borderColor:"#0A0A0A",backgroundColor:"#0A0A0A",color:"#fff",duration:0.15}},{t});')
            if ring:
                self.tw(f'tl.to("{g}",{{borderColor:"#1F6F6B",boxShadow:"0 0 0 4px rgba(31,111,107,0.2)",duration:0.15}},{t});')
        return t

    def unring(self, target, t):
        self.tw(f'tl.to("#{self.id(target)}",{{borderColor:"rgba(10,26,26,0.16)",boxShadow:"0 0 0 0px rgba(31,111,107,0)",duration:0.15}},{t});')

    def type_in(self, span, caret, t, text, d=None, x0=0, cw=8.7):
        """type `text` into a .typ span; a caret rides along and blinks after"""
        d = d or max(0.6, len(text) * 0.045)
        self.typ(span, t, d, keys=True)
        cx = round(len(text) * cw)
        cr = f"#{self.id(caret)}"
        self.tw(f'tl.set("{cr}",{{opacity:1,x:0}},{t});tl.to("{cr}",{{x:{cx},duration:{d},ease:"steps({max(6, len(text))})"}},{t});'
                f'tl.to("{cr}",{{opacity:0,duration:0.01,yoyo:true,repeat:5,repeatDelay:0.32}},{round(t + d + 0.1, 3)});tl.set("{cr}",{{opacity:0}},{round(t + d + 2.2, 3)});')
        return round(t + d, 3)

    def swap_page(self, t, a, b, url=None):
        """navigate: the loading bar runs, the old page leaves, the new one settles in"""
        self.tw(f'tl.fromTo("#{self.id("load")}",{{scaleX:0,opacity:1}},{{scaleX:1,duration:0.45,ease:"power2.out"}},{t});'
                f'tl.to("#{self.id("load")}",{{opacity:0,duration:0.2}},{round(t + 0.45, 3)});')
        if a:
            self.tw(f'tl.to("#{self.id(a)}",{{opacity:0,duration:0.18,ease:"power2.in"}},{round(t + 0.15, 3)});')
        self.tw(f'tl.fromTo("#{self.id(b)}",{{opacity:0,y:14}},{{opacity:1,y:0,duration:0.45,ease:"expo.out"}},{round(t + 0.3, 3)});')
        if url:
            self.tw(f'tl.set("#{self.id("url")}",{{opacity:0}},{round(t + 0.05, 3)});tl.set("#{self.id("url2")}",{{opacity:1}},{round(t + 0.05, 3)});')

    def mate_say(self, page, text, t, hold=1.6):
        b = f"#{self.id(page + '-mb')}"
        self.tw(f'tl.set("{b}",{{textContent:"{text}"}},{t});tl.fromTo("{b}",{{opacity:0,scale:0.7}},{{opacity:1,scale:1,duration:0.3,ease:"back.out(2)"}},{t});'
                f'tl.to("{b}",{{opacity:0,duration:0.2}},{round(t + hold, 3)});')
        self.life(self.id(page + "-mate")).hop(t)
        self.sfx.append(("drop_002", t))

    def mate_state(self, page, a, b, t):
        self.tw(f'tl.set("#{self.id(page + "-mate-" + b)}",{{opacity:1}},{t});tl.set("#{self.id(page + "-mate-" + a)}",{{opacity:0}},{round(t + 0.034, 3)});')

    def scroll(self, el, t, y, d=0.8):
        self.tw(f'tl.to("#{self.id(el)}",{{y:{-y},duration:{d},ease:"power2.inOut"}},{t});')

    def callout(self, name, text, x, y, t, color=OCHRE, hold=None, fg=INK):
        """a label over the window, pointing at what just happened (video annotation, not app UI)"""
        X, Y = self.P(x, y)
        self.el(name, "chip", f"left:{X}px;top:{Y}px;background:{color};color:{fg};font-size:24px;padding:10px 20px;z-index:30")
        self.show(name, t, "pop", "drop_001")
        if hold:
            self.hide(name, round(t + hold, 3))


# ---------------------------------------------------------------- page parts
def chrome(s, page, active, mate_states=("default",)):
    items = "".join(f'<span class="it{" on" if n == active else ""}">{n}</span>' for n in ["Home", "Conversation", "Interview", "Presentation", "Script", "Progress"])
    s.life(s.id(page + "-mate")).idle(0.3, s.D, looks=("left", "default", "down", "default", "tiltl", "left", "default"), gap=(1.4, 2.8))
    return (f'<div class="navp" data-layout-allow-overlap data-layout-allow-occlusion><span class="lg"><i></i>SpeechMate</span>{items}'
            f'<span class="me"><span class="bell"></span><b>AR</b><span><b style="all:unset;font-weight:600;display:block">Aisyah Rahman</b>'
            f'<span style="font-size:12px;color:#7A8584">demo@speechmate.dev</span></span></span></div>'
            f'<div class="rail"><i class="dk"></i><i></i><i></i><i></i><i></i></div>'
            + bot_html(s.id(page + "-mate"), "mate", "right:16px;bottom:10px;width:92px;height:92px;z-index:8")
            + f'<div class="mb" id="{s.id(page + "-mb")}"></div>')


def window(s, url, url2, layers, hidden=False):
    """the browser window: chrome bar, a loading bar, then stacked page layers (only the first visible)"""
    pages = "".join(f'<div id="{s.id(pid)}" class="layer{" dk" if dark else ""}" style="opacity:{1 if i == 0 else 0};background:{NIGHT if dark else BG}">{html}</div>'
                    for i, (pid, html, dark) in enumerate(layers))
    url2s = f'<span id="{s.id("url2")}" style="position:absolute;left:0;top:0;opacity:0">{url2}</span>' if url2 else ""
    bar = (f'<div class="bar"><b></b><b></b><b></b><span style="position:relative;min-width:420px"><span id="{s.id("url")}">{url}</span>{url2s}</span></div>')
    inner = f'{bar}<div class="wc"><div class="load" id="{s.id("load")}" style="transform:scaleX(0)"></div><div class="pg">{pages}</div></div>'
    s.el("w", "win", f"left:{WX}px;top:{WY}px;width:{WW}px;height:{WH}px", inner, hidden)
    s.has_win = True
    if s.sid in STEPS:   # the badge sits on the browser bar's empty right side, above everything
        part, n, of, what, col = STEPS[s.sid]
        fg = "#fff" if col in (TEAL, PINK) else INK
        s.el("step", "abs", f"right:{1920 - WX - WW + 14}px;top:{WY + 5}px;height:36px;display:flex;align-items:center;gap:10px;padding:0 16px;"
             f"border-radius:999px;background:{col};color:{fg};font-size:20px;font-weight:600;z-index:45;white-space:nowrap;box-shadow:0 6px 18px rgba(10,26,26,.25)",
             f'<b style="font-weight:800">{part}</b><span style="opacity:.8">Step {n} of {of}</span><span>· {what}</span>', hidden=False)


def inp(s, name, x, y, w, placeholder="", text="", h=42, multiline=None):
    if multiline:
        lines = "".join(f'<span id="{s.id(name)}-{k}" class="typ" style="display:block;width:max-content">{ln}</span>' for k, ln in enumerate(multiline))
        return (f'<div id="{s.id(name)}" class="in" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;white-space:normal;line-height:1.5">{lines}</div>')
    ph = f'<span class="ph" id="{s.id(name)}-ph" style="position:absolute;left:14px;top:10px">{placeholder}</span>' if placeholder else ""
    return (f'<div id="{s.id(name)}" class="in" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">{ph}'
            f'<span id="{s.id(name)}-t" class="typ" style="position:relative">{text}</span>'
            f'<i id="{s.id(name)}-c" class="caret" style="left:14px;top:10px"></i></div>')


def type_field(s, name, t, text, d=None):
    s.tw(f'tl.set("#{s.id(name)}-ph",{{opacity:0}},{t});')
    return s.type_in(f"{name}-t", f"{name}-c", t, text, d)


def ill(x, y):
    return f'<div class="illus" style="left:{x}px;top:{y}px">ILLUSTRATIVE VALUES</div>'


# ---------------------------------------------------------------- story scenes
def s01():
    s = S("s01-mirror", lead=1.2)
    mirror_room(s, "p01b", "p01r")
    for k, (w, bg) in enumerate([("Presentation", LAVENDER), ("Job interview", MINT)]):
        s.chip(f"c{k}", w, 140, 430 + k * 90, bg, size=32)
        s.show(f"c{k}", s.at(0, 0.3 + 0.25 * k), "pop", "drop_001")
    s.talk("p01r", 0.4, s.ce[0] - 0.2)
    s.gesture("p01r", s.at(0, 0.3), 3)
    s.tw(f'tl.to("#p01b .phead",{{rotation:-3,svgOrigin:"200 380",duration:0.5,yoyo:true,repeat:5,ease:"sine.inOut"}},0.5);')
    for t in (0.9, s.at(0, 0.7), s.at(1, 0.5), s.D - 3):
        s.blink("p01r", t)
    for k in range(2):
        s.hide(f"c{k}", s.at(1))
    s.el("dim", "abs", "inset:0;background:#0A1A1A")
    s.tw(f'tl.fromTo("#{s.id("dim")}",{{opacity:0}},{{opacity:0.18,duration:0.8,ease:"power2.inOut"}},{s.at(1)});')
    s.el("tb", "bubble", f"left:130px;top:190px;background:#fff;color:{INK};font-size:40px;font-weight:600;box-shadow:0 14px 30px rgba(10,26,26,.15);border-radius:30px;padding:22px 34px",
         "…so how did I do?")
    s.show("tb", s.at(1, 0.05), "pop", "drop_002")
    s.hide("tb", s.at(1, 0.05) + 1.9)
    for k, q in enumerate(["Did my answer make sense?", "Did I sound nervous?", "What should I work on?"]):
        s.el(f"q{k}", "bubble", f"left:110px;top:{170 + k * 120}px;background:#fff;color:{INK};font-size:31px;font-weight:600;box-shadow:0 12px 26px rgba(10,26,26,.14)",
             f'{q} <span style="color:{PINK_INK};margin-left:10px">?</span>')
        s.show(f"q{k}", s.at(1, 0.05) + 2.0 + k * 0.6, "pop", "drop_001" if k != 1 else "drop_002")
        s.tw(f'tl.to("#{s.id(f"q{k}")}",{{opacity:0.35,duration:0.6}},{s.D - 1.6});')
    s.tw(f'tl.to("#p01r .phead",{{rotation:6,y:14,svgOrigin:"200 350",duration:0.9,ease:"power2.inOut"}},{s.D - 2.2});')
    s.tw(f'tl.to("#p01b .phead",{{y:16,duration:0.9,ease:"power2.inOut"}},{s.D - 2.2});')
    return s


def s02():
    s = S("s02-problem")
    vign = [("At the mirror", HOODIE, HOODIE_SHADE, "mirror"), ("At the laptop", "#C2416C", "#9E3358", "laptop"), ("With note cards", "#6A4FC9", "#553DA6", "cards")]
    for k, (cap, hc, hs, kind) in enumerate(vign):
        x = 160 + k * 545
        prop = {"mirror": '<div class="abs" style="right:34px;top:70px;width:150px;height:260px;border-radius:75px 75px 10px 10px;background:#B98F55"></div>'
                          '<div class="abs" style="right:44px;top:80px;width:130px;height:240px;border-radius:65px 65px 6px 6px;background:#D4E6E8"></div>',
                "laptop": '<div class="abs" style="left:150px;bottom:0;width:220px;height:120px;border-radius:10px 10px 0 0;background:#3B4A49"></div>'
                          '<div class="abs" style="left:160px;bottom:0;width:200px;height:104px;border-radius:6px;background:#9FC3C6"></div>',
                "cards": '<div class="abs" style="left:300px;top:250px;width:90px;height:120px;border-radius:8px;background:#fff;transform:rotate(12deg);box-shadow:0 6px 14px rgba(0,0,0,.15)"></div>'}[kind]
        px = {"mirror": 40, "laptop": 0, "cards": 120}[kind]
        s.el(f"v{k}", "card", f"left:{x}px;top:120px;width:505px;height:420px;background:#F4EADB;overflow:hidden",
             f'{prop}{svg_person(f"p02{k}", 260, 390, hoodie=hc, shade=hs, extra_style=f"left:{px}px;bottom:-40px")}'
             f'<div class="abs" style="left:24px;top:22px;padding:8px 18px;border-radius:999px;background:#fff;font-size:24px;font-weight:600">{cap}</div>')
        s.show(f"v{k}", 0.3 + k * 0.45, "rise", "card-place-1" if k % 2 == 0 else "card-place-2")
        s.talk(f"p02{k}", 0.8 + k * 0.4, 2.4)
        s.tw(f'tl.to("#p02{k} .phead",{{rotation:5,y:10,svgOrigin:"200 350",duration:0.7}},{s.at(0, 0.8)});')
    s.chip("cg", "Malaysian students &amp; fresh graduates", 160, 590, MINT, size=30)
    s.show("cg", s.at(0, 0.2), "pop")
    for n in ["v0", "v1", "v2", "cg"]:
        s.hide(n, s.at(1))
    for k, (num, label, src, bg) in enumerate([
            ("64", "of employers say poor English is why graduates fail interviews", "JobStreet Malaysia, Graduate Employability Survey 2025", OCHRE),
            ("53", "cite weak communication &amp; presentation skills", "JobStreet Malaysia × Malaysian Employers Federation, 2025", PEACH)]):
        x = 160 + k * 820
        s.el(f"k{k}", "card", f"left:{x}px;top:150px;width:780px;height:470px;background:{bg}",
             f'<div class="disp" style="position:absolute;left:52px;top:40px;font-size:190px"><span id="{s.id(f"n{k}")}">0</span>%</div>'
             f'<div style="position:absolute;left:56px;top:270px;width:660px;font-size:36px;font-weight:600;line-height:1.25">{label}</div>'
             f'<div style="position:absolute;left:56px;bottom:30px;font-size:24px;opacity:.75">{src}</div>')
        t = s.at(1, 0.05 + 0.35 * k)
        s.show(f"k{k}", t, "rise", "card-place-1" if k == 0 else "card-place-2")
        s.tw(f'tl.fromTo({{v:0}},{{v:0}},{{v:{num},duration:1.1,ease:"power2.out",onUpdate:function(){{document.getElementById("{s.id(f"n{k}")}").textContent=Math.round(this.targets()[0].v)}}}},{t + 0.1});')
        s.hide(f"k{k}", s.at(2))
    s.text("built", 'So I built <span style="color:#C21E57">SpeechMate</span>.', 0, 380, 1920, 110, 600, INK, "center")
    s.show("built", s.at(2, 0.1), "blur", "impactSoft_medium_001")
    s.html[-1] = s.html[-1].replace('class="abs disp h"', 'class="abs disp h" data-hold')
    s.hide("built", s.D)
    return s


def s03():
    s = S("s03-intro", lead=0.8)
    s.text("logo", "SpeechMate", 200, 230, 1240, 210, 600, INK)
    s.show("logo", REVEAL, "blur", "impactBell_heavy_000")   # beat-locked: vol-1 strong cue 17.02 s
    s.text("sub", "An AI speaking coach for Malaysian speakers", 210, 480, 1200, 44, 500, ACCENT_INK)
    s.show("sub", s.at(0, 0.3), "blur")
    m = s.lbot("mate", "mate", 1460, 100, 330, start="sleeping")
    s.show("mate", s.at(0, 0.2), "pop", "card-place-1")
    m.look(s.at(0, 0.8), "default"); m.hop(s.at(0, 0.85)); m.look(s.at(1, 0.2), "left"); m.look(s.at(1, 0.9), "default")
    for k, (w, bg) in enumerate([("English", MINT), ("Bahasa Malaysia", PEACH), ("Manglish", LAVENDER)]):
        s.chip(f"l{k}", w, [210, 450, 800][k], 600, bg, size=32)
        s.show(f"l{k}", s.at(1, [0.15, 0.4, 0.8][k]), "pop", "drop_001")
    t_out = s.at(2)
    for n in ["logo", "sub", "l0", "l1", "l2", "mate"]:
        s.hide(n, t_out)
    for k, (name, who, bg, fg, t) in enumerate([
            ("Mock interview", "interviewer", TEAL, "#fff", s.at(2, 0.2)),
            ("Presentation practice", "presenter", LAVENDER, INK, s.at(2, 0.45)),
            ("Daily conversation", "chat", PINK, "#fff", s.at(2, 0.7))]):
        x = 210 + k * 520
        s.el(f"f{k}", "card", f"left:{x}px;top:150px;width:460px;height:470px;background:{bg}",
             bot_html(s.id(f"fb{k}"), who, "left:70px;top:-10px;width:320px;height:320px") +
             f'<div class="disp" style="position:absolute;left:36px;bottom:40px;font-size:40px;color:{fg}">{name}</div>')
        s.show(f"f{k}", t, "rise", "card-place-1" if k != 1 else "card-place-2")
        lf = s.life(s.id(f"fb{k}")); lf.hop(t + 0.5, 30); lf.idle(t + 1.2, s.D, looks=("right", "default", "tiltl", "left", "default"), gap=(0.9, 1.8))
    s.chip("ni", "Never interrupts you while you speak", 650, 680, "#fff", ACCENT_INK, dot=PINK, size=30)
    s.show("ni", s.at(3, 0.0), "rise")
    for n in ["f0", "f1", "f2", "ni"]:
        s.hide(n, s.D)
    return s


# ---------------------------------------------------------------- the walkthrough
def login_page(s):
    orb = (f'<div style="position:absolute;left:0;top:0;width:770px;height:760px;background:{CREAM2}">'
           f'<div style="position:absolute;left:40px;top:30px;display:flex;align-items:center;gap:10px;font-weight:700;font-size:20px">'
           f'<i style="width:32px;height:32px;border-radius:9px;background:#E8467C;display:inline-block"></i>SpeechMate</div>'
           f'<div style="position:absolute;left:130px;top:330px;width:520px;height:150px;border-radius:50%;border:2px solid rgba(214,60,120,.35);transform:rotate(-14deg)"></div>'
           f'<div id="{s.id("orb")}" style="position:absolute;left:220px;top:230px;width:330px;height:330px;border-radius:46% 54% 50% 50%;'
           f'background:radial-gradient(circle at 35% 30%,#FF8FC4,#E2479B 40%,#8E46D9 75%,#6C3BC9);box-shadow:0 30px 60px rgba(142,70,217,.35)"></div>'
           f'<div style="position:absolute;left:300px;top:690px;padding:7px 16px;border-radius:8px;background:#fff;font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)">● Ready when you are</div></div>')
    form = ('<div class="h1" style="left:905px;top:190px;font-size:30px">Sign in</div>'
            '<div class="sub" style="left:905px;top:236px;font-size:15px">Welcome back. Pick up your practice where you left off.</div>'
            '<div class="lb" style="left:905px;top:296px">Email</div>' + inp(s, "em", 905, 324, 400, "you@example.com", "demo@speechmate.dev")
            + '<div class="lb" style="left:905px;top:386px">Password</div>' + inp(s, "pw", 905, 414, 400, "Your password", "••••••••")
            + f'<div id="{s.id("si")}" class="bk" style="left:905px;top:484px;width:400px;height:44px">Sign in →</div>'
            + '<div style="position:absolute;left:905px;top:548px;width:400px;height:62px;border-radius:12px;background:#F6F1E6;font-size:13px;padding:12px 16px;color:#5C6766">'
              'Testing locally? Use the demo account<br><span style="font-family:monospace;color:#0A0A0A">demo@speechmate.dev</span></div>'
            + '<div style="position:absolute;left:905px;top:636px;font-size:15px;color:#3A4645">New to SpeechMate? <b style="color:#0A0A0A">Create an account</b></div>')
    return orb + form


def home_page(s, pid):
    cards = ""
    for k, (eb, title, desc, steps, foot, bg, fg) in enumerate([
            ("EVERYDAY SPEAKING", "Daily conversation", "Chat naturally with an AI partner about everyday topics.",
             ["Pick a topic", "Talk for 3–5 minutes", "Get your voice, language, body-language and confidence report"], "Start a conversation", PINK, "#fff"),
            ("JOB READY", "Mock interview", "A realistic interview with questions curated for your role and resume.",
             ["Enter the position and your background (+ resume)", "Answer the interviewer's questions", "Get feedback on every answer, with a stronger version"], "Set up an interview", TEAL, "#fff"),
            ("SLIDES &amp; Q&amp;A", "Presentation practice", "Upload your deck; the AI studies it, coaches your delivery and runs your Q&amp;A.",
             ["Upload .pptx or .pdf: get a summary and insights", "Rehearse the talk, slide by slide", "Answer audience questions drawn from your deck"], "Upload a deck", LAVENDER, INK)]):
        st = "".join(f'<div style="display:flex;gap:10px;margin-bottom:7px"><b style="flex:none;width:20px;height:20px;border-radius:50%;background:{bg};color:{fg};font-size:12px;display:grid;place-items:center">{i + 1}</b>{x}</div>'
                     for i, x in enumerate(steps))
        cards += (f'<div id="{s.id(pid)}-fc{k}" style="position:absolute;left:{154 + k * 416}px;top:420px;width:398px;height:330px;border-radius:20px;background:{bg};color:{fg}">'
                  f'<div style="position:absolute;left:24px;top:22px;font-size:12px;font-weight:700;letter-spacing:.14em;opacity:.85">{eb}</div>'
                  f'<div style="position:absolute;left:24px;top:42px;font-size:27px;font-weight:700;letter-spacing:-.02em">{title}</div>'
                  f'<div style="position:absolute;left:24px;top:82px;width:350px;font-size:14px;line-height:1.45;opacity:.9">{desc}</div>'
                  f'<div style="position:absolute;left:18px;top:136px;width:362px;height:132px;border-radius:12px;background:#fff;color:#0A0A0A;padding:12px 14px;font-size:13px;line-height:1.35">{st}</div>'
                  f'<div style="position:absolute;left:24px;bottom:18px;font-size:15px;font-weight:600">{foot} →</div></div>')
    return (chrome(s, pid, "Home")
            + '<div style="position:absolute;left:154px;top:96px;padding:5px 12px;border-radius:999px;background:#F1E8D6;font-size:13px">Hello, Aisyah</div>'
            + '<div class="h1" style="left:154px;top:132px;width:640px;font-size:46px">What would you like to practise today?</div>'
            + '<div class="sub" style="left:154px;top:250px;width:560px">Speak with the AI, then get a clear, simple report. Nothing interrupts you while you talk.</div>'
            + f'<div style="position:absolute;left:880px;top:84px;width:470px;height:300px;border-radius:22px;background:radial-gradient(90% 90% at 50% 40%,#FFE3CF,{PEACH})">'
              '<div style="position:absolute;left:200px;top:70px;width:70px;height:70px;border-radius:50%;background:#E8467C;box-shadow:inset 0 -8px 0 rgba(0,0,0,.15)"></div>'
              '<div style="position:absolute;left:222px;top:134px;width:26px;height:110px;border-radius:10px;background:#F3EDE2"></div>'
              f'<div style="position:absolute;left:120px;top:190px;width:44px;height:44px;border-radius:50%;border:10px solid {OCHRE}"></div>'
              f'<div style="position:absolute;left:320px;top:60px;width:70px;height:46px;border-radius:12px;background:{LAVENDER}"></div></div>'
            + cards)


def s04():
    s = S("s04-login", lead=0.6)
    window(s, "speechmate.app/login", "speechmate.app/home",
           [("lg", login_page(s), False), ("hm", home_page(s, "hm"), False)], hidden=True)
    s.show("w", 0.0, "rise", "card-slide-1")
    s.tw(f'tl.to("#{s.id("orb")}",{{rotation:40,duration:{s.D},ease:"none"}},0);')
    s.cursor_at(0.6, 1100, 600)
    s.zoom("w", 0.8, 1.3, 1210, 519, 0.8)                # read the form while it's filled in
    t = s.tap(1.0, 1000, 345, "em", 0.5, ring=True)
    t = type_field(s, "em", t + 0.15, "demo@speechmate.dev", 1.1)
    s.unring("em", t + 0.2)
    t = s.tap(t + 0.2, 1000, 435, "pw", 0.4, ring=True)
    t = type_field(s, "pw", t + 0.15, "••••••••", 0.6)
    s.unring("pw", t + 0.2)
    t = s.tap(t + 0.25, 1100, 506, "si", 0.45)
    s.unzoom("w", t + 0.1)
    s.tw(f'tl.set("#{s.id("si")}",{{innerHTML:"Signing in…"}},{t + 0.05});')
    s.swap_page(t + 0.6, "lg", "hm", True)
    s.tw(f'tl.fromTo("#{s.id("hm-mate")}",{{scale:0,rotation:-30}},{{scale:1,rotation:0,duration:0.6,ease:"back.out(2)"}},{t + 1.2});')
    s.callout("mc", "Mate · your companion", 1180, 590, t + 1.6, MINT)
    s.hide("mc", s.D)
    for k in range(3):
        s.tw(f'tl.fromTo("#{s.id("hm")}-fc{k}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.5,ease:"expo.out"}},{t + 1.0 + k * 0.12});')
    return s


def s05():
    s = S("s05-home", lead=0.3)
    window(s, "speechmate.app/home", "speechmate.app/profile", [("hm", home_page(s, "hm"), False)])
    s.cursor_at(0.0, 1000, 640, fade=False)
    for k in range(3):
        g = f"#{s.id('hm')}-fc{k}"
        t = s.go(0.4 + k * 1.3, 350 + k * 416, 560, 0.55)
        s.tw(f'tl.to("{g}",{{y:-10,rotationX:4,boxShadow:"0 24px 40px rgba(10,26,26,0.22)",duration:0.3,ease:"power2.out"}},{t - 0.1});'
             f'tl.to("{g}",{{y:0,rotationX:0,boxShadow:"0 0 0 rgba(0,0,0,0)",duration:0.3,ease:"power2.out"}},{t + 1.0});')
    s.callout("c3", "3 ways to practise", 640, 380, 0.6, PEACH, hold=4.5)
    s.tap(s.D - 1.6, 32, 140, None, 0.5)   # the profile icon on the rail
    return s


def opt_tiles(s, prefix, items, x, y, w, h=46, cols=3, gap=10, sel=None):
    out = ""
    for k, (a, b) in enumerate(items):
        cx, cy = x + (k % cols) * (w + gap), y + (k // cols) * (h + gap)
        out += f'<div id="{s.id(prefix)}{k}" class="tile{" sel" if sel == k else ""}" style="left:{cx}px;top:{cy}px;width:{w}px;height:{h}px">{a}<small>{b}</small></div>'
    return out


def s06():
    s = S("s06-profile", lead=0.3)
    brief = ("They are an undergraduate student, in Computer Science. Self-rated speaking level: Intermediate. "
             "Use natural, everyday-professional language and ask for reasons and examples. Their goal: Job Interviews. "
             "Feedback style they asked for: Balance strengths and improvements, specific and kind.")
    pg = (chrome(s, "pf", "", ("default",))
          + f'<div id="{s.id("pfs")}" style="position:absolute;left:0;top:0;width:1440px;height:1300px">'
          + '<div class="h1" style="left:234px;top:84px;font-size:40px">Profile</div>'
          + '<div class="sub" style="left:234px;top:134px">Your coach uses these details to pitch questions and feedback at the right level.</div>'
          + '<div class="wcard" style="left:234px;top:180px;width:290px;height:250px">'
            '<div style="position:absolute;left:20px;top:20px;font-size:20px;font-weight:700">Aisyah Rahman</div>'
            '<div style="position:absolute;left:20px;top:50px;font-size:14px;color:#5C6766">demo@speechmate.dev</div>'
            '<div style="position:absolute;left:20px;top:150px;font-size:13px;color:#5C6766">Profile complete</div>'
            f'<div style="position:absolute;left:20px;top:176px;width:250px;height:8px;border-radius:4px;background:#EEE8DC"><div id="{s.id("pc")}" style="width:100%;height:100%;border-radius:4px;background:{TEAL_INK};transform-origin:0 50%"></div></div>'
            f'<div style="position:absolute;right:20px;top:150px;font-size:13px;font-weight:700"><span id="{s.id("pcn")}">40</span>%</div></div>'
          + '<div class="wcard" style="left:546px;top:180px;width:720px;height:1060px">'
          + '<div class="lb" style="left:20px;top:20px">Level of study</div>'
          + opt_tiles(s, "st", [("Secondary school", "SPM level"), ("Pre-university", "Foundation, matriculation, diploma"), ("Undergraduate", "Degree"),
                                ("Postgraduate", "Master's, PhD"), ("Working professional", "In a job")], 20, 48, 220, 52)
          + '<div class="lb" style="left:20px;top:172px">Field of study or work</div>' + inp(s, "fld", 20, 200, 680, "e.g. Computer Science, Nursing, Marketing", "Computer Science")
          + '<div class="lb" style="left:20px;top:262px">Communication goal</div>'
          + "".join(f'<div id="{s.id("cg")}{k}" class="pill" style="left:{20 + sum(len(x) * 8 + 40 for x in ["Academic Presentations", "Job Interviews", "Public Speaking", "Business Communication"][:k])}px;top:292px">{g}</div>'
                    for k, g in enumerate(["Academic Presentations", "Job Interviews", "Public Speaking", "Business Communication"]))
          + '<div class="lb" style="left:20px;top:350px">Skill level</div>'
          + opt_tiles(s, "sk", [("Beginner", "Short, simple questions, one idea at a time"), ("Intermediate", "Everyday-professional questions that ask for reasons"),
                                ("Advanced", "Probing, multi-part questions")], 20, 378, 220, 64)
          + '<div class="lb" style="left:20px;top:466px">How should feedback sound?</div>'
          + opt_tiles(s, "fb", [("Encouraging", "Lead with what went well"), ("Balanced", "Strengths and fixes"), ("Direct", "What to fix first")], 20, 494, 220, 52)
          + f'<div style="position:absolute;left:20px;top:576px;width:680px;height:170px;border-radius:14px;background:#F1ECFD;padding:16px 18px">'
            f'<div style="font-size:15px;font-weight:700;margin-bottom:8px">How your coach uses this</div>'
            f'<div id="{s.id("brief")}" style="font-size:14px;line-height:1.55;color:#2A2A2A;clip-path:inset(0 0 100% 0)"><b>About the learner:</b> {brief}</div></div>'
          + f'<div id="{s.id("save")}" class="bk" style="left:20px;top:770px;width:160px;height:44px">Save profile</div>'
          + '</div></div>')
    window(s, "speechmate.app/profile", None, [("pf", pg, False)])
    s.cursor_at(0.0, 30, 140, fade=False)
    s.zoom("w", 0.3, 1.25, 990, 420, 0.8)
    t = s.tap(0.5, 1136, 254, "st2", 0.5, sel="tile")
    t = s.tap(t + 0.3, 886, 401, "fld", 0.4, ring=True)
    t = type_field(s, "fld", t + 0.1, "Computer Science", 0.8)
    s.unring("fld", t + 0.1)
    t = s.tap(t + 0.2, 842, 488, "cg1", 0.45, sel="pill")
    s.tw(f'tl.fromTo("#{s.id("pc")}",{{scaleX:0.4}},{{scaleX:1,duration:0.6}},{t});')
    s.tw(f'tl.fromTo({{v:40}},{{v:40}},{{v:100,duration:1.2,ease:"power2.out",onUpdate:function(){{document.getElementById("{s.id("pcn")}").textContent=Math.round(this.targets()[0].v)}}}},{t});')
    s.unzoom("w", t + 0.2)
    s.scroll("pfs", t + 0.3, 330, 0.8)
    t = s.tap(t + 1.1, 906, 260, "sk1", 0.45, sel="tile")   # Intermediate (scrolled)
    t = s.tap(t + 0.3, 906, 370, "fb1", 0.4, sel="tile")    # Balanced
    s.tw(f'tl.to("#{s.id("brief")}",{{clipPath:"inset(0 0 0% 0)",duration:1.6,ease:"steps(6)"}},{t + 0.2});')
    t = s.tap(t + 2.0, 646, 972 - 330, "save", 0.5)
    s.mate_say("pf", "Profile saved. I'll pitch things at your level.", t + 0.3, 2.4)
    return s


def form_page(s):
    lv = [("Internship", ""), ("Fresh graduate", ""), ("Junior (1–3 yrs)", ""), ("Mid-level", ""), ("Senior", "")]
    it = [("Behavioural", "Teamwork, challenges, motivation"), ("Technical", "Role-specific problem solving"), ("Mixed", "A bit of both, like most interviews")]
    return (chrome(s, "fm", "Interview")
            + f'<div id="{s.id("fms")}" style="position:absolute;left:0;top:0;width:1440px;height:1400px">'
            + f'<div class="eb" style="left:200px;top:84px;color:{TEAL_INK}">MOCK INTERVIEW</div>'
            + '<div class="h1" style="left:200px;top:104px;font-size:38px">Tell us about the interview</div>'
            + '<div class="sub" style="left:200px;top:154px;width:600px">The interviewer prepares questions for this role, your level and your background. Add your resume and they\'ll ask about your real experience.</div>'
            + f'<div style="position:absolute;left:960px;top:84px;width:300px;height:170px;border-radius:20px;background:radial-gradient(90% 90% at 50% 40%,#F1ECFD,{LAVENDER})">'
              '<div style="position:absolute;left:105px;top:60px;width:90px;height:64px;border-radius:12px;background:#3B4A49"></div>'
              '<div style="position:absolute;left:132px;top:46px;width:36px;height:18px;border-radius:6px;border:5px solid #3B4A49;border-bottom:none"></div></div>'
            + '<div class="wcard" style="left:200px;top:270px;width:640px;height:560px">'
            + '<div style="position:absolute;left:20px;top:18px;font-size:16px;font-weight:700">1 · The role</div>'
            + '<div class="lb" style="left:20px;top:52px">Position you applied for</div>' + inp(s, "pos", 20, 78, 290, "e.g. Data Analyst", "Graduate Data Analyst")
            + '<div class="lb" style="left:330px;top:52px">Company<em>optional</em></div>' + inp(s, "co", 330, 78, 290, "e.g. Maybank", "Nusantara Retail Group")
            + '<div class="lb" style="left:20px;top:136px">Level</div>' + opt_tiles(s, "lv", lv, 20, 162, 140, 38, cols=4, sel=1)
            + '<div class="lb" style="left:20px;top:262px">Interview type</div>' + opt_tiles(s, "it", it, 20, 288, 190, 56, sel=2)
            + '<div class="lb" style="left:20px;top:362px">Job description<em>optional</em></div>'
            + inp(s, "jd", 20, 388, 600, h=96, multiline=["Analyse sales and customer data, build dashboards,", "present insights to non-technical managers. SQL, Python."])
            + '</div>'
            + '<div class="wcard" style="left:200px;top:850px;width:640px;height:250px">'
            + '<div style="position:absolute;left:20px;top:18px;font-size:16px;font-weight:700">2 · About you</div>'
            + '<div class="lb" style="left:20px;top:52px">Your background</div>'
            + inp(s, "bg", 20, 78, 600, h=72, multiline=["Final-year Computer Science student. Internship:", "weekly sales dashboards, data cleaning in Python."])
            + f'<div id="{s.id("up")}" class="wt" style="left:20px;top:170px;width:200px;height:42px">⬆ Upload resume</div>'
            + f'<div id="{s.id("rz")}" style="position:absolute;left:236px;top:176px;padding:7px 14px;border-radius:10px;background:{MINT};font-size:14px;font-weight:600;opacity:0"><i style=display:inline-block;width:14px;height:18px;border-radius:3px;background:#C2416C;vertical-align:-3px;margin-right:6px></i>resume.pdf · read</div>'
            + '</div>'
            + '<div class="wcard" style="left:860px;top:270px;width:400px;height:170px">'
            + '<div style="position:absolute;left:20px;top:18px;font-size:16px;font-weight:700">3 · Your questions</div>'
            + '<div style="position:absolute;left:20px;top:48px;width:360px;font-size:14px;line-height:1.5;color:#3A4645">Preview the questions before you start, or start straight away and be surprised.</div>'
            + f'<div id="{s.id("pv")}" class="wt" style="left:20px;top:108px;width:360px;height:42px">Preview questions</div></div>'
            + f'<div id="{s.id("start")}" class="bk" style="left:860px;top:458px;width:400px;height:46px;background:#9AA3A2">Start interview</div>'
            + '</div>')


def s07():
    s = S("s07-form", lead=0.3)
    window(s, "speechmate.app/profile", "speechmate.app/interview",
           [("pf0", chrome(s, "pf0", "") + '<div class="h1" style="left:234px;top:84px;font-size:40px">Profile</div>', False), ("fm", form_page(s), False)])
    s.cursor_at(0.0, 646, 642, fade=False)
    t = s.tap(0.3, 615, 35, None, 0.6)                 # nav: Interview
    s.swap_page(t + 0.05, "pf0", "fm", True)
    s.zoom("w", t + 0.6, 1.3, 572, 470, 0.8)
    t = s.tap(t + 0.9, 360, 369, "pos", 0.45, ring=True)
    t = type_field(s, "pos", t + 0.1, "Graduate Data Analyst", 1.0)
    s.unring("pos", t + 0.1)
    t = s.tap(t + 0.2, 670, 369, "co", 0.4, ring=True)
    t = type_field(s, "co", t + 0.1, "Nusantara Retail Group", 1.0)
    s.unring("co", t + 0.1)
    s.tw(f'tl.to("#{s.id("start")}",{{backgroundColor:"#0A0A0A",duration:0.3}},{t});')
    s.callout("cd", "Fresh graduate · Mixed (defaults)", 220, 560, t + 0.1, "#fff", hold=1.6)
    t = s.tap(t + 0.4, 420, 700, "jd", 0.45, ring=True)
    for k in range(2):
        s.typ(f"jd-{k}", t + 0.1 + k * 0.7, 0.65, keys=k == 0)
    t += 1.6
    s.unring("jd", t)
    s.unzoom("w", t - 0.1)
    s.scroll("fms", t, 470, 0.8)
    for k in range(2):
        s.typ(f"bg-{k}", t + 0.9 + k * 0.6, 0.55, keys=k == 0)
    t = s.tap(t + 2.1, 320, 571, "up", 0.45)
    s.mate_say("fm", "Reading your resume…", t + 0.15, 0.9)
    s.life(s.id("fm-mate")).state(t + 0.15, 0.9, "working")
    s.mate_say("fm", "Got your resume. I'll use it for the questions.", t + 1.2, 2.2)
    s.tw(f'tl.to("#{s.id("rz")}",{{opacity:1,duration:0.3}},{t + 1.1});')
    s.sfx.append(("drop_001", t + 0.4))
    s.scroll("fms", t + 0.9, 0, 0.8)
    t = s.tap(t + 1.8, 1060, 399, "pv", 0.5)
    s.tw(f'tl.set("#{s.id("pv")}",{{innerHTML:"<span class=\\"dots\\"><i></i><i></i><i></i></span> Preparing questions…"}},{t + 0.05});')
    return s


def s08():
    s = S("s08-plan", lead=0.3)
    qs = PLAN["interview"]
    tags = {1: ("from your resume", MINT), 2: ("from the job description", PEACH), 3: ("from your project", LAVENDER)}
    rows = ""
    for k, q in enumerate(qs[:5]):
        tg = tags.get(k)
        tag = (f'<span id="{s.id(f"tg{k}")}" style="position:absolute;right:16px;top:12px;padding:4px 12px;border-radius:999px;background:{tg[1]};font-size:13px;font-weight:700;opacity:0">{tg[0]}</span>') if tg else ""
        rows += (f'<div id="{s.id(f"q{k}")}" style="position:absolute;left:20px;top:{62 + k * 100}px;width:880px;height:88px;border-radius:12px;background:#FBF8F1;border:1px solid rgba(10,26,26,.07);opacity:0">'
                 f'<div style="position:absolute;left:16px;top:12px;font-size:12px;font-weight:700;letter-spacing:.1em;color:{TEAL_INK}">QUESTION {k + 1}</div>{tag}'
                 f'<div style="position:absolute;left:16px;top:32px;width:{650 if tg else 840}px;font-size:14px;line-height:1.4;max-height:40px;overflow:hidden">{q["question"]}</div></div>')
    plan = (chrome(s, "pl", "Interview")
            + f'<div class="eb" style="left:200px;top:84px;color:{TEAL_INK}">MOCK INTERVIEW · YOUR QUESTIONS</div>'
            + '<div class="h1" style="left:200px;top:104px;font-size:34px">Graduate Data Analyst · Nusantara Retail Group</div>'
            + f'<div id="{s.id("pcard")}" class="wcard" data-layout-allow-overlap style="left:200px;top:160px;width:920px;height:590px">'
            + '<div style="position:absolute;left:20px;top:18px;font-size:16px;font-weight:700">3 · Your questions <span style="font-weight:400;color:#7A8584">· 7, curated for this role</span></div>'
            + rows + '</div>'
            + f'<div id="{s.id("st")}" class="bk" style="left:1140px;top:160px;width:220px;height:46px">Start interview</div>')
    window(s, "speechmate.app/interview", None, [("pl", plan, False)])
    s.cursor_at(0.0, 1060, 399, fade=False)
    s.go(0.2, 1250, 300, 0.6)
    for k in range(5):
        s.tw(f'tl.fromTo("#{s.id(f"q{k}")}",{{opacity:0,y:14}},{{opacity:1,y:0,duration:0.4,ease:"expo.out"}},{0.3 + k * 0.16});')
    s.sfx.append(("card-place-1", 0.3))
    for i, k in enumerate((1, 2, 3)):
        t = s.at(0, 0.35) + i * 0.7
        s.tw(f'tl.fromTo("#{s.id(f"tg{k}")}",{{opacity:0,scale:0.6}},{{opacity:1,scale:1,duration:0.4,ease:"back.out(2)"}},{t});')
        s.sfx.append(("drop_001", t))
    s.zoom("w", s.at(0, 0.3), 1.22, 760, 330, 0.9)
    s.unzoom("w", s.D - 2.4)
    s.tap(s.D - 1.5, 1250, 183, "st", 0.6)
    return s


def session_page(s, pid, partner, who, question, mode_color, header, follow=None):
    turns = [("ai", f"{partner} is talking", "#1E2E2D"), ("you", "Your turn: speak now", mode_color), ("listen", "Listening… keep going", mode_color),
             ("tr", "Got it. Writing down what you said…", "#2A3A39"), ("think", f"{partner} is thinking…", "#2A3A39")]
    tb = "".join(f'<div id="{s.id(pid)}-t{k}" class="turn" style="left:40px;top:560px;background:{bg};color:#fff">'
                 f'<span style="width:10px;height:10px;border-radius:50%;background:#fff"></span>{txt}</div>' for k, txt, bg in turns)
    bars = "".join(f'<i id="{s.id(pid)}-b{k}"></i>' for k in range(7))
    return (f'<div style="position:absolute;left:0;right:0;top:0;height:58px;display:flex;align-items:center;gap:16px;padding:0 40px;border-bottom:1px solid rgba(255,255,255,.08);font-size:15px">'
            f'<span style="opacity:.7">← Leave</span><span style="padding:5px 14px;border-radius:999px;background:{mode_color};font-weight:600">{header}</span>'
            f'<span style="margin-left:auto;font-family:monospace;font-size:16px">● <span id="{s.id(pid)}-clk">00:00</span></span>'
            f'<span id="{s.id(pid)}-end" style="padding:8px 18px;border-radius:10px;background:#E5484D;font-weight:700">End</span></div>'
            f'<div style="position:absolute;left:40px;top:82px;width:860px;height:460px;border-radius:18px;overflow:hidden">{camera_view(s, s.id(pid) + "-me", 860, 460)}</div>'
            f'<div style="position:absolute;left:56px;top:96px;padding:5px 12px;border-radius:999px;background:rgba(10,26,26,.7);font-size:13px;color:#fff">Tracking · Face · Pose</div>'
            f'<div class="bars" style="left:56px;top:506px">{bars}</div>'
            + tb
            + f'<div class="dp" style="left:930px;top:82px;width:470px;height:250px">'
            + bot_html(s.id(pid) + "-bot", who, "left:135px;top:4px;width:200px;height:200px") +
            f'<div style="position:absolute;left:0;right:0;bottom:16px;text-align:center;font-size:17px;font-weight:600">{partner}</div></div>'
            f'<div class="dp" style="left:930px;top:350px;width:470px;height:270px">'
            f'<div style="position:absolute;left:20px;top:16px;font-size:12px;font-weight:700;letter-spacing:.12em;opacity:.6">CURRENT QUESTION</div>'
            f'<div id="{s.id(pid)}-q" style="position:absolute;left:20px;top:42px;right:20px;font-size:16px;line-height:1.5">{question}</div>'
            f'<div id="{s.id(pid)}-q2" style="position:absolute;left:20px;top:42px;right:20px;font-size:17px;line-height:1.5;font-weight:600;color:{MINT};opacity:0">{follow or ""}</div></div>'
            f'<div id="{s.id(pid)}-an" style="position:absolute;inset:0;background:rgba(10,26,26,.82);opacity:0;display:grid;place-items:center">'
            f'<div style="text-align:center"><div style="font-size:26px;font-weight:700">Analysing your session…</div>'
            f'<div style="margin-top:10px;font-size:15px;opacity:.7">Voice · language · body language · confidence</div></div></div>')


def partner_life(s, pid):
    lf = s.life(s.id(pid) + "-bot")
    if not lf.pending:
        lf.idle(0.3, s.D, looks=("tiltl", "default", "left", "default", "tiltr", "default"), gap=(1.3, 2.6))
    return lf


def turn(s, pid, which, t):
    for k in ("ai", "you", "listen", "tr", "think"):
        s.tw(f'tl.set("#{s.id(pid)}-t{k}",{{opacity:{1 if k == which else 0}}},{t});')


def bot_talk(s, pid, on, t):
    lf = partner_life(s, pid)
    if on:
        s.talk_open[pid] = t
    elif pid in s.talk_open:
        t0 = s.talk_open.pop(pid)
        lf.talk(t0, round(t - t0, 3))


def speak(s, pid, t, d):
    """the learner answers: mouth moves, the mic meter jumps; the partner turns to listen and nods"""
    s.talk(s.id(pid) + "-me", t, d)
    if (s.id(pid) + "-bot") in s.lives:
        lf = s.lives[s.id(pid) + "-bot"]
        lf.look(t + 0.1, "left"); lf.nod(round(t + d * 0.45, 3)); lf.look(round(t + d, 3), "default")
    for k in range(7):
        n = max(1, int(d / 0.24))
        s.tw(f'tl.to("#{s.id(pid)}-b{k}",{{height:{[14, 22, 18, 26, 16, 20, 12][k]},duration:0.12,yoyo:true,repeat:{2 * n - 1},ease:"sine.inOut",delay:{k * 0.03}}},{t});')


def clock(s, pid, t0, t1, a, b):
    s.tw(f'tl.fromTo({{v:{a}}},{{v:{a}}},{{v:{b},duration:{round(t1 - t0, 2)},ease:"none",onUpdate:function(){{var v=Math.round(this.targets()[0].v);'
         f'document.getElementById("{s.id(pid)}-clk").textContent=String(Math.floor(v/60)).padStart(2,"0")+":"+String(v%60).padStart(2,"0")}}}},{t0});')


def s09():
    s = S("s09-live", lead=0.5)
    qs = PLAN["interview"]
    window(s, "speechmate.app/interview", "speechmate.app/session",
           [("pl0", chrome(s, "pl0", "Interview"), False),
            ("lv", session_page(s, "lv", "Alex", "interviewer", qs[1]["question"], TEAL, "Mock interview · Graduate Data Analyst",
                                follow="Follow-up: could you give one specific example from your internship?"), True)])
    s.cursor_at(0.0, 1250, 183, fade=False)
    s.swap_page(0.05, "pl0", "lv", True)
    s.tw(f'tl.to("#{s.id("cur")}",{{opacity:0,duration:0.2}},0.3);')
    clock(s, "lv", 0.4, s.D, 74, 74 + round(s.D))
    turn(s, "lv", "ai", 0.5); bot_talk(s, "lv", True, 0.5)
    s.callout("ca", "Question 2 of 7 · from your resume", 860, 330, 0.9, MINT, hold=2.6)
    t = s.at(0, 0.75)
    turn(s, "lv", "you", t); bot_talk(s, "lv", False, t)
    turn(s, "lv", "listen", t + 0.6); speak(s, "lv", t + 0.6, 1.8)
    turn(s, "lv", "tr", t + 2.5)
    turn(s, "lv", "think", t + 3.2)
    t2 = s.at(1, 0.25)
    turn(s, "lv", "ai", t2); bot_talk(s, "lv", True, t2)
    s.tw(f'tl.to("#{s.id("lv")}-q",{{opacity:0,duration:0.2}},{t2});tl.to("#{s.id("lv")}-q2",{{opacity:1,duration:0.3}},{t2 + 0.15});')
    s.sfx.append(("drop_002", t2 + 0.15))
    s.callout("cf", "Short answer → one follow-up", 860, 300, t2 + 0.2, PEACH, hold=2.8)
    t3 = t2 + 3.0
    turn(s, "lv", "you", t3); bot_talk(s, "lv", False, t3)
    turn(s, "lv", "listen", t3 + 0.5); speak(s, "lv", t3 + 0.5, 2.6)
    s.blink(s.id("lv") + "-me", 1.5); s.blink(s.id("lv") + "-me", t3 + 0.2)
    s.cursor_at(t3 + 3.0, 1250, 380)
    t = s.tap(t3 + 3.4, 1347, 29, "lv-end", 0.6)
    s.tw(f'tl.to("#{s.id("lv")}-an",{{opacity:1,duration:0.3}},{t + 0.2});')
    return s


def results_page(s, pid):
    q3 = PLAN["interview"][2]["question"]
    pills = [("Voice &amp; delivery", 74, OCHRE), ("Language &amp; clarity", 70, MINT), ("Body language", 66, PEACH), ("Confidence &amp; presence", 68, LAVENDER)]
    pc = "".join(f'<div class="wcard" style="left:{260 + k * 236}px;top:450px;width:222px;height:120px">'
                 f'<div style="position:absolute;left:16px;top:14px;font-size:14px;font-weight:700">{n}</div>'
                 f'<div style="position:absolute;left:16px;top:40px;font-size:32px;font-weight:700;color:{TEAL_INK}">{v}</div>'
                 f'<div style="position:absolute;left:16px;right:16px;top:90px;height:6px;border-radius:3px;background:#EEE8DC">'
                 f'<div id="{s.id(pid)}-pb{k}" style="width:{v}%;height:100%;border-radius:3px;background:{c};transform-origin:0 50%"></div></div></div>'
                 for k, (n, v, c) in enumerate(pills))
    dots = lambda n: "".join(f'<i style="display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:3px;background:{"#0A0A0A" if i < n else "#D9D2C3"}"></i>' for i in range(5))
    return (chrome(s, pid, "Progress")
            + f'<div id="{s.id(pid)}-sc" data-layout-allow-overlap style="position:absolute;left:0;top:0;width:1440px;height:1400px">'
            + '<div style="position:absolute;left:260px;top:84px;font-size:14px;color:#5C6766">← All sessions</div>'
            + '<div class="h1" style="left:260px;top:106px;font-size:36px">Mock interview</div>'
            + '<div style="position:absolute;left:260px;top:152px;font-size:14px;color:#5C6766">1:32 · 10 Nov 2026 · Graduate Data Analyst</div>'
            + '<div class="bk" style="left:1040px;top:100px;width:170px;height:44px">↻ Practise again</div>'
            + ill(1040, 160)
            + '<div class="wcard" style="left:260px;top:186px;width:950px;height:110px">'
              '<div style="position:absolute;left:20px;top:16px;font-size:12px;font-weight:700;letter-spacing:.12em;color:#5C6766">OVERALL</div>'
              f'<div style="position:absolute;left:20px;top:34px;font-size:46px;font-weight:700"><span id="{s.id(pid)}-ov">0</span></div>'
              '<div style="position:absolute;left:180px;top:30px;width:740px;font-size:15px;line-height:1.5">Biggest opportunity: finish answers with the result. You gave relevant examples, but most answers stopped before saying what changed.</div></div>'
            + f'<div style="position:absolute;left:260px;top:312px;width:950px;height:124px;border-radius:18px;background:{PEACH}">'
              '<div style="position:absolute;left:20px;top:14px;font-size:12px;font-weight:700;letter-spacing:.12em">YOUR #1 FOCUS FOR NEXT TIME</div>'
              '<div style="position:absolute;left:20px;top:34px;font-size:24px;font-weight:700">Finish every answer with the result</div>'
              f'<div id="{s.id(pid)}-go" class="bk" style="left:20px;top:72px;width:190px;height:40px">▶ Practise this now</div>'
              '<div style="position:absolute;left:230px;top:82px;font-size:14px;font-weight:600">Next time, aim for: a result in 4 of 6 answers</div></div>'
            + pc
            + '<div class="wcard" style="left:260px;top:590px;width:950px;height:330px">'
              '<div style="position:absolute;left:20px;top:16px;font-size:16px;font-weight:700">Your answers</div>'
              f'<div style="position:absolute;left:20px;top:46px;width:900px;font-size:14px;font-weight:600">Q3. {q3[:120]}…</div>'
              f'<div style="position:absolute;left:20px;top:92px;font-size:13px">Answered the question {dots(4)} &nbsp; Easy to follow {dots(3)} &nbsp; Real details {dots(3)}</div>'
              f'<div style="position:absolute;left:20px;top:122px;font-size:14px"><b style="color:{TEAL_INK}">✓ Good:</b> a clear, real example from your internship.</div>'
              f'<div style="position:absolute;left:20px;top:148px;font-size:14px"><b style="color:{PINK_INK}">→ Next time:</b> say what the manager decided after your explanation.</div>'
              f'<div id="{s.id(pid)}-ss" style="position:absolute;left:20px;top:180px;font-size:14px;font-weight:700">⌄ See a stronger version of your answer</div>'
              f'<div id="{s.id(pid)}-sv" style="position:absolute;left:20px;top:208px;width:900px;height:100px;border-radius:12px;background:#E3F3EE;padding:12px 16px;font-size:14px;line-height:1.5;opacity:0">'
              '“In my internship I built weekly sales dashboards. When a store manager asked why sales dipped, I showed one chart, explained the cause in plain words, '
              'and suggested what to check next. Built only from what you said.”</div></div>'
            + '</div>')


def s10():
    s = S("s10-results", lead=0.6)
    window(s, "speechmate.app/session", "speechmate.app/results", [("an0", '<div style="position:absolute;inset:0;background:#0A1A1A"></div>', True), ("rs", results_page(s, "rs"), False)])
    s.swap_page(0.1, "an0", "rs", True)
    s.mate_say("rs", "Your results are ready!", 0.9, 2.0)
    s.tw(f'tl.fromTo({{v:0}},{{v:0}},{{v:71,duration:1.2,ease:"power2.out",onUpdate:function(){{document.getElementById("{s.id("rs")}-ov").textContent=Math.round(this.targets()[0].v)}}}},0.6);')
    for k in range(4):
        s.tw(f'tl.fromTo("#{s.id("rs")}-pb{k}",{{scaleX:0}},{{scaleX:1,duration:0.8,ease:"power2.out"}},{s.at(0, 0.2) + k * 0.15});')
    s.callout("cp", "Four pillars", 1080, 430, s.at(0, 0.25), OCHRE, hold=2.0)
    s.cursor_at(s.at(0, 0.5), 900, 500)
    s.scroll("rs-sc", s.at(0, 0.7), 330, 0.9)
    t = s.tap(s.at(0, 0.7) + 1.4, 410, 447, "rs-ss", 0.5)
    s.tw(f'tl.to("#{s.id("rs")}-sv",{{opacity:1,duration:0.4}},{t + 0.1});')
    s.sfx.append(("drop_002", t + 0.1))
    s.zoom("w", t + 0.3, 1.18, 700, 520, 0.8)
    s.unzoom("w", s.at(1, 0.3))
    s.scroll("rs-sc", s.at(1, 0.3), 0, 0.8)
    t = s.tap(s.at(1, 0.3) + 1.0, 360, 404, "rs-go", 0.5)
    s.callout("cd", "Drills · Practise this now", 600, 390, t + 0.1, PINK, hold=2.0, fg="#fff")
    return s


def deck_page(s, pid):
    d = PLAN["deck"]
    bul = [["Why time management matters for", "students and professionals", "Simple habits you can start today"],
           ["Write tomorrow's top three tasks the night before", "Use the Eisenhower matrix: urgent vs. important", "Block focused time on your calendar"],
           ["Silence notifications during deep work", "Work in 25-minute sprints with short breaks", "Review your week every Friday"]]
    sl = "".join(f'<div id="{s.id(pid)}-kp{k}" class="wcard" style="left:{200 + k * 352}px;top:470px;width:336px;height:262px;opacity:0">'
                 f'<div style="position:absolute;left:14px;top:12px;width:308px;height:150px;border-radius:10px;background:#FBF8F1;border:1px solid rgba(10,26,26,.06)">'
                 f'<div style="position:absolute;left:14px;top:12px;font-size:14px;font-weight:700">{sv["title"]}</div>'
                 + "".join(f'<div style="position:absolute;left:14px;top:{44 + i * 22}px;font-size:11px;color:#3A4645">• {b}</div>' for i, b in enumerate(bul[k]))
                 + f'</div><div style="position:absolute;left:14px;top:174px;width:308px;font-size:13px;line-height:1.45"><b>{k + 1}.</b> {sv["key_point"]}</div></div>'
                 for k, sv in enumerate(d["slides"]))
    return (chrome(s, pid, "Presentation")
            + '<div style="position:absolute;left:200px;top:96px;font-size:18px">←</div>'
            + '<div class="h1" style="left:232px;top:84px;font-size:34px">Time management</div>'
            + '<div style="position:absolute;left:232px;top:128px;font-size:14px;color:#5C6766">3 slides · aim for about 2.2–4.5 min</div>'
            + f'<div style="position:absolute;left:200px;top:160px;width:520px;height:150px;border-radius:18px;background:{LAVENDER}">'
              f'<div style="position:absolute;left:20px;top:16px;font-size:12px;font-weight:700;letter-spacing:.12em">STEP 2</div>'
              '<div style="position:absolute;left:20px;top:34px;font-size:24px;font-weight:700">Present it</div>'
              '<div style="position:absolute;left:20px;top:68px;width:480px;font-size:13px;line-height:1.4">Your slides fill the screen and you move through them, talking as you would to a real audience.</div>'
              f'<div id="{s.id(pid)}-pr" class="bk" style="left:20px;top:104px;width:480px;height:36px;font-size:15px">▭ Present it</div></div>'
            + f'<div style="position:absolute;left:736px;top:160px;width:520px;height:150px;border-radius:18px;background:{TEAL};color:#fff">'
              '<div style="position:absolute;left:20px;top:16px;font-size:12px;font-weight:700;letter-spacing:.12em">STEP 3</div>'
              '<div style="position:absolute;left:20px;top:34px;font-size:24px;font-weight:700">Rehearse the Q&amp;A</div>'
              '<div style="position:absolute;left:20px;top:68px;width:480px;font-size:13px;line-height:1.4;opacity:.9">A moderator asks the questions this audience is likely to ask about your deck.</div>'
              '<div class="wt" style="left:20px;top:104px;width:480px;height:36px;font-size:15px">Start Q&amp;A</div></div>'
            + f'<div id="{s.id(pid)}-mm" class="wcard" style="left:200px;top:326px;width:1056px;height:120px;opacity:0">'
              f'<div style="position:absolute;left:18px;top:14px;font-size:12px;font-weight:700;letter-spacing:.12em;color:{LAV_INK}">THE AI\'S READING OF YOUR DECK</div>'
              f'<div style="position:absolute;left:18px;top:36px;width:1010px;font-size:14px;line-height:1.5">{d["summary"]} <b>Main message:</b> {d["main_message"]}</div>'
              f'<div style="position:absolute;left:18px;top:88px;font-size:13px;color:{LAV_INK};font-weight:600">Structure: Introduction · slide 1 → Actionable Strategies · slides 2–3</div></div>'
            + '<div style="position:absolute;left:200px;top:452px;font-size:15px;font-weight:700">Step 1 · What each slide should say</div>'
            + sl)


def upload_page(s, pid):
    return (chrome(s, pid, "Presentation")
            + f'<div class="eb" style="left:234px;top:84px;color:{LAV_INK}">PRESENTATION PRACTICE</div>'
            + '<div class="h1" style="left:234px;top:104px;font-size:38px">Practise your talk and your Q&amp;A</div>'
            + '<div class="sub" style="left:234px;top:152px;width:620px;font-size:14px"><b>1.</b> Upload your slides. The AI reads them: summary, structure and each slide\'s key point. '
              '<b>2.</b> Present it on camera. <b>3.</b> Rehearse the Q&amp;A.</div>'
            + '<div class="wcard" style="left:234px;top:226px;width:1050px;height:340px">'
              '<div style="position:absolute;left:24px;top:20px;font-size:16px;font-weight:700">New presentation</div>'
              f'<div id="{s.id(pid)}-dz" style="position:absolute;left:24px;top:54px;width:1000px;height:120px;border-radius:14px;border:2px dashed rgba(10,26,26,.2);background:#FCFAF5;text-align:center;font-size:15px;font-weight:600;padding-top:44px">'
              f'<span id="{s.id(pid)}-dzt">⬆ Drop a .pptx or .pdf here, or click to browse</span></div>'
              '<div class="lb" style="left:24px;top:192px">Audience and purpose<em>optional</em></div>'
              + inp(s, f"{pid}-au", 24, 220, 1000, "e.g. First-year students, non-specialist audience, 5-minute talk", "First-year students, 3-minute talk")
              + f'<div id="{s.id(pid)}-ub" class="bk" style="left:24px;top:280px;width:200px;height:42px;background:#F0B79B">→ Upload and prepare</div>'
              + f'<div id="{s.id(pid)}-ph" style="position:absolute;left:250px;top:290px;font-size:14px;font-weight:600;color:{LAV_INK};opacity:0">'
              f'<span id="{s.id(pid)}-p1">Uploading…</span></div>'
              + f'<div style="position:absolute;left:250px;top:314px;width:420px;height:6px;border-radius:3px;background:#EEE8F9"><div id="{s.id(pid)}-pb" style="width:100%;height:100%;border-radius:3px;background:{LAV_INK};transform-origin:0 50%"></div></div>'
              '</div>')


def s11():
    s = S("s11-deck", lead=0.3)
    window(s, "speechmate.app/results", "speechmate.app/presentations",
           [("rs0", chrome(s, "rs0", "Progress"), False), ("up", upload_page(s, "up"), False), ("dk", deck_page(s, "dk"), False)])
    s.cursor_at(0.0, 360, 404, fade=False)
    t = s.tap(0.2, 733, 35, None, 0.6)
    s.swap_page(t, "rs0", "up", True)
    # the file is dragged in from the desktop
    X, Y = s.P(780, 340)
    s.el("file", "abs", f"left:{X + 520}px;top:{Y + 380}px;padding:12px 18px;border-radius:12px;background:#fff;font-size:20px;font-weight:600;box-shadow:0 14px 30px rgba(10,26,26,.22);z-index:35",
         "<i style=display:inline-block;width:14px;height:18px;border-radius:3px;background:#E8823A;vertical-align:-3px;margin-right:6px></i>Time management.pptx")
    s.show("file", t + 0.6, "pop")
    s.tw(f'tl.to("#{s.id("cur")}",{{x:{X + 540},y:{Y + 400},duration:0.4}},{t + 0.6});')
    s.tw(f'tl.to(["#{s.id("file")}"],{{x:-520,y:-380,duration:0.9,ease:"power2.inOut"}},{t + 1.1});tl.to("#{s.id("cur")}",{{x:{X + 20},y:{Y + 20},duration:0.9,ease:"power2.inOut"}},{t + 1.1});')
    s.tw(f'tl.to("#{s.id("up")}-dz",{{borderColor:"#4B2FA8",backgroundColor:"#F1ECFD",duration:0.2}},{t + 1.6});')
    s.tw(f'tl.to("#{s.id("file")}",{{opacity:0,scale:0.6,duration:0.2}},{t + 2.0});tl.set("#{s.id("up")}-dzt",{{innerHTML:"<i style=display:inline-block;width:14px;height:18px;border-radius:3px;background:#E8823A;vertical-align:-3px;margin-right:6px></i>Time management.pptx · 3 slides"}},{t + 2.0});')
    s.sfx.append(("drop_001", t + 2.0))
    t = s.tap(t + 2.3, 400, 467, "up-au", 0.45, ring=True)
    t = type_field(s, "up-au", t + 0.1, "First-year students, 3-minute talk", 1.0)
    s.unring("up-au", t)
    s.tw(f'tl.to("#{s.id("up")}-ub",{{backgroundColor:"#0A0A0A",duration:0.2}},{t});')
    t = s.tap(t + 0.2, 340, 527, "up-ub", 0.4)
    s.tw(f'tl.to("#{s.id("up")}-ph",{{opacity:1,duration:0.2}},{t});tl.fromTo("#{s.id("up")}-pb",{{scaleX:0}},{{scaleX:1,duration:2.2,ease:"power1.inOut"}},{t});'
         f'tl.set("#{s.id("up")}-p1",{{textContent:"Reading the slides…"}},{t + 0.8});tl.set("#{s.id("up")}-p1",{{textContent:"Preparing your Q&A…"}},{t + 1.6});')
    s.tw(f'tl.set("#{s.id("up")}-pb",{{scaleX:0}},0);')
    s.mate_say("up", "Uploading your deck…", t + 0.1, 1.0)
    s.life(s.id("up-mate")).state(t + 0.1, 2.0, "working")
    s.mate_say("up", "Got it! I'm reading your slides now.", t + 1.3, 1.4)
    # the Deck Agent at work: three slides fly into the reader, key points come out
    X0, Y0 = s.P(560, 300)
    rd = s.lbot("reader", "presenter", X0 + 150, Y0 - 60, 230, start="down", idle=False)
    s.el("rdl", "chip", f"left:{X0 + 90}px;top:{Y0 + 170}px;background:{LAVENDER};color:{INK};font-size:24px;z-index:31", "Deck Agent · reading 3 slides")
    s.el("rdbg", "abs", f"left:{WX}px;top:{WY + 46}px;width:{WW}px;height:{WH - 46}px;background:rgba(255,250,240,.86);z-index:29")
    for n in ("rdbg", "reader", "rdl"):
        s.html[[i for i, h in enumerate(s.html) if f'id="{s.id(n)}"' in h][0]] = s.html[[i for i, h in enumerate(s.html) if f'id="{s.id(n)}"' in h][0]].replace('style="', 'style="z-index:30;', 1)
    s.show("rdbg", t + 0.3, "fade"); s.show("reader", t + 0.4, "pop", "card-place-2"); s.show("rdl", t + 0.6, "pop")
    for k in range(3):
        sx = X0 - 380 + k * 40
        s.el(f"fs{k}", "abs", f"left:{sx}px;top:{Y0 - 40 + k * 30}px;width:150px;height:96px;border-radius:10px;background:#fff;box-shadow:0 10px 24px rgba(10,26,26,.18);z-index:32;"
             f"font-size:13px;font-weight:700;padding:10px", PLAN["deck"]["slides"][k]["title"])
        tt = t + 0.6 + k * 0.35
        s.tw(f'tl.fromTo("#{s.id(f"fs{k}")}",{{opacity:0,x:-60}},{{opacity:1,x:0,duration:0.3,ease:"expo.out"}},{tt});'
             f'tl.to("#{s.id(f"fs{k}")}",{{x:{X0 + 190 - sx},y:{30 - k * 30},scale:0.2,opacity:0,duration:0.55,ease:"power3.in"}},{tt + 0.35});')
        s.sfx.append(("card-slide-1" if k == 0 else "card-place-1", tt + 0.35))
    rd.state(t + 0.9, 1.6, "working"); rd.hop(t + 2.55, 22)
    for k in range(3):
        s.el(f"kpo{k}", "abs", f"left:{X0 + 420}px;top:{Y0 - 40 + k * 56}px;padding:8px 14px;border-radius:10px;background:#fff;box-shadow:0 6px 14px rgba(10,26,26,.12);font-size:17px;z-index:32;max-width:520px",
             f'<b style="color:{LAV_INK}">Slide {k + 1}:</b> {PLAN["deck"]["slides"][k]["key_point"][:52]}…')
        s.tw(f'tl.fromTo("#{s.id(f"kpo{k}")}",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:0.4,ease:"expo.out"}},{t + 1.6 + k * 0.3});')
    for n in ("rdbg", "reader", "rdl", "kpo0", "kpo1", "kpo2"):
        s.hide(n, t + 3.3)
    t += 0.8
    s.swap_page(t + 2.6, "up", "dk", False)
    t2 = t + 3.3
    s.tw(f'tl.fromTo("#{s.id("dk")}-mm",{{opacity:0,y:14}},{{opacity:1,y:0,duration:0.5,ease:"expo.out"}},{t2});')
    for k in range(3):
        s.tw(f'tl.fromTo("#{s.id("dk")}-kp{k}",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.5,ease:"expo.out"}},{t2 + 0.5 + k * 0.25});')
    s.sfx.append(("card-place-2", t2 + 0.5))
    s.zoom("w", t2 + 1.4, 1.32, 760, 760, 0.8)
    s.callout("ck", "Each slide's key point, written by the AI", 260, 380, t2 + 1.6, LAVENDER, hold=2.4)
    s.unzoom("w", s.D - 1.3)
    s.tap(s.D - 0.9, 460, 280, "dk-pr", 0.5)
    return s


def talk_page(s, pid):
    d = PLAN["deck"]
    def slide(k):
        body = {0: "".join(f'<div style="position:absolute;left:60px;top:{170 + i * 60}px;width:{[560, 470, 520][i]}px;height:26px;border-radius:13px;background:#EDE7DA"></div>' for i in range(3)),
                1: "".join(f'<div style="position:absolute;left:{60 + (i % 2) * 300}px;top:{150 + (i // 2) * 150}px;width:280px;height:134px;border-radius:14px;background:{c};font-size:20px;font-weight:700;padding:14px">{x}</div>'
                           for i, (x, c) in enumerate([("Urgent · important", PEACH), ("Important", MINT), ("Urgent", OCHRE), ("Neither", "#EDE7DA")])),
                2: "".join(f'<div style="position:absolute;left:{60 + i * 150}px;top:{340 - i * 50}px;width:120px;height:{100 + i * 50}px;border-radius:12px;background:{LAVENDER};opacity:{0.5 + i * 0.15}"></div>' for i in range(4))}[k]
        return (f'<div id="{s.id(pid)}-sl{k}" style="position:absolute;inset:0;background:#fff;opacity:{1 if k == 0 else 0}">'
                f'<div style="position:absolute;left:60px;top:50px;font-size:44px;font-weight:700;letter-spacing:-.02em;color:#0A0A0A">{d["slides"][k]["title"]}</div>'
                f'<div style="position:absolute;left:60px;top:120px;width:140px;height:7px;border-radius:4px;background:{LAVENDER}"></div>{body}</div>')
    return (f'<div style="position:absolute;left:40px;top:24px;width:1100px;height:620px;border-radius:16px;overflow:hidden">{"".join(slide(k) for k in range(3))}</div>'
            f'<div style="position:absolute;left:1160px;top:24px;width:240px;height:180px;border-radius:14px;overflow:hidden">{camera_view(s, s.id(pid) + "-me", 240, 180)}</div>'
            f'<div class="dp" style="left:1160px;top:220px;width:240px;height:200px">'
            + bot_html(s.id(pid) + "-bot", "presenter", "left:45px;top:4px;width:150px;height:150px") +
            f'<div style="position:absolute;left:0;right:0;bottom:14px;text-align:center;font-size:14px;font-weight:600">Listening quietly</div></div>'
            f'<div style="position:absolute;left:40px;top:666px;padding:9px 16px;border-radius:10px;background:{LAV_INK};font-size:15px;font-weight:600">● Presenting</div>'
            f'<div style="position:absolute;left:520px;top:662px;display:flex;gap:14px;align-items:center;font-size:16px">'
            f'<span class="wt" style="position:relative;width:46px;height:40px;background:#2A3A39;color:#fff;border:none">←</span>'
            f'<span id="{s.id(pid)}-n" style="font-weight:700">1 / 3</span>'
            f'<span id="{s.id(pid)}-nx" class="wt" style="position:relative;width:46px;height:40px;background:#2A3A39;color:#fff;border:none">→</span></span></div>'
            f'<div id="{s.id(pid)}-end" style="position:absolute;left:1300px;top:666px;padding:9px 18px;border-radius:10px;background:#E5484D;font-size:15px;font-weight:700">End</div>')


def s12():
    s = S("s12-talk", lead=0.4)
    window(s, "speechmate.app/presentations", "speechmate.app/session", [("dk0", chrome(s, "dk0", "Presentation"), False), ("tk", talk_page(s, "tk"), True)])
    s.cursor_at(0.0, 460, 280, fade=False)
    s.swap_page(0.05, "dk0", "tk", True)
    s.life(s.id("tk") + "-bot").idle(0.3, s.D, looks=("left", "default", "down", "left", "tiltl", "left"), gap=(1.0, 2.0))
    s.go(0.4, 657, 700, 0.6)
    s.talk(s.id("tk") + "-me", 0.6, s.D - 2.2)
    for k, t in enumerate([3.2, 6.6]):
        tt = s.tap(t, 657, 682, "tk-nx", 0.35)
        s.tw(f'tl.to("#{s.id("tk")}-sl{k}",{{opacity:0,duration:0.2}},{tt + 0.05});tl.to("#{s.id("tk")}-sl{k + 1}",{{opacity:1,duration:0.2}},{tt + 0.05});'
             f'tl.set("#{s.id("tk")}-n",{{textContent:"{k + 2} / 3"}},{tt + 0.05});')
    s.callout("cs", "Slide 2: the Eisenhower matrix, skipped on purpose", 70, 560, 3.8, PEACH, hold=2.6)
    s.callout("cq", "The AI stays quiet while you present", 860, 450, 1.0, LAVENDER, hold=2.0)
    s.tap(s.D - 1.2, 1335, 685, "tk-end", 0.5)
    return s


def match_page(s, pid):
    d = PLAN["deck"]
    res = [(1, "Covered", 5, MINT, "You introduced the five strategies and why they matter for new students.", None),
           (2, "Left out", 2, PEACH, "You talked about task lists only.", "the Eisenhower matrix, this slide's main tool."),
           (3, "Covered", 4, MINT, "Time-blocking and short work sprints, with an example.", None)]
    rows = "".join(f'<div id="{s.id(pid)}-r{k}" class="wcard" style="left:200px;top:{150 + k * 186}px;width:1060px;height:170px;opacity:0">'
                   f'<div style="position:absolute;left:18px;top:16px;width:180px;height:136px;border-radius:10px;background:#FBF8F1;border:1px solid rgba(10,26,26,.06);font-size:13px;font-weight:700;padding:10px">{d["slides"][n - 1]["title"]}</div>'
                   f'<div style="position:absolute;left:216px;top:16px;font-size:13px;font-weight:700;letter-spacing:.1em;color:{LAV_INK}">SLIDE {n}</div>'
                   f'<div style="position:absolute;right:18px;top:14px;padding:5px 12px;border-radius:999px;background:{c};font-size:13px;font-weight:700">{tag} · match {m}/5</div>'
                   f'<div style="position:absolute;left:216px;top:42px;width:800px;font-size:14px;color:#3A4645"><b>The slide\'s point:</b> {d["slides"][n - 1]["key_point"]}</div>'
                   f'<div style="position:absolute;left:216px;top:72px;width:800px;font-size:14px"><b>You said:</b> {said}</div>'
                   + (f'<div style="position:absolute;left:216px;top:102px;width:800px;font-size:15px;font-weight:700;color:{PINK_INK}">Left out: {lo}</div>' if lo else '')
                   + '</div>' for k, (n, tag, m, c, said, lo) in enumerate(res))
    return (chrome(s, pid, "Progress") + ill(1100, 96)
            + '<div class="h1" style="left:200px;top:90px;font-size:32px">Did your talk match your slides?</div>' + rows)


def s13():
    s = S("s13-match", lead=0.5)
    window(s, "speechmate.app/session", "speechmate.app/results", [("tk0", "", True), ("mt", match_page(s, "mt"), False)])
    s.swap_page(0.05, "tk0", "mt", True)
    for k in range(3):
        s.tw(f'tl.fromTo("#{s.id("mt")}-r{k}",{{opacity:0,y:16}},{{opacity:1,y:0,duration:0.45,ease:"expo.out"}},{0.6 + k * 0.3});')
    s.sfx.append(("card-place-1", 0.6))
    s.zoom("w", s.at(0, 0.45), 1.25, 600, 430, 0.9)
    s.tw(f'tl.fromTo("#{s.id("mt")}-r1",{{boxShadow:"0 0 0 0px rgba(194,30,87,0)"}},{{boxShadow:"0 0 0 4px rgba(194,30,87,0.45)",duration:0.4}},{s.at(0, 0.6)});')
    s.sfx.append(("drop_002", s.at(0, 0.6)))
    s.unzoom("w", s.D - 1.2)
    return s


def s14():
    s = S("s14-qa", lead=0.4)
    q = PLAN["deck"]["qa"][0]
    window(s, "speechmate.app/results", "speechmate.app/session",
           [("mt0", chrome(s, "mt0", "Progress"), False), ("qa", session_page(s, "qa", "The moderator", "presenter", q, LAV_INK, "Q&amp;A rehearsal · Time management"), True)])
    s.swap_page(0.05, "mt0", "qa", True)
    clock(s, "qa", 0.3, s.D, 12, 12 + round(s.D))
    turn(s, "qa", "ai", 0.4); bot_talk(s, "qa", True, 0.4)
    s.callout("cq", "A question about slide 2, from the deck", 860, 300, 0.9, LAVENDER, hold=3.0)
    t = s.ce[0] + 0.4
    turn(s, "qa", "you", t); bot_talk(s, "qa", False, t)
    turn(s, "qa", "listen", t + 0.7); speak(s, "qa", t + 0.7, s.D - t - 1.2)
    return s


def convo_page(s, pid):
    topics = [("Your week", "Catching up: what happened in your week and what you're looking forward to"),
              ("Small talk", "Small talk with someone you just met at a café or event"),
              ("Studies &amp; work", "Talking about your studies, your work and your plans after graduating"),
              ("Making plans", "Planning a weekend outing with a friend: where to go, when, and what to do"),
              ("Malaysia", "Telling a visitor about Malaysian food, festivals and places to see"),
              ("Share an opinion", "Giving and defending your opinion: is social media good for young people?")]
    tl_ = "".join(f'<div id="{s.id(pid)}-tp{k}" class="tile" style="left:{234 + (k % 2) * 350}px;top:{300 + (k // 2) * 106}px;width:336px;height:92px;padding:14px 16px">'
                  f'{t}<small style="font-size:13px;line-height:1.35">{d}</small></div>' for k, (t, d) in enumerate(topics))
    return (chrome(s, pid, "Conversation")
            + f'<div class="eb" style="left:234px;top:84px;color:{PINK_INK}">DAILY CONVERSATION</div>'
            + '<div class="h1" style="left:234px;top:104px;font-size:38px">What would you like to talk about?</div>'
            + '<div class="sub" style="left:234px;top:154px;width:620px;font-size:15px">Have a relaxed spoken conversation with your AI partner. Nothing is scored while you talk; afterwards you get a simple report.</div>'
            + tl_
            + '<div class="wcard" style="left:960px;top:240px;width:320px;height:250px;padding:18px">'
              '<div style="font-size:15px;font-weight:700;margin-bottom:10px">Analysed after you finish</div>'
              + "".join(f'<div style="font-size:14px;font-weight:600;margin-top:8px">{a}<div style="font-weight:400;font-size:12px;color:#5C6766">{b}</div></div>'
                        for a, b in [("Voice", "pace, fluency, pronunciation"), ("Language", "filler words, vocabulary, grammar tips"), ("Body language", "eye contact, posture, gestures"), ("Confidence", "expression, response time")])
              + '</div>'
            + f'<div id="{s.id(pid)}-go" class="bk" style="left:960px;top:506px;width:320px;height:46px">Start conversation</div>')


def chat_page(s, pid):
    return (f'<div style="position:absolute;left:0;right:0;top:0;height:58px;display:flex;align-items:center;gap:16px;padding:0 40px;border-bottom:1px solid rgba(255,255,255,.08);font-size:15px">'
            f'<span style="opacity:.7">← Leave</span><span style="padding:5px 14px;border-radius:999px;background:{PINK_INK};font-weight:600">Daily conversation · Your week</span></div>'
            f'<div style="position:absolute;left:40px;top:82px;width:760px;height:460px;border-radius:18px;overflow:hidden">{camera_view(s, s.id(pid) + "-me", 760, 460)}</div>'
            f'<div class="dp" style="left:830px;top:82px;width:570px;height:620px">'
            + bot_html(s.id(pid) + "-bot", "chat", "left:16px;top:10px;width:100px;height:100px") +
            f'<div style="position:absolute;left:126px;top:44px;font-size:17px;font-weight:600">Your partner</div>'
            f'<div id="{s.id(pid)}-m1" class="bubble" style="left:20px;top:126px;width:420px;background:#2A3A39;font-size:17px;opacity:0">How was your week? Anything fun or stressful?</div>'
            f'<div id="{s.id(pid)}-tr" class="bubble" style="left:130px;top:230px;width:420px;background:{PINK};color:#fff;font-size:17px;opacity:0"><span class="dots"><i></i><i></i><i></i></span> Transcribing…</div>'
            f'<div id="{s.id(pid)}-m2" class="bubble" style="left:130px;top:230px;width:420px;background:{PINK};color:#fff;font-size:17px;opacity:0">This week quite busy lah, but okay. Got my final-year project demo, so macam a bit stressed.</div>'
            f'<div id="{s.id(pid)}-kp" style="position:absolute;left:130px;top:352px;padding:5px 12px;border-radius:999px;background:{MINT};color:#0A0A0A;font-size:12px;font-weight:800;letter-spacing:.06em;opacity:0">KEPT AS SPOKEN</div>'
            f'<div id="{s.id(pid)}-m3" class="bubble" style="left:20px;top:400px;width:420px;background:#2A3A39;font-size:17px;opacity:0">Final-year demo! What is your project about?</div></div>'
            f'<div class="bars" style="left:56px;top:506px">{"".join(f"<i id=\'{s.id(pid)}-b{k}\'></i>" for k in range(7))}</div>')


def s15():
    s = S("s15-convo", lead=0.3)
    window(s, "speechmate.app/presentations", "speechmate.app/conversation",
           [("mt1", chrome(s, "mt1", "Progress"), False), ("cv", convo_page(s, "cv"), False), ("ch", chat_page(s, "ch"), True)])
    s.cursor_at(0.0, 700, 600, fade=False)
    t = s.tap(0.2, 497, 35, None, 0.6)
    s.swap_page(t, "mt1", "cv", True)
    t = s.tap(t + 1.0, 400, 345, "cv-tp0", 0.5, sel="tile")
    t = s.tap(t + 0.5, 1120, 529, "cv-go", 0.5)
    s.swap_page(t + 0.2, "cv", "ch", False)
    s.tw(f'tl.to("#{s.id("cur")}",{{opacity:0,duration:0.2}},{t + 0.5});')
    t += 0.9
    s.zoom("w", t + 0.2, 1.3, 1226, 431, 0.9)
    s.unzoom("w", s.D - 0.9)
    s.tw(f'tl.fromTo("#{s.id("ch")}-m1",{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.35}},{t});'); s.sfx.append(("drop_001", t))
    cb = s.life(s.id("ch") + "-bot"); cb.idle(0.3, s.D, looks=("tiltr", "default", "left", "default"), gap=(1.2, 2.2))
    cb.talk(t - 0.2, 1.3); cb.look(t + 1.3, "left"); cb.nod(t + 2.6); cb.look(t + 4.2, "default"); cb.hop(t + 5.3, 16); cb.talk(t + 6.5, 1.4)
    speak(s, "ch", t + 1.2, 2.8)
    s.tw(f'tl.to("#{s.id("ch")}-tr",{{opacity:1,duration:0.2}},{t + 4.1});tl.to("#{s.id("ch")}-tr",{{opacity:0,duration:0.15}},{t + 4.9});'
         f'tl.fromTo("#{s.id("ch")}-m2",{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.35}},{t + 5.0});tl.to("#{s.id("ch")}-kp",{{opacity:1,duration:0.3}},{t + 5.4});'
         f'tl.fromTo("#{s.id("ch")}-m3",{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.35}},{t + 6.6});')
    s.sfx.append(("drop_002", t + 5.0))
    s.callout("cm", "Manglish, kept as spoken", 1000, 600, t + 5.5, MINT, hold=2.4)
    return s


def tips_page(s, pid):
    return (chrome(s, pid, "Progress") + ill(1100, 96)
            + '<div class="h1" style="left:200px;top:90px;font-size:32px">Daily conversation · Your week</div>'
            + f'<div id="{s.id(pid)}-c" class="wcard" style="left:200px;top:160px;width:1060px;height:300px">'
              f'<div style="position:absolute;left:20px;top:18px;font-size:16px;font-weight:700">Your language</div>'
              f'<div style="position:absolute;left:20px;top:56px;width:1010px;height:100px;border-radius:12px;background:#FBF8F1;padding:14px 18px;font-size:16px;line-height:1.7">'
              f'<b style="color:{PINK_INK}">You said:</b> “This week quite busy lah, but okay.”<br>'
              f'<b style="color:{TEAL_INK}">Try saying:</b> “This week has been quite busy, but it\'s been okay.”</div>'
              f'<div style="position:absolute;left:20px;top:172px;width:1010px;font-size:14px;color:#3A4645">Why: in a formal setting, a full verb sounds clearer. With friends, your original is perfectly fine.</div>'
              f'<div style="position:absolute;left:20px;top:214px;display:flex;gap:10px;font-size:13px">'
              f'<span style="padding:6px 12px;border-radius:999px;background:#F1ECFD">Language mix · English + Malay</span>'
              f'<span style="padding:6px 12px;border-radius:999px;background:#E3F3EE">“lah”, “macam”: not counted as filler words</span></div></div>')


def s16():
    s = S("s16-tips", lead=0.4)
    window(s, "speechmate.app/session", "speechmate.app/results", [("ch0", "", True), ("tp", tips_page(s, "tp"), False)])
    s.swap_page(0.05, "ch0", "tp", True)
    s.zoom("w", 1.2, 1.25, 640, 300, 0.9)
    s.unzoom("w", s.D - 1.0)
    return s


def progress_page(s, pid):
    pts = [(0, 58), (1, 61), (2, 60), (3, 66), (4, 69), (5, 71), (6, 75)]
    path = " ".join(f'{"M" if i == 0 else "L"}{40 + x * 150},{220 - (y - 40) * 3.2}' for i, (x, y) in enumerate(pts))
    return (chrome(s, pid, "Progress") + ill(1180, 96)
            + '<div class="eb" style="left:234px;top:84px;color:#5C6766">PROGRESS</div>'
            + '<div class="h1" style="left:234px;top:104px;font-size:38px">How you\'re improving</div>'
            + "".join(f'<div id="{s.id(pid)}-f{k}" class="pill" style="left:{234 + [0, 70, 210, 320][k]}px;top:166px;border-radius:999px;{"background:#0A0A0A;color:#fff;border-color:#0A0A0A" if k == 0 else ""}">{n}</div>'
                      for k, n in enumerate(["All", "Conversation", "Interview", "Presentation Q&amp;A"]))
            + "".join(f'<div class="wcard" style="left:{234 + k * 262}px;top:220px;width:246px;height:76px"><div style="position:absolute;left:16px;top:12px;font-size:13px;color:#5C6766">{a}</div>'
                      f'<div style="position:absolute;left:16px;top:34px;font-size:24px;font-weight:700">{b}</div></div>'
                      for k, (a, b) in enumerate([("Sessions", "7"), ("Practice time", "48 min"), ("Latest overall", "75"), ("Change since first", "+17")]))
            + '<div class="wcard" style="left:234px;top:312px;width:1034px;height:300px">'
              '<div style="position:absolute;left:18px;top:16px;font-size:16px;font-weight:700">Overall score per session</div>'
              f'<svg viewBox="0 0 1000 240" style="position:absolute;left:18px;top:50px;width:1000px;height:240px">'
              f'<line x1="40" y1="220" x2="980" y2="220" stroke="#EEE8DC" stroke-width="2"/><line x1="40" y1="92" x2="980" y2="92" stroke="#EEE8DC" stroke-width="2" stroke-dasharray="6 6"/>'
              f'<path id="{s.id(pid)}-ln" d="{path}" fill="none" stroke="{TEAL_INK}" stroke-width="5" stroke-linejoin="round" stroke-linecap="butt" pathLength="100" stroke-dasharray="100 100" stroke-dashoffset="100"/>'
              + "".join(f'<circle id="{s.id(pid)}-d{i}" cx="{40 + x * 150}" cy="{220 - (y - 40) * 3.2}" r="8" fill="{TEAL_INK}" opacity="0"/>' for i, (x, y) in enumerate(pts))
              + '</svg></div>')


def s17():
    s = S("s17-progress", lead=0.4)
    window(s, "speechmate.app/results", "speechmate.app/progress", [("tp0", chrome(s, "tp0", "Progress"), False), ("pg", progress_page(s, "pg"), False)])
    s.cursor_at(0.0, 900, 500, fade=False)
    t = s.tap(0.1, 930, 35, None, 0.6)
    s.swap_page(t, "tp0", "pg", True)
    s.tw(f'tl.to("#{s.id("pg")}-ln",{{strokeDashoffset:0,duration:1.8,ease:"power2.inOut"}},{t + 0.8});')
    for i in range(7):
        s.tw(f'tl.to("#{s.id("pg")}-d{i}",{{opacity:1,duration:0.2}},{round(t + 0.8 + i * 0.27, 3)});')
    s.tap(t + 3.0, 490, 184, "pg-f2", 0.5, sel="pill")
    s.mate_say("pg", "Nice one!", t + 3.8)
    return s


def s18():
    s = S("s18-agents", lead=0.5)
    cx, cy, rx, ry = 960, 450, 560, 320
    s.css += f"#s18-ring{{left:{cx - rx}px;top:{cy - ry}px;width:{2 * rx}px;height:{2 * ry}px}}"
    s.add(f'<svg id="s18-ring" class="abs" viewBox="0 0 {2 * rx} {2 * ry}"><ellipse id="s18-ell" cx="{rx}" cy="{ry}" rx="{rx - 4}" ry="{ry - 4}" '
          f'fill="none" stroke="{ACCENT_INK}" stroke-opacity=".28" stroke-width="5" stroke-dasharray="14 14" pathLength="100"/></svg>')
    s.add(f'<svg id="s18-ring2" class="abs" viewBox="0 0 {2 * rx} {2 * ry}" style="left:{cx - rx}px;top:{cy - ry}px;width:{2 * rx}px;height:{2 * ry}px">'
          f'<ellipse id="s18-sweep" cx="{rx}" cy="{ry}" rx="{rx - 4}" ry="{ry - 4}" fill="none" stroke="#C21E57" stroke-width="7" '
          f'stroke-linecap="butt" stroke-dasharray="100 100" stroke-dashoffset="100" pathLength="100"/></svg>')
    s.tw(f'tl.fromTo("#s18-ell",{{strokeDashoffset:100,opacity:0}},{{strokeDashoffset:0,opacity:1,duration:1.6,ease:"power2.inOut"}},{s.at(0)});')
    m = s.lbot("mate", "mate", cx - 120, cy - 150, 240)
    s.show("mate", s.at(0, 0.2), "pop", "card-place-1")
    s.text("ct", "A team of AI agents", cx - 300, cy + 90, 600, 38, 600, INK, "center")
    s.show("ct", s.at(0, 0.5), "blur")
    nodes = [(-90, "Know the learner", "Learner profile", "mate", MINT, s.at(3, 0.0)),
             (-30, "Plan", "Question planner", "interviewer", TEAL, s.at(1, 0.15)),
             (30, "Practise", "Interviewer", "interviewer", TEAL, s.at(1, 0.45)),
             (90, "Check", "Deck reader", "presenter", LAVENDER, s.at(1, 0.8)),
             (150, "Coach", "Measured issues only", "mate", OCHRE, s.at(2, 0.1)),
             (210, "Practise again", "Progress", "chat", PINK, s.at(3, 0.7))]
    for k, (ang, step, agent, who, col, t) in enumerate(nodes):
        x = round(cx + rx * math.cos(math.radians(ang)) - 210)
        y = round(cy + ry * math.sin(math.radians(ang)) - 70)
        fg = "#fff" if col == TEAL else INK
        s.el(f"n{k}", "card", f"left:{x}px;top:{y}px;width:420px;height:140px;background:{col}",
             bot_html(s.id(f"nb{k}"), who, "left:0;top:2px;width:136px;height:136px") +
             f'<div class="disp" style="position:absolute;left:140px;top:28px;width:272px;font-size:30px;white-space:nowrap;color:{fg}">{step}</div>'
             f'<div style="position:absolute;left:142px;top:78px;width:270px;font-size:24px;font-weight:500;color:{fg};opacity:.85">{agent}</div>')
        s.show(f"n{k}", t, "pop", "card-place-1" if k % 2 else "card-place-2")
        lf = s.life(s.id(f"nb{k}")); lf.hop(t + 0.55, 20); lf.idle(t + 1.2, s.D, looks=("tiltr", "default", "left", "default", "right"), gap=(1.0, 2.0))
    s.chip("inv", "It can't invent a problem", cx - 200, cy + 160, "#fff", ACCENT_INK, dot=OCHRE, size=28)
    s.show("inv", s.at(2, 0.5), "rise")
    s.hide("inv", s.at(3, 0.2)); s.hide("ct", s.at(3))
    s.tw(f'tl.fromTo("#s18-sweep",{{strokeDashoffset:100}},{{strokeDashoffset:0,duration:{round(s.ce[3] - s.cs[3] + 1.0, 2)},ease:"power1.inOut"}},{s.at(3, 0.3)});')
    s.text("loop", "Practise → get feedback → practise again", cx - 420, cy + 100, 840, 34, 600, PINK_INK, "center")
    s.show("loop", s.at(3, 0.45), "blur")
    m.talk(s.at(3, 0.05), round(s.ce[3] - s.cs[3], 2)); m.hop(s.ce[3] + 0.5); m.look(s.at(1, 0.15), "right"); m.look(s.at(2, 0.1), "left"); m.look(s.at(2, 0.8), "default")
    for n in ["mate", "loop"] + [f"n{k}" for k in range(6)]:
        s.hide(n, s.D)
    s.tw(f'tl.to(["#s18-ring","#s18-ring2"],{{opacity:0,duration:0.25}},{s.D - 0.25});')
    return s


def s19():
    s = S("s19-close", lead=0.5)
    for k, (big, small, bg) in enumerate([("Malaysian", "speakers first: 4.9% · 7.3% word error rate on real English · Malay", MINT),
                                          ("Private", "by design: recordings deleted after analysis", PEACH),
                                          ("Explained", "every score, never guessed", LAVENDER)]):
        s.el(f"t{k}", "card", f"left:{140 + k * 560}px;top:200px;width:520px;height:380px;background:{bg}",
             f'<div class="disp" style="position:absolute;left:40px;top:60px;font-size:84px">{big}</div>'
             f'<div style="position:absolute;left:42px;top:190px;width:440px;font-size:30px;font-weight:500;line-height:1.3">{small}</div>')
        s.show(f"t{k}", s.at(0, 0.05 + 0.3 * k), "rise", "card-place-1" if k != 1 else "card-place-2")
        s.hide(f"t{k}", s.at(1))
    s.el("room", "abs", "inset:0")
    n0 = len(s.html)
    mirror_room(s, "p19b", "p19r", mouth="smile")
    room = "".join(s.html[n0:]); del s.html[n0:]
    s.html[-1] = s.html[-1].replace("></div>", f">{room}</div>", 1)
    s.show("room", s.at(1) - 0.2, "fade")
    m = s.lbot("mate", "mate", 110, 560, 280, looks=("right", "default", "tiltr", "default"))
    m.hop(s.at(1, 0.8)); m.spin(s.ce[2] + 0.6)
    s.show("mate", s.at(1, 0.4), "pop", "card-place-1")
    s.el("say", "bubble", f"left:150px;top:470px;background:#fff;font-size:30px;font-weight:600;box-shadow:0 10px 22px rgba(10,26,26,.14)", "Nice one!")
    s.show("say", s.at(1, 0.8), "pop", "drop_002")
    s.tw(f'tl.to("#p19r .phead",{{rotation:-5,svgOrigin:"200 350",duration:0.4,yoyo:true,repeat:1,ease:"sine.inOut"}},{s.at(1, 0.5)});')
    for n in ["room", "say"]:
        s.hide(n, s.at(2) - 0.3)
    s.tw(f'tl.to("#{s.id("mate")}",{{x:{810 - 110},y:{130 - 560},scale:1.07,duration:0.7,ease:"power2.inOut"}},{s.at(2) - 0.6});')
    s.text("logo", "SpeechMate", 0, 470, 1920, 170, 600, INK, "center")
    s.show("logo", s.at(2, 0.0), "blur", "impactBell_heavy_003")
    s.text("tag", "Practise, and finally know what to improve.", 0, 680, 1920, 50, 500, ACCENT_INK, "center")
    s.show("tag", s.at(2, 0.4) + 0.3, "blur")
    return s


def analyse_page(s, pid):
    """the analysis, made visible: the recording passes through each model in turn"""
    cw, ch = 600, 360
    # face mesh + pose over the camera (positions follow camera_view's geometry)
    ph = ch * 0.92; top = ch * 0.16; sc = ph / 600; left = (cw - ph * 2 / 3) / 2
    fx, fy = left + 200 * sc, top + 262 * sc
    dots = "".join(f'<circle cx="{fx + 52 * sc * 1.0 * math.cos(a / 18 * math.pi * 2):.1f}" cy="{fy + 62 * sc * math.sin(a / 18 * math.pi * 2):.1f}" r="2.6" fill="#5EEAD4"/>' for a in range(18))
    dots += "".join(f'<circle cx="{fx + (dx - 200) * sc:.1f}" cy="{fy + (dy - 262) * sc:.1f}" r="2.2" fill="#5EEAD4"/>' for dx, dy in [(160, 240), (184, 240), (216, 240), (240, 240), (200, 290), (186, 318), (214, 318), (200, 330)])
    iris = "".join(f'<circle cx="{fx + (ex - 200) * sc:.1f}" cy="{fy + 10 * sc:.1f}" r="9" fill="none" stroke="#FBBF24" stroke-width="2.5"/>' for ex in (172, 228))
    sh_y = top + 420 * sc
    pose = (f'<line x1="{fx - 95 * sc:.1f}" y1="{sh_y:.1f}" x2="{fx + 95 * sc:.1f}" y2="{sh_y:.1f}" stroke="#93C5FD" stroke-width="4"/>'
            f'<line x1="{fx:.1f}" y1="{fy + 80 * sc:.1f}" x2="{fx:.1f}" y2="{sh_y:.1f}" stroke="#93C5FD" stroke-width="4"/>'
            + "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#93C5FD"/>' for x, y in [(fx - 95 * sc, sh_y), (fx + 95 * sc, sh_y), (fx, sh_y), (fx, fy + 80 * sc)]))
    words = [("0:41.2", "So", 0), ("0:41.5", "in", 0), ("0:41.7", "my", 0), ("0:42.0", "internship", 0), ("0:42.8", "uh", 1), ("0:43.3", "I", 0), ("0:43.5", "built", 0),
             ("0:43.9", "weekly", 0), ("0:44.3", "dashboards", 0), ("0:45.0", "lah", 2)]
    wd = "".join(f'<span id="{s.id(pid)}-w{k}" style="display:inline-block;margin:0 6px 8px 0;padding:5px 9px;border-radius:8px;opacity:0;'
                 f'background:{["#1E2E2D", "#5A2A22", "#2F2A55"][kind]};font-size:15px"><b>{w}</b> <span style="font-size:11px;opacity:.6;font-family:monospace">{ts}</span>'
                 + (' <span style="font-size:11px;color:#FCA5A5">filler</span>' if kind == 1 else ' <span style="font-size:11px;color:#C4B5FD">particle · kept</span>' if kind == 2 else "")
                 + '</span>' for k, (ts, w, kind) in enumerate(words))
    bars = "".join(f'<i id="{s.id(pid)}-wv{k}" style="display:inline-block;width:6px;height:8px;margin-right:4px;border-radius:3px;background:#5EEAD4;vertical-align:middle"></i>' for k in range(40))
    steps = [("Speech recognition", "Whisper large-v3 · word timestamps"), ("Fluency, pace &amp; fillers", "Manglish particles not counted as fillers"),
             ("Pronunciation", "wav2vec2 phonemes · Malaysian English accepted"), ("Eye contact, posture, gestures", "MediaPipe face mesh &amp; pose"),
             ("Gaze Tunneling", "looking away vs. stumbling, on one timeline"), ("Confidence", "11 measured cues, weakest first"),
             ("Four pillars + 3 drills", "only from what was measured")]
    st = "".join(f'<div id="{s.id(pid)}-s{k}" style="position:absolute;left:0;top:{k * 76}px;width:620px;height:66px;border-radius:14px;background:#13201F;opacity:.35">'
                 f'<div id="{s.id(pid)}-sp{k}" style="position:absolute;left:16px;top:19px;width:26px;height:26px;border-radius:50%;border:3px solid rgba(94,234,212,.25);border-top-color:#5EEAD4"></div>'
                 f'<div id="{s.id(pid)}-ok{k}" style="position:absolute;left:16px;top:19px;width:28px;height:28px;border-radius:50%;background:#5EEAD4;color:#0A1A1A;font-weight:800;font-size:17px;display:grid;place-items:center;opacity:0">✓</div>'
                 f'<div style="position:absolute;left:60px;top:11px;font-size:18px;font-weight:700">{a}</div>'
                 f'<div style="position:absolute;left:60px;top:37px;font-size:13px;font-family:monospace;color:#9FD8CF">{b}</div></div>' for k, (a, b) in enumerate(steps))
    gz = (f'<svg viewBox="0 0 560 120" style="position:absolute;left:20px;top:40px;width:560px;height:90px" preserveAspectRatio="none">'
          f'<path d="M0 100 L60 98 L100 96 L130 40 L160 96 L260 98 L300 94 L330 30 L360 92 L460 98 L560 96" fill="none" stroke="#FBBF24" stroke-width="4"/>'
          f'<path d="M0 104 L60 102 L104 100 L134 52 L164 100 L262 102 L304 98 L334 44 L364 98 L460 102 L560 100" fill="none" stroke="#FCA5A5" stroke-width="4" stroke-dasharray="7 6"/></svg>'
          f'<div style="position:absolute;left:20px;top:14px;font-size:15px;font-weight:700">Gaze Tunneling</div>'
          f'<div style="position:absolute;left:200px;top:16px;font-size:12px"><b style="color:#FBBF24">— looking away</b> &nbsp; <b style="color:#FCA5A5">- - stumbles</b></div>'
          f'<div style="position:absolute;left:20px;top:140px;font-size:14px;color:#FBBF24;font-weight:600">“You look away right when you lose your words.”</div>')
    return (f'<div style="position:absolute;left:0;right:0;top:0;height:58px;display:flex;align-items:center;gap:16px;padding:0 40px;border-bottom:1px solid rgba(255,255,255,.08);font-size:15px">'
            f'<span style="padding:5px 14px;border-radius:999px;background:{TEAL};font-weight:600">Mock interview · analysing</span>'
            f'<span style="margin-left:auto;font-size:13px;padding:5px 12px;border-radius:999px;background:#E8B94A;color:#0A0A0A;font-weight:800;letter-spacing:.08em">ILLUSTRATIVE</span></div>'
            f'<div style="position:absolute;left:40px;top:80px;width:{cw}px;height:{ch}px;border-radius:16px;overflow:hidden">{camera_view(s, s.id(pid) + "-me", cw, ch)}'
            f'<svg id="{s.id(pid)}-mesh" viewBox="0 0 {cw} {ch}" style="position:absolute;inset:0;opacity:0">{dots}{iris}</svg>'
            f'<svg id="{s.id(pid)}-pose" viewBox="0 0 {cw} {ch}" style="position:absolute;inset:0;opacity:0">{pose}</svg>'
            f'<div id="{s.id(pid)}-ec" style="position:absolute;right:12px;top:12px;padding:6px 12px;border-radius:999px;background:rgba(10,26,26,.75);font-size:13px;color:#FBBF24;opacity:0">eye contact · iris tracking</div></div>'
            f'<div style="position:absolute;left:40px;top:456px;width:{cw}px;height:30px">{bars}</div>'
            f'<div style="position:absolute;left:40px;top:496px;width:{cw}px">{wd}</div>'
            f'<div id="{s.id(pid)}-gz" class="dp" style="left:40px;top:580px;width:{cw}px;height:170px;opacity:0">{gz}</div>'
            f'<div style="position:absolute;left:740px;top:80px;width:620px;height:540px">{st}</div>')


def s09b():
    s = S("s09b-analyse", lead=0.4)
    window(s, "speechmate.app/session", None, [("an", analyse_page(s, "an"), True)])
    a = f"#{s.id('an')}"
    T0 = [s.at(0, 0.3), s.at(1, 0.05), s.at(1, 0.3), s.at(1, 0.55), s.at(2, 0.1), s.at(2, 0.6), s.ce[2] + 0.5]
    for k, t in enumerate(T0):
        s.tw(f'tl.to("{a}-s{k}",{{opacity:1,duration:0.25}},{t});tl.to("{a}-sp{k}",{{rotation:720,duration:1.4,ease:"none"}},{t});'
             f'tl.to("{a}-sp{k}",{{opacity:0,duration:0.1}},{t + 1.3});tl.to("{a}-ok{k}",{{opacity:1,scale:1,duration:0.3,ease:"back.out(2.5)"}},{t + 1.3});')
        s.sfx.append(("switch_002", t + 1.3))
    # speech recognition: the waveform plays, words land with their timestamps
    for k in range(40):
        h = 8 + (k * 37 % 22)
        s.tw(f'tl.to("{a}-wv{k}",{{height:{h},duration:0.14,yoyo:true,repeat:9,ease:"sine.inOut",delay:{(k % 7) * 0.02}}},{T0[0]});')
    for k in range(10):
        s.tw(f'tl.fromTo("{a}-w{k}",{{opacity:0,y:8}},{{opacity:1,y:0,duration:0.25,ease:"expo.out"}},{T0[0] + 0.2 + k * 0.17});')
    s.tw(f'tl.fromTo("{a}-w4",{{boxShadow:"0 0 0 0 rgba(252,165,165,0)"}},{{boxShadow:"0 0 0 3px rgba(252,165,165,.8)",duration:0.3}},{T0[1] + 0.2});')
    s.tw(f'tl.fromTo("{a}-w9",{{boxShadow:"0 0 0 0 rgba(196,181,253,0)"}},{{boxShadow:"0 0 0 3px rgba(196,181,253,.8)",duration:0.3}},{T0[1] + 0.5});')
    # MediaPipe
    s.tw(f'tl.to("{a}-mesh",{{opacity:1,duration:0.4}},{T0[3]});tl.to("{a}-pose",{{opacity:1,duration:0.4}},{T0[3] + 0.3});tl.to("{a}-ec",{{opacity:1,duration:0.3}},{T0[3] + 0.5});')
    s.sfx.append(("drop_001", T0[3]))
    s.blink(s.id("an") + "-me", T0[3] + 1.0)
    s.tw(f'tl.to("#{s.id("an")}-me .phead",{{rotation:-7,svgOrigin:"200 350",duration:0.35,yoyo:true,repeat:1,ease:"sine.inOut"}},{T0[4] + 0.3});')
    # Gaze Tunneling
    s.tw(f'tl.fromTo("{a}-gz",{{opacity:0,y:16}},{{opacity:1,y:0,duration:0.5,ease:"expo.out"}},{T0[4]});')
    s.sfx.append(("impactSoft_medium_001", T0[4]))
    s.zoom("w", T0[4] + 0.2, 1.16, 330, 700, 0.8)
    s.unzoom("w", T0[5] + 0.2)
    s.callout("cw", "Whisper large-v3", 330, 440, T0[0] + 0.3, MINT, hold=2.2)
    s.callout("cm", "MediaPipe", 470, 90, T0[3] + 0.2, "#93C5FD", hold=2.4)
    return s


def s10b():
    s = S("s10b-factcheck", lead=0.4)
    draft = ('In my internship <span id="{f1}" style="border-radius:6px;padding:0 3px">at Maybank</span>, I built weekly sales dashboards that '
             '<span id="{f2}" style="border-radius:6px;padding:0 3px">raised sales by 30%</span>. When a store manager asked why sales dipped, '
             'I showed one chart, explained the cause in plain words, and suggested what to check next.')
    pg = (chrome(s, "fc", "Progress")
          + '<div class="h1" style="left:200px;top:96px;font-size:30px">Mock interview · your answers</div>'
          + '<div class="illus" style="left:1110px;top:100px">ILLUSTRATIVE</div>'
          + f'<div class="wcard" style="left:200px;top:150px;width:1060px;height:470px">'
          f'<div style="position:absolute;left:24px;top:20px;font-size:17px;font-weight:700">A stronger version of your answer</div>'
          f'<div id="{s.id("st")}" style="position:absolute;left:24px;top:52px;font-size:15px;font-weight:600;color:{LAV_INK}"><span class="dots"><i></i><i></i><i></i></span> Checking names and numbers against your answer, the question and your resume…</div>'
          f'<div style="position:absolute;left:24px;top:96px;width:1010px;height:200px;border-radius:14px;background:#FBF8F1;overflow:hidden">'
          f'<div id="{s.id("scan")}" style="position:absolute;left:0;right:0;top:0;height:34px;background:linear-gradient(rgba(75,47,168,0),rgba(75,47,168,.16),rgba(75,47,168,0))"></div>'
          f'<div id="{s.id("dr")}" style="position:absolute;left:22px;top:20px;width:960px;font-size:20px;line-height:1.7">{draft.format(f1=s.id("f1"), f2=s.id("f2"))}</div>'
          f'<div id="{s.id("fin")}" style="position:absolute;left:22px;top:20px;width:960px;font-size:20px;line-height:1.7;opacity:0">“In my internship I built weekly sales dashboards. When a store manager asked why sales dipped, '
          f'I showed one chart, explained the cause in plain words, and suggested what to check next.”</div></div>'
          + "".join(f'<div id="{s.id(f"nv{k}")}" style="position:absolute;left:{x}px;top:{y}px;padding:5px 12px;border-radius:999px;background:#E5484D;color:#fff;font-size:14px;font-weight:700;opacity:0">✕ never said: “{w}”</div>'
                    for k, (x, y, w) in enumerate([(110, 316, "Maybank"), (560, 316, "30%")]))
          + f'<div id="{s.id("rw")}" style="position:absolute;left:24px;top:370px;font-size:15px;font-weight:600;color:{PINK_INK};opacity:0">Re-writing without them…</div>'
          + f'<div id="{s.id("ok")}" style="position:absolute;left:24px;top:362px;padding:10px 18px;border-radius:12px;background:#E3F3EE;color:{TEAL_INK};font-size:18px;font-weight:700;opacity:0">✓ Fact-checked · only what you actually said</div>'
          + '</div>')
    window(s, "speechmate.app/results", None, [("fc", pg, False)])
    s.tw(f'tl.to("#{s.id("scan")}",{{y:170,duration:1.1,ease:"sine.inOut",yoyo:true,repeat:3}},0.4);')
    for k, (f, t) in enumerate([("f1", s.at(1, 0.15)), ("f2", s.at(1, 0.35))]):
        s.tw(f'tl.to("#{s.id(f)}",{{backgroundColor:"rgba(229,72,77,.18)",color:"#B4232A",textDecoration:"line-through",duration:0.2}},{t});')
        s.tw(f'tl.fromTo("#{s.id(f"nv{k}")}",{{opacity:0,y:8,scale:0.8}},{{opacity:1,y:0,scale:1,duration:0.35,ease:"back.out(2)"}},{t + 0.1});')
        s.sfx.append(("drop_002", t + 0.1))
    t = s.ce[1] + 0.2
    s.tw(f'tl.to("#{s.id("rw")}",{{opacity:1,duration:0.2}},{t});tl.to("#{s.id("rw")}",{{opacity:0,duration:0.2}},{t + 1.2});'
         f'tl.to(["#{s.id("dr")}","#{s.id("nv0")}","#{s.id("nv1")}","#{s.id("st")}"],{{opacity:0,duration:0.3}},{t + 1.2});'
         f'tl.to("#{s.id("fin")}",{{opacity:1,duration:0.4}},{t + 1.4});'
         f'tl.fromTo("#{s.id("ok")}",{{opacity:0,scale:0.8}},{{opacity:1,scale:1,duration:0.4,ease:"back.out(2)"}},{t + 1.7});')
    s.sfx.append(("impactBell_heavy_000", t + 1.7))
    s.mate_say("fc", "Nice one!", t + 2.0, 1.6)
    s.zoom("w", 0.6, 1.14, 700, 330, 1.0)
    s.unzoom("w", s.D - 1.0)
    return s


def s17b():
    s = S("s17b-mate", lead=0.4)
    sugg = ["How did my last session go?", "What should I practise next?", "How do I prepare for a presentation?", "What does the confidence score mean?"]
    panel = (f'<div id="{s.id("mc")}" data-layout-allow-overlap style="position:absolute;z-index:9;right:24px;bottom:116px;width:440px;height:520px;border-radius:20px;background:#fff;'
             f'box-shadow:0 24px 60px rgba(10,26,26,.25);opacity:0;transform-origin:100% 100%">'
             f'<div style="position:absolute;left:0;right:0;top:0;height:60px;border-bottom:1px solid rgba(10,26,26,.08);display:flex;align-items:center;gap:10px;padding:0 18px;font-size:17px;font-weight:700">'
             f'<img src="assets/bots/mate-default.png" alt="" style="width:40px;height:40px">Mate<span style="margin-left:auto;color:#7A8584">✕</span></div>'
             + "".join(f'<div id="{s.id(f"sg{k}")}" class="pill" style="left:18px;top:{78 + k * 46}px;border-radius:999px;font-size:14px">{q}</div>' for k, q in enumerate(sugg))
             + f'<div id="{s.id("uq")}" class="bubble" style="right:18px;top:270px;max-width:300px;background:{ACCENT_INK};color:#fff;font-size:15px;padding:10px 14px;border-radius:16px 16px 4px 16px;opacity:0">What should I practise next?</div>'
             + f'<div id="{s.id("dt")}" class="bubble" style="left:18px;top:330px;background:#F3EEE3;color:#0A0A0A;font-size:15px;padding:10px 14px;opacity:0"><span class="dots"><i></i><i></i><i></i></span></div>'
             + f'<div id="{s.id("rp")}" class="bubble" style="left:18px;top:330px;width:380px;background:#F3EEE3;color:#0A0A0A;font-size:15px;line-height:1.45;padding:12px 14px;border-radius:16px 16px 16px 4px;opacity:0">'
               'Your last mock interview stopped before the result. Do one more and finish each answer with what changed. Your trend is on <u style="color:#1A3A3A;font-weight:700">/progress</u>.'
               '<div style="margin-top:6px"><span class="illus" style="position:static;font-size:10px">ILLUSTRATIVE</span></div></div>'
             + '<div style="position:absolute;left:18px;right:18px;bottom:16px;height:44px;border-radius:12px;border:1.5px solid rgba(10,26,26,.14);font-size:15px;color:#9AA3A2;padding:11px 14px">Ask Mate…</div></div>')
    pg = progress_page(s, "p2").replace('<div class="mb"', panel + '<div class="mb"', 1)
    window(s, "speechmate.app/progress", None, [("p2", pg, False)])
    s.tw(f'tl.set("#{s.id("p2")}-ln",{{strokeDashoffset:0}},0);' + "".join(f'tl.set("#{s.id("p2")}-d{i}",{{opacity:1}},0);' for i in range(7)))
    m = s.life(s.id("p2-mate"))
    s.cursor_at(0.1, 900, 400)
    t = s.tap(0.6, 1378, 704, None, 0.7)
    m.hop(t + 0.05)
    s.tw(f'tl.fromTo("#{s.id("mc")}",{{opacity:0,scale:0.6}},{{opacity:1,scale:1,duration:0.45,ease:"back.out(1.6)"}},{t + 0.1});')
    s.sfx.append(("card-place-1", t + 0.1))
    for k in range(4):
        s.tw(f'tl.fromTo("#{s.id(f"sg{k}")}",{{opacity:0,x:20}},{{opacity:1,x:0,duration:0.3,ease:"expo.out"}},{t + 0.4 + k * 0.1});')
    t = s.tap(t + 1.4, 1110, 266, "sg1", 0.6)
    s.tw(f'tl.to(["#{s.id("sg0")}","#{s.id("sg1")}","#{s.id("sg2")}","#{s.id("sg3")}"],{{opacity:0,duration:0.2}},{t + 0.2});'
         f'tl.fromTo("#{s.id("uq")}",{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.3}},{t + 0.3});'
         f'tl.to("#{s.id("dt")}",{{opacity:1,duration:0.2}},{t + 0.7});tl.to("#{s.id("dt")}",{{opacity:0.4,duration:0.25,yoyo:true,repeat:5}},{t + 0.8});tl.set("#{s.id("dt")}",{{opacity:0}},{t + 2.3});'
         f'tl.fromTo("#{s.id("rp")}",{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.4,ease:"expo.out"}},{t + 2.35});')
    m.state(t + 0.6, 1.8, "working"); m.hop(t + 2.45); m.look(t + 2.9, "left")
    s.sfx.append(("drop_001", t + 2.35))
    s.zoom("w", t + 0.2, 1.18, 1300, 420, 0.8, right=WW)
    return s


def s17c():
    s = S("s17c-measured", lead=0.4)
    rows = [("Speech recognition", "Whisper large-v3 (Groq) · auto language · Manglish prompt", "Word error: 4.9% English, 7.3% Malay"),
            ("Pronunciation", "wav2vec2 phonemes + forced alignment", "Malaysian English counts as regional, not error"),
            ("Eye contact", "MediaPipe Face Mesh · iris position", "% of the time you look at the camera"),
            ("Gaze Tunneling", "gaze stream vs. stumble timings · significance test", "Whether you look away as you lose your words"),
            ("Confidence", "11 measured cues, weakest listed first", "No score unless 30% of the evidence was measured")]
    tr = "".join(f'<div id="{s.id(f"r{k}")}" style="position:absolute;left:0;top:{56 + k * 92}px;width:1060px;height:84px;border-radius:12px;background:#FBF8F1;opacity:0">'
                 f'<div style="position:absolute;left:18px;top:28px;width:220px;font-size:17px;font-weight:700">{a}</div>'
                 f'<div style="position:absolute;left:250px;top:18px;width:420px;font-size:14px;font-family:monospace;line-height:1.45;color:#2A3A39">{b}</div>'
                 f'<div style="position:absolute;left:700px;top:20px;width:340px;font-size:15px;line-height:1.4">{c}</div></div>' for k, (a, b, c) in enumerate(rows))
    pg = (chrome(s, "me", "")
          + '<div class="eb" style="left:200px;top:84px;color:#5C6766">REFERENCE</div>'
          + '<div class="h1" style="left:200px;top:104px;font-size:38px">How it\'s measured</div>'
          + '<div class="sub" style="left:200px;top:152px;width:900px">Every score: the method, the model, and how to read it. Anything that could not be measured is shown as not measured, never estimated.</div>'
          + f'<div style="position:absolute;left:200px;top:200px;width:1060px;height:540px">'
          + '<div style="position:absolute;left:18px;top:14px;font-size:13px;font-weight:700;letter-spacing:.1em;color:#7A8584">METRIC</div>'
          + '<div style="position:absolute;left:250px;top:14px;font-size:13px;font-weight:700;letter-spacing:.1em;color:#7A8584">METHOD · MODEL</div>'
          + '<div style="position:absolute;left:700px;top:14px;font-size:13px;font-weight:700;letter-spacing:.1em;color:#7A8584">WHAT YOU SEE</div>'
          + tr + '</div>')
    window(s, "speechmate.app/progress", "speechmate.app/methodology", [("p3", chrome(s, "p3", "Progress"), False), ("me", pg, False)])
    s.cursor_at(0.0, 1378, 704, fade=False)
    t = s.tap(0.2, 32, 260, None, 0.7)       # the reference book on the rail
    s.swap_page(t, "p3", "me", True)
    for k in range(5):
        s.tw(f'tl.fromTo("#{s.id(f"r{k}")}",{{opacity:0,x:-20}},{{opacity:1,x:0,duration:0.4,ease:"expo.out"}},{t + 0.6 + k * 0.28});')
    s.sfx.append(("card-place-1", t + 0.6))
    for k, tt in enumerate([s.at(0, 0.3), s.at(0, 0.55), s.at(0, 0.8)]):
        y = 200 + 56 + [0, 3, 4][k] * 92 + 42
        s.go(tt, 760, y, 0.5)
        s.tw(f'tl.to("#{s.id(f"r{[0, 3, 4][k]}")}",{{backgroundColor:"#F1ECFD",boxShadow:"0 0 0 2px rgba(75,47,168,.35)",duration:0.25}},{tt + 0.4});')
    s.zoom("w", s.at(0, 0.4), 1.12, 700, 500, 0.9)
    return s


SCENES = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s09b, s10, s10b, s11, s12, s13, s14, s15, s16, s17, s17b, s17c, s18, s19]

if __name__ == "__main__":
    # reuse build.main's assembly (index, audio, captions) with these scenes
    import types
    src = Path(B.__file__).read_text()
    start = src.index("def main():")
    body = src[start:src.index('\nif __name__ == "__main__":')]
    body = body.replace("scenes = [f() for f in (s01, s02, s03, s04, s05, s06, s07, s07b, s08, s09, s10)]", "scenes = [f() for f in SCENES]")
    body = body.replace('s3 = starts["s03-intro"]', 's3 = starts["s03-intro"]')
    for old in [f for f in (COMP / "compositions").glob("*.html")]:
        old.unlink()
    ns = dict(globals()); exec(body, ns); ns["main"]()
