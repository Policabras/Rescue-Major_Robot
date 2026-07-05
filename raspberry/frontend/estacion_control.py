from flask import Flask
from flask_sock import Sock
import serial
import serial.tools.list_ports  # <- NUEVO: Para buscar los puertos USB automáticamente
import json
import os

# Encontrar la carpeta exacta donde vive este archivo script
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

# --- NUEVA CONFIGURACIÓN SERIAL AUTO-DETECTABLE ---
BAUD_RATE = 115200
ser = None

print("[*] [SERIAL] Buscando la ESP32 en los puertos USB de la Raspberry Pi...")
puertos = list(serial.tools.list_ports.comports())

for p in puertos:
    # Buscamos ttyUSB o ttyACM que son los nombres estándar en la Rasp
    if 'ttyUSB' in p.device or 'ttyACM' in p.device:
        try:
            ser = serial.Serial(p.device, BAUD_RATE, timeout=0.05)
            print(f"[*] [SERIAL] ¡Conectado exitosamente a la ESP32 en: {p.device} ({p.description})!")
            break
        except Exception as e:
            print(f"[!] [SERIAL] Se encontró {p.device} pero no se pudo abrir: {e}")

if ser is None:
    print(f"[!] [SERIAL] ERROR CRÍTICO: No se detectó ninguna ESP32 conectada. Modo simulación activo.")


# TÚNEL WEBSOCKET (Alta velocidad)
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
                # Comando formateado para bridge.cpp (sin coma tras la 'v')
                comando = f"v{int(izq)},{int(der)}\n"
                ser.write(comando.encode('utf-8'))
        except Exception as e:
            print(f"Error procesando datos: {e}")

# Servir el HTML
@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    print("\n========================================================")
    print("[*] Estación de Control Unificada Iniciada en Puerto 8000")
    print("========================================================")
    
    app.run(host='0.0.0.0', port=8000, debug=False)