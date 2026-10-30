# ============================================================
# IMPORTACIÓN DE BIBLIOTECAS
# ============================================================

import socket       # Permite establecer comunicaciones de red UDP y TCP
import threading    # Permite ejecutar varias tareas concurrentemente
import time         # Permite controlar los intervalos de tiempo
import random       # Genera valores aleatorios para simular el uso de CPU
import sys          # Permite leer argumentos y finalizar el programa


# ============================================================
# CONFIGURACIÓN DE CONEXIÓN CON EL MASTER
# ============================================================

MASTER_IP = '127.0.0.1'  # Dirección IP del Master (localhost)
UDP_PORT = 5000          # Puerto UDP para enviar heartbeats
TCP_PORT = 5001          # Puerto TCP para recibir órdenes y enviar reportes


# ============================================================
# IDENTIFICACIÓN DEL WORKER
# ============================================================

# Comprobar si el usuario proporcionó el identificador del Worker
# como argumento al ejecutar el programa.
#
# Ejemplo:
# python worker.py worker1

if len(sys.argv) < 2:
    print("Uso: python worker.py <node_id>")
    sys.exit(1)  # Finalizar con código de error si falta el identificador

# Guardar el identificador del nodo recibido desde la terminal.
# Este ID permite al Master distinguir este Worker de los demás.
NODE_ID = sys.argv[1]


# ============================================================
# 1. ENVÍO PERIÓDICO DE HEARTBEATS MEDIANTE UDP
# ============================================================

def send_heartbeats():
    """
    Envía un mensaje UDP al Master cada dos segundos.
    El mensaje incluye el ID del Worker, un valor de CPU simulado
    y el estado actual informado por este programa.
    """

    # Crear un socket UDP utilizando IPv4.
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Mantener el envío de latidos mientras el programa esté activo.
    while True:
        try:

            # Simular el porcentaje de uso de CPU con un valor aleatorio
            # entre 10 y 90. No mide la CPU real del sistema.
            cpu_usage = random.randint(10, 90)

            # Construir el mensaje que recibirá el Master.
            # Formato: PING:<NODE_ID> <CPU> ONLINE
            #
            # Ejemplo:
            # PING:worker1 45 ONLINE
            message = f"PING:{NODE_ID} {cpu_usage} ONLINE"

            # Codificar el mensaje en UTF-8 y enviarlo al Master
            # mediante UDP al puerto configurado.
            udp_socket.sendto(
                message.encode('utf-8'),
                (MASTER_IP, UDP_PORT)
            )

        except Exception as e:
            # Mostrar el error si no se puede enviar el heartbeat.
            print(f"[!] Error enviando latido UDP: {e}")

        # Esperar dos segundos antes de enviar el siguiente latido.
        time.sleep(2)


# ============================================================
# 2. GENERACIÓN DE TRÁFICO DE PRUEBA
# ============================================================

def execute_stress_burst(target_ip, duration):
    """
    La función original genera repetidamente datagramas UDP
    dirigidos a la IP indicada, utilizando el puerto 80.

    IMPORTANTE:
    Una gran cantidad de paquetes puede saturar un sistema o una red.
    Para realizar pruebas, es preferible utilizar un servidor de
    laboratorio propio y limitar la tasa de envío.
    """

    print(
        f"\n[ESTRÉS] Iniciando prueba hacia {target_ip} "
        f"durante {duration} segundos..."
    )

    # Calcular el instante en que debería finalizar la prueba.
    end_time = time.time() + int(duration)

    # Contador de datagramas enviados correctamente por sendto().
    requests_sent = 0

    # Enviar tráfico hasta alcanzar el tiempo de finalización.
    while time.time() < end_time:
        try:

            # Crear un socket UDP.
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # En el código original se enviaba un datagrama al puerto 80.
            # No se comprueba si existe un servicio escuchando en ese puerto
            # ni si el destinatario recibe o procesa el paquete.
            #
            # Para evitar generar tráfico ilimitado contra un destino,
            # esta versión comentada no realiza el envío de paquetes.

            # s.sendto(b"STRESS_PACKET", (target_ip, 80))

            # Cerrar el socket después de su utilización.
            s.close()

            # En una prueba real, este contador debería incrementarse
            # únicamente después de una operación de envío controlada.
            #
            # requests_sent += 1

            # Evitar un bucle que consuma CPU continuamente.
            time.sleep(0.01)

        except Exception as e:
            # Registrar errores de la prueba.
            print(f"[!] Error durante la prueba: {e}")

    # Mostrar el resumen de la ejecución.
    print(
        f"[ESTRÉS] Prueba finalizada. "
        f"Paquetes/Peticiones contabilizadas: {requests_sent}"
    )

    # Devolver el total contabilizado.
    return requests_sent


# ============================================================
# 3. EJECUCIÓN DE TAREAS EN SEGUNDO PLANO
# ============================================================

def handle_task_background(task_name, tcp_conn):
    """
    Simula el procesamiento de una tarea solicitada por el Master.
    Se ejecuta en un hilo independiente para no bloquear la recepción
    de otros mensajes por la conexión TCP.
    """

    # Mostrar el nombre de la tarea que se está procesando.
    print(f"[TRABAJO] Ejecutando tarea en segundo plano: {task_name}")

    # Simular una operación que tarda dos segundos.
    time.sleep(2)

    # Crear un mensaje con el resultado simulado.
    result = (
        f"RESULT:{task_name} -> "
        "Completado exitosamente con métricas simuladas."
    )

    try:
        # Enviar el resultado al Master mediante la conexión TCP.
        # El salto de línea ayuda a separar mensajes de texto.
        tcp_conn.sendall(result.encode('utf-8') + b"\n")

    except Exception as e:
        # Mostrar el error si el resultado no puede enviarse.
        print(f"[!] Error enviando resultado al Master: {e}")


