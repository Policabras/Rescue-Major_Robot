from flask import Flask
from flask_sock import Sock
import serial
import json
import os

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

PORT = '/dev/ttyUSB0'  
BAUD_RATE = 115200

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    print(f"[*] [SERIAL] ¡Conectado exitosamente a la ESP32 en: {PORT}!")
except Exception as e:
    print(f"[!] [SERIAL] No se detectó la ESP32 en {PORT}. Intentando puerto alternativo...")
    try:
        PORT = '/dev/ttyACM0'  # Cambiado a ACM0 por si acaso
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
        print(f"[*] [SERIAL] ¡Conectado en puerto alternativo: {PORT}!")
    except Exception as e2:
        print(f"[!] [SERIAL] ERROR CRÍTICO: No se encontró la ESP32. Modo simulación.")
        ser = None

@sock.route('/robot')
def canal_robot(ws):
    print("[*] [WEBSOCKET] ¡Controlador conectado al túnel de telemetría!")
    while True:
        mensaje = ws.receive()
        if not mensaje:
            break
        try:
            datos = json.loads(mensaje)
            izq = datos.get("izq", 0)
            der = datos.get("der", 0)
            
            if ser and ser.is_open:
                comando = f"v,{int(izq)},{int(der)}\n"
                ser.write(comando.encode('utf-8'))
        except Exception as e:
            print(f"Error en datos: {e}")

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    print("\n========================================================")
    print("[*] Servidor de TELEMETRÍA y Motores Activo en Puerto 8000")
    print("========================================================")
    app.run(host='0.0.0.0', port=8000, debug=False)
