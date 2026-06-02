# spacemouse_keyboard.py
# Lit l'ESP32 via UART et envoie des touches fléchées
# Calibration automatique au démarrage
#
# Installation : python -m pip install pyserial pyautogui

import serial
import pyautogui
import time
import sys

# ─── Configuration ────────────────────────────────────────────────────────
COM_PORT   = "COM7"
BAUD_RATE  = 115200

# Vitesse min/max de répétition des touches (en secondes)
DELAY_MAX  = 0.15   # délai quand joystick légèrement incliné
DELAY_MIN  = 0.02   # délai quand joystick à fond

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0

# ─── Init Serial ──────────────────────────────────────────────────────────
print(f"Connexion ESP32 sur {COM_PORT}...")
try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.05)
    print("✓ ESP32 connecté\n")
except Exception as e:
    print(f"❌ {e}")
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        print(f"  {p.device} — {p.description}")
    sys.exit(1)

# ─── Lecture d'une valeur ADC ──────────────────────────────────────────────
def read_values():
    for _ in range(10):
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("X:"):
                parts = line.split(",")
                x = int(parts[0].split(":")[1])
                y = int(parts[1].split(":")[1])
                return x, y
        except Exception:
            pass
    return None, None

# ─── Calibration ──────────────────────────────────────────────────────────
def calibrate():
    print("╔══════════════════════════════════════╗")
    print("║         CALIBRATION JOYSTICK         ║")
    print("╚══════════════════════════════════════╝")
    print()

    # Étape 1 : position de repos
    print("► Étape 1/3 — LÂCHE le joystick (position repos)")
    print("  Appuie sur ENTRÉE quand il est bien centré...")
    input()

    samples_x, samples_y = [], []
    print("  Mesure en cours...", end="", flush=True)
    for _ in range(50):
        x, y = read_values()
        if x is not None:
            samples_x.append(x)
            samples_y.append(y)
        time.sleep(0.02)

    center_x = sum(samples_x) // len(samples_x)
    center_y = sum(samples_y) // len(samples_y)
    noise_x  = max(samples_x) - min(samples_x)
    noise_y  = max(samples_y) - min(samples_y)
    print(f" OK  (centre X:{center_x} Y:{center_y}, bruit X:{noise_x} Y:{noise_y})")

    # Étape 2 : mouvement maximum
    print()
    print("► Étape 2/3 — Bouge le joystick dans TOUS les sens à fond")
    print("  Appuie sur ENTRÉE quand c'est fait...")
    input()

    max_x, max_y = 0, 0
    print("  Mesure en cours (5 secondes)...", end="", flush=True)
    t = time.time()
    while time.time() - t < 5:
        x, y = read_values()
        if x is not None:
            max_x = max(max_x, abs(x - center_x))
            max_y = max(max_y, abs(y - center_y))
    print(f" OK  (max X:{max_x} Y:{max_y})")

    # Étape 3 : calcul zone morte
    deadzone_x = max(noise_x * 3, 200)
    deadzone_y = max(noise_y * 3, 200)
    deadzone   = max(deadzone_x, deadzone_y)

    print()
    print("╔══════════════════════════════════════╗")
    print("║         CALIBRATION TERMINÉE         ║")
    print(f"║  Centre  : X={center_x:<6} Y={center_y:<6}       ║")
    print(f"║  Zone morte : {deadzone:<6}                ║")
    print(f"║  Plage max  : X={max_x:<6} Y={max_y:<6}       ║")
    print("╚══════════════════════════════════════╝")
    print()

    return center_x, center_y, deadzone, max_x, max_y

# ─── Fonctions ────────────────────────────────────────────────────────────
def get_delay(value, max_val):
    intensity = min(abs(value) / max(max_val, 1), 1.0)
    return DELAY_MAX - (DELAY_MAX - DELAY_MIN) * intensity

def get_key(x, y, center_x, center_y, deadzone):
    dx = x - center_x
    dy = y - center_y
    if abs(dx) >= abs(dy):
        if dx >  deadzone: return 'right', dx
        if dx < -deadzone: return 'left',  dx
    else:
        if dy >  deadzone: return 'down', dy
        if dy < -deadzone: return 'up',   dy
    return None, 0

# ─── Calibration ──────────────────────────────────────────────────────────
center_x, center_y, deadzone, max_x, max_y = calibrate()

# ─── Boucle principale ────────────────────────────────────────────────────
print("─────────────────────────────────────────")
print("SpaceMouse → Clavier démarré !")
print("Ouvre OnShape et bouge le joystick")
print("Coin haut-gauche de l'écran pour stopper")
print("─────────────────────────────────────────\n")

last_key  = None
last_send = 0

try:
    while True:
        x_val, y_val = read_values()
        if x_val is None:
            continue

        key, val = get_key(x_val, y_val, center_x, center_y, deadzone)
        now = time.time()

        if key:
            delay = get_delay(val, max(max_x, max_y))
            if now - last_send >= delay:
                pyautogui.press(key)
                last_send = now
                intensity = min(abs(val) / max(max_x, max_y), 1.0)
                bar = "█" * int(intensity * 20)
                print(f"\r[{key:^5}] {bar:<20} ({intensity*100:.0f}%)  ", end="", flush=True)
        else:
            if last_key:
                print(f"\r{'':50}", end="", flush=True)
            last_send = 0

        last_key = key
        time.sleep(0.005)

except KeyboardInterrupt:
    print("\n\nArrêt.")
    ser.close()
