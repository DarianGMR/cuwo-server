# Nombre del servidor global
server_name = 'CubeWorld CubanPlay'

# Numero máximo de jugadores en el servidor simultaneamente.
max_players = 4

# Semilla para el servidor
seed = 26879

# Modificador de velocidad de tiempo, 1.0 es el valor predeterminado
time_modifier = 1.0

# Lista de scripts que se ejecutaran en el servidor al iniciar.
# Considera activar los siguientes dos scripts: pvp y ctf.
scripts = ['log', 'ddos', 'commands', 'welcome', 'ban', 'console',
           'anticheat', 'pvp', 'web']

# Contraseñas utilizadas para la gestion de permisos. Las claves son contraseñas y los valores son:
# una lista de tipos de usuario asociados a esa contraseña. Actualmente, solo esta definido el tipo 'admin',
# pero los scripts pueden restringir su uso segun el tipo de usuario.
passwords = {
    'PASSWORDREPLACEME': ['admin']
}

# Utilizado por el script welcome.py. Envia un breve mensaje de bienvenida a los usuarios
# reemplazando %(server_name)s con el nombre del servidor definido en este archivo.
welcome = ["Bienvenido a %(server_name)s!",
           "(Server powered by DarianGMR)"]

# Registro de variables
log_name = './logs/log.txt'
rotate_daily = True
console_log_format = '%(message)s'
file_log_format = '[%(asctime)s] %(message)s'

# Depuracion mundial
world_debug_file = None
world_debug_info = False

# Archivo de perfil. Establazcalo en algo distinto de Ninguno para habilitarlo.
profile_file = None

# Numero maximo de conexiones por IP para evitar ataques DoS.
max_connections_per_ip = 2

# Tiempo de espera de conexion en segundos
connection_timeout = 10.0

# Interfaz de red a la que enlazar. Por defecto, se utilizan todas las interfaces IPv4.
network_interface = '0.0.0.0'

# Puerto del servidor. ¡No lo cambie a menos que tenga un cliente modificado!
port = 12345

# Tasa de envio del servidor. Cambie este valor a uno menor para servidores con mucho tráfico.
# El servidor predeterminado usa 50, pero 40 o 25 podrían ser valores mas adecuados.
network_fps = 50

# Frecuencia de actualizacion del mundo. Cambiala a un valor menor para reducir el uso de la CPU.
# El servidor predeterminado usa 50, pero se puede reducir ligeramente sin mucha diferencia.
update_fps = 50

# Frecuencia de actualizacion de la mision en segundos.
mission_update_rate = 5

# Distancia desde la que se muestran las misiones a los jugadores. Por defecto, se utiliza una region.
mission_max_distance = 0x10000 * 256 * 64

# Permite la generacion de terreno. Esto puede no ser necesario para servidores PvP basicos.
use_tgen = True

# Habilita los PNJ. Actualmente, solo funcionan los PNJ estaticos.
use_entities = True

# Numero de segundos antes de que se destruya un chunk cuando ningun jugador lo ha visitado durante un tiempo.
chunk_retire_time = 15.0

# Distancia a la que el servidor oculta a los PNJ y las criaturas a los jugadores.
# Reduce este valor para disminuir el trafico de red. Por defecto, es de 128 bloques.
max_distance = 0x10000 * 128

# Distancia a la que el servidor reduce la tasa de envio de PNJ y criaturas.
# Por defecto, 50 bloques.
max_reduce_distance = 0x10000 * 50
reduce_skip = 8 # sends only every 8th packet

# Directorio de guardado de datos para almacenar, por ejemplo, informacion sobre prohibiciones.
save_path = './save'