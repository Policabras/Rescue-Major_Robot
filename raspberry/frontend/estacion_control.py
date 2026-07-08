#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import serial
import threading
import time
import cv2
from flask import Flask, request, jsonify, Response
from flask_sock import Sock
from pyngrok import ngrok

# =========================================================
# CONFIGURACIÓN GENERAL DE RUTAS Y FLASK
# =========================================================
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

UART_PORT = "/dev/serial0"
UART_BAUD = 115200
ser = None
clientes_conectados = set()

# =========================================================
# CONEXIÓN SERIAL INTERNA (A ESP32)
# =========================================================
try:
    ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0.1)
    print(f"[*] [SERIAL] Conectado a la ESP32 en ({UART_PORT})")
except Exception as e:
    print(f"[!] [SERIAL] Error en pines GPIO: {e}. Intentando USB (/dev/ttyUSB0)...")
    try:
        ser = serial.Serial("/dev/ttyUSB0", UART_BAUD, timeout=0.1)
        print("[*] [SERIAL] ¡Conectado por USB de respaldo!")
    except Exception as err:
        print(f"[!] [SERIAL] Modo simulación activo (Motores en pausa).")

# =========================================================
# ESCÁNER MEJORADO DE CÁMARA
# =========================================================
def inicializar_camara_inteligente():
    for index in [2, 4, 1, 0, 10, 11, 14]:
        print(f"[*] [CÁMARA] Evaluando canal físico /dev/video{index}...")
        test_cap = cv2.VideoCapture(index)
        if test_cap.isOpened():
            for _ in range(3):
                ret, frame = test_cap.read()
            if ret and frame is not None and frame.shape[0] > 0:
                print(f"✨ [CÁMARA] ¡Webcam REAL detectada en /dev/video{index}!")
                test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                return test_cap
        test_cap.release()
    
    print("[!] [CÁMARA] Usando canal por defecto 0.")
    return cv2.VideoCapture(0)

cap = inicializar_camara_inteligente()

# =========================================================
# GENERADOR MAESTRO MJPEG (RÁPIDO Y LIGERO PARA TUNEL)
# =========================================================
def generar_fotogramas_mjpeg():
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.03)
            continue
        
        # Comprimimos a JPEG al 70% de calidad para que vuele por el túnel de Ngrok sin lag
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ret:
            continue
            
        bytes_imagen = buffer.tobytes()
        
        # Empaquetado binario estándar que los navegadores entienden de forma nativa
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytes_imagen + b'\r\n')
        
        # Forzamos una pequeña pausa para clavar la transmisión a unos ~30 FPS estables
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    # Retorna el streaming continuo usando el formato multipart nativo
    return Response(generar_fotogramas_mjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# =========================================================
# TELEMETRÍA DE BATERÍA Y MANDOS POR WEBSOCKET
# =========================================================
def escuchar_esp32_bateria():
    while True:
        if ser and ser.is_open:
            try:
                if ser.in_waiting > 0:
                    linea = ser.readline().decode('utf-8', errors='ignore').strip()
                    if linea.startswith("<b,") and linea.endswith(">"):
                        datos = linea[3:-1].split(',')
                        if len(datos) == 2:
                            paquete_web = json.dumps({"tipo": "telemetria", "voltaje": datos[0], "porcentaje": datos[1]})
                            for ws in list(clientes_conectados):
                                try:
                                    ws.send(paquete_web)
                                except Exception:
                                    clientes_conectados.remove(ws)
            except Exception:
                pass
        time.sleep(0.01)

threading.Thread(target=escuchar_esp32_bateria, daemon=True).start()

@sock.route('/robot')
def canal_robot(ws):
    print("[*] [WEBSOCKET] Mando en línea detectado por el túnel.")
    clientes_conectados.add(ws)
    paquetes_recibidos = 0
    try:
        while True:
            mensaje = ws.receive()
            if not mensaje: break
            try:
                datos = json.loads(mensaje)
                v = max(-1000, min(1000, int(datos.get("v", 0))))
                w = max(-1000, min(1000, int(datos.get("w", 0))))
                
                paquetes_recibidos += 1
                if paquetes_recibidos % 33 == 0: 
                    print(f"📡 [WEB -> PI] Mandos: v={v:4d} | w={w:4d}")
                
                if ser and ser.is_open:
                    ser.write(f"<{v},{w}>\n".encode('utf-8'))
            except Exception:
                pass
    finally:
        if ws in clientes_conectados: clientes_conectados.remove(ws)

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    PUERTO_LOCAL = 8000
    try:
        tunel_publico = ngrok.connect(PUERTO_LOCAL, bind_tls=True)
        print(f"\n🚀 ¡ROVER ONLINE CON MJPEG! 🔗 Abre este enlace: {tunel_publico.public_url}\n")
    except Exception as e:
        print(f"[!] Ngrok deshabilitado: {e}")
    app.run(host='0.0.0.0', port=PUERTO_LOCAL, debug=False)