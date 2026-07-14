#include "Pid.h"

void inicializarPID(ControladorPID &pid, float p, float i, float d, float minVal, float maxVal) {
    pid.kp = p;
    pid.ki = i;
    pid.kd = d;
    pid.limiteMin = minVal;
    pid.limiteMax = maxVal;
    pid.errorAcumulado = 0;
    pid.ultimoError = 0;
    pid.tiempoAnterior = millis();
}

int calcularPID(ControladorPID &pid, float valorDeseado, float valorReal) {
    unsigned long tiempoActual = millis();
    float dt = (tiempoActual - pid.tiempoAnterior) / 1000.0; // Tiempo en segundos
    
    // Si el tiempo transcurrido es cero, evitamos división por cero
    if (dt <= 0) return 0;
    pid.tiempoAnterior = tiempoActual;

    // 1. Calcular el Error (Proporcional)
    float error = valorDeseado - valorReal;

    // 2. Calcular la Integral (El pasado: acumula los errores en el tiempo)
    pid.errorAcumulado += error * dt;
    
    // Anti-windup: Evita que la integral crezca infinitamente si el robot se atraca
    pid.errorAcumulado = constrain(pid.errorAcumulado, pid.limiteMin, pid.limiteMax);

    // 3. Calcular la Derivada (El futuro: predice qué tan rápido cambia el error)
    float derivada = (error - pid.ultimoError) / dt;
    pid.ultimoError = error;

    // 4. Sumar los tres componentes
    float salida = (pid.kp * error) + (pid.ki * pid.errorAcumulado) + (pid.kd * derivada);

    // Restringir la salida al rango permitido del PWM (-255 a 255)
    return (int)constrain(salida, pid.limiteMin, pid.limiteMax);
}