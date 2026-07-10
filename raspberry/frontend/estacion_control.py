#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import serial
import threading
import time
import cv2
import pyaudio
import av
import numpy as np
from fractions import Fraction
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

UART_PORT = "/dev/serial0"
UART_BAUD = 115200
ser = None
pcs = set()
telemetria_actual = {"tipo": "telemetria", "voltaje": "0.0", "porcentaje": "0"}

# CONEXIÓN SERIAL (A ESP32)
try:
    ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0.1)
    print(f"[*] [SERIAL] Conectado a la ESP32 en ({UART_PORT})")
except Exception:
    try:
        ser = serial.Serial("/dev/ttyUSB0", UART_BAUD, timeout=0.1)
        print("[*] [SERIAL] Conectado por USB de respaldo.")
    except Exception:
        print("[!] Modo simulación activo.")

# ESCÁNER DE CÁMARA
def inicializar_camara_inteligente():
    for index in [2, 4, 1, 0, 10, 11, 14]:
        test_cap = cv2.VideoCapture(index)
        if test_cap.isOpened():
            for _ in range(3): ret, frame = test_cap.read()
            if ret and frame is not None and frame.shape[0] > 0:
                print(f"✨ [CÁMARA] ¡Webcam detectada en /dev/video{index}!")
                return test_cap
        test_cap.release()
    return cv2.VideoCapture(0)

cap = inicializar_camara_inteligente()

# =========================================================
# TRACKS WEBRTC (VIDEO Y AUDIO NATIVOS)
# =========================================================
class VideoStreamTrack(MediaStreamTrack):
    kind = "video"
    def __init__(self, cap):
        super().__init__()
        self.cap = cap
        self.pts = 0

    async def recv(self):
        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, self.cap.read)
        if not ret or frame is None:
            await asyncio.sleep(0.03)
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            frame = cv2.resize(frame, (640, 480))
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        self.pts += 1
        video_frame.pts = self.pts
        video_frame.time_base = Fraction(1, 30)
        return video_frame

class AudioStreamTrack(MediaStreamTrack):
    kind = "audio"
    def __init__(self):
        super().__init__()
        self.p = pyaudio.PyAudio()
        try:
            self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=960)
            print("[*] [AUDIO] Micrófono físico acoplado a WebRTC.")
        except Exception as e:
            print(f"[!] No se detectó micrófono físico: {e}. Enviando silencio.")
            self.stream = None
        self.pts = 0

    async def recv(self):
        if self.stream is None:
            await asyncio.sleep(0.06)
            frame = av.AudioFrame(format='s16', layout='mono', samples=960)
            frame.sample_rate = 16000
            self.pts += 960
            frame.pts = self.pts
            frame.time_base = Fraction(1, 16000)
            return frame

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, self.stream.read, 960, False)
        frame = av.AudioFrame(format='s16', layout='mono', samples=960)
        frame.sample_rate = 16000
        frame.planes[0].update(data)
        self.pts += 960
        frame.pts = self.pts
        frame.time_base = Fraction(1, 16000)
        return frame

# HILO TELEMETRÍA ESP32
def escuchar_esp32_bateria():
    global telemetria_actual
    while True:
        if ser and ser.is_open:
            try:
                if ser.in_waiting > 0:
                    linea = ser.readline().decode('utf-8', errors='ignore').strip()
                    if linea.startswith("<b,") and linea.endswith(">"):
                        datos = linea[3:-1].split(',')
                        if len(datos) == 2:
                            telemetria_actual = {"tipo": "telemetria", "voltaje": datos[0], "porcentaje": datos[1]}
            except Exception: pass
        time.sleep(0.01)

threading.Thread(target=escuchar_esp32_bateria, daemon=True).start()

# =========================================================
# RUTAS DEL SERVIDOR INTERNET / LOCAL
# =========================================================
async def index(request):
    return web.FileResponse(os.path.join(CARPETA_ACTUAL, 'index.html'))

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)

    # Añadimos los canales multimedia directos
    pc.addTrack(VideoStreamTrack(cap))
    pc.addTrack(AudioStreamTrack())

    # Data Channel para Mandos y Telemetría rápida
    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            try:
                datos = json.loads(message)
                v = max(-1000, min(1000, int(datos.get("v", 0))))
                w = max(-1000, min(1000, int(datos.get("w", 0))))
                if ser and ser.is_open:
                    ser.write(f"<{v},{w}>\n".encode('utf-8'))
            except Exception: pass

        async def enviar_telemetria_loop():
            ultimo_pct = ""
            while channel.readyState == "open":
                global telemetria_actual
                if telemetria_actual.get("porcentaje") != ultimo_pct:
                    try:
                        channel.send(json.dumps(telemetria_actual))
                        ultimo_pct = telemetria_actual.get("porcentaje")
                    except Exception: break
                await asyncio.sleep(0.2)

        asyncio.create_task(enviar_telemetria_loop())

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.json_response({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

async def al_cerrar(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
    cap.release()

app = web.Application()
app.router.add_get('/', index)
app.router.add_post('/offer', offer)
app.router.add_static('/imgs/', path=os.path.join(CARPETA_ACTUAL, 'imgs'))
app.on_shutdown.append(al_cerrar)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=8000)