# Nivel de registro 2 = Detallado, 1 = Predeterminado o 0 = Ninguno
log_level = 2

# Iniciando sesion en irc, los mismos niveles que arriba
irc_log_level = 2

# Filtro de nombres mediante expresiones regulares; cualquier elemento que no coincida con este filtro sera eliminado.
# Actualmente, se aplican a todas las teclas de un teclado. Cubeworld no es muy exigente.
name_filter = "^[a-zA-Z0-9_!@#$%\^&*()\[\]|:;'.,/\-+ <>\\\"{}~`=?]{2,16}$"

# Si permitimos el error de doble empuñadura (equipar un arma a 2 manos y una a 1 mano al mismo tiempo)
allow_dual_wield = False

# Nivel maximo permitido
# Incluso los jugadores que suban de nivel legitimamente mientras juegan seran eliminados.
level_cap = 1000

# Nivel de rareza mas alto permitido en los objetos, 4 es oro
rarity_cap = 4

# Numero de veces que alguien puede atacar y cambiar de planeador antes de ser detectado.
# Si lo pones demasiado bajo, quienes planeen despues de atacar seran expulsados.
# Pero quizas quieras ponerlo un poco mas alto si expulsan a jugadores que estan jugando normalmente.
# Esto es principalmente para evitar el error del bumeran, pero quien sabe que otras habilidades
# se pueden reiniciar usando el planeador repetidamente.
glider_abuse_count = 5

# Margen de tiempo que puede haber entre la disponibilidad real del enfriamiento y la disponibilidad recibida.
# Un margen menor significa mayor precision, pero también mayor probabilidad de que alguien sea
# expulsado si tiene lag.
cooldown_margin = 0.5

# Numero maximo de veces que alguien puede romper los tiempos de reutilizacion seguidos antes de ser expulsado.
# Esto deberia ser 1 o mas por culpa de Wollay.
max_cooldown_strikes = 3

# distancia del objetivo al que estan impactando, una mayor distancia permite mayor retardo.
max_hit_distance = 2000000

# Numero de veces seguidas que un jugador puede superar la distancia maxima de impacto antes de que
# sea expulsado. Probablemente, esto siempre deberia ser superior a 1, ya que si alguien
# reaparece instantaneamente, aun puede recibir daño de personas con lag.
max_hit_distance_strikes = 5

# Cantidad de segundos que alguien puede estar en el aire antes de ser expulsado por volar
max_air_time = 10

# Margen permitido entre la velocidad maxima real y la velocidad maxima percibida
# (aun no implementado)
speed_margin = 1

# Cantidad de segundos de diferencia entre el ultimo golpe y la recepcion de un paquete de impacto
# margen_ultimo_golpe * tiempo_maximo_ultimo_golpe_de_recuperacion + maximo_golpes_ultimo_golpe
# last_hit_margin * max_last_hit_time_catchup + max_last_hit_strikes
# debe ser menor que 15
# para que sea efectivo; cuanto mas cerca de 15, menor sera la probabilidad de que haga algo.
last_hit_margin = 3.0

# El ultimo golpe de Times se recuperara en lugar de dar un strike
max_last_hit_time_catchup = 3

# El ultimo impacto se comprueba cada segundo; si supera el margen, se aplicara una penalización.
# Este valor deberia ser superior a 0, ya que last_hit probablemente se actualice ANTES de que llegue el paquete de impacto.
max_last_hit_strikes = 3

# Cantidad de veces que alguien puede superar la diferencia maxima del contador de golpes consecutivamente
max_hit_counter_strikes = 3

# Diferencia maxima entre el contador de golpes estimado y el contador de golpes real.
max_hit_counter_difference = 4

# Maximo de veces que los puntos de vida de alguien pueden superar sus puntos de vida maximos reales
# Se usa para evitar expulsiones al cambiar de objeto y al obtener puntos de vida superiores a los maximos gracias a espiritus malignos.
max_max_hp_strikes = 4

# Daño maximo que un jugador puede golpear a otro jugador con
max_damage = 10000

log_message = "{playername}({ip}) fue baneado por: {reason}."
disconnect_message = "{name} - has sido baneado por: {reason}."
