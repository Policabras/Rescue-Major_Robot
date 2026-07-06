#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask
from flask_sock import Sock
import serial
import json
import os
from pyngrok import ngrok

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

# --- CONFIGURACIÓN SERIAL FORZADA (Pines GPIO de la Rasp) ---
UART_PORT = "/dev/serial0"
BAUD_RATE = 115200
ser = None

try:
    ser = serial.Serial(UART_PORT, BAUD_RATE, timeout=0.05)
    print(f"[*] [SERIAL] ¡Conectado exitosamente a la ESP32 en pines GPIO ({UART_PORT})!")
except Exception as e:
    print(f"[!] [SERIAL] Error abriendo {UART_PORT}: {e}")
    print("[*] [SERIAL] Intentando por USB (/dev/ttyUSB0) por si acaso...")
    try:
        ser = serial.Serial("/dev/ttyUSB0", BAUD_RATE, timeout=0.05)
        print("[*] [SERIAL] Conectado por USB!")
    except Exception as err:
        print(f"[!] [SERIAL] Tampoco se pudo por USB: {err}. Modo simulación activo.")
        ser = None

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
            
            # Recibimos throttle y giro directamente desde el index.html
            throttle = datos.get("izq", 0)  
            giro = datos.get("der", 0)      
            
            # Escalamos el rango de la web (-150 a 150) al rango de la ESP32 (-1000 a 1000)
            v = int((throttle / 150.0) * 1000)
            w = int((giro / 150.0) * 1000)
            f = 0  # Flipper por defecto en 0
            
            # Limitamos por seguridad
            v = max(-1000, min(1000, v))
            w = max(-1000, min(1000, w))
            
            if ser and ser.is_open:
                # FORMATO EXACTO QUE TU CODIGO DE ARDUINO ENTIENDE
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