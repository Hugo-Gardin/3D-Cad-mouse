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
DEFAULT_MAX_VALUE = 1

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

# ─── Lecture des valeurs UART ───────────────────────────────────────────────
def read_values():
    for _ in range(10):
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("X:"):
                data = {}
                for part in line.split(","):
                    if ":" not in part:
                        continue
                    k, v = part.split(":", 1)
                    data[k] = v
                x = int(data["X"])
                y = int(data["Y"])
                z = int(data.get("Z", 0))
                b = int(data.get("B", 0))
                return x, y, z, b
        except Exception:
            pass
    return None, None, None, None

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

    samples_x, samples_y, samples_z = [], [], []
    print("  Mesure en cours...", end="", flush=True)
    for _ in range(50):
        x, y, z, _ = read_values()
        if x is not None:
            samples_x.append(x)
            samples_y.append(y)
            samples_z.append(z)
        time.sleep(0.02)

    center_x = sum(samples_x) // len(samples_x)
    center_y = sum(samples_y) // len(samples_y)
    center_z = sum(samples_z) // len(samples_z)
    noise_x  = max(samples_x) - min(samples_x)
    noise_y  = max(samples_y) - min(samples_y)
    noise_z  = max(samples_z) - min(samples_z)
    print(f" OK  (centre X:{center_x} Y:{center_y} Z:{center_z}, bruit X:{noise_x} Y:{noise_y} Z:{noise_z})")

    # Étape 2 : mouvement maximum
    print()
    print("► Étape 2/3 — Bouge le joystick dans TOUS les sens à fond")
    print("  Appuie sur ENTRÉE quand c'est fait...")
    input()

    max_x, max_y, max_z = 0, 0, 0
    print("  Mesure en cours (5 secondes)...", end="", flush=True)
    t = time.time()
    while time.time() - t < 5:
        x, y, z, _ = read_values()
        if x is not None:
            max_x = max(max_x, abs(x - center_x))
            max_y = max(max_y, abs(y - center_y))
            max_z = max(max_z, abs(z - center_z))
    print(f" OK  (max X:{max_x} Y:{max_y} Z:{max_z})")

    # Étape 3 : calcul zone morte
    deadzone_x = max(noise_x * 3, 200)
    deadzone_y = max(noise_y * 3, 200)
    deadzone_z = max(noise_z * 3, 200)

    print()
    print("╔══════════════════════════════════════╗")
    print("║         CALIBRATION TERMINÉE         ║")
    print(f"║  Centre  : X={center_x:<6} Y={center_y:<6} Z={center_z:<6}  ║")
    print(f"║  Zone morte : X={deadzone_x:<6} Y={deadzone_y:<6} Z={deadzone_z:<6} ║")
    print(f"║  Plage max  : X={max_x:<6} Y={max_y:<6} Z={max_z:<6} ║")
    print("╚══════════════════════════════════════╝")
    print()

    return center_x, center_y, center_z, deadzone_x, deadzone_y, deadzone_z, max_x, max_y, max_z

# ─── Fonctions ────────────────────────────────────────────────────────────
def get_delay(value, max_val):
    intensity = min(abs(value) / max(max_val, 1), 1.0)
    return DELAY_MAX - (DELAY_MAX - DELAY_MIN) * intensity

def get_rotation_key(x, y, center_x, center_y, deadzone_x, deadzone_y):
    # Retourne (touche, valeur) ; touche peut être None et valeur=0 si aucune direction active.
    dx = x - center_x
    dy = y - center_y

    if abs(dx) >= abs(dy):
        if dx >  deadzone_x: return 'right', dx
        if dx < -deadzone_x: return 'left',  dx
    else:
        if dy >  deadzone_y: return 'down', dy
        if dy < -deadzone_y: return 'up',   dy
    return None, 0

def get_rotation_modifier(z, center_z, deadzone_z):
    # Retourne le mode de rotation selon l'axe Z : precision / grossiere / None.
    dz = z - center_z
    if dz < -deadzone_z:
        return "precision"
    if dz > deadzone_z:
        return "grossiere"
    return None

def get_view_action(x, y, z, center_x, center_y, center_z, deadzone_x, deadzone_y, deadzone_z):
    # Retourne (nom_action, combo_clavier, valeur_axe, reference_axe).
    dx = x - center_x
    dy = y - center_y
    dz = z - center_z

    abs_dx, abs_dy, abs_dz = abs(dx), abs(dy), abs(dz)

    if abs_dx >= abs_dy and abs_dx >= abs_dz:
        if dx > deadzone_x:
            return "vue_droite", ("shift", "4"), dx, deadzone_x
        if dx < -deadzone_x:
            return "vue_gauche", ("shift", "3"), dx, deadzone_x
    elif abs_dy >= abs_dz:
        if dy < -deadzone_y:
            return "vue_dessus", ("shift", "5"), dy, deadzone_y
        if dy > deadzone_y:
            return "vue_dessous", ("shift", "6"), dy, deadzone_y
    else:
        if dz > deadzone_z:
            return "vue_arriere", ("shift", "2"), dz, deadzone_z
        if dz < -deadzone_z:
            return "vue_face", ("shift", "1"), dz, deadzone_z

    return None, (), 0, DEFAULT_MAX_VALUE

# ─── Calibration ──────────────────────────────────────────────────────────
center_x, center_y, center_z, deadzone_x, deadzone_y, deadzone_z, max_x, max_y, max_z = calibrate()

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
        x_val, y_val, z_val, button = read_values()
        if x_val is None:
            continue

        if button:
            action, combo, val, max_val = get_view_action(
                x_val, y_val, z_val,
                center_x, center_y, center_z,
                deadzone_x, deadzone_y, deadzone_z
            )
            mode = "VUE"
            send_delay = 0.30
        else:
            action, val = get_rotation_key(
                x_val, y_val,
                center_x, center_y,
                deadzone_x, deadzone_y
            )
            z_modifier = get_rotation_modifier(z_val, center_z, deadzone_z)
            max_val = DEFAULT_MAX_VALUE
            if action in ("left", "right"):
                max_val = max_x
            elif action in ("up", "down"):
                max_val = max_y
            mode = "ROT"
            if z_modifier == "precision":
                mode = "ROT_PREC"
            elif z_modifier == "grossiere":
                mode = "ROT_GROSS"
            send_delay = get_delay(val, max_val) if action else DELAY_MAX

        now = time.time()

        if action:
            if now - last_send >= send_delay:
                if button:
                    pyautogui.hotkey(*combo)
                else:
                    if z_modifier == "precision":
                        pyautogui.hotkey("ctrl", action)
                    elif z_modifier == "grossiere":
                        pyautogui.hotkey("shift", action)
                    else:
                        pyautogui.press(action)
                last_send = now
                denom = float(max_val) or 1.0
                intensity = min(abs(val) / denom, 1.0)
                bar = "█" * int(intensity * 20)
                print(f"\r[{mode}:{action:^12}] {bar:<20} ({intensity*100:.0f}%)  ", end="", flush=True)
        else:
            if last_key:
                print(f"\r{'':50}", end="", flush=True)
            last_send = 0

        last_key = action
        time.sleep(0.005)

except KeyboardInterrupt:
    print("\n\nArrêt.")
    ser.close()
