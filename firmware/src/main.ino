// --- CONFIGURACIÓN DE PINES NUEVOS (Drivers BTS7960) ---
const int RPWM_IZQ = 32;  // Adelante Izquierda
const int LPWM_IZQ = 33;  // Atrás Izquierda

// Si la ESP32 no bootea al encender, mueve el 12 al pin 25 o 26.
const int RPWM_DER = 12;  // Adelante Derecha
const int LPWM_DER = 13;  // Atrás Derecha

// ========================================================
// 🛠️ CONFIGURACIÓN DE LOS NUEVOS PINES SERIAL (TX/RX)
// Reemplaza estos números por los pines físicos que usó tu equipo:
const int PIN_RX = 22; 
const int PIN_TX = 23; 
// ========================================================

// Velocidades OBJETIVO e INTERNAS ACTUALES
int targetIzq = 0;
int targetDer = 0;
float currentIzq = 0.0;
float currentDer = 0.0;

// Configuración de la rampa de aceleración
unsigned long ultimoTiempoRampa = 0;
const unsigned long INTERVALO_RAMPA_MS = 5; 
const float PASO_ACELERACION = 1.5;         

void aplicarVoltajeDirecto(int izq, int der);

void setup() {
    // MODIFICADO: Ahora el Serial escucha por los pines de hardware asignados en lugar del USB por defecto
    Serial.begin(115200, SERIAL_8N1, PIN_RX, PIN_TX); 
    Serial.setTimeout(10); // Evita que la ESP32 se paralice esperando texto
    
    // Configuración de pines como salidas
    pinMode(RPWM_IZQ, OUTPUT);
    pinMode(LPWM_IZQ, OUTPUT);
    pinMode(RPWM_DER, OUTPUT);
    pinMode(LPWM_DER, OUTPUT);
    
    // Forzar apagado inicial
    aplicarVoltajeDirecto(0, 0);
    
    Serial.println("[*] ESP32 lista. Formato esperado: v{izq},{der}");
}

void loop() {
    // 1. LEER LOS DATOS DESDE EL PUERTO SERIAL (Raspberry Pi)
    if (Serial.available() > 0) {
        String comando = Serial.readStringUntil('\n');
        
        // Buscamos que empiece con 'v' (Formato: v150,-100)
        if (comando.startsWith("v")) {
            comando = comando.substring(1); // Quitamos la 'v'
            int posicionComa = comando.indexOf(',');
            
            if (posicionComa != -1) {
                targetIzq = comando.substring(0, posicionComa).toInt();
                targetDer = comando.substring(posicionComa + 1).toInt();
            }
        }
    }

    // 2. LA RAMPA DE SUAVIZADO ASÍNCRONA (Protege drivers y motores)
    if (millis() - ultimoTiempoRampa >= INTERVALO_RAMPA_MS) {
        ultimoTiempoRampa = millis();

        if (currentIzq < targetIzq) currentIzq = min((float)targetIzq, currentIzq + PASO_ACELERACION);
        else if (currentIzq > targetIzq) currentIzq = max((float)targetIzq, currentIzq - PASO_ACELERACION);

        if (currentDer < targetDer) currentDer = min((float)targetDer, currentDer + PASO_ACELERACION);
        else if (currentDer > targetDer) currentDer = max((float)targetDer, currentDer - PASO_ACELERACION);

        // Aplicamos el PWM final recalculado por la rampa
        aplicarVoltajeDirecto((int)currentIzq, (int)currentDer);
    }
}

// 3. CONTROL DE VOLTAJE DIRECTO OPTIMIZADO PARA BTS7960
void aplicarVoltajeDirecto(int izq, int der) {
    // --- MOTOR IZQUIERDO (Pines 32 y 33) ---
    if (izq > 0) {
        int pwm = map(izq, 0, 150, 0, 255);
        analogWrite(RPWM_IZQ, pwm);
        analogWrite(LPWM_IZQ, 0);
    } else if (izq < 0) {
        int pwm = map(abs(izq), 0, 150, 0, 255);
        analogWrite(RPWM_IZQ, 0);
        analogWrite(LPWM_IZQ, pwm);
    } else {
        analogWrite(RPWM_IZQ, 0);
        analogWrite(LPWM_IZQ, 0);
    }

    // --- MOTOR DERECHO (Pines 12 y 13) ---
    if (der > 0) {
        int pwm = map(der, 0, 150, 0, 255);
        analogWrite(RPWM_DER, pwm);
        analogWrite(LPWM_DER, 0);
    } else if (der < 0) {
        int pwm = map(abs(der), 0, 150, 0, 255);
        analogWrite(RPWM_DER, 0);
        analogWrite(LPWM_DER, pwm);
    } else {
        analogWrite(RPWM_DER, 0);
        analogWrite(LPWM_DER, 0);
    }
}