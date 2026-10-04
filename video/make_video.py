"""코드만으로 30초짜리 16:9 모션 그래픽 영상을 만든다.

Pillow로 프레임을 그려 ffmpeg로 바로 넘기고, numpy로 합성한 배경음을 입힌다.

    pip install pillow numpy
    python video/make_video.py            # -> video/output.mp4
"""

import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
FPS = 30
DURATION = 30.0
SAMPLE_RATE = 44100
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BG = (14, 17, 28)
FG = (236, 240, 248)
MUTED = (140, 150, 175)
PALETTE = [(255, 107, 129), (255, 186, 73), (82, 214, 160), (86, 164, 255), (178, 124, 255)]

# (시작, 끝, 장면 함수 이름) — 장면 경계에서 0.6초 크로스페이드
SCENES = [
    (0.0, 6.0, "intro"),
    (6.0, 12.5, "orbits"),
    (12.5, 19.0, "waves"),
    (19.0, 25.0, "bars"),
    (25.0, 30.0, "outro"),
]
FADE = 0.6

_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT_PATH, size)
    return _fonts[size]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def text_center(draw, y, text, size, fill):
    f = font(size)
    w = draw.textlength(text, font=f)
    draw.text(((W - w) / 2, y), text, font=f, fill=fill)


def caption(draw, t, number, title, sub):
    """장면 왼쪽 위의 번호 + 제목, 0.8초에 걸쳐 나타남."""
    a = ease(t / 0.8)
    x = 70 - 30 * (1 - a)
    draw.text((x, 56), f"{number:02d}", font=font(26), fill=mix(BG, PALETTE[number % 5], a))
    draw.text((x + 50, 50), title, font=font(36), fill=mix(BG, FG, a))
    draw.text((x + 50, 98), sub, font=font(20), fill=mix(BG, MUTED, a))


def new_frame():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


# ---------------------------------------------------------------- 장면들


def scene_intro(t):
    img, d = new_frame()
    # 배경 격자
    for gx in range(0, W, 40):
        d.line([(gx, 0), (gx, H)], fill=(20, 24, 38))
    for gy in range(0, H, 40):
        d.line([(0, gy), (W, gy)], fill=(20, 24, 38))

    title = "영상만들기"
    shown = min(len(title), int(max(t - 0.4, 0) / 0.28))
    f = font(110)
    full_w = d.textlength(title, font=f)
    x0 = (W - full_w) / 2
    d.text((x0, 230), title[:shown], font=f, fill=FG)
    cursor_x = x0 + d.textlength(title[:shown], font=f) + 8
    if int(t * 2.5) % 2 == 0 or shown < len(title):
        d.rectangle([cursor_x, 245, cursor_x + 10, 350], fill=PALETTE[0])

    a = ease((t - 2.2) / 0.8)
    text_center(d, 390, "Python  ·  Pillow  ·  numpy  ·  ffmpeg", 30, mix(BG, MUTED, a))

    # 아래쪽 컬러 바가 차오름
    b = ease((t - 2.8) / 1.5)
    seg = 160
    total = seg * len(PALETTE)
    bx = (W - total) / 2
    for i, c in enumerate(PALETTE):
        part = min(max(b * len(PALETTE) - i, 0), 1)
        if part > 0:
            d.rectangle([bx + i * seg, 470, bx + i * seg + seg * part, 478], fill=c)
    return img


def scene_orbits(t):
    img, d = new_frame()
    cx, cy = W / 2 + 120, H / 2 + 30
    grow = ease(t / 1.5)
    for ring in range(1, 7):
        r = ring * 42 * grow
        n = ring * 6
        speed = (0.9 if ring % 2 else -0.7) / ring ** 0.5
        color = PALETTE[ring % 5]
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(30, 36, 56))
        for k in range(n):
            ang = 2 * math.pi * k / n + t * speed * 2
            px, py = cx + r * math.cos(ang), cy + r * math.sin(ang)
            s = 4 + 2 * math.sin(t * 3 + k)
            d.ellipse([px - s, py - s, px + s, py + s], fill=color)
    # 가운데 맥동하는 원
    pr = 18 + 6 * math.sin(t * 4)
    d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=FG)

    glow = img.filter(ImageFilter.GaussianBlur(8))
    img = Image.blend(img, glow, 0.35)
    d = ImageDraw.Draw(img)
    caption(d, t, 1, "도형", "삼각함수로 궤도를 그립니다")
    return img


def scene_waves(t):
    img, d = new_frame()
    reveal = ease(t / 1.2)
    xs = np.linspace(0, W, 320)
    for i, c in enumerate(PALETTE):
        amp = 70 + 25 * i
        freq = 0.006 + 0.0018 * i
        phase = t * (1.6 + 0.35 * i) + i
        ys = H / 2 + 50 + amp * reveal * np.sin(xs * freq + phase) * np.sin(t * 0.8 + i * 0.6)
        pts = list(zip(xs.tolist(), ys.tolist()))
        d.line(pts, fill=c, width=4)
    glow = img.filter(ImageFilter.GaussianBlur(10))
    img = Image.blend(img, glow, 0.4)
    d = ImageDraw.Draw(img)
    caption(d, t, 2, "파형", "다섯 개의 사인파가 겹쳐 흐릅니다")
    return img


