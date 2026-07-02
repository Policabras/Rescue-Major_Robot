import cv2
import time
import threading
import asyncio
from fractions import Fraction
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

# --- CÁMARA EN HILO INDEPENDIENTE ---
class ThreadedCamera:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
        self.detector = cv2.QRCodeDetector()
        
        self.ret, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()
        self.qr_memoria = []
        self.persistencia = 0.25

    def start(self):
        if self.started: return self
        self.started = True
        threading.Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while self.started:
            ret, frame = self.cap.read()
            if ret:
                ahora = time.time()
                small = cv2.resize(frame, (320, 240))
                retval, decoded_info, points, _ = self.detector.detectAndDecodeMulti(small)
                
                nuevos_qr = []
                if retval and points is not None:
                    scale_x = frame.shape[1] / 320
                    scale_y = frame.shape[0] / 240
                    for i, data in enumerate(decoded_info):
                        if data != "":
                            pts = points[i]
                            scaled_pts = [((p[0] * scale_x), (p[1] * scale_y)) for p in pts]
                            nuevos_qr.append({"data": data, "bbox": scaled_pts, "time": ahora})

                if nuevos_qr:
                    self.qr_memoria = nuevos_qr
                else:
                    self.qr_memoria = [qr for qr in self.qr_memoria if ahora - qr["time"] < self.persistencia]

                for qr in self.qr_memoria:
                    bbox = qr["bbox"]
                    for j in range(4):
                        cv2.line(frame, tuple(map(int, bbox[j])), tuple(map(int, bbox[(j+1)%4])), (0, 255, 0), 2)
                    cv2.putText(frame, qr["data"], (int(bbox[0][0]), int(bbox[0][1]) - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                with self.read_lock:
                    self.ret = ret
                    self.frame = frame
            time.sleep(0.01)

    def get_frame(self):
        with self.read_lock:
            return self.ret, self.frame.copy() if self.ret else None

    def stop(self):
        self.started = False
        self.cap.release()

camara = ThreadedCamera(src=0).start()

# --- TRACK WEBRTC ---
class CameraTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.counter = 0

    async def recv(self):
        ret, frame = camara.get_frame()
        if not ret or frame is None:
            await asyncio.sleep(0.01)
            return await self.recv()

        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        self.counter += 1
        video_frame.pts = self.counter
        video_frame.time_base = Fraction(1, 30)
        return video_frame

# --- MANEJO DEL SERVIDOR ASÍNCRONO ---
pcs = set()

async def offer(request):
    params = await request.json()
    pc = RTCPeerConnection()
    pcs.add(pc)
    
    pc.addTrack(CameraTrack())
    
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return web.json_response({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    camara.stop()

app = web.Application()
app.router.add_post("/offer", offer)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    print("\n========================================================")
    print("[*] Servidor de VIDEO WebRTC Activo en Puerto 8080")
    print("========================================================")
    web.run_app(app, host="0.0.0.0", port=8080)
