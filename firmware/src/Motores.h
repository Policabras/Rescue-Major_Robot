#ifndef MOTORES_H
#define MOTORES_H

#include <Arduino.h>

// Configuración de Pines para los 4 LEDs/Motores
const int RPWM_IZQ = 5;  // LED Izquierda Adelante
const int LPWM_IZQ = 6;  // LED Izquierda Atrás
const int RPWM_DER = 9;  // LED Derecha Adelante
const int LPWM_DER = 10; // LED Derecha Atrás

// Declaración de funciones
void inicializarMotores();
void controlarMotores(int velocidadIzquierda, int velocidadDerecha); // Ahora define el "objetivo"
void actualizarMotores(); // <-- ¡NUEVA! Maneja la rampa en segundo plano

void giroPivotante(bool haciaDerecha, int velocidad);
void giroCurvo(bool haciaDerecha, int velocidadBase, int reduccion);

int obtenerVelocidadIzq();
int obtenerVelocidadDer();

#endif