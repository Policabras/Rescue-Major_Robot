import serial
import time
import sys

def iniciar_control():
    # ==========================================
    # CONFIGURACIÓN DEL PUERTO SERIAL
    # ==========================================
    PUERTO_SERIAL = '/dev/ttyACM0' 
    BAUDIOS = 115200

    try:
        arduino = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.1)
        time.sleep(2) 
        print("[OK] ¡Conectado exitosamente al Arduino!")
    except Exception as e:
        print(f"[ERROR] No se pudo abrir el puerto {PUERTO_SERIAL}. {e}")
        return

    print("\n-------------------------------------------------")
    print("   ¡MODO TERMINAL MÓVIL ACTIVO (WASD + Enter)!")
    print("-------------------------------------------------")
    print(" Escribe una letra y presiona ENTER en tu cel:")
    print("  w -> Avanzar  |  s -> Retroceder")
    print("  a -> Izquierda |  d -> Derecha")
    print("  x -> FRENAR    |  q -> Salir del script")
    print("-------------------------------------------------")

    try:
        while True:
            # Captura lo que escribas en el teclado del teléfono
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

            # Matemática de conversión para los motores
            izq_proporcional = throttle + steering
            der_proporcional = throttle - steering

            vel_izq = max(-255, min(255, int(izq_proporcional * 255)))
            vel_der = max(-255, min(255, int(der_proporcional * 255)))

            # Mandar la cadena de texto "v,izq,der" al Arduino
            comando_serial = f"v,{vel_izq},{vel_der}\n"
            arduino.write(comando_serial.encode('utf-8'))
            
            print(f" -> Ejecutando en Arduino: v,{vel_izq},{vel_der}\n")

    except KeyboardInterrupt:
        pass
    finally:
        print("\n[INFO] Enviando freno de emergencia...")
        arduino.write(b"v,0,0\n")
        arduino.close()
        print("[OK] Puerto cerrado de forma segura.")

if __name__ == "__main__":
    iniciar_control()