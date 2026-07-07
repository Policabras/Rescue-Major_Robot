#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import serial
import threading
import time
from flask import Flask
from flask_sock import Sock
from pyngrok import ngrok

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

UART_PORT = "/dev/serial0"
UART_BAUD = 115200
ser = None

# Set para rastrear las pestañas web conectadas simultáneamente
clientes_conectados = set()

# =========================================================
# CONEXIÓN SERIAL (A ESP32)
# =========================================================
try:
    ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0.1)
    print(f"[*] [SERIAL] Conectado exitosamente a la ESP32 en pines GPIO ({UART_PORT})")
except Exception as e:
    print(f"[!] [SERIAL] Error en GPIO: {e}. Intentando por USB (/dev/ttyUSB0)...")
    try:
        ser = serial.Serial("/dev/ttyUSB0", UART_BAUD, timeout=0.1)
        print("[*] [SERIAL] Conectado por USB de respaldo!")
    except Exception as err:
        print(f"[!] [SERIAL] Error crítico: {err}. Modo simulación activo (Motores apagados).")

# =========================================================
# HILO SECUNDARIO: OÍDO DE LA RASPBERRY (LEER BATERÍA)
# =========================================================
def escuchar_esp32_bateria():
    global ser
    print("[*] [HILO-BATERÍA] Buscando telemetría de la ESP32...")
    while True:
        if ser and ser.is_open:
            try:
                if ser.in_waiting > 0:
                    # Leemos la línea que manda la ESP32
                    linea = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    # Filtramos el paquete de batería: <b,voltaje,porcentaje>
                    if linea.startswith("<b,") and linea.endswith(">"):
                        datos = linea[3:-1].split(',')
                        if len(datos) == 2:
                            voltaje = datos[0]
                            porcentaje = datos[1]
                            
                            # Creamos el JSON para la página web
                            paquete_web = json.dumps({
                                "tipo": "telemetria",
                                "voltaje": voltaje,
                                "porcentaje": porcentaje
                            })
                            
                            # Se lo disparamos a todas las webs que estén viendo el rover
                            for ws in list(clientes_conectados):
                                try:
                                    ws.send(paquete_web)
                                except Exception:
                                    clientes_conectados.remove(ws)
                                    
            except Exception as e:
                print(f"[!] [HILO-BATERÍA] Error leyendo serial: {e}")
        time.sleep(0.01) # Pausa micro para no saturar el procesador de la Pi

# Iniciamos el hilo de la batería en background para que no trabe la web
threading.Thread(target=escuchar_esp32_bateria, daemon=True).start()

# =========================================================
# CANAL WEBSOCKET (MANDOS DESDE LA WEB)
# =========================================================
@sock.route('/robot')
def canal_robot(ws):
    print("[*] [WEBSOCKET] ¡Mando en línea detectado por el túnel!")
    clientes_conectados.add(ws)
    
    try:
        while True:
            mensaje = ws.receive()
            if not mensaje:
                break
                
            try:
                datos = json.loads(mensaje)
                
                # Tu nueva ESP32 pide velocidad lineal (v) y giro angular (w)
                # en un rango potente de -1000 a 1000
                v = int(datos.get("v", 0))
                w = int(datos.get("w", 0))
                
                # Límites estrictos de seguridad de tu nuevo código
                v = max(-1000, min(1000, v))
                w = max(-1000, min(1000, w))
                
                if ser and ser.is_open:
                    # Formato exacto que parsea tu main.ino: <v,w>\n
                    paquete_serial = f"<{v},{w}>\n"
                    ser.write(paquete_serial.encode('utf-8'))
                    
            except Exception as e:
                print(f"[!] Error procesando JSON de la web: {e}")
                
    finally:
        if ws in clientes_conectados:
            clientes_conectados.remove(ws)
        print("[*] [WEBSOCKET] Mando web desconectado.")

@app.route('/')
def index():
    return app.send_static_file('index.html')

# =========================================================
# ARRANQUE DEL SERVIDOR Y TÚNEL NGROK
# =========================================================
if __name__ == '__main__':
    PUERTO_LOCAL = 8000
    
    print("\n========================================================")
    print("[*] [NGROK] Levantando puente seguro hacia Internet...")
    print("========================================================")
    
    try:
        tunel_publico = ngrok.connect(PUERTO_LOCAL, bind_tls=True)
        url_publica = tunel_publico.public_url
        print("\n🚀 ¡SISTEMA UNIFICADO EN LÍNEA DESDE CUALQUIER LUGAR! 🚀")
        print(f"🔗 Entra desde tu cel aquí: {url_publica}")
        print("========================================================\n")
    except Exception as e:
        print(f"[!] [NGROK] Error al iniciar túnel: {e}. Solo disponible en red local.")

    app.run(host='0.0.0.0', port=PUERTO_LOCAL, debug=False)