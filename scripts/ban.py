"""
Ban management - Mejorado para banear jugadores por nombre y por IP por separado
"""

from cuwo.script import ServerScript, command, admin

SELF_BANNED_PLAYER = 'Estás baneado: {reason}'
SELF_BANNED_IP = 'Tu IP está baneada: {reason}'
PLAYER_BANNED = '{name} ha sido baneado: {reason}'
IP_BANNED = 'IP {ip} ha sido baneada: {reason}'
DEFAULT_REASON = 'Sin motivo'

PLAYER_BAN_DATA = 'banlist_players'
IP_BAN_DATA = 'banlist_ips'


class BanServer(ServerScript):
    def on_load(self):
        # Cargar listas de bans por separado
        self.banned_players = self.server.load_data(PLAYER_BAN_DATA, {})
        self.banned_ips = self.server.load_data(IP_BAN_DATA, {})

    def save_bans(self):
        self.server.save_data(PLAYER_BAN_DATA, self.banned_players)
        self.server.save_data(IP_BAN_DATA, self.banned_ips)

    def ban_player(self, player_name, reason):
        """Banea a un jugador por su nombre (no por IP)"""
        player_name_lower = player_name.lower()
        self.banned_players[player_name_lower] = reason
        self.save_bans()
        
        banned_players = []
        for connection in self.server.connections.copy():
            if not connection.name or connection.name.lower() != player_name_lower:
                continue
            
            name = connection.name
            connection.send_chat(SELF_BANNED_PLAYER.format(reason=reason))
            connection.disconnect()
            banned_players.append(connection)
            
            message = PLAYER_BANNED.format(name=name, reason=reason)
            print(message)
            self.server.send_chat(message)
        
        return banned_players

    def ban_ip(self, ip, reason):
        """Banea una IP (no afecta al nombre del jugador)"""
        self.banned_ips[ip] = reason
        self.save_bans()
        
        banned_players = []
        for connection in self.server.connections.copy():
            if connection.address[0] != ip:
                continue
            
            name = connection.name
            if name is not None:
                connection.send_chat(SELF_BANNED_IP.format(reason=reason))
            connection.disconnect()
            banned_players.append(connection)
            
            if name is None:
                continue
            
            message = IP_BANNED.format(ip=ip, reason=reason)
            print(message)
            self.server.send_chat(message)
        
        return banned_players

    def unban_player(self, player_name):
        """Desbanea a un jugador por su nombre"""
        try:
            player_name_lower = player_name.lower()
            self.banned_players.pop(player_name_lower)
            self.save_bans()
            return True
        except KeyError:
            return False

    def unban_ip(self, ip):
        """Desbanea una IP"""
        try:
            self.banned_ips.pop(ip)
            self.save_bans()
            return True
        except KeyError:
            return False

    def is_player_banned(self, player_name):
        """Verifica si un jugador está baneado por nombre"""
        return player_name.lower() in self.banned_players

    def is_ip_banned(self, ip):
        """Verifica si una IP está baneada"""
        return ip in self.banned_ips

    def on_connection_attempt(self, event):
        """Verifica el ban tanto por jugador como por IP"""
        ip = event.address[0]
        
        # Primero verifica ban de IP
        if ip in self.banned_ips:
            return SELF_BANNED_IP.format(reason=self.banned_ips[ip])
        
        # Las conexiones iniciales no tienen nombre de jugador, así que solo podemos verificar IP aquí
        return None


def get_class():
    return BanServer


@command
@admin
def ban(script, name, *reason):
    """Banea un jugador por su nombre (no por IP)."""
    reason = ' '.join(reason) or DEFAULT_REASON
    banned = script.parent.ban_player(name, reason)
    if banned:
        return f'Jugador "{name}" baneado exitosamente'
    else:
        return f'No se encontró al jugador "{name}" en el servidor'


@command
@admin
def banip(script, ip, *reason):
    """Banea una IP (no afecta al nombre del jugador)."""
    reason = ' '.join(reason) or DEFAULT_REASON
    banned = script.parent.ban_ip(ip, reason)
    return f'{len(banned)} jugador(es) conectado(s) desde IP {ip} fue(ron) baneado(s)'


@command
@admin
def unban(script, name):
    """Desbanea un jugador por su nombre."""
    if script.parent.unban_player(name):
        return f'Jugador "{name}" desbaneado exitosamente'
    else:
        return f'Jugador "{name}" no encontrado en la lista de baneados'


@command
@admin
def unbanip(script, ip):
    """Desbanea una IP."""
    if script.parent.unban_ip(ip):
        return f'IP "{ip}" desbaneada exitosamente'
    else:
        return f'IP "{ip}" no encontrada en la lista de baneados'
