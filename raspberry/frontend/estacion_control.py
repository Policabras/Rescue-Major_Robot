from flask import Flask
from flask_sock import Sock
import serial
import json
import webbrowser
import os
from threading import Timer

# TRUCO DE RUTA: Encontrar la carpeta exacta donde vive este archivo script
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

# Le decimos a Flask que busque el HTML y las imágenes exactamente ahí
app = Flask(__name__, static_folder=CARPETA_ACTUAL, static_url_path='')
sock = Sock(app)

# --- CONFIGURACIÓN SERIAL ---
PORT = 'COM6'  
BAUD_RATE = 115200

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    print(f"[*] Conectado exitosamente a la ESP32 en: {PORT}")
except Exception as e:
    print(f"[!] Alerta Serial: No se detectó la ESP32 ({e}). Modo simulación activo.")
    ser = None

# TÚNEL WEBSOCKET (Alta velocidad)
@sock.route('/robot')
def canal_robot(ws):
    print("[*] ¡Controlador web conectado al túnel WebSocket!")
    while True:
        mensaje = ws.receive()
        if not mensaje:
            break
        try:
            datos = json.loads(mensaje)
            izq = datos.get("izq", 0)
            der = datos.get("der", 0)
            
            if ser and ser.is_open:
                comando = f"v,{int(izq)},{int(der)}\n"
                ser.write(comando.encode('utf-8'))
        except Exception as e:
            print(f"Error en datos: {e}")

@app.route('/')
def index():
    return app.send_static_file('index.html')

def abrir_navegador():
    webbrowser.open_new_tab("http://localhost:8000/")

if __name__ == '__main__':
    print("\n========================================================")
    print("[*] Lanzando Estación de Control Unificada...")
    print("========================================================")
    
    Timer(1.0, abrir_navegador).start()
    app.run(host='0.0.0.0', port=8000, debug=False)