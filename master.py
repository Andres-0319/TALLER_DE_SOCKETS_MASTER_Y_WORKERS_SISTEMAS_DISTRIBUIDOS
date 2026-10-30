# Importar las bibliotecas necesarias
import socket       # Permite la comunicación de red mediante UDP y TCP
import threading    # Permite ejecutar varias tareas al mismo tiempo
import time         # Permite medir el tiempo y realizar pausas
import sys          # Permite finalizar el programa mediante sys.exit()

# ============================================================
# CONFIGURACIÓN DE RED DEL MASTER
# ============================================================

HOST = '0.0.0.0'  # Escucha conexiones en todas las interfaces de red
UDP_PORT = 5000   # Puerto utilizado para recibir los latidos UDP
TCP_PORT = 5001   # Puerto utilizado para las conexiones TCP


# ============================================================
# ESTRUCTURA GLOBAL PARA ALMACENAR LOS WORKERS ACTIVOS
# ============================================================

# Diccionario que almacena la información de cada Worker.
# La clave es el identificador del nodo (node_id).
#
# Cada Worker contiene:
#   ip        -> Dirección IP del Worker.
#   cpu       -> Porcentaje de uso de CPU informado.
#   status    -> Estado del Worker.
#   last_seen -> Marca de tiempo del último latido recibido.
#   tcp_conn  -> Socket de la conexión TCP persistente.
#
# Ejemplo:
# active_workers = {
#     "worker1": {
#         "ip": "192.168.1.10",
#         "cpu": "25",
#         "status": "ACTIVE",
#         "last_seen": 1234567890.0,
#         "tcp_conn": objeto_socket
#     }
# }

active_workers = {}

# Bloqueo para evitar que varios hilos modifiquen o lean
# simultáneamente el diccionario mientras se actualiza.
workers_lock = threading.Lock()


# ============================================================
# 1. ESCUCHA DE LATIDOS UDP (HEARTBEATS)
# ============================================================

def udp_heartbeat_listener():
    """
    Escucha los mensajes UDP enviados periódicamente por los Workers.
    Actualiza la información de cada nodo y responde con un ACK.
    """

    # Crear un socket UDP usando IPv4.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Asociar el socket a todas las interfaces y al puerto UDP indicado.
    server_socket.bind((HOST, UDP_PORT))

    print(f"[*] Servidor UDP de Latidos activo en el puerto {UDP_PORT}")

    # Mantener el servidor escuchando continuamente.
    while True:
        try:
            # Esperar un datagrama de hasta 1024 bytes.
            # addr contiene la IP y el puerto de origen del Worker.
            data, addr = server_socket.recvfrom(1024)

            # Convertir los bytes recibidos en una cadena de texto.
            message = data.decode('utf-8')

            # Formato esperado:
            # PING:<node_id> <cpu_usage> <status>
            #
            # Ejemplo:
            # PING:worker1 25 ACTIVE

            if message.startswith("PING:"):

                # Eliminar el prefijo PING: y separar los datos.
                # split(' ', 2) limita la separación a dos espacios,
                # permitiendo que status contenga espacios.
                parts = message[5:].strip().split(' ', 2)

                # Comprobar si se recibieron los tres campos esperados.
                if len(parts) >= 3:
                    node_id, cpu_usage, status = (
                        parts[0], parts[1], parts[2]
                    )
                else:
                    # Valores predeterminados si faltan datos.
                    node_id = parts[0]
                    cpu_usage = "N/A"
                    status = "UNKNOWN"

                # Bloquear el diccionario durante la actualización.
                with workers_lock:

                    # Registrar o actualizar los datos del Worker.
                    active_workers[node_id] = {
                        'ip': addr[0],  # IP de origen del mensaje UDP
                        'cpu': cpu_usage,
                        'status': status,

                        # Guardar el instante del último latido recibido.
                        'last_seen': time.time(),

                        # Conservar la conexión TCP existente si la hay.
                        # Esto evita perderla al actualizar el heartbeat.
                        'tcp_conn': active_workers.get(
                            node_id, {}
                        ).get('tcp_conn', None)
                    }

                # Responder al Worker para confirmar la recepción.
                server_socket.sendto(b"ACK", addr)

        except Exception as e:
            # Mostrar errores sin detener el bucle de escucha.
            print(f"[!] Error en UDP listener: {e}")


# ============================================================
# 2. DETECCIÓN DE WORKERS DESCONECTADOS
# ============================================================

