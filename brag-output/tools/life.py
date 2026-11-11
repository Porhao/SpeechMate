"""Bring a character to life: a stack of real pose frames from the bot-avatars component (front,
left, right, down, tilts, working, eyes closed) driven by a schedule of glances, blinks, hops,
nods and talking. Deterministic (seeded), so every render is identical.
"""
import random

FRAMES = ["default", "left", "right", "down", "tiltl", "tiltr", "working", "sleeping"]


def bot_html(fid, who, style, start="default"):
    """the frames, stacked; `sleeping` (eyes shut) sits on top and only flashes for a blink"""
    imgs = "".join(
        f'<img id="{fid}-{f}" src="assets/bots/{who}-{f}.png" alt="" '
        f'style="position:absolute;inset:0;width:100%;height:100%;opacity:{1 if f == start else 0};{"z-index:2;" if f == "sleeping" else ""}">'
        for f in FRAMES)
    # outer: breathes all the time; inner (fid): hops, nods, talks
    return f'<div id="{fid}-br" style="position:absolute;{style}"><div id="{fid}" style="position:absolute;inset:0">{imgs}</div></div>'


def swap(fid, a, b, t):
    """show frame b instead of a, at once (the new frame goes on before the old one goes off: never see-through)"""
    return f'tl.set("#{fid}-{b}",{{opacity:1}},{t});tl.set("#{fid}-{a}",{{opacity:0}},{round(t + 0.034, 3)});'


class Life:
    def __init__(self, fid, seed=1, start="default"):
        self.fid, self.cur, self.ev = fid, start, []
        self.rng = random.Random(seed)
        self.busy = []          # (t0, t1) spans where idle life must not interrupt (talking, hops)
        self.pending = []

    def _free(self, t, d=0.5):
        return all(not (a - 0.2 < t + d and t < b + 0.2) for a, b in self.busy)

    def look(self, t, frame):
        self.ev.append((t, "look", frame))

    def blink(self, t):
        self.ev.append((t, "blink", None))

    def hop(self, t, h=26):
        self.ev.append((t, "hop", h)); self.busy.append((t, t + 0.75))

    def nod(self, t):
        self.ev.append((t, "nod", None)); self.busy.append((t, t + 0.7))

    def spin(self, t):
        self.ev.append((t, "spin", None)); self.busy.append((t, t + 0.9))

    def talk(self, t, d):
        """speaking: the working face, a bounce in time with the words, glances at the listener"""
        self.ev.append((t, "talk", d)); self.busy.append((t, t + d))

    def state(self, t, d, frame):
        """hold a frame (e.g. working while busy), then go back"""
        self.ev.append((t, "hold", (d, frame))); self.busy.append((t, t + d))

    def idle(self, t0, t1, looks=("left", "default", "right", "default", "down", "default", "tiltl", "default"), gap=(1.6, 3.2), blinks=True, hops=0):
        """glances and blinks between t0 and t1, around whatever else is scheduled (worked out at compile)"""
        self.pending.append((t0, t1, looks, gap, blinks, hops))

    def _idle(self, t0, t1, looks, gap, blinks, hops):
        t, k = t0 + self.rng.uniform(0.3, 1.0), 0
        while t < t1 - 0.4:
            if self._free(t):
                if blinks and self.rng.random() < 0.45:
                    self.blink(t)
                else:
                    self.look(t, looks[k % len(looks)]); k += 1
            t += self.rng.uniform(*gap)
        for _ in range(hops):
            for _try in range(8):
                ht = self.rng.uniform(t0 + 0.5, t1 - 1)
                if self._free(ht, 0.8):
                    self.hop(ht, 18); break

    def compile(self):
        for args in self.pending:
            self._idle(*args)
        js, cur, fid = [], self.cur, self.fid
        for t, kind, arg in sorted(self.ev, key=lambda e: e[0]):
            t = round(t, 3)
            if kind == "look" and arg != cur:
                js.append(swap(fid, cur, arg, t))
                cur = arg
            elif kind == "blink":
                js.append(f'tl.set("#{fid}-sleeping",{{opacity:1}},{t});tl.set("#{fid}-sleeping",{{opacity:0}},{round(t + 0.13, 3)});')
            elif kind == "hop":
                js.append(f'tl.to("#{fid}",{{y:-{arg},scaleY:1.06,scaleX:0.96,duration:0.2,ease:"power2.out"}},{t});'
                          f'tl.to("#{fid}",{{y:0,scaleY:1,scaleX:1,duration:0.5,ease:"bounce.out"}},{round(t + 0.2, 3)});')
            elif kind == "nod":
                js.append(f'tl.to("#{fid}",{{rotation:6,transformOrigin:"50% 90%",duration:0.17,yoyo:true,repeat:3,ease:"sine.inOut"}},{t});')
            elif kind == "spin":
                js.append(f'tl.to("#{fid}",{{rotation:"+=360",transformOrigin:"50% 60%",duration:0.8,ease:"power2.inOut"}},{t});')
            elif kind in ("talk", "hold"):
                d, frame = (arg, "working") if kind == "talk" else arg
                back = cur
                js.append(swap(fid, cur, frame, t))
                if kind == "talk":
                    n = max(1, int(d / 0.34))
                    js.append(f'tl.to("#{fid}",{{y:-5,scaleY:1.035,scaleX:0.985,transformOrigin:"50% 100%",duration:0.17,yoyo:true,repeat:{2 * n - 1},ease:"sine.inOut"}},{t});')
                js.append(swap(fid, frame, back, round(t + d, 3)))
        if self.pending:  # a slow breath under everything else, so the character is never frozen
            t0, t1 = min(p[0] for p in self.pending), max(p[1] for p in self.pending)
            n = max(1, int((t1 - t0) / 2.4))
            js.append(f'tl.fromTo("#{fid}-br",{{y:0,scaleY:1,scaleX:1}},{{y:-4,scaleY:1.03,scaleX:0.985,transformOrigin:"50% 100%",'
                      f'duration:1.2,ease:"sine.inOut",yoyo:true,repeat:{2 * n - 1}}},{round(t0, 3)});')
        return js
