from flask import Flask
from flask_sock import Sock
import serial
import serial.tools.list_ports
import json
import os
from pyngrok import ngrok  # <- NUEVO: Para crear el túnel de internet

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')

# --- CONFIGURACIÓN DE SEGURIDAD PARA WEBSOCKETS EN INTERNET ---
# Por defecto, Flask-Sock bloquea conexiones externas si el host no coincide.
# Con esto permitimos que el WebSocket funcione a través de cualquier URL de ngrok.
app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': 25, 'ping_timeout': 15}
sock = Sock(app)

# --- CONFIGURACIÓN SERIAL AUTO-DETECTABLE ---
BAUD_RATE = 115200
ser = None

print("[*] [SERIAL] Buscando la ESP32 en los puertos USB de la Raspberry Pi...")
puertos = list(serial.tools.list_ports.comports())

for p in puertos:
    if 'ttyUSB' in p.device or 'ttyACM' in p.device:
        try:
            ser = serial.Serial(p.device, BAUD_RATE, timeout=0.05)
            print(f"[*] [SERIAL] ¡Conectado exitosamente a la ESP32 en: {p.device} ({p.description})!")
            break
        except Exception as e:
            print(f"[!] [SERIAL] Se encontró {p.device} pero no se pudo abrir: {e}")

if ser is None:
    print(f"[!] [SERIAL] ERROR CRÍTICO: No se detectó ninguna ESP32 conectada. Modo simulación activo.")


# TÚNEL WEBSOCKET
@sock.route('/robot')
def canal_robot(ws):
    print("[*] [WEBSOCKET] ¡Mando conectado remotamente al túnel de control!")
    while True:
        mensaje = ws.receive()
        if not mensaje:
            break
        try:
            datos = json.loads(mensaje)
            izq = datos.get("izq", 0)
            der = datos.get("der", 0)
            
            if ser and ser.is_open:
                comando = f"v{int(izq)},{int(der)}\n"
                ser.write(comando.encode('utf-8'))
        except Exception as e:
            print(f"Error procesando datos: {e}")

# Servir el HTML
@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    PUERTO_LOCAL = 8000
    
    print("\n========================================================")
    print("[*] [NGROK] Abriendo túnel hacia el internet exterior...")
    print("========================================================")
    
    try:
        # Abrimos el túnel HTTP en el puerto 8000 (Soporta HTTP y WebSockets automáticamente)
        tunel_publico = ngrok.connect(PUERTO_LOCAL, bind_tls=True)
        # Convertimos la URL a un formato limpio
        url_publica = tunel_publico.public_url
        
        print("\n🚀 ¡ROVER EN LÍNEA DESDE CUALQUIER PARTE DEL MUNDO! 🚀")
        print(f"🔗 Entra a esta URL desde tu celular o laptop: {url_publica}")
        print("========================================================\n")
    except Exception as e:
        print(f"[!] [NGROK] Error al iniciar el túnel: {e}")
        print("[*] Continuando solo en red local...")

    # Arrancamos Flask de forma normal
    app.run(host='0.0.0.0', port=PUERTO_LOCAL, debug=False)