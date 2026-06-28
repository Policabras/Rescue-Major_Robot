#ifndef PID_H
#define PID_H

#include <Arduino.h>

struct ControladorPID {
    // Constantes de sintonización (Las que tú calibras)
    float kp;
    float ki;
    float kd;

    // Variables internas de control
    float errorAcumulado;
    float ultimoError;
    unsigned long tiempoAnterior;

    // Límites para proteger los motores
    float limiteMax;
    float limiteMin;
};

// Funciones para inicializar y calcular el PID
void inicializarPID(ControladorPID &pid, float p, float i, float d, float minVal, float maxVal);
int calcularPID(ControladorPID &pid, float valorDeseado, float valorReal);

#endif