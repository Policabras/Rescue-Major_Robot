#include "Motores.h"
#include "Pid.h"
#include "Encoders.h"

// --- VARIABLES GLOBALES ---

// Lo que los motores entregan físicamente (sirve también para el simulador de encoders)
int velocidadActualIzq = 0;
int velocidadActualDer = 0;

// Las RPM deseadas que pide la Raspberry Pi
float rpmDeseadasIzq = 0;
float rpmDeseadasDer = 0;

// Cronómetro para que el PID corra exactamente cada 20ms
unsigned long cronometroPID = 0;

// Objetos PID para cada lado del carro
ControladorPID pidIzq;
ControladorPID pidDer;


// --- FUNCIÓN INTERNA PARA ESCRIBIR EN LOS PINES ---
// Esta función aplica el PWM real a los puentes H y actualiza el simulador
void aplicarPwmFisico(int velIzq, int velDer) {
    velocidadActualIzq = velIzq; // Guardamos el valor actual para que el simulador lo lea
    velocidadActualDer = velDer;

    // LADO IZQUIERDO
    if (velIzq > 0) {
        analogWrite(RPWM_IZQ, velIzq);
        analogWrite(LPWM_IZQ, 0);
    } else if (velIzq < 0) {
        analogWrite(RPWM_IZQ, 0);
        analogWrite(LPWM_IZQ, abs(velIzq));
    } else {
        analogWrite(RPWM_IZQ, 0);
        analogWrite(LPWM_IZQ, 0);
    }

    // LADO DERECHO
    if (velDer > 0) {
        analogWrite(RPWM_DER, velDer);
        analogWrite(LPWM_DER, 0);
    } else if (velDer < 0) {
        analogWrite(RPWM_DER, 0);
        analogWrite(LPWM_DER, abs(velDer));
    } else {
        analogWrite(RPWM_DER, 0);
        analogWrite(LPWM_DER, 0);
    }
}


// --- FUNCIONES PÚBLICAS (Las que ven los otros archivos) ---

void inicializarMotores() {
    pinMode(RPWM_IZQ, OUTPUT);
    pinMode(LPWM_IZQ, OUTPUT);
    pinMode(RPWM_DER, OUTPUT);
    pinMode(LPWM_DER, OUTPUT);
    
    // Inicializamos los motores apagados
    aplicarPwmFisico(0, 0);
    
    // Sintonización del PID (Kp, Ki, Kd, Min PWM, Max PWM)
    inicializarPID(pidIzq, 1.5, 0.5, 0.1, -255.0, 255.0);
    inicializarPID(pidDer, 1.5, 0.5, 0.1, -255.0, 255.0);
    
    cronometroPID = millis();
}

// Ahora la Raspberry Pi define objetivos en RPM, no en PWM directo
void controlarMotores(int rpmIzquierda, int rpmDerecha) {
    rpmDeseadasIzq = rpmIzquierda;
    rpmDeseadasDer = rpmDerecha;
}

// Se ejecuta en el loop() constantemente protegiendo los motores con el PID
void actualizarMotores() {
    if (millis() - cronometroPID >= 20) { 
        cronometroPID = millis();

        // 1. Leer las RPM calculadas por el simulador de encoders
        float rpmRealIzq = obtenerRpmRealesIzq(); 
        float rpmRealDer = obtenerRpmRealesDer();

        // 2. El PID calcula cuánto PWM se necesita realmente
        int pwmCalculadoIzq = calcularPID(pidIzq, rpmDeseadasIzq, rpmRealIzq);
        int pwmCalculadoDer = calcularPID(pidDer, rpmDeseadasDer, rpmRealDer);

        // 3. Mandar la potencia calculada a los pines
        aplicarPwmFisico(pwmCalculadoIzq, pwmCalculadoDer);
    }
}

void giroPivotante(bool haciaDerecha, int velocidad) {
    if (haciaDerecha) {
        controlarMotores(velocidad, -velocidad); 
    } else {
        controlarMotores(-velocidad, velocidad);
    }
}

void giroCurvo(bool haciaDerecha, int velocidadBase, int reduccion) {
    if (haciaDerecha) {
        controlarMotores(velocidadBase, velocidadBase - reduccion);
    } else {
        controlarMotores(velocidadBase - reduccion, velocidadBase);
    }
}

// Estas dos funciones son vitales para que Encoders.cpp no falle:
int obtenerVelocidadIzq() { return velocidadActualIzq; }
int obtenerVelocidadDer() { return velocidadActualDer; }