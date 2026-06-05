#!/usr/bin/env python3
import sys
import time
import math
import signal
import random

SYSFS_PATH = "/sys/class/leds/rgb:lightbar/multi_intensity"

def hsv_to_rgb(h, s, v):
    if s == 0.0: return v, v, v
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0: return v, t, p
    if i == 1: return q, v, p
    if i == 2: return p, v, t
    if i == 3: return p, q, v
    if i == 4: return t, p, v
    if i == 5: return v, p, q

def set_color(f, r, g, b):
    try:
        f.seek(0)
        f.write(f"{int(r)} {int(g)} {int(b)}")
        f.flush()
    except Exception:
        pass

# --- Animações existentes ---

def rainbow_loop(f):
    """Arco-íris contínuo percorrendo todo o espectro HSV."""
    h = 0.0
    while True:
        r, g, b = hsv_to_rgb(h, 1.0, 255.0)
        set_color(f, r, g, b)
        h += 0.01
        if h > 1.0: h = 0.0
        time.sleep(0.03)

def breathing_loop(f, r_base, g_base, b_base):
    """Pulsa a intensidade de uma cor de forma suave (inspiração/expiração)."""
    t = 0.0
    while True:
        intensity = (math.sin(t) + 1) / 2.0
        r = r_base * intensity
        g = g_base * intensity
        b = b_base * intensity
        set_color(f, r, g, b)
        t += 0.05
        time.sleep(0.03)

# --- Novas animações ---

def strobe_loop(f, r_base, g_base, b_base):
    """Pisca rapidamente entre cor máxima e apagado (efeito strobe/flash)."""
    while True:
        set_color(f, r_base, g_base, b_base)
        time.sleep(0.07)
        set_color(f, 0, 0, 0)
        time.sleep(0.07)

def pulse_loop(f, r_base, g_base, b_base):
    """Pulsa com batida mais rápida e intensa, como um coração."""
    while True:
        # Batida dupla rápida
        for _ in range(2):
            for step in range(20):
                intensity = step / 19.0
                set_color(f, r_base * intensity, g_base * intensity, b_base * intensity)
                time.sleep(0.015)
            for step in range(20, -1, -1):
                intensity = step / 20.0
                set_color(f, r_base * intensity, g_base * intensity, b_base * intensity)
                time.sleep(0.015)
            time.sleep(0.05)
        # Pausa entre batidas duplas
        set_color(f, 0, 0, 0)
        time.sleep(0.5)

def fire_loop(f):
    """Simula chamas com tons de laranja/vermelho com variações aleatórias."""
    while True:
        # Chama: vermelho alto, verde variável (0-100), azul quase zero
        r = random.randint(200, 255)
        g = random.randint(30, 110)
        b = random.randint(0, 10)
        set_color(f, r, g, b)
        time.sleep(random.uniform(0.04, 0.12))

def wave_loop(f):
    """Onda senoidal que varia entre duas cores complementares suavemente."""
    t = 0.0
    while True:
        # Cicla entre azul ciano e violeta
        r = int((math.sin(t) + 1) / 2.0 * 180)
        g = int((math.sin(t + math.pi / 3) + 1) / 2.0 * 50)
        b = int((math.cos(t) + 1) / 2.0 * 255)
        set_color(f, r, g, b)
        t += 0.04
        if t > 2 * math.pi: t = 0.0
        time.sleep(0.03)

def aurora_loop(f):
    """Transição lenta e suave entre verdes, azuis e roxos (efeito Aurora Boreal)."""
    colors = [
        (0, 255, 120),    # verde neon
        (0, 180, 255),    # azul ciano
        (80, 0, 255),     # violeta
        (150, 0, 200),    # roxo
        (0, 255, 180),    # verde água
    ]
    steps = 80
    idx = 0
    while True:
        c1 = colors[idx % len(colors)]
        c2 = colors[(idx + 1) % len(colors)]
        for step in range(steps):
            t = step / steps
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            set_color(f, r, g, b)
            time.sleep(0.04)
        idx += 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: lightbar_anim.py <modo> [r g b]")
        print("Modos: rainbow, breathing, strobe, pulse, fire, wave, aurora")
        sys.exit(1)

    mode = sys.argv[1]

    def signal_handler(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGTERM, signal_handler)

    # Cor base para animações que a usam (default: azul)
    r_base = int(sys.argv[2]) if len(sys.argv) > 4 else 0
    g_base = int(sys.argv[3]) if len(sys.argv) > 4 else 150
    b_base = int(sys.argv[4]) if len(sys.argv) > 4 else 255

    try:
        with open(SYSFS_PATH, 'w') as f:
            if mode == "rainbow":
                rainbow_loop(f)
            elif mode == "breathing":
                breathing_loop(f, r_base, g_base, b_base)
            elif mode == "strobe":
                strobe_loop(f, r_base, g_base, b_base)
            elif mode == "pulse":
                pulse_loop(f, r_base, g_base, b_base)
            elif mode == "fire":
                fire_loop(f)
            elif mode == "wave":
                wave_loop(f)
            elif mode == "aurora":
                aurora_loop(f)
            else:
                print(f"Modo '{mode}' desconhecido.")
                sys.exit(1)
    except PermissionError:
        print("Erro: Sem permissão para escrever na lightbar. (Execute com sudo)")
    except Exception as e:
        print(f"Erro: {e}")
