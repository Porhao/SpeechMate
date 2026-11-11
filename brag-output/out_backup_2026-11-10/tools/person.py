"""The learner: a flat, clay-palette person drawn in SVG, used in the real-life scenes and as the
camera feed of the demo sessions. Parts carry classes so a scene can animate them (and the mirror
reflection, which is the same drawing flipped, moves with it):
  .pbody (bob, slump) .phead (tilt) .peyes (blink) .pmouth (talk) .psmile .parm (gesture) .pbrow
"""

SKIN, SKIN_SHADE, HAIR, HOODIE, HOODIE_SHADE, MOUTH = "#C98B5E", "#B57A50", "#1D1A18", "#2F6B6B", "#245656", "#6B2A22"


def person(pid, hoodie=HOODIE, shade=HOODIE_SHADE, mouth="closed", extra=""):
    """viewBox 0 0 400 600, head and torso, facing the viewer. mouth: closed | open | smile"""
    m = {
        "closed": f'<ellipse class="pmouth" cx="200" cy="318" rx="15" ry="5" fill="{MOUTH}"/>',
        "open": f'<ellipse class="pmouth" cx="200" cy="320" rx="16" ry="11" fill="{MOUTH}"/>',
        "smile": f'<path class="psmile" d="M180 312 Q200 334 220 312" stroke="{MOUTH}" stroke-width="7" fill="none" stroke-linecap="round"/>',
    }[mouth]
    return f"""<g id="{pid}" class="pbody" style="transform-box:fill-box;transform-origin:50% 100%">
  <path d="M84 600 C84 452 126 392 200 392 C274 392 316 452 316 600 Z" fill="{hoodie}"/>
  <path d="M150 400 C160 440 240 440 250 400 C236 392 164 392 150 400 Z" fill="{shade}"/>
  <rect x="181" y="336" width="38" height="62" rx="12" fill="{SKIN_SHADE}"/>
  <g class="parm" style="transform-box:view-box;transform-origin:292px 452px">
    <path d="M276 440 C318 452 340 500 334 546 L300 552 C300 516 290 490 266 474 Z" fill="{shade}"/>
    <circle cx="318" cy="552" r="22" fill="{SKIN}"/>
  </g>
  <g class="phead" style="transform-box:view-box;transform-origin:200px 350px">
    <circle cx="122" cy="268" r="15" fill="{SKIN_SHADE}"/><circle cx="278" cy="268" r="15" fill="{SKIN_SHADE}"/>
    <ellipse cx="200" cy="262" rx="78" ry="90" fill="{SKIN}"/>
    <path d="M118 258 C108 170 156 146 206 148 C258 150 296 178 284 258 C272 214 240 198 204 202 C168 206 138 220 118 258 Z" fill="{HAIR}"/>
    <g class="pbrow"><rect x="156" y="238" width="32" height="8" rx="4" fill="{HAIR}"/><rect x="212" y="238" width="32" height="8" rx="4" fill="{HAIR}"/></g>
    <g class="peyes" style="transform-box:fill-box;transform-origin:50% 50%"><ellipse cx="172" cy="272" rx="8.5" ry="10.5" fill="{HAIR}"/><ellipse cx="228" cy="272" rx="8.5" ry="10.5" fill="{HAIR}"/></g>
    <ellipse cx="156" cy="300" rx="13" ry="7" fill="#E07A6A" opacity=".35"/><ellipse cx="244" cy="300" rx="13" ry="7" fill="#E07A6A" opacity=".35"/>
    <g style="transform-box:fill-box;transform-origin:50% 50%">{m}</g>
  </g>
  {extra}
</g>"""


def svg(inner, w=400, h=600, extra_attr=""):
    return f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" {extra_attr}>{inner}</svg>'


if __name__ == "__main__":
    # a quick look: the three mouth states side by side
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "person.html"
    cells = "".join(f'<div style="width:400px;height:600px">{svg(person("p" + m, mouth=m))}</div>' for m in ("closed", "open", "smile"))
    open(out, "w").write(f'<!doctype html><body style="margin:0;display:flex;background:#FFFAF0">{cells}</body>')