def scene_bars(t):
    img, d = new_frame()
    n = 16
    base_y = H - 110
    bw = 52
    gap = 16
    x0 = (W - (n * bw + (n - 1) * gap)) / 2
    d.line([(x0 - 20, base_y), (W - x0 + 20, base_y)], fill=(50, 58, 84), width=2)
    for i in range(n):
        delay = i * 0.08
        g = ease((t - 0.3 - delay) / 0.9)
        target = 120 + 300 * (0.5 + 0.5 * math.sin(i * 0.7 + t * 1.3)) * (0.6 + 0.4 * math.cos(i * 0.31))
        h = target * g
        c = PALETTE[i % 5]
        x = x0 + i * (bw + gap)
        d.rounded_rectangle([x, base_y - h, x + bw, base_y], radius=8, fill=c)
        if h > 30:
            val = f"{int(h / 4)}"
            tw = d.textlength(val, font=font(18))
            d.text((x + (bw - tw) / 2, base_y - h - 28), val, font=font(18), fill=MUTED)
    caption(d, t, 3, "데이터", "막대가 실시간으로 움직입니다")
    return img


def scene_outro(t):
    img, d = new_frame()
    # 퍼져 나가는 동심원
    for k in range(6):
        r = ((t * 140 + k * 90) % 540)
        c = mix(PALETTE[k % 5], BG, 0.45 + 0.55 * r / 540)
        d.ellipse([W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r], outline=c, width=3)
    a = ease((t - 0.3) / 1.0)
    text_center(d, 270, "감사합니다", 96, mix(BG, FG, a))
    b = ease((t - 1.2) / 1.0)
    text_center(d, 400, "이 영상은 전부 코드로 만들었습니다", 30, mix(BG, MUTED, b))
    # 마지막 0.8초 동안 검게
    out = 1 - ease((t - (SCENES[-1][1] - SCENES[-1][0] - 0.8)) / 0.8)
    if out < 1:
        img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, out)
    return img


SCENE_FUNCS = {
    "intro": scene_intro,
    "orbits": scene_orbits,
    "waves": scene_waves,
    "bars": scene_bars,
    "outro": scene_outro,
}


def render_frame(time):
    for idx, (start, end, name) in enumerate(SCENES):
        if start <= time < end:
            img = SCENE_FUNCS[name](time - start)
            # 다음 장면과 크로스페이드
            if idx + 1 < len(SCENES) and time > end - FADE:
                nxt_start, _, nxt = SCENES[idx + 1]
                nimg = SCENE_FUNCS[nxt](time - nxt_start)
                img = Image.blend(img, nimg, ease((time - (end - FADE)) / FADE))
            break
    else:
        img = Image.new("RGB", (W, H), (0, 0, 0))
    # 진행 표시줄
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 4, W * time / DURATION, H], fill=PALETTE[3])
    return img


# ---------------------------------------------------------------- 오디오


def synth_audio(path):
    n = int(SAMPLE_RATE * DURATION)
    t = np.arange(n) / SAMPLE_RATE
    out = np.zeros(n)

    def note(freq):
        return 440.0 * 2 ** ((freq - 69) / 12)

    # C - Am - F - G 진행, 마디당 2초
    chords = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]
    bar = 2.0
    for b in range(int(DURATION / bar)):
        chord = chords[b % 4]
        s, e = int(b * bar * SAMPLE_RATE), int((b + 1) * bar * SAMPLE_RATE)
        tt = t[s:e] - b * bar
        env = np.minimum(tt / 0.3, 1) * np.minimum((bar - tt) / 0.3, 1)
        for m in chord:
            f = note(m - 12)
            out[s:e] += 0.07 * env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt))
        # 8분음표 아르페지오
        arp = chord + [chord[1] + 12]
        step = bar / 8
        for k in range(8):
            ps = s + int(k * step * SAMPLE_RATE)
            pe = min(ps + int(step * SAMPLE_RATE), e)
            at = np.arange(pe - ps) / SAMPLE_RATE
            f = note(arp[k % len(arp)] + 12)
            out[ps:pe] += 0.06 * np.exp(-at * 9) * np.sin(2 * np.pi * f * at)

    fade = np.minimum(np.minimum(t / 1.0, 1), (DURATION - t) / 1.5)
    out = out * np.clip(fade, 0, 1)
    out = out / max(np.abs(out).max(), 1e-9) * 0.8
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- 메인


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT_DIR, "output.mp4")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        synth_audio(wav)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-i", wav,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
            out_path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        total = int(DURATION * FPS)
        for i in range(total):
            proc.stdin.write(render_frame(i / FPS).tobytes())
            if i % FPS == 0:
                print(f"\r{i // FPS:2d}/{int(DURATION)}s", end="", flush=True)
        proc.stdin.close()
        if proc.wait() != 0:
            sys.exit("ffmpeg 실패")
    print(f"\n완료: {out_path}")


if __name__ == "__main__":
    main()
