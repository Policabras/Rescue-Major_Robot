#include "motores.h"

void inicializarMotores() {
    pinMode(EN_IZQ, OUTPUT);
    pinMode(RPWM_IZQ, OUTPUT);
    pinMode(LPWM_IZQ, OUTPUT);
    
    // Activamos el driver
    digitalWrite(EN_IZQ, HIGH);
}

void moverIzquierda(int velocidad) {
    // Si la velocidad es positiva, va hacia adelante
    if (velocidad > 0) {
        analogWrite(RPWM_IZQ, velocidad);
        analogWrite(LPWM_IZQ, 0);
    } 
    // Si es negativa, va hacia atrás (usamos abs() para quitar el signo menos)
    else if (velocidad < 0) {
        analogWrite(RPWM_IZQ, 0);
        analogWrite(LPWM_IZQ, abs(velocidad));
    } 
    // Si es cero, se detiene
    else {
        analogWrite(RPWM_IZQ, 0);
        analogWrite(LPWM_IZQ, 0);
    }
}