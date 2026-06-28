import serial
import time

# Intentemos con USB0 que es el estándar para ESP32
PUERTO = '/dev/ttyACM0' 
BAUDIOS = 115200

print(f"Abriendo puerto {PUERTO}...")
arduino = serial.Serial(PUERTO, BAUDIOS, timeout=1)
time.sleep(2) # Esperar a que el chip despierte

print("Enviando '1' (Encender LED)...")
arduino.write(b'1')
time.sleep(2)

print("Enviando '0' (Apagar LED)...")
arduino.write(b'0')
time.sleep(1)

arduino.close()
print("Prueba terminada.")