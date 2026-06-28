#include "Bridge.h"
#include "Motores.h"

void inicializarComunicacion() {
    Serial.begin(115200); 
}

void escucharRaspberryPi() {
    if (Serial.available() > 0) {
        char indicador = Serial.read();
        
        if (indicador == 'v') {
            int velIzq = Serial.parseInt();
            int velDer = Serial.parseInt();
            
            // Enviamos el objetivo a los motores
            controlarMotores(velIzq, velDer);
            
            // Respondemos una Sola Vez para confirmar a la Pi y vaciar el canal
            Serial.print("ACK_OK:I=");
            Serial.print(velIzq);
            Serial.print("_D=");
            Serial.println(velDer);
        }
    }
}