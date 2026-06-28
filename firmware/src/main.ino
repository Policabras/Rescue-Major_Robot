#include "Motores.h"
#include "Encoders.h"
#include "Bridge.h"

void setup() {
    inicializarComunicacion(); // Inicializa el puerto Serial a 115200
    inicializarMotores();
    inicializarEncoders();
}

void loop() {
    // 1. Escucha las órdenes de la Raspberry Pi
    escucharRaspberryPi();

    // 2. Procesa la rampa de aceleración/frenado suave
    actualizarRampas();

    // 3. El simulador calcula la telemetría en silencio
    actualizarEncoders();
}