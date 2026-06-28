#include "Motores.h"
#include "Encoders.h"

void setup() {
    // Es vital que esta velocidad sea la misma que pusiste en server.py (115200)
    Serial.begin(115200); 
    
    // Inicializamos hardware y controladores PID
    inicializarMotores();
    inicializarEncoders();
}

void loop() {
    // 1. El simulador de encoders calcula las RPM reales y manda telemetría a Python
    actualizarEncoders();

    // 2. Escuchar si Python (desde la laptop) mandó un comando por USB
    if (Serial.available() > 0) {
        // Lee la línea completa hasta el salto de línea '\n'
        String comando = Serial.readStringUntil('\n');
        
        // Verificamos si el comando empieza con "v," (Comando de velocidad)
        if (comando.startsWith("v,")) {
            // Cortamos el "v," para quedarnos solo con los números sueltos (ej: "150,150")
            comando = comando.substring(2); 
            
            // Buscamos la coma que separa el motor izquierdo del derecho
            int posicionComa = comando.indexOf(',');
            if (posicionComa != -1) {
                // Separamos los dos textos
                String textoIzq = comando.substring(0, posicionComa);
                String textoDer = comando.substring(posicionComa + 1);
                
                // Convertimos el texto a números enteros (RPM deseadas)
                int rpmDeseadaIzq = textoIzq.toInt();
                int rpmDeseadaDer = textoDer.toInt();
                
                // Le asignamos el nuevo objetivo al PID
                controlarMotores(rpmDeseadaIzq, rpmDeseadaDer);
            }
        }
    }

    // 3. El PID calcula el PWM necesario cada 20ms y lo aplica a los pines físicos
    actualizarMotores();
}