"""
Conjunto de comandos predeterminado incluido con cuwo
"""

from cuwo.script import ServerScript, command, admin, alias
from cuwo.common import get_chunk
from cuwo import constants
from cuwo import static
from cuwo.vector import vec3, qvec3
import platform

MAX_STUN_TIME = 1000 * 60  # 60 segundos en milisegundos


class CommandServer(ServerScript):
    pass


def get_class():
    return CommandServer


@command
@admin
def say(script, *message):
    """Envia un mensaje global al servidor."""
    message = ' '.join(message)
    script.server.send_chat(message)
    response = f"Mensaje enviado: {message}"
    return response


@command
def server(script):
    """Devuelve informacion sobre la plataforma del servidor."""
    msg = 'El servidor se esta ejecutando %r' % platform.system()
    revision = script.server.git_rev
    if revision is not None:
        msg += ', revision %s' % revision
    return msg


@command
def login(script, password):
    """Inicia sesion con la contraseña especificada."""
    password = password.lower()
    user_types = script.server.passwords.get(password, [])
    if not user_types:
        response = 'Contraseña no valida'
    else:
        response = 'Iniciado sesion como %s' % (', '.join(user_types))
    return response


@command
def help(script, name=None):
    """Devuelve informacion sobre los comandos."""
    if name is None:
        # Diccionario con información de todos los comandos
        commands_help = {
            'help': ('help [nombre_comando]', 'Muestra información sobre los comandos'),
            'say': ('say (mensaje)', 'Envía un mensaje global al servidor'),
            'server': ('server', 'Muestra información sobre la plataforma del servidor'),
            'login': ('login (contraseña)', 'Inicia sesión con permisos especiales'),
            'kick': ('kick (nombre) [razón]', 'Expulsa a un jugador del servidor'),
            'setclock': ('setclock (hh:mm)', 'Establece la hora del día'),
            'whereis': ('whereis [nombre]', 'Muestra la ubicación de un jugador'),
            'pm': ('pm (nombre) (mensaje)', 'Envía un mensaje privado a un jugador'),
            'kill': ('kill [nombre]', 'Mata a un jugador'),
            'stun': ('stun (nombre) [segundos]', 'Aturde a un jugador por un tiempo'),
            'heal': ('heal [nombre] [hp]', 'Cura a un jugador'),
            'who': ('who', 'Lista todos los jugadores conectados'),
            'whowhere': ('whowhere', 'Lista jugadores y sus ubicaciones'),
            'player': ('player (nombre)', 'Muestra información detallada de un jugador'),
            'addrights': ('addrights (nombre) (derecho)', 'Otorga derechos especiales a un usuario'),
            'removerights': ('removerights (nombre) (derecho)', 'Elimina derechos especiales de un usuario'),
            'rights': ('rights [nombre]', 'Muestra los derechos de un usuario'),
            'sound': ('sound (nombre)', 'Reproduce un sonido global'),
            'teleport': ('teleport (jugador) | (x) (y) | (x) (y) (z)', 'Teletransportate a un jugador o ubicación'),
            't': ('t (jugador) | (x) (y) | (x) (y) (z)', 'Alias de teleport'),
            'load': ('load (nombre_script)', 'Carga un script en tiempo de ejecución'),
            'unload': ('unload (nombre_script)', 'Descarga un script en tiempo de ejecución'),
            'reload': ('reload (nombre_script)', 'Recarga un script en tiempo de ejecución'),
            'scripts': ('scripts', 'Muestra los scripts cargados actualmente'),
            'ban': ('ban (nombre) [razón]', 'Banea a un jugador por su IP'),
            'unban': ('unban (IP)', 'Desbanea una IP'),
            'banlist': ('banlist', 'Muestra todas las IPs baneadas'),
        }
        
        lines = []
        lines.append("=" * 90)
        lines.append("COMANDOS DISPONIBLES:")
        lines.append("=" * 90)
        
        # Obtener comandos válidos del script
        valid_commands = {cmd.name for cmd in script.get_commands()}
        
        # Calcular ancho máximo para alineación
        max_width = max(len(usage) for usage, _ in commands_help.values() if usage)
        
        for cmd_name in sorted(commands_help.keys()):
            if cmd_name in valid_commands or cmd_name == 't':  # Incluir alias
                usage, description = commands_help[cmd_name]
                line = f"  {usage.ljust(max_width)} → {description}"
                lines.append(line)
        
        lines.append("=" * 90)
        lines.append("Nota: (parámetro) = obligatorio | [parámetro] = opcional")
        lines.append("=" * 90)
        
        return '\n'.join(lines)
    else:
        # Mostrar información detallada de un comando específico
        command = script.get_command(name)
        if command is None:
            return f'No existe tal comando: {name}'
        
        help_text = command.get_help()
        return help_text if help_text else f"Sin información disponible para el comando: {name}"


