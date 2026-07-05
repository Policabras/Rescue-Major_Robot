from flask import Flask
from flask_sock import Sock
import serial
import json
import os

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

PORT = '/dev/ttyACM0'  # Intentamos primero con ACM (Estándar de Arduino en Linux)
BAUD_RATE = 115200
ser = None

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.05)
    print(f"[*] [SERIAL] ¡Conectado exitosamente a la ESP32 en: {PORT}!")
except Exception as e:
    print(f"[!] [SERIAL] No se detectó en {PORT}. Intentando puerto alternativo /dev/ttyUSB0...")
    try:
        PORT = '/dev/ttyUSB0' # Puerto alternativo para integrados tipo CH340
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.05)
        print(f"[*] [SERIAL] ¡Conectado en puerto alternativo: {PORT}!")
    except Exception as e2:
        print(f"[!] [SERIAL] ERROR CRÍTICO: No se encontró la ESP32. Modo simulación activo.")
        ser = None

@sock.route('/robot')
def canal_robot(ws):
    print("[*] [WEBSOCKET] ¡Cliente conectado al túnel de control!")
    while True:
        mensaje = ws.receive()
        if not mensaje:
            break
        try:
            datos = json.loads(mensaje)
            izq = datos.get("izq", 0)
            der = datos.get("der", 0)
            
            if ser and ser.is_open:
                # Modificado: Se quita la coma intermedia después de la 'v' 
                # para que coincida exactamente con lo que tu bridge.cpp espera.
                comando = f"v{int(izq)},{int(der)}\n"
                ser.write(comando.encode('utf-8'))
        except Exception as e:
            print(f"Error procesando datos: {e}")

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    print("\n========================================================")
    print("[*] Estación de Control Unificada Iniciada en Puerto 8000")
    print("========================================================")
    app.run(host='0.0.0.0', port=8000, debug=False)