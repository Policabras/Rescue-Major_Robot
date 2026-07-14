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

# VARIABLE GLOBAL DE CONTROL DE CPU
AUDIO_DESACTIVADO_POR_SOBRECARGA = False

# =========================================================
# MONITOR DE CPU (FRENO DE MANO SEGURO)
# =========================================================
def monitor_seguridad_cpu():
    """ Monitorea la CPU. Si se sobrecarga, apaga el audio para salvar al robot """
    global AUDIO_DESACTIVADO_POR_SOBRECARGA
    while True:
        try:
            # Leemos la carga de la CPU de forma nativa en Linux (evita instalar psutil)
            with open("/proc/loadavg", "r") as f:
                load_1min = float(f.read().split()[0])
            
            # Si la carga promedio supera el número de núcleos o un umbral alto
            # Nota: Puedes ajustar este valor. Si notas ralentización, bájalo a 1.5 o 2.0
            if load_1min > 3.2 and not AUDIO_DESACTIVADO_POR_SOBRECARGA:
                AUDIO_DESACTIVADO_POR_SOBRECARGA = True
                print("[⚠️ SEGURIDAD] ¡CPU SOBRECARGADA! Desactivando captura de audio para proteger el sistema.")
            elif load_1min < 1.8 and AUDIO_DESACTIVADO_POR_SOBRECARGA:
                AUDIO_DESACTIVADO_POR_SOBRECARGA = False
                print("[✨ SEGURIDAD] CPU normalizada. Reactivando audio.")
        except Exception:
            pass
        time.sleep(2.0)

threading.Thread(target=monitor_seguridad_cpu, daemon=True).start()


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
# TRACKS WEBRTC
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
            await asyncio.sleep(0.04)
            frame = np.zeros((360, 480, 3), dtype=np.uint8)
        else:
            frame = cv2.resize(frame, (480, 360))
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        self.pts += 1
        video_frame.pts = self.pts
        video_frame.time_base = Fraction(1, 25)
        return video_frame

class AudioStreamTrack(MediaStreamTrack):
    kind = "audio"
    def __init__(self):
        super().__init__()
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.pts = 0
        self.rate = 16000
        self.samples = 320
        
        index_micro = None
        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    nombre = info.get('name', '').lower()
                    if any(x in nombre for x in ["usb", "mic", "webcam", "audio"]):
                        index_micro = i
                        break
                    if index_micro is None: index_micro = i
            except Exception: pass

        if index_micro is not None:
            for rate_test in [16000, 44100, 48000, 8000]:
                try:
                    samples_test = int(rate_test * 0.02)
                    self.stream = self.p.open(
                        format=pyaudio.paInt16, 
                        channels=1, 
                        rate=rate_test, 
                        input=True, 
                        input_device_index=index_micro,
                        frames_per_buffer=samples_test
                    )
                    self.rate = rate_test
                    self.samples = samples_test
                    print(f"✨ [AUDIO] Micrófono activo a {self.rate}Hz")
                    break
                except Exception: continue

    async def recv(self):
        global AUDIO_DESACTIVADO_POR_SOBRECARGA
        
        # Si el micro falló al abrir o el freno de mano de CPU se activó, inyectamos silencio
        if self.stream is None or AUDIO_DESACTIVADO_POR_SOBRECARGA:
            await asyncio.sleep(0.02) # Emula los 20ms de retraso de hardware
            data = b'\x00' * (self.samples * 2) # Bytes vacíos = Silencio absoluto
        else:
            loop = asyncio.get_event_loop()
            try:
                # exception_on_overflow=False impide que el script muera si la Pi se retrasa
                data = await loop.run_in_executor(
                    None, 
                    self.stream.read, 
                    self.samples, 
                    False
                )
            except Exception:
                data = b'\x00' * (self.samples * 2)
            
        frame = av.AudioFrame(format='s16', layout='mono', samples=self.samples)
        frame.sample_rate = self.rate
        frame.planes[0].update(data)
        self.pts += self.samples
        frame.pts = self.pts
        frame.time_base = Fraction(1, self.rate)
        return frame

    def cerrar_hardware(self):
        """ Libera el micrófono inmediatamente al desconectarse el cliente """
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.p:
                self.p.terminate()
            print("[*] [AUDIO] Hardware de micrófono liberado correctamente.")
        except Exception:
            pass

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
# RUTAS DEL SERVIDOR LOCAL
# =========================================================
async def index(request):
    return web.FileResponse(os.path.join(CARPETA_ACTUAL, 'index.html'))

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    pcs.add(pc)

    audio_track = AudioStreamTrack()

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState in ["failed", "closed"]:
            audio_track.cerrar_hardware() # Forzamos la liberación del micrófono
            await pc.close()
            pcs.discard(pc)

    pc.addTrack(VideoStreamTrack(cap))
    pc.addTrack(audio_track)

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