@command
@admin
def kick(script, name, *reason):
    """expulsa al jugador especificado."""
    reason = ' '.join(reason) or 'No se especifica ningun motivo'
    player = script.get_player(name)
    player.kick(reason)
    response = f"Jugador {player.name} expulsado. Razón: {reason}"
    return response


@command
@admin
def setclock(script, value):
    """Establece la hora del dia. Formato: hh:mm."""
    try:
        script.server.set_clock(value)
        response = 'Reloj configurado en %s' % value
    except ValueError:
        response = 'Reloj especificado no valido'
    return response


@command
def whereis(script, name=None):
    """Muestra donde esta un jugador en el mundo."""
    player = script.get_player(name)
    if player is script.connection:
        message = 'estas en %s'
    else:
        message = '%s esta en %%s' % player.name
    response = message % (get_chunk(player.position),)
    return response


@command
def pm(script, name, *message):
    """Envia un mensaje privado a un jugador."""
    player = script.get_player(name)
    message_text = ' '.join(message)
    
    sender_name = script.connection.name
    receiver_name = player.name
    
    # Mensaje que recibe el jugador que envía el PM (el que ejecuta el comando)
    sender_message = f"yo (pm-{receiver_name}): {message_text}"
    
    # Mensaje que recibe el jugador que recibe el PM
    receiver_message = f"{sender_name} (pm): {message_text}"
    
    # Mostrar en consola cuwo y chat web
    console_message = f"{sender_name} (pm-{receiver_name}): {message_text}"
    
    # Enviar mensaje privado al receptor
    player.send_chat(receiver_message)
    
    # Imprimir para que aparezca en consola cuwo y se capture en chat web
    print(console_message)
    
    response = sender_message
    return response


@command
@admin
def kill(script, name=None):
    """Mata a un jugador."""
    player = script.get_player(name)
    player.entity.kill()
    message = '%s fue asesinado' % player.name
    script.server.send_chat(message)
    return message


