#include "Motores.h"
#include "Pid.h"
#include "Encoders.h"

// --- VARIABLES GLOBALES ---
int velocidadActualIzq = 0;
int velocidadActualDer = 0;

float rpmDeseadasIzq = 0;
float rpmDeseadasDer = 0;

unsigned long cronometroPID = 0;

ControladorPID pidIzq;
ControladorPID pidDer;

// --- APLICAR POTENCIA FÍSICA A LOS BTS7960 ---
void aplicarPwmFisico(int velIzq, int velDer) {
    velocidadActualIzq = velIzq; 
    velocidadActualDer = velDer;

    // LADO IZQUIERDO (GPIO 32 y 33)
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

    // LADO DERECHO (GPIO 12 y 13)
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

void inicializarMotores() {
    pinMode(RPWM_IZQ, OUTPUT);
    pinMode(LPWM_IZQ, OUTPUT);
    pinMode(RPWM_DER, OUTPUT);
    pinMode(LPWM_DER, OUTPUT);
    
    aplicarPwmFisico(0, 0);
    
    // Sintonización del PID (Kp, Ki, Kd, Min PWM, Max PWM)
    // Mientras sigas usando LEDs, estos valores pueden hacer oscilar la luz.
    inicializarPID(pidIzq, 1.5, 0.5, 0.1, -255.0, 255.0);
    inicializarPID(pidDer, 1.5, 0.5, 0.1, -255.0, 255.0);
    
    cronometroPID = millis();
}

void controlarMotores(int rpmIzquierda, int rpmDerecha) {
    rpmDeseadasIzq = rpmIzquierda;
    rpmDeseadasDer = rpmDerecha;
}

void actualizarMotores() {
    if (millis() - cronometroPID >= 20) { 
        cronometroPID = millis();

        // 1. Lee las RPM (del simulador de encoders por ahora)
        float rpmRealIzq = obtenerRpmRealesIzq(); 
        float rpmRealDer = obtenerRpmRealesDer();

        // 2. Cálculo de la señal PID
        int pwmCalculadoIzq = calcularPID(pidIzq, rpmDeseadasIzq, rpmRealIzq);
        int pwmCalculadoDer = calcularPID(pidDer, rpmDeseadasDer, rpmRealDer);

        // 3. Envío de señal a los pines actualizados
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

int obtenerVelocidadIzq() { return velocidadActualIzq; }
int obtenerVelocidadDer() { return velocidadActualDer; }