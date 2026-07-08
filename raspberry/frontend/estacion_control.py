#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import serial
import threading
import time
import cv2
import asyncio
from flask import Flask, request, jsonify
from flask_sock import Sock
from pyngrok import ngrok

# Librerías de WebRTC y procesamiento de fotogramas
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaPlayer
from av import VideoFrame

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
# ESCÁNER MEJORADO: FILTRA CÁMARAS FANTASMAS
# =========================================================
def inicializar_camara_inteligente():
    # Escanea puertos físicos reales saltándose el puerto virtual /dev/video0 si es ciego
    for index in [2, 4, 1, 0, 10, 11, 14]:
        print(f"[*] [CÁMARA] Evaluando canal físico /dev/video{index}...")
        test_cap = cv2.VideoCapture(index)
        if test_cap.isOpened():
            # Limpiamos buffer interno leyendo cuadros basura
            for _ in range(3):
                ret, frame = test_cap.read()
            
            # Si responde con pixeles reales y dimensiones válidas
            if ret and frame is not None and frame.shape[0] > 0:
                print(f"✨ [CÁMARA] ¡Webcam REAL detectada y transmitiendo en /dev/video{index}!")
                test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                return test_cap
        test_cap.release()
    
    print("[!] [CÁMARA] Alerta: No se obtuvo respuesta de hardware real. Usando canal por defecto.")
    return cv2.VideoCapture(0)

cap = inicializar_camara_inteligente()

# =========================================================
# ESCÁNER INTELIGENTE DE MICRÓFONO (EVITA ERRORES ALSA)
# =========================================================
audio_player = None
for dispositivo_audio in ["hw:1", "hw:2", "default"]:
    try:
        audio_player = MediaPlayer(dispositivo_audio, format="alsa")
        print(f"🎤 [WEBRTC] Micrófono USB enganchado correctamente en: {dispositivo_audio}")
        break
    except Exception:
        audio_player = None

if not audio_player:
    print("[⚠️] [WEBRTC] No se detectó micrófono compatible. Transmisión solo de video activa.")

# =========================================================
# CLASE: TRACK DE VIDEO PERSONALIZADO DE OPENCV
# =========================================================
class OpenCVVideoTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, cap.read)
        
        if not ret or frame is None:
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "ERROR DE CAPTURA", (180, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

# =========================================================
# HILO ASÍNCRONO PARA WEBRTC (Evita congelar Flask)
# =========================================================
rtc_loop = asyncio.new_event_loop()
def correr_bucle_webrtc(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=correr_bucle_webrtc, args=(rtc_loop,), daemon=True).start()

pcs = set()

async def procesar_signaling_webrtc(offer_dict):
    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)
            print("[*] [WEBRTC] Conexión multimedia finalizada.")

    pc.addTrack(OpenCVVideoTrack())

    if audio_player and audio_player.audio:
        pc.addTrack(audio_player.audio)

    offer = RTCSessionDescription(sdp=offer_dict["sdp"], type=offer_dict["type"])
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

@app.route('/offer', methods=['POST'])
def handle_offer():
    datos_oferta = request.get_json()
    futuro = asyncio.run_coroutine_threadsafe(procesar_signaling_webrtc(datos_oferta), rtc_loop)
    respuesta_sdp = futuro.result()
    return jsonify(respuesta_sdp)

# =========================================================
# MANEJO DE BATERÍA Y MANDOS POR WEBSOCKET
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
                    print(f"📡 [WEB -> PI] Datos en vivo: v={v:4d} | w={w:4d}")
                
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
        print(f"\n🚀 ¡ROVER ONLINE! 🔗 Entra aquí: {tunel_publico.public_url}\n")
    except Exception as e:
        print(f"[!] Ngrok deshabilitado: {e}")
    app.run(host='0.0.0.0', port=PUERTO_LOCAL, debug=False)