"""
Ban management - Banea solo por IP
El comando /ban banea la IP del jugador
"""

from cuwo.script import ServerScript, ConnectionScript, command, admin

SELF_BANNED_IP = 'Tu IP esta baneada (Razon: {reason}).'
IP_BANNED = 'El jugador {name} ha sido baneado (Razon: {reason}).'
DEFAULT_REASON = 'Sin motivo especificado'

IP_BAN_DATA = 'banlist_ips'


class BanConnectionScript(ConnectionScript):
    """Script de conexión para verificar ban de IP"""
    pass


class BanServer(ServerScript):
    connection_class = BanConnectionScript
    
    def on_load(self):
        """Cargar lista de IPs baneadas"""
        self.banned_ips = self.server.load_data(IP_BAN_DATA, {})

    def save_bans(self):
        """Guardar lista de IPs baneadas"""
        self.server.save_data(IP_BAN_DATA, self.banned_ips)

    def ban_ip(self, ip, reason, player_name=None):
        """Banea una IP y guarda el nombre del jugador"""
        # Guardar como dict con nombre y razón
        self.banned_ips[ip] = {
            'reason': reason,
            'name': player_name or 'Desconocido'
        }
        self.save_bans()
        
        banned_players = []
        # Desconectar jugadores de esa IP
        for connection in self.server.connections.copy():
            if connection.address[0] != ip:
                continue
            
            name = connection.name
            if name is not None:
                connection.send_chat(SELF_BANNED_IP.format(reason=reason))
            connection.disconnect()
            banned_players.append(connection)
            
            if name is not None:
                message = IP_BANNED.format(ip=ip, reason=reason, name=name)
                print(message)
                self.server.send_chat(message)
        
        return banned_players

    def unban_ip(self, ip):
        """Desbanea una IP"""
        try:
            self.banned_ips.pop(ip)
            self.save_bans()
            return True
        except KeyError:
            return False

    def is_ip_banned(self, ip):
        """Verifica si una IP está baneada"""
        return ip in self.banned_ips

    def get_ban_reason(self, ip):
        """Obtiene la razón del ban de una IP"""
        ban_data = self.banned_ips.get(ip, {})
        if isinstance(ban_data, dict):
            return ban_data.get('reason', DEFAULT_REASON)
        return ban_data or DEFAULT_REASON

    def get_ban_name(self, ip):
        """Obtiene el nombre del jugador baneado"""
        ban_data = self.banned_ips.get(ip, {})
        if isinstance(ban_data, dict):
            return ban_data.get('name', 'Desconocido')
        return 'Desconocido'

    def on_connection_attempt(self, event):
        """Verifica si la IP está baneada ANTES de conectar"""
        ip = event.address[0]
        
        if ip in self.banned_ips:
            reason = self.get_ban_reason(ip)
            return SELF_BANNED_IP.format(reason=reason)
        
        return None


def get_class():
    return BanServer


@command
@admin
def ban(script, name, *reason):
    """Banea la IP de un jugador. Uso: /ban (nombre_jugador) (razón)"""
    reason_str = ' '.join(reason) or DEFAULT_REASON
    
    # Encontrar el jugador por nombre
    player = script.get_player(name)
    if player is None:
        return f'No se encontró al jugador "{name}"'
    
    # Obtener IP del jugador
    ip = player.address[0]
    player_name = player.name
    
    # Banear la IP (ahora con el nombre del jugador)
    script.parent.ban_ip(ip, reason_str, player_name)
    
    return f'IP {ip} del jugador "{player_name}" baneada correctamente. Razón: {reason_str}'


@command
@admin
def unban(script, ip):
    """Desbanea una IP. Uso: /unban (IP)"""
    if script.parent.unban_ip(ip):
        return f'IP "{ip}" desbaneada exitosamente'
    else:
        return f'IP "{ip}" no encontrada en la lista de baneados'


@command
@admin
def banlist(script):
    """Muestra la lista de IPs baneadas"""
    if not script.parent.banned_ips:
        return 'No hay IPs baneadas'
    
    ban_list = []
    for ip, ban_data in script.parent.banned_ips.items():
        if isinstance(ban_data, dict):
            reason = ban_data.get('reason', DEFAULT_REASON)
            name = ban_data.get('name', 'Desconocido')
            ban_list.append(f'{ip} ({name}): {reason}')
        else:
            # Compatibilidad con bans antiguos en formato string
            ban_list.append(f'{ip}: {ban_data}')
    
    message = f'IPs baneadas ({len(ban_list)}): ' + ' | '.join(ban_list)
    return message
