# Nivel de registro: 2 = Detallado, 1 = Predeterminado, 0 = Ninguno
log_level = 2

# Nivel de registro en IRC (mismo sistema que arriba)
irc_log_level = 2

# Filtro de nombres mediante expresiones regulares
# Cualquier nombre que no coincida sera rechazado
name_filter = "^[a-zA-Z0-9_!@#$%\^&*()\[\]|:;'.,/\-+ <>\\\"{}~`=?]{2,16}$"

# Permitir empuñadura dual (un arma a dos manos + una a una mano)
# Por defecto: False (deshabilitado)
allow_dual_wield = False

# Nivel maximo permitido en el servidor
# Jugadores que suban por encima seran baneados
level_cap = 1000

# Rareza maxima permitida (4 = oro)
# Raridades superiores seran detectadas como ilegal
rarity_cap = 4

# Contador de tolerancia para planeo/ataque rapido
# Evita expulsar jugadores con lag al cambiar
glider_abuse_count = 5

# Margen de tiempo para enfriamiento de habilidades (en segundos)
# Menor = mas preciso pero mas falsos positivos con lag
cooldown_margin = 0.5

# Cantidad maxima de violaciones de enfriamiento permitidas
max_cooldown_strikes = 3

# Distancia maxima de golpe permitida (en unidades)
# Se eleva al cuadrado internamente
max_hit_distance = 2000000

# Cantidad de violaciones de distancia permitidas
max_hit_distance_strikes = 5

# Tiempo maximo en el aire antes de ser detectado volando (segundos)
max_air_time = 10

# Margen de velocidad permitido (no implementado)
speed_margin = 1

# Margen de tiempo para ultimo golpe (segundos)
# Permite diferencias de tiempo del cliente
last_hit_margin = 3.0

# Recuperaciones permitidas de ultimo golpe (cada 15 segundos)
max_last_hit_time_catchup = 3

# Violaciones maximas de ultimo golpe permitidas
max_last_hit_strikes = 3

# Violaciones maximas de contador de golpes
max_hit_counter_strikes = 3

# Diferencia maxima entre contador estimado y real
max_hit_counter_difference = 4

# Violaciones maximas de vida maxima permitidas
max_max_hp_strikes = 4

# Daño maximo permitido por golpe (en daño)
max_damage = 10000

# Mensaje de registro cuando se banea a un jugador
log_message = "{playername}({ip}) fue baneado (Razon: {reason})."

# Mensaje desconexion al ser baneado
disconnect_message = "{name} has sido baneado (Razon: {reason})."
