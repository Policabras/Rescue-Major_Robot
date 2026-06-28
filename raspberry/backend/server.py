from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import os

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN SERIAL ---
PORT = '/dev/ttyACM0' if os.name != 'nt' else 'COM5' # Ya configurado en tu COM5

try:
    ser = serial.Serial(PORT, 115200, timeout=1)
    print(f"[*] Conectado exitosamente al Arduino en el puerto: {PORT}")
except Exception as e:
    print(f"[!] Ojo: No se detectó Arduino en {PORT}. Corriendo en modo simulación.")
    ser = None

MAX_RPM = 150 

# =========================================================================
# AQUÍ EMPIEZA LA FUNCIÓN MOVER (Sustituye por completo a la anterior)
# =========================================================================
@app.route('/api/mover', methods=['POST'])
def mover():
    global ser # Nos permite cerrar y reabrir el puerto si se cae
    
    data = request.json
    x = data.get('axis_x', 0.0)
    y = data.get('axis_y', 0.0)
    
    # Matemática Mix Diferencial
    v = -y  
    w = x   
    
    rpm_izq = int((v + w) * MAX_RPM)
    rpm_der = int((v - w) * MAX_RPM)
    
    rpm_izq = max(-MAX_RPM, min(MAX_RPM, rpm_izq))
    rpm_der = max(-MAX_RPM, min(MAX_RPM, rpm_der))
    
    comando_serial = f"v,{rpm_izq},{rpm_der}\n"
    
    # --- BLOQUE SEGURO CONTRA CAÍDAS DEL USB ---
    if ser and ser.is_open:
        try:
            ser.write(comando_serial.encode('utf-8'))
            print(f"[API] Joystick: X={x:5.2f} Y={y:5.2f} | Enviado -> {comando_serial.strip()}")
        except Exception as e:
            print(f"[!] Error de comunicación: El Arduino se reinició por consumo eléctrico. ({e})")
            ser.close()
            ser = None 
    else:
        # Intento de reconexión automática en tiempo real
        try:
            ser = serial.Serial(PORT, 115200, timeout=1)
            print("[*] Puerto recuperado: Reconexión exitosa con el Arduino.")
        except:
            print(f"[!] Arduino sigue apagado o desconectado en {PORT}... Modo simulación activo.")
    
    return jsonify({
        "status": "processed",
        "rpm_izq": rpm_izq,
        "rpm_der": rpm_der
    })
# =========================================================================
# AQUÍ TERMINA LA FUNCIÓN MOVER
# =========================================================================

if __name__ == '__main__':
    # use_reloader=False evita que Flask intente abrir el puerto COM5 dos veces
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)