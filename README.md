<div align="center">

# Universidad Politécnica Salesiana

# Carrera de Computación

# Asignatura de Sistemas Distribuidos

</div>

**Integrantes:** Burgos Andrés, Morales Pool, Narváez Cristian

**Fecha:** 30 de octubre de 2026

**Tema:** Taller de Sockets (Master y Worker)

**Objetivos**
- El objetivo es construir una infraestructura donde un Nodo Central (Master) gobierna y coordina a múltiples Nodos de Trabajo (Workers / Agentes) distribuidos en la red. El Master debe ser capaz de rastrear qué nodos están activos, enviarles comandos de forma concurrente y coordinar una tarea masiva sincronizada.
- Diseñar protocolos de comunicación basados en sockets TCP y UDP para arquitecturas Master-Worker.
- Implementar mecanismos de detección de vida (Heartbeats) mediante datagramas UDP.
- Gestionar servidores TCP multihilo capaces de despachar tareas y recibir telemetría de múltiples agentes simultáneamente.
- Orquestar la ejecución sincronizada de comandos distribuidos.

**Desarrollo de la actividad**

**Paso 1:** Se ejecuta el archivo "master.py".

<img width="1339" height="488" alt="image" src="https://github.com/user-attachments/assets/150eaa2e-89f9-467b-bc73-76ce1da623b0" />

<div align="center">

**Parte del "master.py"**

</div>

**Paso 2:** Ejecución de la opción de listado.

<img width="810" height="154" alt="image" src="https://github.com/user-attachments/assets/98d08a06-7e2f-4372-abd0-cf5fd23f76e2" />

**Paso 3:** Se envía una tarea específica a un worker con el comando exec Worker_01 scan_ports.

<img width="980" height="235" alt="image" src="https://github.com/user-attachments/assets/e7012527-dfc6-433a-a0c1-6f5e45f0454f" />

**Paso 4:** Se lanza una ráfaga sincronizada de carga con el broadcast de 127.0.0.1 10

<img width="696" height="112" alt="image" src="https://github.com/user-attachments/assets/a4605d86-d8a5-41b5-8d7e-5ce2bebe4840" />

<div align="center">

**Parte del "worker.py"**

</div>

**Paso 5:** Se ejecuta el worker 1.

<img width="1087" height="350" alt="image" src="https://github.com/user-attachments/assets/f513f772-2c7c-4415-82be-dabedbc5ab83" />

**Paso 6:** Se ejecuta el worker 2.

<img width="933" height="327" alt="image" src="https://github.com/user-attachments/assets/67fdc922-0181-446b-bbae-b6d11cae68f7" />

**Conclusiones**

- **CONCLUSIÓN 1**
- **CONCLUSIÓN 2**
