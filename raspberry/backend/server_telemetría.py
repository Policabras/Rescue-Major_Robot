from flask import Flask, jsonify
from flask_cors import CORS
import serial
import pygame
import time
import threading
import sys

app = Flask(__name__)
CORS(app)

# Diccionario global para guardar lo que está pasando en el taller
estado_robot = {
    "throttle": 0,
    "giro": 0,
    "rpm_izq": 0,
    "rpm_der": 0
}

# --- FUNCIÓN EN SEGUNDO PLANO (MANDO + SERIAL) ---
def bucle_mando():
    global estado_robot
    
    PORT = 'COM6'
    BAUD_RATE = 115200

    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
        print(f"[*] [HILO] Conectado a la ESP32 en {PORT}")
    except Exception as e:
        print(f"[!] [HILO] Error serial: {e}")
        return

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("[!] [HILO] No se detectó mando por Bluetooth. Conéctalo primero.")
        return

    mando = pygame.joystick.Joystick(0)
    mando.init()
    print(f"[*] [HILO] Mando operativo: {mando.get_name()}")

    MAX_VEL = 150
    ZONA_MUERTA = 0.15

    while True:
        pygame.event.pump()

        # Leer ejes (Mapeo DS4Windows)
        steer = mando.get_axis(0)
        l2_raw = mando.get_axis(4)
        r2_raw = mando.get_axis(5)

        reversa = (l2_raw + 1) / 2.0
        avance = (r2_raw + 1) / 2.0

        if abs(steer) < ZONA_MUERTA:
            steer = 0.0

        throttle = (avance - reversa) * MAX_VEL
        giro = steer * MAX_VEL

        rpm_izq = int(max(-MAX_VEL, min(MAX_VEL, throttle + giro)))
        rpm_der = int(max(-MAX_VEL, min(MAX_VEL, throttle - giro)))

        # Actualizar la vitrina global para la página web
        estado_robot = {
            "throttle": int(throttle),
            "giro": int(giro),
            "rpm_izq": rpm_izq,
            "rpm_der": rpm_der
        }

        # Mandar a la ESP32
        if ser and ser.is_open:
            comando = f"v,{rpm_izq},{rpm_der}\n"
            ser.write(comando.encode('utf-8'))

        time.sleep(0.02) # 50Hz constantes

# --- RUTA PARA QUE LA PÁGINA WEB VEA LA TELEMETRÍA ---
@app.route('/api/status', methods=['GET'])
def obtener_status():
    return jsonify(estado_robot)

if __name__ == '__main__':
    # Arrancamos la lectura del mando en un hilo separado antes de encender Flask
    hilo = threading.Thread(target=bucle_mando, daemon=True)
    hilo.start()

    # Encendemos el servidor web local para el frontend
    print("[*] Arrancando servidor de telemetría...")
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)