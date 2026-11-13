from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
source = ROOT.parent / "tests/kanban_hold_harness/artifacts/430.png"
out = ROOT / "mobile-interactions-e78904f1-editorial.png"
telegram_out = ROOT / "mobile-interactions-e78904f1-editorial-telegram.jpg"
canvas = Image.new("RGB", (1800, 1800), "#f4f0e8")
draw = ImageDraw.Draw(canvas)
font_path = "/usr/share/fonts/TTF/DejaVuSans.ttf"
bold_path = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
mono_path = "/usr/share/fonts/TTF/DejaVuSansMono.ttf"
font = lambda path, size: ImageFont.truetype(path, size)

# Top rule and header
draw.rectangle((0, 0, 1800, 24), fill="#e63e32")
draw.text((84, 74), "HERMES KANBAN MOBILE INTERACTIONS", font=font(bold_path, 30), fill="#d2362b")
draw.text((84, 130), "Mobile lanes now", font=font(bold_path, 102), fill="#161616")
draw.text((84, 240), "move on intent.", font=font(bold_path, 102), fill="#161616")
draw.text((88, 370), "PRIVATE PREVIEW ACTIVE  |  exact approved product e78904f1", font=font(mono_path, 28), fill="#1769aa")

# Summary cards
cards = [
    (84, "01", "HOLD", "199ms stays inert.\n200ms arms drag." , "#d2362b"),
    (636, "02", "GESTURE", "Vertical scroll stays native.\nHorizontal moves one lane.", "#1769aa"),
    (1188, "03", "SCOPE", "Desktop behavior stays intact.\nBaseline :8450 is untouched.", "#278657"),
]
for x, number, title, body, accent in cards:
    draw.rectangle((x, 440, x + 492, 650), outline="#161616", width=4)
    draw.rectangle((x, 440, x + 14, 650), fill=accent)
    draw.text((x + 34, 468), number, font=font(mono_path, 28), fill=accent)
    draw.text((x + 104, 462), title, font=font(bold_path, 34), fill="#161616")
    draw.multiline_text((x + 34, 530), body, font=font(font_path, 25), fill="#313131", spacing=8)

# Dominant actual evidence frame
frame = (84, 710, 1716, 1505)
draw.rectangle(frame, fill="#111111", outline="#161616", width=4)
shot = Image.open(source).convert("RGB")
# Keep whole mobile screenshot uncropped and large enough to inspect.
target_h = 735
target_w = round(shot.width * target_h / shot.height)
shot = shot.resize((target_w, target_h), Image.Resampling.LANCZOS)
x0 = 900 - target_w // 2
canvas.paste(shot, (x0, 740))
draw.text((116, 748), "ACTUAL 430 PX CAPTURE", font=font(mono_path, 24), fill="#f4f0e8")
draw.text((118, 794), "Synthetic isolated board", font=font(font_path, 24), fill="#b9b9b9")
draw.text((118, 842), "No production data", font=font(font_path, 24), fill="#b9b9b9")

# Evidence callouts
callouts = [
    (84, "BOUNDARY", "199 / 200 ms passed", "#d2362b"),
    (636, "MATRIX", "320  360  390  430  1280", "#1769aa"),
    (1188, "BYTES", "JS + CSS exact hashes", "#278657"),
]
for x, label, value, color in callouts:
    draw.rectangle((x, 1545, x + 492, 1658), outline="#161616", width=3)
    draw.rectangle((x, 1545, x + 492, 1557), fill=color)
    draw.text((x + 24, 1574), label, font=font(bold_path, 23), fill=color)
    draw.text((x + 24, 1612), value, font=font(font_path, 22), fill="#161616")

draw.text((84, 1712), "Hermes standalone Kanban WebUI  |  evidence ba17e7644  |  Tailnet-only  |  baseline :8450 unchanged", font=font(mono_path, 22), fill="#4b4b4b")
canvas.save(out, format="PNG", compress_level=1)
canvas.resize((1080, 1080), Image.Resampling.LANCZOS).save(telegram_out, format="JPEG", quality=90, optimize=True)
print(out)
print(telegram_out)