@command
@admin
def stun(script, name, seconds=1):
    """Aturde a un jugador por un tiempo especifico en segundos."""
    
    # Convertir segundos a milisegundos
    try:
        seconds = int(seconds)
    except ValueError:
        return f"Error: El tiempo debe ser un número en segundos, recibido: {seconds}"
    
    # Convertir a milisegundos
    milliseconds = seconds * 1000
    
    # Limita el tiempo de aturdimiento
    milliseconds = abs(milliseconds)
    if milliseconds > MAX_STUN_TIME:
        err = 'El tiempo de aturdimiento es demasiado largo. Por favor, especifique un valor inferior a %d segundos' % (MAX_STUN_TIME // 1000)
        return err
    
    try:
        player = script.get_player(name)
        player.entity.damage(stun_duration=int(milliseconds))
        message = '%s fue aturdido durante %d segundos' % (player.name, seconds)
        script.server.send_chat(message)
        return message
    except Exception as e:
        return f"Jugador inválido especificado"


@command
@admin
def heal(script, name=None, hp=1000):
    """Cura a un jugador en una cantidad especifica."""
    player = script.get_player(name)
    player.entity.damage(-int(hp))
    response = '%s fue sanado' % player.name
    return response


def who_where(script, include_where):
    server = script.server
    player_count = len(server.players)
    if player_count == 0:
        return 'No hay jugadores conectados'
    formatted_names = []
    for player in list(server.players.values()):
        name = '%s #%s' % (player.name, player.entity_id)
        if include_where:
            name += ' %s' % (get_chunk(player.position),)
        formatted_names.append(name)
    noun = 'jugador' if player_count == 1 else 'jugadores'
    msg = '%s %s conectado: ' % (player_count, noun)
    msg += ', '.join(formatted_names)
    return msg


@command
def who(script):
    """Lista de jugadores."""
    response = who_where(script, False)
    return response


@command
def whowhere(script):
    """Enumera a los jugadores y sus ubicaciones."""
    response = who_where(script, True)
    return response


@command
def player(script, name):
    """Devuelve informacion sobre un jugador."""
    player = script.get_player(name)
    entity = player.entity
    typ = entity.class_type
    klass = constants.CLASS_NAMES[typ]
    spec = constants.CLASS_SPECIALIZATIONS[typ][entity.specialization]
    level = entity.level
    response = '%r es un nivel %s %s (%s)' % (player.name, level, klass, spec)
    return response


@command
@admin
def addrights(script, player, *rights):
    """Otorga derechos a un usuario."""
    player = script.get_player(player)
    rights = set(rights) & player.rights
    player.rights.update(rights)
    if rights:
        rights = ', '.join((repr(right) for right in rights))
    else:
        rights = 'no'
    response = '%s derechos otorgados a %r' % (rights, player.name)
    return response


@command
@admin
def removerights(script, player, *rights):
    """Elimina los derechos de un usuario."""
    player = script.get_player(player)
    rights = set(rights) & player.rights
    player.rights.difference_update(rights)
    if rights:
        rights = ', '.join((repr(right) for right in rights))
    else:
        rights = 'no'
    response = '%s derechos eliminados de %r' % (rights, player.name)
    return response


@command
def rights(script, player=None):
    """Muestra los derechos de un usuario."""
    player = script.get_player(player)
    rights = player.rights
    if rights:
        rights = ', '.join((repr(right) for right in player.rights))
    else:
        rights = 'no'
    response = '%r tiene %s derechos' % (player.name, rights)
    return response


@command
@admin
def sound(script, name):
    """Reproduce un sonido global."""
    try:
        script.server.play_sound(name)
        response = f"Sonido '{name}' reproducido"
    except KeyError:
        response = 'No hay tal sonido'
    return response

def create_teleport_packet(pos, chunk_pos, user_id):
    packet = static.StaticEntityPacket()
    header = static.StaticEntityHeader()
    packet.header = header
    packet.chunk_x = chunk_pos[0]
    packet.chunk_y = chunk_pos[1]
    packet.entity_id = 0
    header.set_type('Bench')
    header.size = vec3(0, 0, 0)
    header.closed = True
    header.orientation = static.ORIENT_SOUTH
    header.pos = pos
    header.time_offset = 0
    header.something8 = 0
    header.user_id = user_id
    return packet


@command
@admin
@alias('t')
def teleport(script, a, b=None, c=None):
    """Teletransportate a un chunk o jugador."""
    entity = script.connection.entity

    if b is None:
        # teletransportarse al jugador
        player = script.get_player(a)
        pos = player.entity.pos
    elif c is None:
        # teletransportarse al chunk
        pos = qvec3(int(a), int(b), 0) * constants.CHUNK_SCALE
        pos.z = script.world.get_height(pos.xy) or entity.pos.z
    else:
        # teletransportarse a la posicion
        pos = qvec3(int(a), int(b), int(c))

    update_packet = script.server.update_packet
    chunk = script.connection.chunk

    packet = create_teleport_packet(pos, chunk.pos, entity.entity_id)
    update_packet.static_entities.append(packet)

    def send_reset_packet():
        if chunk.static_entities:
            chunk.static_entities[0].update()
        else:
            packet = create_teleport_packet(pos, chunk.pos, 0)
            update_packet.static_entities.append(packet)

    script.loop.call_later(0.1, send_reset_packet)


@command
@admin
def load(script, name):
    """Carga un script en tiempo de ejecucion."""
    name = str(name)
    if name in script.server.scripts:
        response = 'El script %r ya esta activado' % name
    else:
        script.server.load_script(name)
        response = 'Script %r activado' % name
    return response


@command
@admin
def unload(script, name):
    """Desactiva un script en tiempo de ejecucion."""
    name = str(name)
    if not script.server.unload_script(name):
        response = 'El script %r no esta activado' % name
    else:
        response = 'Script %r desactivado' % name
    return response


@command
@admin
def reload(script, name):
    """Recarga un script en tiempo de ejecucion."""
    name = str(name)
    if not script.server.unload_script(name):
        response = 'El script %r no esta activado.' % name
    else:
        script.server.load_script(name, update=True)
        response = 'Script %r recargado' % name
    return response


@command
def scripts(script):
    """Muestra los scripts cargados actualmente."""
    response = 'Scripts: ' + ', '.join(script.server.scripts.items)
    return response
