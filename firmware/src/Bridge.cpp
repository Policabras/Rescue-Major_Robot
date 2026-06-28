#include "Bridge.h"
#include "Motores.h"

void inicializarComunicacion() {
    Serial.begin(115200); 
    Serial.setTimeout(10); // Si algo sale mal, no te quedes trabado más de 10ms
}

void escucharRaspberryPi() {
    if (Serial.available() > 0) {
        // Lee toda la cadena de golpe hasta el salto de línea y limpia el búfer
        String cadena = Serial.readStringUntil('\n');
        cadena.trim(); 

        // Validamos que empiece con 'v' y tenga estructura adecuada
        if (cadena.length() > 0 && cadena.charAt(0) == 'v') {
            int primeraComa = cadena.indexOf(',');
            int segundaComa = cadena.indexOf(',', primeraComa + 1);
            
            // Si encontramos las dos comas divisorias: "v,izq,der"
            if (primeraComa != -1 && segundaComa != -1) {
                String strIzq = cadena.substring(primeraComa + 1, segundaComa);
                String strDer = cadena.substring(segundaComa + 1);
                
                int velIzq = strIzq.toInt();
                int velDer = strDer.toInt();
                
                // Aplicar velocidad a los motores
                controlarMotores(velIzq, velDer);
                
                // RESPUESTA OBLIGATORIA: Le avisamos a Python que ya terminamos
                Serial.print("ACK:I=");
                Serial.print(velIzq);
                Serial.print("_D=");
                Serial.println(velDer);
            }
        }
    }
}
//q rancio