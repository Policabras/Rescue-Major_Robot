import os
from flask import Flask, request, jsonify
import serial
import time

# El truco maestro: static_url_path='' hace que Flask encuentre la carpeta 'imgs'
# directamente en tu frontend sin dar errores 404
app = Flask(__name__, static_folder='../frontend', static_url_path='')

# ==========================================
# CONEXIÓN SERIAL CON ARDUINO
# ==========================================
PUERTO_SERIAL = '/dev/ttyACM0'  # Cambia a /dev/ttyUSB0 si es necesario
BAUDIOS = 115200
arduino = None

try:
    arduino = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.1)
    time.sleep(2)
    print("[OK] ¡Conectado exitosamente al Arduino por Serial!")
except Exception as e:
    print(f"[WARN] Modo simulación activo. No se detectó Arduino. {e}")

# ==========================================
# RUTAS DEL SERVIDOR (CORREGIDAS)
# ==========================================

# Sirve el index.html automáticamente cuando entras a la IP
@app.route('/')
def index():
    return app.send_static_file('index.html')

# LA RUTA EXACTA QUE BUSCA TU COLOCOAL (POST /api/mover)
@app.route('/api/mover', methods=['POST'])
def mover():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Faltan datos"}), 400

    axis_x = data.get('axis_x', 0.0)
    axis_y = data.get('axis_y', 0.0)

    # Invertimos el eje Y del Gamepad API
    throttle = -axis_y  
    steering = axis_x

    # Algoritmo Arcade Drive
    izq_proporcional = throttle + steering
    der_proporcional = throttle - steering

    vel_izq = max(-255, min(255, int(izq_proporcional * 255)))
    vel_der = max(-255, min(255, int(der_proporcional * 255)))

    comando_serial = f"v,{vel_izq},{vel_der}\n"
    
    # Esto te dejará ver en la terminal si los botones están respondiendo
    print(f"[ENVIO] X: {axis_x} | Y: {axis_y} ==> Serial: {comando_serial.strip()}")

    if arduino:
        arduino.write(comando_serial.encode('utf-8'))
        if arduino.in_waiting > 0:
            arduino.readline()

    return jsonify({"status": "success", "izq": vel_izq, "der": vel_der})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=False)
    # q rancio