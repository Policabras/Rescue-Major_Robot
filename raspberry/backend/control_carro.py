import serial
import time
import sys

def iniciar_control():
    # Recuerda verificar si tu puerto es ttyACM0 o ttyUSB0
    PUERTO_SERIAL = '/dev/ttyACM0' 
    BAUDIOS = 115200

    try:
        # Ponemos un timeout de 0.5s por si el Arduino se desconecta, no colgar el script
        arduino = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.5)
        time.sleep(2) 
        print("[OK] ¡Conectado exitosamente al Arduino!")
    except Exception as e:
        print(f"[ERROR] No se pudo abrir el puerto {PUERTO_SERIAL}. {e}")
        return

    print("\n-------------------------------------------------")
    print("   ¡MODO TERMINAL MÓVIL ESTABLE (WASD + Enter)!")
    print("-------------------------------------------------")
    print(" Escribe una letra y presiona ENTER en tu cel:")
    print("  w -> Avanzar  |  s -> Retroceder")
    print("  a -> Izquierda |  d -> Derecha")
    print("  x -> FRENAR    |  q -> Salir del script")
    print("-------------------------------------------------")

    try:
        while True:
            comando_usuario = input("Comando movil > ").strip().lower()

            throttle = 0.0
            steering = 0.0
            
            if comando_usuario == 'q':
                print("[INFO] Saliendo...")
                break
            elif comando_usuario == 'w':
                throttle = 0.7
            elif comando_usuario == 's':
                throttle = -0.7
            elif comando_usuario == 'a':
                steering = -0.5
            elif comando_usuario == 'd':
                steering = 0.5
            elif comando_usuario == 'x':
                throttle = 0.0
                steering = 0.0
            else:
                print("[!] Opción inválida. Usa: w, a, s, d, x o q")
                continue

            # Matemática Arcade Drive
            izq_proporcional = throttle + steering
            der_proporcional = throttle - steering

            vel_izq = max(-255, min(255, int(izq_proporcional * 255)))
            vel_der = max(-255, min(255, int(der_proporcional * 255)))

            # 1. Enviar comando al Arduino con su \n bien marcado
            comando_serial = f"v,{vel_izq},{vel_der}\n"
            arduino.write(comando_serial.encode('utf-8'))
            arduino.flush() # Forzar el envío inmediato de los bytes

            # 2. ESPERA SÍNCRONA: Python se frena hasta recibir la respuesta del Arduino
            respuesta = arduino.readline().decode('utf-8').strip()
            
            if respuesta:
                print(f" -> Arduino confirmo: {respuesta}\n")
            else:
                print(" -> [WARN] El Arduino tardó mucho en responder (Timeout).\n")

    except KeyboardInterrupt:
        pass
    finally:
        print("\n[INFO] Enviando freno de emergencia...")
        arduino.write(b"v,0,0\n")
        arduino.close()
        print("[OK] Puerto cerrado de forma segura.")

if __name__ == "__main__":
    iniciar_control()
      # q rancio