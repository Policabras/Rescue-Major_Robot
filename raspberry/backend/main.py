import os
from flask import Flask, send_from_directory, request
import serial
import time

# Inicializamos Flask apuntando a tu carpeta frontend
app = Flask(__name__, static_folder='../frontend')

# ==========================================
# CONFIGURACIÓN SERIAL CON EL ARDUINO
# ==========================================
PUERTO_SERIAL = '/dev/ttyACM0'  # Cambia a /dev/ttyUSB0 si es necesario
BAUDIOS = 115200
arduino = None

try:
    arduino = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.1)
    time.sleep(2)
    print("[OK] ¡Conectado exitosamente al Arduino por Serial!")
except Exception as e:
    print(f"[WARN] No se detectó Arduino en {PUERTO_SERIAL}. Modo simulación activo. {e}")

# ==========================================
# RUTAS DEL SERVIDOR WEB
# ==========================================

# 1. Sirve la página web del control remoto
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# 2. Recibe las pulsaciones de los botones del teléfono
@app.route('/mover')
def mover():
    comando_usuario = request.args.get('cmd', 'x')
    
    throttle = 0.0
    steering = 0.0
    
    if comando_usuario == 'w':
        throttle = 0.7
    elif comando_usuario == 's':
        throttle = -0.7
    elif comando_usuario == 'a':
        steering = -0.5
    elif comando_usuario == 'd':
        steering = 0.5
    elif comando_usuario == 'x':
        throttle = 0.0
        steering = 0.0

    # Mezcla Arcade Drive para motores
    izq_proporcional = throttle + steering
    der_proporcional = throttle - steering

    vel_izq = max(-255, min(255, int(izq_proporcional * 255)))
    vel_der = max(-255, min(255, int(der_proporcional * 255)))

    # Mandar comando al Arduino
    comando_serial = f"v,{vel_izq},{vel_der}\n"
    print(f"Web mandó: {comando_usuario} -> Serial: v,{vel_izq},{vel_der}")
    
    if arduino:
        arduino.write(comando_serial.encode('utf-8'))
        # Limpieza rápida del búfer por si el Arduino responde
        if arduino.in_waiting > 0:
            arduino.readline() 

    return "OK"

if __name__ == "__main__":
    # Arranca el servidor accesible para cualquier dispositivo en la misma red Wi-Fi
    # Puerto por defecto: 5000
    app.run(host='0.0.0.0', port=5000, debug=False)