def monitor_dead_workers():
    """
    Comprueba periódicamente si los Workers siguen enviando latidos.
    Si pasan más de 6 segundos sin recibir uno, los declara desconectados.
    """

    while True:

        # Esperar dos segundos antes de realizar otra comprobación.
        time.sleep(2)

        # Obtener el tiempo actual.
        current_time = time.time()

        # Bloquear la tabla global mientras se comprueban los Workers.
        with workers_lock:

            # Lista temporal de nodos que deben eliminarse.
            # Se utiliza para no modificar el diccionario mientras
            # se está recorriendo.
            to_remove = []

            # Revisar cada Worker registrado.
            for node_id, info in active_workers.items():

                # Si han pasado más de 6 segundos desde el último
                # heartbeat, considerar que el Worker está desconectado.
                if current_time - info['last_seen'] > 6:

                    print(
                        f"\n[ALERTA] Worker '{node_id}' "
                        f"({info['ip']}) declarado CAÍDO / "
                        "DESCONECTADO (Sin latidos)."
                    )

                    # Marcar el nodo para eliminarlo después.
                    to_remove.append(node_id)

            # Eliminar los nodos que se han declarado desconectados.
            for node_id in to_remove:

                # Si el Worker tiene una conexión TCP registrada,
                # intentar cerrarla.
                if active_workers[node_id]['tcp_conn']:
                    try:
                        active_workers[node_id]['tcp_conn'].close()
                    except Exception:
                        # Ignorar errores al cerrar el socket.
                        pass

                # Eliminar el Worker de la tabla global.
                del active_workers[node_id]


# ============================================================
# 3. GESTIÓN DE CLIENTES TCP
# ============================================================

def handle_tcp_client(client_socket, addr):
    """
    Gestiona la conexión TCP persistente de un Worker.
    Permite registrar el nodo y recibir sus reportes.
    """

    # Todavía no se conoce el identificador del Worker.
    current_node_id = None

    try:

        # Mantener la conexión abierta mientras el cliente siga conectado.
        while True:

            # Esperar datos enviados por el Worker.
            data = client_socket.recv(1024)

            # Si recv devuelve vacío, el cliente cerró la conexión.
            if not data:
                break

            # Convertir los bytes recibidos en texto y quitar
            # los espacios o saltos de línea de los extremos.
            message = data.decode('utf-8').strip()

            # ----------------------------------------------------
            # REGISTRO INICIAL DEL WORKER
            # ----------------------------------------------------
            # Formato esperado:
            # REGISTER:<node_id>
            #
            # Ejemplo:
            # REGISTER:worker1

            if message.startswith("REGISTER:"):

                # Obtener el identificador del nodo.
                current_node_id = message.split(":")[1]

                # Actualizar la tabla global de Workers.
                with workers_lock:

                    # Solo asociar el socket si el Worker ya existe
                    # en la tabla creada mediante los heartbeats UDP.
                    if current_node_id in active_workers:
                        active_workers[current_node_id]['tcp_conn'] = (
                            client_socket
                        )

                print(
                    f"\n[TCP] Sesión persistente establecida con "
                    f"Worker: {current_node_id} desde {addr}"
                )

                # Confirmar el registro al Worker.
                client_socket.sendall(b"REGISTRATION_OK\n")

            else:
                # Si el mensaje no es de registro, tratarlo como
                # un reporte enviado por el Worker.
                print(
                    f"\n[TCP Reporte de {current_node_id}]: {message}"
                )

    except Exception:
        # El código original ignora los errores de la conexión.
        pass

    finally:

        # Si se conoce el nodo, limpiar su referencia TCP.
        if current_node_id:
            with workers_lock:

                # Comprobar que el Worker siga en la tabla.
                if current_node_id in active_workers:
                    active_workers[current_node_id]['tcp_conn'] = None

        # Cerrar el socket al terminar la sesión.
        client_socket.close()


# ============================================================
# 4. SERVIDOR TCP MULTIHILO
# ============================================================

def tcp_server_listener():
    """
    Abre el servidor TCP y crea un hilo independiente
    para gestionar cada conexión entrante.
    """

    # Crear un socket TCP sobre IPv4.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Permitir reutilizar el puerto después de reiniciar el servidor,
    # cuando las condiciones del sistema operativo lo permitan.
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Asociar el socket al host y al puerto TCP configurados.
    server.bind((HOST, TCP_PORT))

    # Comenzar a escuchar conexiones.
    # El valor 5 indica el tamaño solicitado para la cola de conexiones.
    server.listen(5)

    print(f"[*] Servidor TCP Multihilo activo en el puerto {TCP_PORT}")

    # Aceptar conexiones de forma continua.
    while True:

        # Esperar una nueva conexión de un Worker.
        client_sock, addr = server.accept()

        # Crear un hilo para gestionar al cliente sin bloquear
        # la aceptación de nuevas conexiones.
        threading.Thread(
            target=handle_tcp_client,
            args=(client_sock, addr),
            daemon=True
        ).start()


# ============================================================
# 5. INTERFAZ DE LÍNEA DE COMANDOS (CLI) DEL MASTER
# ============================================================

