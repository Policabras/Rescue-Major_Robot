import serial
import time
import pygame
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
        print("[OK] Conectado exitosamente al Arduino!")
    except Exception as e:
        print(f"[ERROR] No se pudo abrir el puerto {PUERTO_SERIAL}. {e}")
        return

    # ==========================================
    # INICIALIZACIÓN DE PYGAME (MANDO Y VENTANA)
    # ==========================================
    pygame.init()
    pygame.joystick.init()

    # Creamos una ventana pequeña obligatoria para capturar el teclado
    pantalla = pygame.display.set_mode((400, 200))
    pygame.display.set_caption("Control del Tanque")

    control_conectado = False
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"[OK] Control detectado: {joystick.get_name()}")
        control_conectado = True
    else:
        print("[INFO] No se detectó mando. ¡MODO TECLADO ACTIVADO!")
        print("-> Haz clic en la ventana que se abrió para usar: W (Avanzar), S (Retroceder), A (Izquierda), D (Derecha)")

    print("\n--- TRANSMISIÓN INICIADA ---")

    try:
        while True:
            # Procesar eventos de Pygame (ventanas, teclas, etc.)
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    raise KeyboardInterrupt

            throttle = 0.0
            steering = 0.0

            # --- OPCIÓN A: CONTROL FÍSICO ---
            if control_conectado:
                throttle = -joystick.get_axis(1) 
                steering = joystick.get_axis(3) if joystick.get_numaxes() > 3 else joystick.get_axis(0)
            
            # --- OPCIÓN B: TECLADO (WASD) ---
            else:
                teclas = pygame.key.get_pressed()
                if teclas[pygame.K_w]:     # Adelante
                    throttle = 0.7
                elif teclas[pygame.K_s]:   # Atrás
                    throttle = -0.7
                
                if teclas[pygame.K_a]:     # Izquierda
                    steering = -0.5
                elif teclas[pygame.K_d]:   # Derecha
                    steering = 0.5

            # --- MATEMÁTICA DE CONVERSIÓN (Arcade Drive) ---
            izq_proporcional = throttle + steering
            der_proporcional = throttle - steering

            vel_izq = max(-255, min(255, int(izq_proporcional * 255)))
            vel_der = max(-255, min(255, int(der_proporcional * 255)))

            # --- ENVIAR AL ARDUINO ---
            comando = f"v,{vel_izq},{vel_der}\n"
            arduino.write(comando.encode('utf-8'))

            print(f"Modo: {'Mando' if control_conectado else 'Teclado'} | Enviado: v,{vel_izq},{vel_der}      ", end='\r')
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[INFO] Deteniendo robot...")
        arduino.write(b"v,0,0\n")
        arduino.close()
        pygame.quit()