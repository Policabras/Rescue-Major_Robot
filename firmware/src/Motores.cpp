#include "Motores.h"

int velocidadObjetivoIzq = 0;
int velocidadObjetivoDer = 0;
int velocidadActualIzq = 0;
int velocidadActualDer = 0;

unsigned long ultimoCambioRampa = 0;
const int PASO_RAMPA = 8;          // Ajusta el suavizado aquí
const int TIEMPO_PASO_RAMPA = 10;  

void inicializarMotores() {
    pinMode(RPWM_IZQ, OUTPUT);
    pinMode(LPWM_IZQ, OUTPUT);
    pinMode(RPWM_DER, OUTPUT);
    pinMode(LPWM_DER, OUTPUT);
    controlarMotores(0, 0);
}

void controlarMotores(int velocidadIzquierda, int velocidadDerecha) {
    velocidadObjetivoIzq = velocidadIzquierda;
    velocidadObjetivoDer = velocidadDerecha;
}

void aplicarPwmFisico(int velIzq, int velDer) {
    // Lado Izquierdo
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

    // Lado Derecho
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

void actualizarRampas() {
    unsigned long tiempoActual = millis();

    if (tiempoActual - ultimoCambioRampa >= TIEMPO_PASO_RAMPA) {
        ultimoCambioRampa = tiempoActual;

        if (velocidadActualIzq < velocidadObjetivoIzq) {
            velocidadActualIzq += PASO_RAMPA;
            if (velocidadActualIzq > velocidadObjetivoIzq) velocidadActualIzq = velocidadObjetivoIzq;
        } else if (velocidadActualIzq > velocidadObjetivoIzq) {
            velocidadActualIzq -= PASO_RAMPA;
            if (velocidadActualIzq < velocidadObjetivoIzq) velocidadActualIzq = velocidadObjetivoIzq;
        }

        if (velocidadActualDer < velocidadObjetivoDer) {
            velocidadActualDer += PASO_RAMPA;
            if (velocidadActualDer > velocidadObjetivoDer) velocidadActualDer = velocidadObjetivoDer;
        } else if (velocidadActualDer > velocidadObjetivoDer) {
            velocidadActualDer -= PASO_RAMPA;
            if (velocidadActualDer < velocidadObjetivoDer) velocidadActualDer = velocidadObjetivoDer;
        }

        aplicarPwmFisico(velocidadActualIzq, velocidadActualDer);
    }
}

int obtenerVelocidadIzq() { return velocidadActualIzq; }
int obtenerVelocidadDer() { return velocidadActualDer; }
//q rancio