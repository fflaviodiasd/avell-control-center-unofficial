#!/usr/bin/env python3
import sys
import time
import math
import signal

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

def rainbow_loop(f):
    h = 0.0
    while True:
        r, g, b = hsv_to_rgb(h, 1.0, 255.0)
        set_color(f, r, g, b)
        h += 0.01
        if h > 1.0: h = 0.0
        time.sleep(0.03)

def breathing_loop(f, r_base, g_base, b_base):
    t = 0.0
    while True:
        # Breathing math: (sin(t) + 1) / 2 -> ranges 0 to 1
        intensity = (math.sin(t) + 1) / 2.0
        r = r_base * intensity
        g = g_base * intensity
        b = b_base * intensity
        set_color(f, r, g, b)
        t += 0.05
        time.sleep(0.03)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
        
    mode = sys.argv[1]
    
    # Catch SIGTERM to exit cleanly
    def signal_handler(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        with open(SYSFS_PATH, 'w') as f:
            if mode == "rainbow":
                rainbow_loop(f)
            elif mode == "breathing":
                r_base = int(sys.argv[2]) if len(sys.argv) > 4 else 0
                g_base = int(sys.argv[3]) if len(sys.argv) > 4 else 150
                b_base = int(sys.argv[4]) if len(sys.argv) > 4 else 255
                breathing_loop(f, r_base, g_base, b_base)
    except PermissionError:
        print("Erro: Sem permissão para escrever na lightbar. (Execute com sudo)")
    except Exception as e:
        print(f"Erro: {e}")
