"""The home page opener: a brush drops onto the page and paints the line under Caitlin's name.

It is all CSS, and only transform and opacity ever change, so the browser runs it on its
compositor. That means three things:

- it starts on the first frame the page is drawn, with no script to wait for (on a phone the
  scripts can arrive seconds after the page appears, behind the photos);
- it stays smooth while the page is still loading and the main thread is busy;
- the line and the brush cannot drift apart. The line is revealed by a window that slides right
  while its contents slide left by the same amount, so the line stays put and only the window
  grows; the brush rides the window's edge, using the very same keyframes.

The brush also has to rise and fall with the wave of the line. CSS cannot follow a curve for us,
so this script samples the line's own Bezier curve and writes the brush's height out as keyframes.

    python -I _src/opener.py    rewrites the block between the opener markers in assets/site.css

Edit the timings here and rerun; do not edit the generated block by hand.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = ROOT / "assets" / "site.css"
HOME = ROOT / "_src" / "pages" / "00-home.html"

# The line under the name, as drawn in 00-home.html: a 600 by 18 drawing stretched to the line's width
PATH = "M2 9 C 80 4, 140 14, 220 9 S 360 3, 440 10 S 560 14, 598 8"
SEGMENTS = [((2, 9), (80, 4), (140, 14), (220, 9)),          # the S commands written out in full
            ((220, 9), (300, 4), (360, 3), (440, 10)),
            ((440, 10), (520, 17), (560, 14), (598, 8))]

# Timings, in seconds from the moment the page is first drawn
START = 0.10    # the brush starts to drop towards the page
DROP = 0.45     # it lands on the start of the line
PAINT = 1.40    # it paints the line
LIFT = 0.60     # it lifts away and fades
PAINT_EASE = (0.35, 0.05, 0.25, 1)   # quick to get going, a long gentle finish
DRY = 1.20      # the wet sheen on the paint fades out after the brush has passed

MARGIN = 10     # px the painted window reaches past each end of the line, so its glow is not cut off
WIDTH = 440     # px, a typical line width; the brush's rise and fall barely depends on it
SAMPLES = 48    # keyframes for the brush's rise and fall


def cubic(p0, p1, p2, p3, t):
    m = 1 - t
    return tuple(m ** 3 * a + 3 * m * m * t * b + 3 * m * t * t * c + t ** 3 * d
                 for a, b, c, d in zip(p0, p1, p2, p3))


def bezier_ease(x1, y1, x2, y2):
    """The CSS cubic-bezier() timing function, as a Python function of progress."""
    def f(x):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            s = (lo + hi) / 2
            bx = 3 * x1 * s * (1 - s) ** 2 + 3 * x2 * s * s * (1 - s) + s ** 3
            lo, hi = (s, hi) if bx < x else (lo, s)
        s = (lo + hi) / 2
        return 3 * y1 * s * (1 - s) ** 2 + 3 * y2 * s * s * (1 - s) + s ** 3
    return f


TABLE = [cubic(*seg, i / 800) for seg in SEGMENTS for i in range(800)] + [SEGMENTS[-1][3]]


def y_at(x):
    """The line's height at a given across-position, in its own 600 by 18 units."""
    if x <= TABLE[0][0]:
        return TABLE[0][1]
    if x >= TABLE[-1][0]:
        return TABLE[-1][1]
    lo, hi = 0, len(TABLE) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if TABLE[mid][0] <= x else (lo, mid)
    (x0, y0), (x1, y1) = TABLE[lo], TABLE[hi]
    return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def pct(fraction):
    return ("%.3f" % (fraction * 100)).rstrip("0").rstrip(".") + "%"


def secs(v):
    return ("%.3f" % v).rstrip("0").rstrip(".") + "s"


def bez(points):
    return "cubic-bezier(%s)" % ", ".join(("%g" % p) for p in points)


def pose(x, y, rx, ry, rz, s):
    # The same functions in the same order in every keyframe, so the browser interpolates each one
    return ("translate3d(%gpx, %gpx, 0) perspective(800px) rotateX(%gdeg) rotateY(%gdeg) rotateZ(%gdeg) scale(%g)"
            % (x, y, rx, ry, rz, s))