def master_cli():
    """
    Permite al operador consultar Workers y enviar órdenes
    mediante la conexión TCP.
    """

    print("\n--- CLI Master Iniciada ---")
    print("Comandos disponibles:")
    print("  1. list                         - Lista los workers activos")
    print("  2. exec <node_id> <comando>     - Envía un comando a un Worker")
    print("  3. broadcast <ip> <duration>    - Envía una orden a los Workers")
    print("  4. exit                         - Cierra el Master\n")

    # Mantener la interfaz disponible hasta recibir el comando exit.
    while True:
        try:

            # Leer la orden escrita por el operador.
            cmd_input = input("Master> ").strip()

            # Ignorar entradas vacías.
            if not cmd_input:
                continue

            # Separar la entrada por espacios.
            parts = cmd_input.split(' ')

            # Convertir la acción a minúsculas.
            action = parts[0].lower()

            # ----------------------------------------------------
            # COMANDO: list
            # ----------------------------------------------------
            # Muestra todos los Workers registrados y su información.

            if action == 'list':

                # Bloquear el diccionario durante la lectura.
                with workers_lock:

                    print("\n--- TABLA GLOBAL DE WORKERS ---")

                    if not active_workers:
                        print("No hay workers activos.")

                    # Recorrer e imprimir los datos de cada Worker.
                    for nid, info in active_workers.items():
                        print(
                            f"ID: {nid} | "
                            f"IP: {info['ip']} | "
                            f"CPU: {info['cpu']}% | "
                            f"Status: {info['status']} | "
                            f"TCP: {'Conectado' if info['tcp_conn'] else 'Desconectado'}"
                        )

                    print("-------------------------------\n")

            # ----------------------------------------------------
            # COMANDO: exec <node_id> <comando>
            # ----------------------------------------------------
            # Envía un mensaje a un Worker específico.
            #
            # Ejemplo:
            # exec worker1 status

            elif action == 'exec' and len(parts) >= 3:

                # Identificador del Worker de destino.
                target_node = parts[1]

                # Comando que se desea enviar.
                # En esta versión solo se toma parts[2].
                command_to_send = parts[2]

                # Buscar el Worker y comprobar su conexión TCP.
                with workers_lock:
                    worker_info = active_workers.get(target_node)

                    if worker_info and worker_info['tcp_conn']:

                        # Obtener el socket de la conexión TCP.
                        conn = worker_info['tcp_conn']

                        # Enviar el comando con el prefijo EXEC_TASK.
                        conn.sendall(
                            f"EXEC_TASK:{command_to_send}\n".encode('utf-8')
                        )

                        print(
                            f"[>] Comando '{command_to_send}' "
                            f"enviado a {target_node}"
                        )

                    else:
                        print(
                            f"[!] Worker '{target_node}' no encontrado "
                            "o sin sesión TCP activa."
                        )

            # ----------------------------------------------------
            # COMANDO: broadcast <ip> <duration>
            # ----------------------------------------------------
            # Envía una orden a todos los Workers que tengan
            # una conexión TCP activa.
            #
            # IMPORTANTE:
            # BROADCAST_STRESS puede representar una orden de
            # generación de tráfico o carga. Debe limitarse a
            # pruebas autorizadas y entornos controlados.

            elif action == 'broadcast' and len(parts) >= 3:

                # Dirección IP que se incluirá en la orden.
                target_ip = parts[1]

                # Duración indicada por el operador.
                duration = parts[2]

                # Construir el mensaje que recibirán los Workers.
                payload = (
                    f"BROADCAST_STRESS:{target_ip}:{duration}\n"
                )

                # Recorrer los Workers bajo el bloqueo.
                with workers_lock:

                    count = 0

                    for nid, info in active_workers.items():

                        # Enviar solo a los Workers conectados por TCP.
                        if info['tcp_conn']:

                            info['tcp_conn'].sendall(
                                payload.encode('utf-8')
                            )

                            # Contabilizar la orden enviada.
                            count += 1

                    print(
                        f"[>] Orden de ráfaga sincronizada enviada "
                        f"a {count} workers activos."
                    )

            # ----------------------------------------------------
            # COMANDO: exit
            # ----------------------------------------------------
            # Termina el proceso del Master.

            elif action == 'exit':
                print("Saliendo del Master...")
                sys.exit(0)

            # ----------------------------------------------------
            # COMANDO NO VÁLIDO
            # ----------------------------------------------------

            else:
                print("[!] Comando inválido o incompleto.")

        except Exception as e:
            # Mostrar errores producidos al procesar las órdenes.
            print(f"[!] Error en CLI: {e}")


# ============================================================
# 6. PUNTO DE ENTRADA DEL PROGRAMA
# ============================================================

# Esta condición se cumple cuando el archivo se ejecuta directamente,
# pero no cuando se importa como módulo desde otro archivo.
if __name__ == "__main__":

    # Iniciar el hilo encargado de recibir heartbeats UDP.
    # daemon=True permite que el hilo no impida finalizar el proceso.
    threading.Thread(
        target=udp_heartbeat_listener,
        daemon=True
    ).start()

    # Iniciar el hilo que detecta Workers desconectados.
    threading.Thread(
        target=monitor_dead_workers,
        daemon=True
    ).start()

    # Iniciar el servidor TCP que recibe conexiones de los Workers.
    threading.Thread(
        target=tcp_server_listener,
        daemon=True
    ).start()

    # Ejecutar la interfaz de comandos en el hilo principal.
    # Este hilo espera las órdenes introducidas por el operador.
    master_cli()
