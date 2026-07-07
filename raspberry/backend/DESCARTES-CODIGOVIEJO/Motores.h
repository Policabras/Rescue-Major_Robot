#ifndef MOTORES_H
#define MOTORES_H

#include <Arduino.h>

// --- NUEVA CONFIGURACIÓN DE PINES (Para Drivers BTS7960) ---
// Lado Izquierdo (Mismo pin controla ambos drivers de la izquierda)
const int RPWM_IZQ = 32;  // Adelante Izquierda
const int LPWM_IZQ = 33;  // Atrás Izquierda

// Lado Derecho (Mismo pin controla ambos drivers de la derecha)
// *Nota: Si la ESP32 no bootea al encender, mueve el 12 al pin 25 o 26.
const int RPWM_DER = 12;  // Adelante Derecha 
const int LPWM_DER = 13;  // Atrás Derecha

// Declaración de funciones
void inicializarMotores();
void controlarMotores(int velocidadIzquierda, int velocidadDerecha); 
void actualizarMotores(); 

void giroPivotante(bool haciaDerecha, int velocidad);
void giroCurvo(bool haciaDerecha, int velocidadBase, int reduccion);

int obtenerVelocidadIzq();
int obtenerVelocidadDer();

#endif