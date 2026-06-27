#include "Motores.h"
#include "Encoders.h"
#include "Bridge.h"

void setup() {
    inicializarComunicacion(); // Inicializa el Serial a 115200
    inicializarMotores();
    inicializarEncoders();
    Serial.println("--- SCRIPT DE TELEMETRÍA Y CONTROL SERIAL ACTIVO ---");
    Serial.println("Envía comandos con el formato: v,izq,der (Ejemplo: v,150,150)");
}

void loop() {
    // 1. Simulador de encoders corre en segundo plano todo el tiempo
    actualizarEncoders();

    // 2. Escucha si la Raspberry Pi (o tú) mandó una orden de movimiento
    escucharRaspberryPi();
}