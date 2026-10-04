"""「오늘도 잘했어」 포트폴리오 소개 영상 (44초, 16:9). 대본은 SCRIPT.md.

    pip install pillow numpy
    python video/portfolio/make_portfolio_video.py   # -> video/portfolio/portfolio.mp4
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
SAMPLE_RATE = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

# 포트폴리오 페이지의 라이트 테마 토큰
PAPER = (254, 250, 239)  # 스크린샷 배경과 같은 값
SURFACE = (255, 255, 255)
INK = (46, 42, 34)
MUTED = (106, 99, 85)
LINE = (239, 229, 211)
AMBER = (255, 201, 60)
AMBER_SOFT = (255, 244, 214)
AMBER_INK = (122, 86, 0)
MINT = (56, 200, 149)
MINT_SOFT = (220, 247, 235)
MINT_TEXT = (3, 121, 88)

# (시작, 끝, 장면, 자막)
SCENES = [
    (0.0, 5.0, "intro", "오늘 한 일이 우리 아이의 용돈이 돼요."),
    (5.0, 10.0, "why", "집에서 쓰던 구글 시트 체크리스트를, 다른 집도 쓸 수 있는 앱으로 만들었습니다."),
    (10.0, 17.0, "loop", "설정은 처음 한 번, 그다음은 체크와 승인뿐입니다."),
    (17.0, 23.0, "progress", "할 일 하나가 한 칸. 시안 → 합의 → 구현 → 배포를 피드백 당일에 다섯 번 반복했습니다."),
    (23.0, 29.0, "data", "아이의 기록은 부모의 구글 시트에만. 서버에는 로그인과 알림에 필요한 설정값만 둡니다."),
    (29.0, 36.0, "numbers", "감이 아니라 측정으로. 출시 전 단계라 품질 지표를 기록했습니다."),
    (36.0, 40.0, "next", "지금은 Google Play 정식 출시를 준비하고 있습니다."),
    (40.0, 44.0, "outro", "기능을 만들었다가 아니라, 헷갈리지 않고 쓴다를 완료 기준으로."),
]
DURATION = SCENES[-1][1]
FADE = 0.5

_fonts = {}


def font(kind, size):
    """kind: 'display'(나눔스퀘어 라운드 800), 'bold'(Pretendard 700), 'body'(Pretendard 400)."""
    key = (kind, size)
    if key not in _fonts:
        name = {"display": "NSR800.woff", "bold": "Pre700.woff", "body": "Pre400.woff"}[kind]
        _fonts[key] = ImageFont.truetype(os.path.join(ASSETS, name), size)
    return _fonts[key]


def _load(name):
    return Image.open(os.path.join(ASSETS, name))


MASCOT = _load("mascot.png").convert("RGBA")
SCREENS_MAIN = _load("screens_main.jpg").convert("RGB")
SCREENS_PROGRESS = _load("screens_progress.jpg").convert("RGB")


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def mix(c1, c2, t):
    t = min(max(t, 0.0), 1.0)
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def fade_in(t, start, dur=0.6):
    return ease((t - start) / dur)


def text_w(d, text, f):
    return d.textlength(text, font=f)


def draw_text(d, xy, text, f, color, alpha=1.0, center=False):
    x, y = xy
    if center:
        x -= text_w(d, text, f) / 2
    d.text((x, y), text, font=f, fill=mix(PAPER, color, alpha))


def eyebrow(d, t, label, title):
    """장면 왼쪽 위의 영문 라벨 + 제목."""
    a = fade_in(t, 0.0)
    off = 20 * (1 - a)
    draw_text(d, (80, 62 + off), label, font("bold", 18), AMBER_INK, a)
    draw_text(d, (80, 88 + off), title, font("display", 44), INK, a)


def paste_card(img, src, box, t_in, t, radius=22):
    """스크린샷을 둥근 카드로 붙인다. 아래에서 떠오르며 나타남."""
    x, y, w, h = box
    a = fade_in(t, t_in, 0.8)
    if a <= 0:
        return
    y += int(40 * (1 - a))
    pic = src.copy()
    pic.thumbnail((w, h), Image.LANCZOS)
    pw, ph = pic.size
    x += (w - pw) // 2
    shadow = Image.new("L", (pw + 60, ph + 60), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([30, 36, pw + 30, ph + 36], radius, fill=int(55 * a))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    img.paste((120, 100, 60), (x - 30, y - 30), shadow)
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius, fill=int(255 * a))
    img.paste(pic, (x, y), mask)


def paste_mascot(img, center, size, t, bounce=True):
    s = int(size)
    if s < 4:
        return
    m = MASCOT.resize((s, s), Image.LANCZOS)
    dy = -abs(math.sin(t * 3.2)) * size * 0.12 if bounce else 0
    img.paste(m, (int(center[0] - s / 2), int(center[1] - s / 2 + dy)), m)


def pill(d, x, y, text, f, fg, bg, alpha=1.0, pad=(16, 8)):
    w = text_w(d, text, f)
    hh = f.size + pad[1] * 2
    d.rounded_rectangle([x, y, x + w + pad[0] * 2, y + hh], hh / 2, fill=mix(PAPER, bg, alpha))
    d.text((x + pad[0], y + pad[1] - 2), text, font=f, fill=mix(PAPER, fg, alpha))
    return w + pad[0] * 2


# ---------------------------------------------------------------- 장면들


def scene_intro(img, d, t):
    pop = ease(t / 0.7)
    paste_mascot(img, (W / 2, 230), 170 * pop, t)
    a = fade_in(t, 0.5)
    draw_text(d, (W / 2, 340 + 20 * (1 - a)), "오늘도 잘했어", font("display", 92), INK, a, center=True)
    b = fade_in(t, 1.2)
    draw_text(d, (W / 2, 466), "오늘 한 일이 우리 아이의 용돈이 돼요", font("body", 30), MUTED, b, center=True)
    c = fade_in(t, 1.8)
    label = "PRODUCT MANAGER PORTFOLIO"
    f = font("bold", 16)
    pw = text_w(d, label, f) + 32
    pill(d, W / 2 - pw / 2, 530, label, f, AMBER_INK, AMBER_SOFT, c)


def scene_why(img, d, t):
    eyebrow(d, t, "WHY · PROBLEM", "왜 만들었나")
    # 왼쪽: 출발점 카드
    a = fade_in(t, 0.4)
    x0, y0 = 80, 230 + 20 * (1 - a)
    d.rounded_rectangle([x0, y0, x0 + 480, y0 + 250], 20, fill=mix(PAPER, SURFACE, a), outline=mix(PAPER, LINE, a), width=2)
    draw_text(d, (x0 + 32, y0 + 30), "출발점", font("bold", 20), MUTED, a)
    draw_text(d, (x0 + 32, y0 + 70), "집에서 구글 시트로", font("display", 34), INK, a)
    draw_text(d, (x0 + 32, y0 + 116), "직접 쓰던 할 일·용돈", font("display", 34), INK, a)
    draw_text(d, (x0 + 32, y0 + 162), "체크리스트", font("display", 34), INK, a)
    # 화살표
    b = fade_in(t, 1.3)
    ax = 600 + 40 * b
    if b > 0:
        d.line([(600, 355), (ax, 355)], fill=AMBER, width=6)
        d.polygon([(ax, 341), (ax + 22, 355), (ax, 369)], fill=mix(PAPER, AMBER, b))
    # 오른쪽: 목표 카드
    c = fade_in(t, 1.8)
    x1, y1 = 700, 230 + 20 * (1 - c)
    d.rounded_rectangle([x1, y1, x1 + 500, y1 + 250], 20, fill=mix(PAPER, AMBER_SOFT, c))
    draw_text(d, (x1 + 32, y1 + 30), "목표", font("bold", 20), AMBER_INK, c)
    draw_text(d, (x1 + 32, y1 + 80), "잔소리 대신", font("display", 44), INK, c)
    draw_text(d, (x1 + 32, y1 + 140), "기록이 되는 앱", font("display", 44), INK, c)


def scene_loop(img, d, t):
    eyebrow(d, t, "CORE LOOP", "하루가 돌아가는 방식")
    paste_card(img, SCREENS_MAIN, (560, 160, 660, 470), 0.3, t)
    d = ImageDraw.Draw(img)
    steps = [
        ("아이", "할 일 체크"),
        ("아이", "\"다 했어요!\" 요청"),
        ("부모", "알림 받고 승인"),
        ("자동", "시트 표 자동 갱신"),
        ("부모", "주 단위로 지급"),
    ]
    for i, (who, what) in enumerate(steps):
        a = fade_in(t, 0.8 + i * 0.75, 0.5)
        y = 200 + i * 82
        x = 80 + 24 * (1 - a)
        done = a >= 1
        r = 18
        cx, cy = x + r, y + 22
        if done:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=MINT)
            d.line([(cx - 8, cy), (cx - 2, cy + 7), (cx + 9, cy - 7)], fill=SURFACE, width=4)
        else:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=mix(PAPER, LINE, a), width=3)
        tag_bg = {"아이": AMBER_SOFT, "부모": MINT_SOFT, "자동": LINE}[who]
        tag_fg = {"아이": AMBER_INK, "부모": MINT_TEXT, "자동": MUTED}[who]
        tw = pill(d, x + 52, y + 6, who, font("bold", 15), tag_fg, tag_bg, a, pad=(10, 6))
        draw_text(d, (x + 64 + tw, y + 3), what, font("bold", 30), INK, a)


def scene_progress(img, d, t):
    eyebrow(d, t, "CASE STUDY", "진행 막대: 하는 중 → 확인 중 → 받았어요")
    paste_card(img, SCREENS_PROGRESS, (80, 160, 1120, 410), 0.2, t)
    d = ImageDraw.Draw(img)
    # 칸 막대 (할 일 하나 = 한 칸)
    n = 4
    x0, y0, cw, gap, hgt = 290, 595, 160, 12, 22
    fill_t = (t - 1.2) / 3.0
    for i in range(n):
        x = x0 + i * (cw + gap)
        d.rounded_rectangle([x, y0, x + cw, y0 + hgt], 8, fill=LINE)
        p = min(max(fill_t * n - i, 0), 1)
        if p > 0:
            col = MINT if fill_t > 1.05 else AMBER
            d.rounded_rectangle([x, y0, x + cw * p, y0 + hgt], 8, fill=col)
    if fill_t > 1.05:
        paste_mascot(img, (x0 + n * (cw + gap) + 30, y0 + 10), 56, t)


def scene_data(img, d, t):
    eyebrow(d, t, "DATA POLICY", "아이의 기록은 부모의 구글 시트에만")
    boxes = [
        (80, "아이 앱 · 웹", "체크 · 다 했어요!", SURFACE, INK),
        (380, "Cloud Functions", "PIN 로그인 · 요청 · 푸시", SURFACE, INK),
        (680, "부모의 구글 시트", "유일한 원본", MINT_SOFT, MINT_TEXT),
        (980, "부모 앱 · 웹", "알림 · 승인 · 지급", SURFACE, INK),
    ]
    by, bw, bh = 250, 220, 150
    for i, (x, title, sub, bg, fg) in enumerate(boxes):
        a = fade_in(t, 0.4 + i * 0.45, 0.5)
        y = by + 20 * (1 - a)
        line = MINT if bg == MINT_SOFT else LINE
        d.rounded_rectangle([x, y, x + bw, y + bh], 18, fill=mix(PAPER, bg, a), outline=mix(PAPER, line, a), width=3)
        draw_text(d, (x + bw / 2, y + 40), title, font("bold", 24), fg, a, center=True)
        draw_text(d, (x + bw / 2, y + 86), sub, font("body", 18), MUTED, a, center=True)
    # 화살표: → → ←
    for i, (xa, xb) in enumerate([(300, 380), (600, 680), (980, 900)]):
        a = fade_in(t, 0.7 + i * 0.45, 0.4)
        if a <= 0:
            continue
        y = by + bh / 2
        end = xa + (xb - xa) * a
        d.line([(xa + 6, y), (end - 6, y)], fill=AMBER, width=5)
        s = 1 if xb > xa else -1
        d.polygon([(end - 6 * s, y - 11), (end + 8 * s, y), (end - 6 * s, y + 11)], fill=AMBER)
    c = fade_in(t, 2.6)
    d.rounded_rectangle([80, 460, 1200, 540], 16, fill=mix(PAPER, AMBER_SOFT, c))
    draw_text(d, (110, 474), "서버 보관", font("bold", 20), AMBER_INK, c)
    draw_text(d, (110, 502), "암호화한 로그인 토큰 · PIN 해시 · 알림 토큰 같은 설정값만. 아이 활동 데이터는 남기지 않습니다.",
              font("body", 20), INK, c)


def scene_numbers(img, d, t):
    eyebrow(d, t, "TRACTION", "성과 — 제품 품질 지표")
    tiles = [
        (-55, "%", "웹 첫 로딩 자산", "9.1MB → 4.1MB"),
        (83, "회", "반복 업데이트", "6주간, 회차마다 기록"),
        (59, "개", "자동 테스트", "데이터 규칙 · 재발 방지"),
        (1, "인", "단독 오너십", "기획 · 디자인 · 구현 · 운영"),
    ]
    tw, gap = 260, 26
    x0 = (W - (4 * tw + 3 * gap)) / 2
    for i, (num, unit, label, sub) in enumerate(tiles):
        a = fade_in(t, 0.3 + i * 0.35, 0.5)
        x = x0 + i * (tw + gap)
        y = 220 + 24 * (1 - a)
        d.rounded_rectangle([x, y, x + tw, y + 260], 22, fill=mix(PAPER, SURFACE, a), outline=mix(PAPER, LINE, a), width=2)
        k = ease((t - 0.4 - i * 0.35) / 1.4)
        val = round(num * k)
        shown = ("−" if val < 0 else "") + f"{abs(val)}"
        nf = font("bold", 76)
        uf = font("bold", 30)
        total_w = text_w(d, shown, nf) + 6 + text_w(d, unit, uf)
        nx = x + (tw - total_w) / 2
        col = MINT_TEXT if i == 0 else INK
        d.text((nx, y + 40), shown, font=nf, fill=mix(PAPER, col, a))
        d.text((nx + text_w(d, shown, nf) + 6, y + 82), unit, font=uf, fill=mix(PAPER, MUTED, a))
        draw_text(d, (x + tw / 2, y + 150), label, font("bold", 24), INK, a, center=True)
        draw_text(d, (x + tw / 2, y + 190), sub, font("body", 18), MUTED, a, center=True)


def scene_next(img, d, t):
    eyebrow(d, t, "ROADMAP", "다음 계획")
    rows = [
        ("출시 준비 중", "Google Play 정식 출시", AMBER_INK, AMBER_SOFT),
        ("진행 중", "구글 인증 심사", MINT_TEXT, MINT_SOFT),
    ]
    for i, (tag, title, fg, bg) in enumerate(rows):
        a = fade_in(t, 0.4 + i * 0.5, 0.5)
        y = 250 + i * 130 + 20 * (1 - a)
        d.rounded_rectangle([80, y, 1200, y + 104], 20, fill=mix(PAPER, SURFACE, a), outline=mix(PAPER, LINE, a), width=2)
        pw = pill(d, 112, y + 32, tag, font("bold", 18), fg, bg, a, pad=(14, 8))
        draw_text(d, (112 + pw + 24, y + 30), title, font("display", 36), INK, a)


def scene_outro(img, d, t):
    pop = ease(t / 0.6)
    paste_mascot(img, (W / 2, 220), 150 * pop, t)
    a = fade_in(t, 0.3)
    draw_text(d, (W / 2, 320), "오늘도 잘했어", font("display", 80), INK, a, center=True)
    b = fade_in(t, 0.9)
    draw_text(d, (W / 2, 434), "gooodjobbaby.web.app", font("bold", 30), AMBER_INK, b, center=True)


SCENE_FUNCS = {
    "intro": scene_intro,
    "why": scene_why,
    "loop": scene_loop,
    "progress": scene_progress,
    "data": scene_data,
    "numbers": scene_numbers,
    "next": scene_next,
    "outro": scene_outro,
}


def draw_subtitle(img, text, t, dur):
    a = fade_in(t, 0.2, 0.4) * (1 - ease((t - (dur - 0.35)) / 0.35))
    if a <= 0:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = font("bold", 24)
    w = text_w(d, text, f)
    x, y = (W - w) / 2, H - 70
    d.rounded_rectangle([x - 22, y - 10, x + w + 22, y + 40], 14, fill=(46, 42, 34, int(225 * a)))
    d.text((x, y), text, font=f, fill=(255, 250, 240, int(255 * a)))


def render_scene(idx, time):
    start, end, name, sub = SCENES[idx]
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    SCENE_FUNCS[name](img, d, time - start)
    draw_subtitle(img, sub, time - start, end - start)
    return img


def render_frame(time):
    idx = next((i for i, s in enumerate(SCENES) if s[0] <= time < s[1]), len(SCENES) - 1)
    img = render_scene(idx, time)
    end = SCENES[idx][1]
    if idx + 1 < len(SCENES) and time > end - FADE:
        img = Image.blend(img, render_scene(idx + 1, time), ease((time - (end - FADE)) / FADE))
    if time > DURATION - 0.8:
        img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), ease((time - (DURATION - 0.8)) / 0.8))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 5, W * time / DURATION, H], fill=AMBER)
    return img


# ---------------------------------------------------------------- 오디오


def synth_audio(path):
    n = int(SAMPLE_RATE * DURATION)
    t = np.arange(n) / SAMPLE_RATE
    out = np.zeros(n)

    def hz(m):
        return 440.0 * 2 ** ((m - 69) / 12)

    # F - C - Dm - Bb, 마디당 2초
    chords = [[65, 69, 72], [60, 64, 67], [62, 65, 69], [58, 62, 65]]
    bar = 2.0
    for b in range(int(math.ceil(DURATION / bar))):
        chord = chords[b % 4]
        s = int(b * bar * SAMPLE_RATE)
        e = min(int((b + 1) * bar * SAMPLE_RATE), n)
        tt = t[s:e] - b * bar
        env = np.minimum(tt / 0.25, 1) * np.minimum((bar - tt) / 0.25, 1)
        for m in chord:
            f = hz(m - 12)
            out[s:e] += 0.06 * env * (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt))
        out[s:e] += 0.08 * env * np.sin(2 * np.pi * hz(chord[0] - 24) * tt)
        # 통통 튀는 8분음표 아르페지오
        arp = [chord[0], chord[1], chord[2], chord[1] + 12, chord[2], chord[1], chord[0] + 12, chord[2]]
        step = bar / 8
        for k in range(8):
            ps = s + int(k * step * SAMPLE_RATE)
            pe = min(ps + int(step * SAMPLE_RATE), e)
            if ps >= pe:
                continue
            at = np.arange(pe - ps) / SAMPLE_RATE
            f = hz(arp[k] + 12)
            out[ps:pe] += 0.05 * np.exp(-at * 10) * (np.sin(2 * np.pi * f * at) + 0.2 * np.sin(6 * np.pi * f * at))

    env = np.clip(np.minimum(t / 1.0, (DURATION - t) / 2.0), 0, 1)
    out *= env
    out = out / max(np.abs(out).max(), 1e-9) * 0.75
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "portfolio.mp4")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        synth_audio(wav)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-i", wav,
            "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
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
