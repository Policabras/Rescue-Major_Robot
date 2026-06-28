#include "Encoders.h"
#include "Motores.h"

unsigned long ultimoTiempoEncoders = 0;
double rpmSimuladasIzq = 0.0;
double posicionAnguloIzq = 0.0;
double rpmSimuladasDer = 0.0;
double posicionAnguloDer = 0.0;

void inicializarEncoders() {
    ultimoTiempoEncoders = millis();
}

void actualizarEncoders() {
    unsigned long tiempoActual = millis();
    if (tiempoActual - ultimoTiempoEncoders >= 100) {
        ultimoTiempoEncoders = tiempoActual;

        // Lado Izquierdo
        int velFisicaIzq = obtenerVelocidadIzq();
        rpmSimuladasIzq = (velFisicaIzq / 255.0) * 150.0;
        posicionAnguloIzq += (rpmSimuladasIzq * 6.0) * 0.1;
        if (posicionAnguloIzq >= 360.0) posicionAnguloIzq -= 360.0;
        if (posicionAnguloIzq < 0.0) posicionAnguloIzq += 360.0;

        // Lado Derecho
        int velFisicaDer = obtenerVelocidadDer();
        rpmSimuladasDer = (velFisicaDer / 255.0) * 150.0;
        posicionAnguloDer += (rpmSimuladasDer * 6.0) * 0.1;
        if (posicionAnguloDer >= 360.0) posicionAnguloDer -= 360.0;
        if (posicionAnguloDer < 0.0) posicionAnguloDer += 360.0;

        // NOTA: Los prints automáticos fueron removidos para no bloquear el puerto serie.
    }
}
//q rancio