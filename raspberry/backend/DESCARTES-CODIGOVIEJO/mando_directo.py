import serial
import pygame
import time
import sys

# --- CONFIGURACIÓN SERIAL ---
PORT = 'COM6'
BAUD_RATE = 115200

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    print(f"[*] Conectado exitosamente a la ESP32 en {PORT}")
except Exception as e:
    print(f"[!] Error serial: {e}")
    sys.exit()

# --- INICIALIZAR PYGAME PARA EL MANDO ---
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("[!] No se detectó ningún mando de PS4. ¡Conéctalo por USB o Bluetooth!")
    sys.exit()

# Agarrar el primer control disponible
mando = pygame.joystick.Joystick(0)
mando.init()
print(f"[*] Mando detectado: {mando.get_name()}")

MAX_VEL = 150
ZONA_MUERTA = 0.15

print("\n=============================================")
# Mantener las cosas claras en la terminal
print("[*] ¡SISTEMA LISTO! Controla con tu mando de PS4:")
print("    - R2: Avanzar")
print("    - L2: Reversa")
print("    - Joystick Izquierdo (Eje X): Giro")
print("    Presiona CTRL+C en la terminal para salir.")
print("=============================================")

try:
    while True:
        # Procesar los eventos de Pygame (Obligatorio para que lea el control)
        pygame.event.pump()

        # 1. LEER EJES DEL MANDO DE PS4
        # Mapeo estándar en Windows para PS4 (Pygame):
        # Axis 0 = Joystick Izquierdo (X)
        # Axis 4 = Gatillo L2 (En Pygame va de -1 cuando está libre a 1 cuando se presiona a tope)
        # Axis 5 = Gatillo R2 (Igual, -1 libre a 1 presionado)
        
        steer = mando.get_axis(0)
        
        # Ajuste de gatillos (Convertir rango -1 a 1 de pygame a rango 0 a 1 limpio)
        l2_raw = mando.get_axis(4)
        r2_raw = mando.get_axis(5)
        
        reversa = (l2_raw + 1) / 2.0  # Rango 0.0 a 1.0
        avance = (r2_raw + 1) / 2.0   # Rango 0.0 a 1.0

        # Filtro de zona muerta para el joystick
        if abs(steer) < ZONA_MUERTA:
            steer = 0.0

        # 2. CALCULAR ENTRADAS BASE
        throttle = (avance - reversa) * MAX_VEL
        giro = steer * MAX_VEL

        # 3. MEZCLA DIFERENCIAL (Tus reglas de giros de tanque, abiertos y cerrados)
        rpm_izq = throttle + giro
        rpm_der = throttle - giro

        # Limitar estrictamente los rangos finales
        rpm_izq = max(-MAX_VEL, min(MAX_VEL, rpm_izq))
        rpm_der = max(-MAX_VEL, min(MAX_VEL, rpm_der))

        # Convertir a enteros
        rpm_izq = int(rpm_izq)
        rpm_der = int(rpm_der)

        # 4. ENVIAR A LA ESP32 (Solo si el puerto está abierto)
        if ser and ser.is_open:
            comando = f"v,{rpm_izq},{rpm_der}\n"
            ser.write(comando.encode('utf-8'))
            
            # Imprime en pantalla para que veas la telemetría volar en tiempo real
            print(f"[MANDO] Mandando -> T: {int(throttle)} | G: {int(giro)} | Cadena: {comando.strip()}", end='\r')

        # Dormir el script exactamente 20ms (Correr a 50Hz constantes sin saturar)
        time.sleep(0.02)

except KeyboardInterrupt:
    print("\n[-] Apagando el control del mando...")
    if ser and ser.is_open:
        ser.write(b"v,0,0\n") # Detener motores al salir
        ser.close()
    print("[*] Puerto serial cerrado. ¡Bye!")