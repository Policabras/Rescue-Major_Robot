#include "Bridge.h"
#include "Motores.h" // Necesario para pasarle las velocidades recibidas

void inicializarComunicacion() {
    // La comunicación con la Pi será a alta velocidad
    Serial.begin(115200); 
}

void escucharRaspberryPi() {
    // Si la Raspberry Pi envió datos...
    if (Serial.available() > 0) {
        // Buscamos el inicio de nuestro comando (la letra 'v')
        char indicador = Serial.read();
        
        if (indicador == 'v') {
            // Saltamos la coma y leemos el primer número entero (Izq)
            int velIzq = Serial.parseInt();
            // Saltamos la siguiente coma y leemos el segundo entero (Der)
            int velDer = Serial.parseInt();
            
            // Le mandamos la orden a los motores y LEDs
            controlarMotores(velIzq, velDer);
            
            // Feedback para la Pi (o para ti en la consola)
            Serial.print("[Pi Bridge] Comando recibido -> Izq: ");
            Serial.print(velIzq);
            Serial.print(" | Der: ");
            Serial.println(velDer);
        }
    }
}