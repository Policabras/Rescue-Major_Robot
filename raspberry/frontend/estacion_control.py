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
# CONEXIÓN SERIAL INTERNA (A ESP32)
# =========================================================
try:
    ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0.1)
    print(f"[*] [SERIAL] Conectado exitosamente a la ESP32 en ({UART_PORT})")
except Exception as e:
    print(f"[!] [SERIAL] Error en pines GPIO: {e}. Intentando por USB (/dev/ttyUSB0)...")
    try:
        ser = serial.Serial("/dev/ttyUSB0", UART_BAUD, timeout=0.1)
        print("[*] [SERIAL] ¡Conectado por USB de respaldo!")
    except Exception as err:
        print(f"[!] [SERIAL] Error crítico: {err}. Modo simulación activo (Motores en pausa).")

# =========================================================
# HILO SECUNDARIO: LEER BATERÍA DESDE LA ESP32
# =========================================================
def escuchar_esp32_bateria():
    global ser
    print("[*] [HILO-BATERÍA] Escuchando telemetría de la ESP32...")
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
                            
                            # Estructura JSON para enviar a la web
                            paquete_web = json.dumps({
                                "tipo": "telemetria",
                                "voltaje": voltaje,
                                "porcentaje": porcentaje
                            })
                            
                            # Transmitimos en vivo a todos los navegadores conectados
                            for ws in list(clientes_conectados):
                                try:
                                    ws.send(paquete_web)
                                except Exception:
                                    clientes_conectados.remove(ws)
                                    
            except Exception as e:
                print(f"[!] [HILO-BATERÍA] Error leyendo serial: {e}")
        time.sleep(0.01) # Pequeña pausa para no saturar el procesador

# Lanzamos el hilo de la batería en background
threading.Thread(target=escuchar_esp32_bateria, daemon=True).start()

# =========================================================
# CANAL WEBSOCKET (RECIBIR MANDOS DESDE LA WEB)
# =========================================================
@sock.route('/robot')
def canal_robot(ws):
    print("[*] [WEBSOCKET] ¡Mando en línea detectado por el túnel!")
    clientes_conectados.add(ws)
    
    # Contador chismoso para el terminal
    paquetes_recibidos = 0
    
    try:
        while True:
            mensaje = ws.receive()
            if not mensaje:
                break
                
            try:
                datos = json.loads(mensaje)
                
                # Leemos avance (v) y giro (w) mandados desde javascript
                v = int(datos.get("v", 0))
                w = int(datos.get("w", 0))
                
                # Límites de seguridad (-1000 a 1000)
                v = max(-1000, min(1000, v))
                w = max(-1000, min(1000, w))
                
                # Imprime en tu terminal una muestra para saber si la web responde
                paquetes_recibidos += 1
                if paquetes_recibidos % 33 == 0: 
                    print(f"📡 [WEB -> PI] Datos en vivo: v={v:4d} | w={w:4d}")
                
                # Escribimos directo al hardware en formato <v,w>\n
                if ser and ser.is_open:
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
# ARRANQUE DE SERVIDORES Y TÚNEL NGROK
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
        print(f"[!] [NGROK] Error al iniciar túnel: {e}. Disponible solo en red local.")

    app.run(host='0.0.0.0', port=PUERTO_LOCAL, debug=False)