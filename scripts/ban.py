# Copyright (c) Mathias Kaerlev 2013-2017.
#
# This file is part of cuwo.
#
# cuwo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cuwo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cuwo.  If not, see <http://www.gnu.org/licenses/>.

"""
Ban management - Banea por entity_id (jugador específico) y por IP por separado
"""

from cuwo.script import ServerScript, command, admin

SELF_BANNED_PLAYER = 'Estás baneado como jugador: {reason}'
SELF_BANNED_IP = 'Tu IP está baneada: {reason}'
PLAYER_BANNED = '{name} ha sido baneado como jugador: {reason}'
IP_BANNED = 'IP {ip} ha sido baneada: {reason}'
DEFAULT_REASON = 'Sin motivo'

PLAYER_BAN_DATA = 'banlist_players_entities'
IP_BAN_DATA = 'banlist_ips'


class BanServer(ServerScript):
    def on_load(self):
        # Cargar listas de bans por separado
        # Para ban de jugadores, guardamos {entity_id: reason}
        self.banned_players = self.server.load_data(PLAYER_BAN_DATA, {})
        self.banned_ips = self.server.load_data(IP_BAN_DATA, {})

    def save_bans(self):
        self.server.save_data(PLAYER_BAN_DATA, self.banned_players)
        self.server.save_data(IP_BAN_DATA, self.banned_ips)

    def ban_player(self, entity_id, player_name, reason):
        """Banea un jugador específico por su entity_id (NO por nombre)"""
        entity_id_str = str(entity_id)
        self.banned_players[entity_id_str] = {
            'name': player_name,
            'reason': reason
        }
        self.save_bans()
        
        banned_players = []
        for connection in self.server.connections.copy():
            if connection.entity_id != entity_id:
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
        """Banea una IP (no afecta al entity_id del jugador)"""
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

    def unban_player(self, entity_id):
        """Desbanea un jugador por su entity_id"""
        try:
            entity_id_str = str(entity_id)
            player_info = self.banned_players.pop(entity_id_str)
            self.save_bans()
            return True, player_info.get('name', 'Unknown')
        except KeyError:
            return False, None

    def unban_ip(self, ip):
        """Desbanea una IP"""
        try:
            self.banned_ips.pop(ip)
            self.save_bans()
            return True
        except KeyError:
            return False

    def is_player_banned(self, entity_id):
        """Verifica si un jugador está baneado por entity_id"""
        return str(entity_id) in self.banned_players

    def is_ip_banned(self, ip):
        """Verifica si una IP está baneada"""
        return ip in self.banned_ips

    def on_connection_attempt(self, event):
        """Verifica el ban tanto por jugador como por IP"""
        ip = event.address[0]
        
        # Primero verifica ban de IP
        if ip in self.banned_ips:
            return SELF_BANNED_IP.format(reason=self.banned_ips[ip])
        
        # Las conexiones iniciales no tienen entity_id aún, así que solo podemos verificar IP aquí
        return None


def get_class():
    return BanServer


@command
@admin
def ban(script, name, *reason):
    """Banea un jugador específico por su nombre actual (banea al jugador por entity_id, NO al nombre)."""
    reason_str = ' '.join(reason) or DEFAULT_REASON
    
    # Encontrar el jugador por nombre
    player = script.get_player(name)
    if player is None:
        return f'No se encontró al jugador "{name}"'
    
    # Banear por entity_id del jugador
    entity_id = player.entity_id
    player_name = player.name
    banned = script.parent.ban_player(entity_id, player_name, reason_str)
    
    if banned:
        return f'Jugador "{player_name}" (ID: {entity_id}) baneado correctamente'
    else:
        return f'Error al banear a "{player_name}"'


@command
@admin
def banip(script, ip, *reason):
    """Banea una IP (no afecta al jugador individual)."""
    reason_str = ' '.join(reason) or DEFAULT_REASON
    banned = script.parent.ban_ip(ip, reason_str)
    return f'{len(banned)} jugador(es) conectado(s) desde IP {ip} fue(ron) baneado(s)'


@command
@admin
def unban(script, entity_id_str):
    """Desbanea un jugador por su entity_id."""
    try:
        entity_id = int(entity_id_str)
    except ValueError:
        return f'Entity ID inválido: "{entity_id_str}"'
    
    success, player_name = script.parent.unban_player(entity_id)
    if success:
        return f'Jugador (ID: {entity_id}) desbaneado exitosamente'
    else:
        return f'Jugador con ID {entity_id} no encontrado en la lista de baneados'


@command
@admin
def unbanip(script, ip):
    """Desbanea una IP."""
    if script.parent.unban_ip(ip):
        return f'IP "{ip}" desbaneada exitosamente'
    else:
        return f'IP "{ip}" no encontrada en la lista de baneados'