# ============================================================
# 4. CONEXIÓN TCP PERSISTENTE CON EL MASTER
# ============================================================

def worker_tcp_client():
    """
    Intenta conectarse al servidor TCP del Master.
    Una vez conectado, se registra y espera órdenes.
    Si la conexión se pierde, intenta reconectarse.
    """

    # Bucle externo para permitir reconexiones.
    while True:
        try:

            # Informar que se está intentando establecer la conexión.
            print(
                f"[*] Intentando conectar por TCP al Master "
                f"en {MASTER_IP}:{TCP_PORT}..."
            )

            # Crear un socket TCP basado en IPv4.
            tcp_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            # Conectarse al servidor TCP del Master.
            tcp_socket.connect((MASTER_IP, TCP_PORT))

            # ----------------------------------------------------
            # REGISTRO DEL WORKER
            # ----------------------------------------------------

            # Enviar el identificador del nodo al Master.
            # Formato: REGISTER:<NODE_ID>
            tcp_socket.sendall(
                f"REGISTER:{NODE_ID}\n".encode('utf-8')
            )

            # ----------------------------------------------------
            # RECEPCIÓN DE MENSAJES TCP
            # ----------------------------------------------------

            # Esperar mensajes mientras la conexión permanezca abierta.
            while True:

                # Recibir hasta 1024 bytes del Master.
                data = tcp_socket.recv(1024)

                # Si no llegan datos, el Master cerró la conexión.
                if not data:
                    break

                # Convertir los datos recibidos a texto.
                message = data.decode('utf-8').strip()

                # Mostrar el mensaje recibido.
                print(f"[TCP RECIBIDO]: {message}")

                # ------------------------------------------------
                # ORDEN: EXEC_TASK
                # ------------------------------------------------

                # Detectar si el Master ha enviado una orden de tarea.
                # Formato esperado: EXEC_TASK:<nombre_tarea>
                if message.startswith("EXEC_TASK:"):

                    # Extraer el nombre de la tarea.
                    # Esta separación solo conserva el primer segmento
                    # posterior a los dos puntos.
                    task = message.split(":")[1]

                    # Crear un hilo para procesar la tarea sin bloquear
                    # la recepción de nuevos mensajes TCP.
                    threading.Thread(
                        target=handle_task_background,
                        args=(task, tcp_socket),
                        daemon=True
                    ).start()

                # ------------------------------------------------
                # ORDEN: BROADCAST_STRESS
                # ------------------------------------------------

                # Detectar una orden de prueba de tráfico.
                # Formato esperado:
                # BROADCAST_STRESS:<IP>:<DURACIÓN>
                elif message.startswith("BROADCAST_STRESS:"):

                    # Separar los campos de la orden.
                    parts = message.split(":")

                    # Obtener la dirección IP de destino.
                    target_ip = parts[1]

                    # Obtener la duración indicada.
                    duration = parts[2]

                    # Definir una función auxiliar que ejecuta la
                    # prueba y devuelve un reporte al Master.
                    def run_and_report():

                        # Ejecutar la rutina de prueba.
                        reqs = execute_stress_burst(
                            target_ip,
                            duration
                        )

                        # Preparar un reporte con el resultado.
                        report = (
                            f"REPORT: Stress hacia {target_ip} "
                            f"completado. Total peticiones: {reqs}"
                        )

                        try:
                            # Enviar el reporte al Master.
                            tcp_socket.sendall(
                                report.encode('utf-8') + b"\n"
                            )

                        except Exception as e:
                            # Registrar errores de envío.
                            print(
                                f"[!] Error enviando reporte: {e}"
                            )

                    # Ejecutar la función auxiliar en otro hilo.
                    threading.Thread(
                        target=run_and_report,
                        daemon=True
                    ).start()

        except socket.error:
            # Informar si no se puede establecer o mantener
            # la conexión con el Master.
            print(
                "[!] Conexión TCP perdida o no disponible. "
                "Reintentando en 3 segundos..."
            )

            # Esperar antes de volver a intentarlo.
            time.sleep(3)

        except Exception as e:
            # Capturar otros errores inesperados.
            print(f"[!] Excepción TCP: {e}")

            # Esperar antes de repetir el intento.
            time.sleep(3)

        finally:
            # Intentar cerrar el socket al salir del bloque try.
            # close() libera el recurso local de red.
            try:
                tcp_socket.close()
            except (NameError, OSError):
                # Puede que el socket no se haya creado o ya esté cerrado.
                pass


# ============================================================
# 5. PUNTO DE ENTRADA DEL PROGRAMA
# ============================================================

# Ejecutar este bloque solo cuando el archivo se inicia directamente.
if __name__ == "__main__":

    # Iniciar un hilo para enviar heartbeats UDP cada dos segundos.
    # daemon=True permite que el hilo termine cuando finalice el proceso.
    threading.Thread(
        target=send_heartbeats,
        daemon=True
    ).start()

    # Ejecutar el cliente TCP en el hilo principal.
    # Esta función mantiene la conexión y procesa las órdenes del Master.
    worker_tcp_client()
