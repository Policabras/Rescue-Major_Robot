from flask import Flask
from flask_sock import Sock
import serial
import serial.tools.list_ports
import json
import os
from pyngrok import ngrok

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

# --- CONFIGURACIÓN SERIAL AUTO-DETECTABLE ---
BAUD_RATE = 115200
ser = None

print("[*] [SERIAL] Buscando la ESP32 en los puertos USB de la Raspberry Pi...")
puertos = list(serial.tools.list_ports.comports())

for p in puertos:
    # Detecta cables USB o el mapeo por pines ttyAMA0 / ttySerial0
    if 'ttyUSB' in p.device or 'ttyACM' in p.device or 'ttyAMA' in p.device or 'serial0' in p.device:
        try:
            ser = serial.Serial(p.device, BAUD_RATE, timeout=0.05)
            print(f"[*] [SERIAL] ¡Conectado exitosamente a la ESP32 en: {p.device}!")
            break
        except Exception as e:
            print(f"[!] [SERIAL] No se pudo abrir {p.device}: {e}")

if ser is None:
    print(f"[!] [SERIAL] ERROR: No se detectó la ESP32. Modo simulación activo.")

# CANAL WEBSOCKET (CON INTERNET VÍA NGROK)
@sock.route('/robot')
def canal_robot(ws):
    print("[*] [WEBSOCKET] ¡Mando web conectado vía Túnel Seguro!")
    while True:
        mensaje = ws.receive()
        if not mensaje:
            break
        try:
            datos = json.loads(mensaje)
            
            # Recibimos los valores brutos mapeados desde el index.html
            # Mapeamos los rangos de la interfaz web (-150 a 150) al formato esperado (-1000 a 1000)
            izq_web = datos.get("izq", 0)  # Representa el avance/gatillo (v)
            der_web = datos.get("der", 0)  # Representa el giro/joystick (w)
            
            # Escalamos los valores a la escala de 1000 que usa el nuevo firmware
            v = int((izq_web / 150.0) * 1000)
            w = int((der_web / 150.0) * 1000)
            f = 0  # Flipper / Extra en 0 por ahora
            
            # Limitamos por seguridad
            v = max(-1000, min(1000, v))
            w = max(-1000, min(1000, w))
            
            if ser and ser.is_open:
                # NUEVO FORMATO REQUERIDO POR EL FIRMWARE CORRETO
                paquete = f"<{v},{w},{f}>\n"
                ser.write(paquete.encode('utf-8'))
                
        except Exception as e:
            print(f"Error procesando datos: {e}")

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    PUERTO_LOCAL = 8000
    
    print("\n========================================================")
    print("[*] [NGROK] Abriendo túnel seguro hacia el internet...")
    print("========================================================")
    
    try:
        tunel_publico = ngrok.connect(PUERTO_LOCAL, bind_tls=True)
        url_publica = tunel_publico.public_url
        print("\n🚀 ¡ROVER EN LÍNEA DESDE CUALQUIER PARTE DEL MUNDO! 🚀")
        print(f"🔗 URL para tu celular/laptop: {url_publica}")
        print("========================================================\n")
    except Exception as e:
        print(f"[!] [NGROK] Error al iniciar túnel: {e}. Solo red local.")

    app.run(host='0.0.0.0', port=PUERTO_LOCAL, debug=False)