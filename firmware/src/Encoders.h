#ifndef ENCODERS_H
#define ENCODERS_H

#include <Arduino.h>

void inicializarEncoders();
void actualizarEncoders();

// ¡AGREGA ESTAS DOS LÍNEAS!
float obtenerRpmRealesIzq();
float obtenerRpmRealesDer();

#endif