def shade(x, y, rz, sx, sy):
    return "translate(%gpx, %gpx) rotate(%gdeg) scale(%g, %g)" % (x, y, rz, sx, sy)


def keyframes(name, frames, total):
    """frames: (seconds into the animation, declarations, timing function or None)."""
    out = ["@keyframes %s {" % name]
    for t, decl, timing in frames:
        if timing:
            decl = decl + "; animation-timing-function: " + timing
        out.append("  %s { %s; }" % (pct(t / total), decl))
    out.append("}")
    return "\n".join(out)


def build():
    paint_at = START + DROP
    lift_at = paint_at + PAINT
    pose_len = DROP + PAINT + LIFT
    land = DROP
    lift = DROP + PAINT
    swoop = bez((0.45, 0, 0.25, 1))
    away = bez((0.4, 0, 0.9, 0.5))

    # The brush's rise and fall: where the window's edge is, at each moment of the paint, on the line
    ease = bezier_ease(*PAINT_EASE)
    rows = ["@keyframes pen-y {"]
    for i in range(SAMPLES + 1):
        t = i / SAMPLES
        edge = -MARGIN + ease(t) * (WIDTH + 2 * MARGIN)
        rows.append("  %s { transform: translateY(%.2fpx); }" % (pct(t), y_at(edge / WIDTH * 600) - 9))
    rows.append("}")
    pen_y = "\n".join(rows)

    # The brush itself: drops in from in front of the page, tilts back out of it while it paints
    # (the handle comes towards you), then lifts away towards you and fades
    pen_pose = keyframes("pen-pose", [
        (0, "transform: %s; opacity: 0" % pose(90, -190, -38, 26, -14, 1.6), swoop),
        (0.16, "opacity: 1", None),
        (land, "transform: %s" % pose(0, 0, -26, 0, 26, 0.94), "ease-out"),
        (land + 0.11, "transform: %s" % pose(0, 0, -26, 0, 29, 1), "ease-in-out"),
        (land + 0.5, "transform: %s" % pose(0, 0, -24, 0, 32, 1), "ease-in-out"),
        (land + 0.95, "transform: %s" % pose(0, 0, -27, 0, 27, 1), "ease-in-out"),
        (lift, "transform: %s; opacity: 1" % pose(0, 0, -26, 0, 28, 1), away),
        (pose_len, "transform: %s; opacity: 0" % pose(70, -170, -40, -24, 8, 1.4), None),
    ], pose_len)

    # Its shadow on the page: far off and faint while the brush is high, tight under it while it paints
    pen_shadow = keyframes("pen-shadow", [
        (0, "transform: %s; opacity: 0" % shade(170, 70, 22, 1.3, 1.15), swoop),
        (land, "transform: %s; opacity: 0.42" % shade(9, 7, 38, 1, 0.92), None),
        (lift, "transform: %s; opacity: 0.42" % shade(9, 7, 38, 1, 0.92), away),
        (pose_len, "transform: %s; opacity: 0" % shade(150, 60, 28, 1.3, 1.15), None),
    ], pose_len)

    dry_len = PAINT + 0.1 + DRY
    css = f"""/* opener:start  (written by _src/opener.py: change the timings there and rerun it, not here) */
/* The line under the name, painted in by a brush as the home page opens. Only transform and opacity
   move, so it all runs on the compositor: it starts on the first frame, needs no script, and the
   line's edge and the brush's tip share one set of keyframes, so they cannot drift apart. */
.ink {{ position: relative; z-index: 2; width: min(100%, 36rem); height: 18px; margin: 1rem 0 1.5rem; container-type: inline-size; pointer-events: none; }}
.ink-clip {{ position: absolute; left: -{MARGIN}px; right: -{MARGIN}px; top: -18px; bottom: -18px; overflow: hidden; }}
.ink-slide {{ position: absolute; inset: 0; }}
.ink-slide svg {{ position: absolute; left: {MARGIN}px; top: 18px; width: calc(100% - {2 * MARGIN}px); height: 18px; overflow: visible; }}
.ink-slide path {{ fill: none; stroke: var(--violet); stroke-linecap: round; vector-effect: non-scaling-stroke; }}
.ink-line path {{ stroke-width: 4.5px; filter: drop-shadow(0 0 6px rgba(154,127,209,0.8)); }}
.ink-wet {{ opacity: 0; }}
.ink-wet path {{ stroke-width: 12px; filter: blur(3px); }}
.pen-x {{ position: absolute; left: -{MARGIN}px; right: -{MARGIN}px; top: 0; height: 18px; }}
.pen-y {{ position: absolute; right: 0; top: 9px; width: 0; height: 0; }}
.pen, .pen-shadow {{ position: absolute; bottom: 0; --h: clamp(130px, 50cqw, 340px); height: var(--h); width: calc(var(--h) * 0.375); left: calc(var(--h) * -0.1875); transform-origin: 50% 100%; opacity: 0; }}
.pen svg, .pen-shadow svg {{ display: block; width: 100%; height: 100%; overflow: visible; }}
.pen-shadow svg {{ filter: blur(6px); }}
.ink .fleck {{ position: absolute; left: 100%; top: 8px; width: var(--s); height: var(--s); margin: calc(var(--s) / -2) 0 0 calc(var(--s) / -2); border-radius: 50%; background: var(--violet); box-shadow: 0 0 6px rgba(154,127,209,0.8); opacity: 0; }}
.name-glow {{ position: absolute; z-index: -1; left: -12%; top: -8%; width: 100%; height: 58%; pointer-events: none; opacity: 0; background: radial-gradient(ellipse at 38% 45%, rgba(154,127,209,0.5), rgba(154,127,209,0.16) 42%, transparent 70%); }}
@media (prefers-reduced-motion: no-preference) {{
  .ink-clip, .pen-x {{ animation: ink-x {secs(PAINT)} {bez(PAINT_EASE)} {secs(paint_at)} both; }}
  .ink-slide {{ animation: ink-x-back {secs(PAINT)} {bez(PAINT_EASE)} {secs(paint_at)} both; }}
  .pen-y {{ animation: pen-y {secs(PAINT)} linear {secs(paint_at)} both; }}
  .pen {{ animation: pen-pose {secs(pose_len)} linear {secs(START)} both; }}
  .pen-shadow {{ animation: pen-shadow {secs(pose_len)} linear {secs(START)} both; }}
  .ink-wet {{ animation: ink-dry {secs(dry_len)} linear {secs(paint_at)} both; }}
  .ink .fleck {{ animation: fleck var(--t) cubic-bezier(0.1, 0.6, 0.4, 1) {secs(lift_at)} both; }}
  .name-glow {{ animation: name-glow 1.8s linear {secs(paint_at - 0.15)} both; }}
}}
@keyframes ink-x {{ from {{ transform: translateX(-100%); }} to {{ transform: translateX(0); }} }}
@keyframes ink-x-back {{ from {{ transform: translateX(100%); }} to {{ transform: translateX(0); }} }}
{pen_y}
{pen_pose}
{pen_shadow}
@keyframes ink-dry {{ 0% {{ opacity: 0.35; }} {pct((PAINT + 0.1) / dry_len)} {{ opacity: 0.35; }} 100% {{ opacity: 0; }} }}
@keyframes fleck {{ 0% {{ transform: translate(0, 0) scale(1); opacity: 0; }} 8% {{ opacity: 0.95; }} 100% {{ transform: translate(var(--dx), var(--dy)) scale(0.2); opacity: 0; }} }}
@keyframes name-glow {{ 0% {{ opacity: 0; animation-timing-function: ease-out; }} 20% {{ opacity: 1; animation-timing-function: ease-in-out; }} 100% {{ opacity: 0; }} }}
/* opener:end */"""
    return css


def main():
    if PATH not in HOME.read_text(encoding="utf-8"):
        raise SystemExit("The line in 00-home.html is not the one this script samples; update PATH and SEGMENTS.")
    block = build()
    text = CSS.read_text(encoding="utf-8")
    begin, end = "/* opener:start", "/* opener:end */"
    if begin in text:
        a = text.index(begin)
        b = text.index(end, a) + len(end)
        text = text[:a] + block + text[b:]
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    CSS.write_text(text, encoding="utf-8", newline="\n")
    print("opener written:", block.count("\n") + 1, "lines")


if __name__ == "__main__":
    main()
