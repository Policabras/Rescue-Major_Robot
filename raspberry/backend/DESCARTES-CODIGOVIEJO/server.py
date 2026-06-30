from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import os

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN SERIAL ---
PORT = 'COM6'          # Forzamos el puerto de la ESP32 en tu laptop
BAUD_RATE = 115200     # ¡Ojo! La ESP32 corre a 115200, no a 9600

try:
    # Inicializa la conexión serial con la ESP32
    ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
    print(f"[*] Conectado exitosamente a la ESP32 en el puerto: {PORT}")
except Exception as e:
    print(f"[!] Error al conectar con la ESP32: {e}")
    ser = None


MAX_RPM = 100 

# =========================================================================
# AQUÍ EMPIEZA LA FUNCIÓN MOVER (Sustituye por completo a la anterior)
# =========================================================================
@app.route('/api/mover', methods=['POST'])
def mover():
    datos = request.json
    # Recibimos las velocidades ya mezcladas desde el JS
    rpm_izq = datos.get('rpm_izq', 0)
    rpm_der = datos.get('rpm_der', 0)

    if ser and ser.is_open:
        # Empaquetamos en el formato string que lee la ESP32: "v,izq,der\n"
        comando = f"v,{int(rpm_izq)},{int(rpm_der)}\n"
        ser.write(comando.encode('utf-8'))
        print(f"[MANDO] Enviado a ESP32 -> {comando.strip()}")

    return jsonify({"status": "ok", "izq": rpm_izq, "der": rpm_der})
# =========================================================================
# AQUÍ TERMINA LA FUNCIÓN MOVER
# =========================================================================

if __name__ == '__main__':
    # use_reloader=False evita que Flask intente abrir el puerto COM5 dos veces
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)