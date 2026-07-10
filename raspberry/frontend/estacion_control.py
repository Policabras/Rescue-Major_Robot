#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import serial
import threading
import time
import cv2
import pyaudio
from flask import Flask, request, jsonify, Response
from flask_sock import Sock

# CONFIGURACIÓN GENERAL
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

UART_PORT = "/dev/serial0"
UART_BAUD = 115200
ser = None
clientes_conectados = set()

# CONEXIÓN SERIAL (A ESP32)
try:
    ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0.1)
    print(f"[*] [SERIAL] Conectado a la ESP32 en ({UART_PORT})")
except Exception as e:
    print(f"[!] [SERIAL] Error en GPIO: {e}. Intentando USB (/dev/ttyUSB0)...")
    try:
        ser = serial.Serial("/dev/ttyUSB0", UART_BAUD, timeout=0.1)
        print("[*] [SERIAL] ¡Conectado por USB de respaldo!")
    except Exception as err:
        print(f"[!] [SERIAL] Modo simulación activo.")

# ESCÁNER DE CÁMARA
def inicializar_camara_inteligente():
    for index in [2, 4, 1, 0, 10, 11, 14]:
        test_cap = cv2.VideoCapture(index)
        if test_cap.isOpened():
            for _ in range(3): ret, frame = test_cap.read()
            if ret and frame is not None and frame.shape[0] > 0:
                print(f"✨ [CÁMARA] ¡Webcam detectada en /dev/video{index}!")
                test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                return test_cap
        test_cap.release()
    return cv2.VideoCapture(0)

cap = inicializar_camara_inteligente()

# STREAMING DE VIDEO (MJPEG LOCAL)
def generar_fotogramas_mjpeg():
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.03)
            continue
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ret: continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    return Response(generar_fotogramas_mjpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 🔥 NUEVO: TUNEL DE AUDIO CON DETECTOR AUTOMÁTICO DE MICRÓFONO USB
@sock.route('/audio')
def canal_audio(ws):
    print("[*] [AUDIO] Intentando abrir canal de sonido...")
    p = pyaudio.PyAudio()
    CHUNKS = 1024
    dispositivo_index = None

    # 🔎 ESCÁNER DE MICRÓFONOS EN LINUX
    try:
        conteo = p.get_device_count()
        print(f"[AUDIO] Escaneando {conteo} dispositivos de audio disponibles...")
        for i in range(conteo):
            info = p.get_device_info_by_index(i)
            nombre = info.get('name', '').lower()
            canales_entrada = info.get('maxInputChannels', 0)
            
            # Si tiene canales de entrada, es un micrófono
            if canales_entrada > 0:
                print(f"   🎤 ID {i}: {info.get('name')} (Entradas: {canales_entrada})")
                # Si el nombre dice USB o Cam, asumimos que es el de la webcam
                if "usb" in nombre or "cam" in nombre or "audio" in nombre or "mic" in nombre:
                    dispositivo_index = i

        if dispositivo_index is not None:
            print(f"🎯 [AUDIO] ¡Target fijado! Usando micrófono USB de la cámara (ID: {dispositivo_index})")
        else:
            print("⚠️ [AUDIO] No se detectó micrófono USB explícito. Usando el predeterminado del sistema.")
    except Exception as e:
        print(f"[!] Error al escanear hardware de audio: {e}")

    # ABRIR STREAM CON EL ID CORRECTO
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=dispositivo_index, # <-- Forzamos el ID mapeado
            frames_per_buffer=CHUNKS
        )
        print("[*] [AUDIO] ¡Micrófono transmitiendo con éxito!")
    except Exception as e:
        print(f"[!] [AUDIO] Error crítico al abrir el hardware de audio: {e}")
        p.terminate()
        return

    try:
        while True:
            datos_audio = stream.read(CHUNKS, exception_on_overflow=False)
            ws.send(datos_audio)
    except Exception: pass
    finally:
        print("[-] [AUDIO] Canal de sonido cerrado.")
        try:
            stream.stop_stream()
            stream.close()
        except: pass
        p.terminate()

# TELEMETRÍA DE BATERÍA
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
                                try: ws.send(paquete_web)
                                except Exception: clientes_conectados.remove(ws)
            except Exception: pass
        time.sleep(0.01)

threading.Thread(target=escuchar_esp32_bateria, daemon=True).start()

# CANAL DE MANDOS
@sock.route('/robot')
def canal_robot(ws):
    print("[*] [WEBSOCKET] Mando conectado localmente.")
    clientes_conectados.add(ws)
    try:
        while True:
            mensaje = ws.receive()
            if not mensaje: break
            try:
                datos = json.loads(mensaje)
                v = max(-1000, min(1000, int(datos.get("v", 0))))
                w = max(-1000, min(1000, int(datos.get("w", 0))))
                if ser and ser.is_open:
                    ser.write(f"<{v},{w}>\n".encode('utf-8'))
            except Exception: pass
    finally:
        if ws in clientes_conectados: clientes_conectados.remove(ws)

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)