from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
source = root / "tests/kanban_hold_harness/artifacts/390.png"
out = root / ".preview/hold-drag-density-v3-poster.png"
canvas = Image.new("RGB", (1800, 1080), "#F4EFE4")
d = ImageDraw.Draw(canvas)
font = "/usr/share/fonts/TTF/DejaVuSans.ttf"
bold = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
f18 = ImageFont.truetype(font, 18)
f24 = ImageFont.truetype(bold, 24)
f34 = ImageFont.truetype(bold, 34)
f72 = ImageFont.truetype(bold, 72)
d.rectangle((0, 0, 1800, 14), fill="#1D4ED8")
d.text((72, 44), "HERMES KANBAN  /  PRIVATE INTEGRATION PROOF", font=f18, fill="#303030")
d.text((72, 78), "HOLD. DRAG. DENSER.", font=f72, fill="#111111")
d.text((76, 175), "APPROVED INPUTS COMPOSED • COMBINED MATRIX PASS • TAILNET :8450", font=f24, fill="#1D4ED8")
shot = Image.open(source).convert("RGB")
scale = min(820 / shot.width, 760 / shot.height)
shot = shot.resize((round(shot.width * scale), round(shot.height * scale)), Image.Resampling.LANCZOS)
sx, sy = 72, 250
canvas.paste(shot, (sx, sy))
d.rectangle((sx - 2, sy - 2, sx + shot.width + 2, sy + shot.height + 2), outline="#111111", width=4)
callouts = [
    ("01", "STRICT HOLD ORACLE", "199ms stays inert; 200ms arms.\nExact 9px slop remains eligible."),
    ("02", "INPUTS STAY NATIVE", "Mouse drag remains native. Touch tap\nand scroll stay untouched before arm."),
    ("03", "COMPACT, NOT CRAMPED", "Density alignment is composed across\n320 / 360 / 390 / 430 / 1280."),
]
colors = ["#D92D20", "#1D4ED8", "#16803A"]
for i, ((num, title, body), color) in enumerate(zip(callouts, colors)):
    y = 285 + i * 220
    d.ellipse((1050, y, 1110, y + 60), fill=color)
    d.text((1063, y + 14), num, font=f24, fill="white")
    d.text((1140, y), title, font=f34, fill="#111111")
    d.multiline_text((1140, y + 58), body, font=f24, fill="#303030", spacing=8)
d.rectangle((1048, 930, 1715, 994), fill="#111111")
d.text((1080, 949), "DECISION  →  REVIEW PRIVATE :8450", font=f24, fill="white")
d.text((72, 1033), "Product dcb6804e9411c9559e9f53a3958876882ec247da  •  Standalone Kanban WebUI  •  Synthetic isolated board  •  No public PR mutation", font=f18, fill="#444444")
canvas.save(out, format="PNG", compress_level=1)
print(out)
