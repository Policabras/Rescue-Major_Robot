#include "Encoders.h"
#include "Motores.h"

long contadorFantasmaIzq = 0;
long contadorFantasmaDer = 0;
const int PPR = 4096; 

unsigned long tiempoAnteriorSim = 0;
unsigned long tiempoAnteriorCalc = 0;

long ultimoContadorIzq = 0;
long ultimoContadorDer = 0;

// ¡AGREGA ESTAS DOS VARIABLES GLOBALES!
float rpmRealIzq = 0.0;
float rpmRealDer = 0.0;

void inicializarEncoders() {
    tiempoAnteriorSim = millis();
    tiempoAnteriorCalc = millis();
}

void actualizarEncoders() {
    unsigned long tiempoActual = millis();
    
    if (tiempoActual - tiempoAnteriorSim >= 10) {
        tiempoAnteriorSim = tiempoActual;
        int velIzq = obtenerVelocidadIzq();
        int velDer = obtenerVelocidadDer();
        if (velIzq != 0) contadorFantasmaIzq += (velIzq / 15); 
        if (velDer != 0) contadorFantasmaDer += (velDer / 15); 
    }

    unsigned long tiempoTranscurrido = tiempoActual - tiempoAnteriorCalc;
    if (tiempoTranscurrido >= 200) {
        long pulsosNuevosIzq = contadorFantasmaIzq - ultimoContadorIzq;
        // Modificado: Ahora guardamos el resultado en las variables globales
        rpmRealIzq = ((pulsosNuevosIzq / (float)PPR) * 60000.0) / tiempoTranscurrido;

        long pulsosNuevosDer = contadorFantasmaDer - ultimoContadorDer;
        rpmRealDer = ((pulsosNuevosDer / (float)PPR) * 60000.0) / tiempoTranscurrido;

        // Telemetría para la Pi
        Serial.print("t,");
        Serial.print(contadorFantasmaIzq); Serial.print(",");
        Serial.print(contadorFantasmaDer); Serial.print(",");
        Serial.print(rpmRealIzq, 1);           Serial.print(",");
        Serial.print(rpmRealDer, 1);
        Serial.println();

        ultimoContadorIzq = contadorFantasmaIzq;
        ultimoContadorDer = contadorFantasmaDer;
        tiempoAnteriorCalc = tiempoActual;
    }
}

// ¡AGREGA ESTAS DOS FUNCIONES AL FINAL!
float obtenerRpmRealesIzq() { return rpmRealIzq; }
float obtenerRpmRealesDer() { return rpmRealDer; }