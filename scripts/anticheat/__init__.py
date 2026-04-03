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

"""Script Antitrampa para Cuwo"""

from cuwo.constants import (RANGER_CLASS, ATTACKING_FLAG, STEALTH_FLAG,
                            GLIDER_FLAG)
from cuwo.script import ServerScript, ConnectionScript
from cuwo.common import get_power, get_item_name, is_bit_set
from cuwo.packet import ServerUpdate, PickupAction
from .constants import (LOG_LEVEL_VERBOSE, LOG_LEVEL_DEFAULT, CUWO_ANTICHEAT,
                        LEGAL_RECIPE_ITEMS, LEGAL_ITEMS, LEGAL_CLASSES,
                        LEGAL_ITEMSLOTS, TWOHANDED_WEAPONS, CLASS_WEAPONS,
                        CLASS_ARMOR, ARMOR_IDS, ABILITIES, APPEARANCES)
from cuwo import tgen_wrap as entitydata

import re
import math
import traceback


def is_similar(float1, float2, tolerance=0.1):
    """Verifica si dos numeros flotantes son similares dentro de un margen"""
    return float1 > float2 - tolerance and float1 < float2 + tolerance


def is_valid_float(v):
    """Valida que un numero flotante sea valido (no NaN ni Inf)"""
    return not math.isnan(v) and not math.isinf(v)


class AntiCheatConnection(ConnectionScript):
    def on_load(self):
        """Inicializa todas las variables de deteccion de trampas"""
        # Tiempo de combate
        self.combat_end_time = 0
        self.last_glider_active = 0
        self.last_attacking = 0

        # Contador de abusos
        self.glider_count = 0
        self.attack_count = 0

        # Actualizacion de entidad
        self.time_since_update = 0
        self.last_entity_update = None
        self.last_update_mode = 0

        # Salud y mana
        self.max_health = 0
        self.last_mana = 0
        self.last_health = 0
        self.mana = 0
        self.health = 0

        # Vuelo y aire
        self.air_time = 0
        self.hit_distance_strikes = 0
        self.is_dead = False

        # Velocidad
        self.last_pos = None
        self.last_speed_check = 0
        self.time_traveled = 0
        self.distance_traveled = 0

        # Enfriamiento de habilidades
        self.cooldown_strikes = 0
        self.ability_cooldown = {}

        # Golpes
        self.last_hit_time = 0
        self.last_hit_strikes = 0
        self.last_hit_check = 0
        self.hit_counter = 0
        self.hit_counter_strikes = 0
        self.max_hp_strikes = 0

        # Recuperacion de golpes al conectar
        self.last_hit_time_catchup = self.loop.time() + 10
        self.last_hit_time_catchup_count = -10

        # Cargar configuracion
        try:
            config = self.server.config.anticheat
            self.level_cap = config.level_cap
            self.allow_dual_wield = config.allow_dual_wield
            self.rarity_cap = config.rarity_cap
            self.name_filter = config.name_filter
            self.log_level = config.log_level
            self.log_message = config.log_message
            self.disconnect_message = config.disconnect_message
            self.irc_log_level = config.irc_log_level
            self.glider_abuse_count = config.glider_abuse_count
            self.cooldown_margin = config.cooldown_margin
            self.max_hit_distance = config.max_hit_distance ** 2
            self.max_hit_distance_strikes = config.max_hit_distance_strikes
            self.max_cooldown_strikes = config.max_cooldown_strikes
            self.max_air_time = config.max_air_time
            self.speed_margin = config.speed_margin
            self.last_hit_margin = config.last_hit_margin
            self.max_last_hit_strikes = config.max_last_hit_strikes
            self.max_hit_counter_strikes = config.max_hit_counter_strikes
            self.max_hit_counter_difference = config.max_hit_counter_difference
            self.max_max_hp_strikes = config.max_max_hp_strikes
            self.max_last_hit_time_catchup = config.max_last_hit_time_catchup
            self.max_damage = config.max_damage
        except Exception as e:
            self.log("Error cargando configuracion: {}".format(str(e)), LOG_LEVEL_VERBOSE)
            raise

    def on_join(self, event):
        """Realiza comprobaciones completas al conectar un jugador"""
        try:
            if self.on_name_update() is False:
                return False

            if self.on_class_update() is False:
                return False

            if self.on_equipment_update() is False:
                return False

            if self.on_level_update() is False:
                return False

            if self.on_skill_update() is False:
                return False

            if self.on_multiplier_update() is False:
                return False

            if self.on_flags_update() is False:
                return False

            if self.on_appearance_update() is False:
                return False

            if self.check_hostile_type() is False:
                return False

            self.update_max_health()
            if self.check_max_health(True) is False:
                return False
        except Exception as e:
            self.log("Error en on_join: {}".format(str(e)), LOG_LEVEL_VERBOSE)
            self.remove_cheater('error en verificacion de conexion')
            return False

    def update_max_health(self):
        """Actualiza la salud maxima del personaje basado en su poder"""
        try:
            self.max_health = self.connection.entity.get_max_hp()
        except Exception as e:
            self.log("Error actualizando salud maxima: {}".format(str(e)), LOG_LEVEL_VERBOSE)

    def check_max_health(self, no_strikes=False):
        """Verifica que la salud no exceda el maximo permitido"""
        try:
            entity = self.connection.entity
            if entity.hp > self.max_health + 1:
                self.max_hp_strikes += 1

                if no_strikes or self.max_hp_strikes > self.max_max_hp_strikes:
                    self.log("salud del personaje {hp} superior a la maxima {max}".format(
                        hp=entity.hp, max=self.max_health), LOG_LEVEL_VERBOSE)
                    self.remove_cheater('truco de salud')
                    return False
            else:
                self.max_hp_strikes = 0
        except Exception as e:
            self.log("Error verificando salud maxima: {}".format(str(e)), LOG_LEVEL_VERBOSE)
        return True

    def on_name_update(self, event=None):
        """Verifica nombre del personaje al conectar o cambiar"""
        if self.has_illegal_name():
            self.remove_cheater('nombre de personaje ilegal')
            return False

    def on_equipment_update(self, event=None):
        """Verifica que el equipo sea legal"""
        if self.has_illegal_items():
            self.remove_cheater('objetos ilegales equipados')
            return False

        self.update_max_health()

    def on_level_update(self, event=None):
        """Verifica el nivel del personaje"""
        if self.has_illegal_level():
            self.remove_cheater('nivel de personaje ilegal, maximo: {}'.format(
                self.level_cap))
            return False

        self.update_max_health()

    def on_skill_update(self, event=None):
        """Verifica la distribucion de habilidades"""
        if self.has_illegal_skills():
            self.remove_cheater('distribucion de habilidades ilegal')
            return False

    def on_mode_update(self, event=None):
        """Verifica modo de combate y enfriamientos de habilidades"""
        try:
            entity = self.connection.entity

            if (entity.current_mode == 0 and self.combat_end_time == 0):
                self.combat_end_time = self.loop.time()

            if entity.current_mode != 0:
                self.combat_end_time = 0

            if self.has_illegal_mode():
                self.remove_cheater('modo de personaje ilegal (habilidad)')
                return False

            if entity.current_mode != 0:
                if self.use_ability(entity.current_mode) is False:
                    self.remove_cheater('truco de enfriamiento')
                    return False
        except Exception as e:
            self.log("Error verificando modo: {}".format(str(e)), LOG_LEVEL_VERBOSE)

    def on_class_update(self, event=None):
        """Verifica que la clase sea valida"""
        if self.has_illegal_class():
            self.remove_cheater('clase de personaje ilegal')
            return False

    def on_multiplier_update(self, event=None):
        """Verifica que los multiplicadores de atributos sean legales"""
        if self.has_illegal_multiplier():
            self.remove_cheater('multiplicador de atributo ilegal')
            return False

    def on_charged_mp_update(self, event=None):
        """Verifica mana cargado"""
        if self.has_illegal_charged_mp():
            self.remove_cheater('multiplicador de carga ilegal')
            return False

    def on_consumable_update(self, event=None):
        """Verifica consumibles equipados"""
        if self.has_illegal_consumable():
            self.remove_cheater('consumible ilegal equipado')
            return False

    def on_flags_update(self, event=None):
        """Verifica banderas de personaje"""
        if self.has_illegal_flags():
            self.remove_cheater('banderas de personaje ilegales')
            return False

    def on_appearance_update(self, event=None):
        """Verifica apariencia del personaje"""
        if self.has_illegal_appearance():
            self.remove_cheater('apariencia de personaje ilegal')
            return False

    def on_entity_update(self, event):
        """Verificaciones en tiempo real durante el juego"""
        try:
            entity = self.connection.entity
            if self.last_entity_update is None:
                self.last_entity_update = self.loop.time()
                if not self.connection.has_joined:
                    self.remove_cheater('actualizacion completa de entidad no enviada')
                    return False

            self.time_since_update = self.loop.time() - self.last_entity_update
            self.last_entity_update = self.loop.time()

            self.last_mana = self.mana
            self.last_health = self.health

            self.mana = entity.mp
            self.health = entity.hp

            if is_bit_set(event.mask, 7):
                if self.check_hostile_type() is False:
                    return False

            if is_bit_set(event.mask, 27):
                if self.check_max_health() is False:
                    return False

            if self.loop.time() - self.last_hit_check > 1.0:
                self.last_hit_check = self.loop.time()
                if self.check_last_hit() is False:
                    return False

            if self.check_flying() is False:
                return False

            if not self.is_dead and self.health <= 0:
                self.is_dead = True
                self.on_death()

            if self.health > 0 and self.is_dead:
                self.is_dead = False
        except Exception as e:
            self.log("Error en entity update: {}".format(str(e)), LOG_LEVEL_VERBOSE)

    def on_drop(self, event):
        """Verifica objetos siendo soltados"""
        try:
            if self.is_item_illegal(event.item):
                pack = ServerUpdate()
                pack.reset()
                action = PickupAction()
                action.entity_id = self.connection.entity_id
                action.item_data = event.item
                pack.pickups.append(action)

                self.connection.send_packet(pack)

                self.remove_cheater('objeto ilegal soltado')
                return False
        except Exception as e:
            self.log("Error verificando drop: {}".format(str(e)), LOG_LEVEL_VERBOSE)

    def on_hit(self, event):
        """Verifica golpes y daño"""
        try:
            packet = event.packet
            if packet.entity_id != self.connection.entity_id:
                return False

            damage = event.packet.damage

            # Sanitizar valor de daño
            if not is_valid_float(damage) or math.fabs(damage) > self.max_damage:
                self.remove_cheater('daño de golpe invalido ({})'.format(damage))
                return False

            # Solo paquetes de daño, no curacion
            if damage >= 0:
                self.last_hit_time = self.loop.time()
                self.hit_counter += 1

            # Verificar distancia de golpe
            hitdistance = (packet.pos - event.target.pos).squared_length
            if hitdistance > self.max_hit_distance:
                self.hit_distance_strikes += 1
                if self.hit_distance_strikes > self.max_hit_distance_strikes:
                    self.remove_cheater('distancia de golpe demasiado lejana, '
                                      'o bien hace trampas o tiene mucho lag')
                    return False
            else:
                self.hit_distance_strikes = 0
        except Exception as e:
            self.log("Error verificando golpe: {}".format(str(e)), LOG_LEVEL_VERBOSE)

    def on_death(self, event=None):
        """Al morir, reinicia enfriamientos y contadores"""
        try:
            self.ability_cooldown = {}
            self.last_hit_time_catchup = self.loop.time()
            self.last_hit_time_catchup_count = -1
        except Exception as e:
            self.log("Error en muerte: {}".format(str(e)), LOG_LEVEL_VERBOSE)

    def log(self, message, loglevel=LOG_LEVEL_DEFAULT):
        """Registra un mensaje de antitrampa en consola y web"""
        if self.log_level >= loglevel:
            # Mostrar en consola cuwo y capturar en web
            full_message = CUWO_ANTICHEAT + " - " + message
            print(full_message)
        if self.irc_log_level >= loglevel:
            try:
                self.server.scripts.irc.send(CUWO_ANTICHEAT + " - " + message)
            except (KeyError, AttributeError):
                self.disable_irc_logging()

    def disable_irc_logging(self):
        """Desactiva registro en IRC si no esta disponible"""
        self.irc_log_level = 0
        self.server.config.anticheat.irc_log_level = 0

    def remove_cheater(self, reason):
        """Banea a un jugador tramposero por IP"""
        try:
            connection = self.connection
            
            # Mensaje para consola del servidor (cuwo y web)
            anticheat_msg = f"{CUWO_ANTICHEAT} - El jugador {connection.name}({connection.address[0]}) fue baneado (Razon: {reason})"
            print(anticheat_msg)
            
            # Mensaje ÚNICO para el jugador baneado
            disconnect_msg = f"anticheat: has sido baneado (Razon: {reason})"
            connection.send_chat(disconnect_msg)

            # Mensaje ÚNICO en el servidor para todos los jugadores
            broadcast_msg = f"anticheat: El jugador {connection.name} a sido baneado (Razon: {reason})"
            self.server.send_chat(broadcast_msg)

            # Usar el sistema de bans por IP
            try:
                ban_script = self.server.scripts.ban
                ip = connection.address[0]
                player_name = connection.name if connection.name else "Desconocido"
                
                # Banear marca como 'anticheat'
                ban_script.ban_ip(ip, reason, player_name, ban_by='anticheat')
            except (KeyError, AttributeError) as e:
                connection.disconnect()
                return

            connection.disconnect()
        except Exception as e:
            try:
                connection.disconnect()
            except:
                pass

    def has_illegal_name(self):
        """Verifica si el nombre del personaje es ilegal"""
        try:
            entity = self.connection.entity
            if re.search(self.name_filter, entity.name) is None:
                self.log("nombre de personaje no cumple requisitos: {}".format(
                    entity.name), LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando nombre: {}".format(str(e)), LOG_LEVEL_VERBOSE)
        return False

    def has_illegal_items(self):
        """Verifica si hay objetos ilegales equipados"""
        try:
            entity = self.connection.entity
            for slotindex in range(13):
                if entity.equipment[slotindex].type == 0:
                    continue

                if self.is_item_illegal(entity.equipment[slotindex]):
                    return True

                if self.is_equipped_illegal(entity.equipment[slotindex], slotindex):
                    return True
        except Exception as e:
            self.log("Error verificando items: {}".format(str(e)), LOG_LEVEL_VERBOSE)
        return False

    def is_item_illegal(self, item):
        """Verifica si un objeto individual es ilegal"""
        try:
            # Nivel negativo
            if item.level < 0:
                self.log("nivel de objeto negativo: {}".format(item.level), LOG_LEVEL_VERBOSE)
                return True

            # Demasiados bloques de personalizacion
            if item.upgrade_count > 32:
                self.log("demasiados bloques de personalizacion: {}".format(
                    item.upgrade_count), LOG_LEVEL_VERBOSE)
                return True

            # Rareza excesiva
            if item.rarity > self.rarity_cap:
                self.log("rareza de objeto excesiva: {}".format(
                    item.rarity), LOG_LEVEL_VERBOSE)
                return True

            # Consumible con rareza
            if item.type == 1 and item.rarity > 0:
                self.log("consumible con rareza: {}".format(
                    get_item_name(item)), LOG_LEVEL_VERBOSE)
                return True

            # Receta ilegal
            if item.type == 2:
                if item.minus_modifier not in LEGAL_RECIPE_ITEMS:
                    self.log("receta invalida tipo={}".format(
                        item.minus_modifier), LOG_LEVEL_VERBOSE)
                    return True

                if not (item.material in LEGAL_ITEMS.get((item.minus_modifier, item.sub_type), ())):
                    self.log("material invalido en receta", LOG_LEVEL_VERBOSE)
                    return True

                return False

            # Verificar item tipo/subtipo
            if (item.type, item.sub_type) not in LEGAL_ITEMS:
                self.log("objeto invalido tipo={} subtipo={} item={}".format(
                    item.type, item.sub_type, get_item_name(item)), LOG_LEVEL_VERBOSE)
                return True

            # Verificar material
            if item.material not in LEGAL_ITEMS.get((item.type, item.sub_type), ()):
                self.log("material invalido: tipo={} material={} item={}".format(
                    item.type, item.material, get_item_name(item)), LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando item: {}".format(str(e)), LOG_LEVEL_VERBOSE)
            return False

        return False

    def is_equipped_illegal(self, item, in_slotindex):
        """Verifica si un objeto equipado es ilegal para su posicion"""
        try:
            entity = self.connection.entity

            # Nivel muy alto
            power_item = get_power(item.level)
            power_char = get_power(entity.level)
            if power_item > power_char:
                self.log("nivel de objeto {} superior a nivel de personaje {}".format(
                    item.level, entity.level), LOG_LEVEL_VERBOSE)
                return True

            # Ranura no equipable
            if item.type not in LEGAL_ITEMSLOTS:
                self.log("tipo de objeto no equipable: tipo={}".format(item.type), LOG_LEVEL_VERBOSE)
                return True

            # Ranura invalida
            if in_slotindex not in LEGAL_ITEMSLOTS.get(item.type, ()):
                self.log("ranura invalida para tipo: tipo={} ranura={}".format(
                    item.type, in_slotindex), LOG_LEVEL_VERBOSE)
                return True

            # Doble empunadura
            if in_slotindex == 6 and item.sub_type in TWOHANDED_WEAPONS:
                if (self.allow_dual_wield is False and entity.equipment[7].type != 0):
                    self.log("error de doble empunadura detectado", LOG_LEVEL_VERBOSE)
                    return True
                if entity.equipment[7].sub_type in TWOHANDED_WEAPONS:
                    self.log("doble empunadura con dos armas", LOG_LEVEL_VERBOSE)
                    return True

            if in_slotindex == 7 and item.sub_type in TWOHANDED_WEAPONS:
                if (self.allow_dual_wield is False and entity.equipment[6].type != 0):
                    self.log("error de doble empunadura en ranura 7", LOG_LEVEL_VERBOSE)
                    return True

            # Arma no permitida para clase
            if (item.type == 3 and not item.sub_type in CLASS_WEAPONS.get(entity.class_type, ())):
                self.log("arma no permitida para clase: clase={}".format(
                    entity.class_type), LOG_LEVEL_VERBOSE)
                return True

            # Armadura no permitida para clase
            if (item.type in ARMOR_IDS and 
                    not item.material in CLASS_ARMOR.get(entity.class_type, ())):
                self.log("armadura no permitida para clase: clase={}".format(
                    entity.class_type), LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando equipo: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return False

    def has_illegal_consumable(self):
        """Verifica si el consumible equipado es ilegal"""
        try:
            entity = self.connection.entity
            item = entity.consumable

            if item.type == 0:
                return False

            if self.is_item_illegal(item):
                return True

            power_item = get_power(item.level)
            power_char = get_power(entity.level)
            if power_item > power_char:
                self.log("nivel de consumible {} superior a nivel {}".format(
                    item.level, entity.level), LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando consumible: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return False

    def has_illegal_skills(self):
        """Verifica si la distribucion de habilidades es legal"""
        try:
            entity = self.connection.entity
            total_skillpoints = 0
            for item in entity.skills:
                if item < 0:
                    self.log("puntos de habilidad negativo detectado", LOG_LEVEL_VERBOSE)
                    return True

                total_skillpoints += item

            if total_skillpoints > (entity.level - 1) * 2:
                self.log("mas puntos gastados que disponibles", LOG_LEVEL_VERBOSE)
                return True

            # Verificar prerequisitos de habilidades especiales
            if entity.skills[1] > 0 and entity.skills[0] < 5:
                self.log("maestro de mascotas sin prerequisitos", LOG_LEVEL_VERBOSE)
                return True

            if entity.skills[3] > 0 and entity.skills[2] < 5:
                self.log("planeo sin prerequisitos", LOG_LEVEL_VERBOSE)
                return True

            if entity.skills[5] > 0 and entity.skills[4] < 5:
                self.log("navegacion sin prerequisitos", LOG_LEVEL_VERBOSE)
                return True

            if entity.skills[7] > 0 and entity.skills[6] < 5:
                self.log("habilidad 2 sin prerequisitos", LOG_LEVEL_VERBOSE)
                return True

            if entity.skills[8] > 0 and entity.skills[7] < 5:
                self.log("habilidad 3 sin prerequisitos", LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando habilidades: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return False

    def has_illegal_mode(self):
        """Verifica si el modo o habilidad es ilegal"""
        try:
            entity = self.connection.entity
            mode = entity.current_mode

            if mode == 0:
                return False

            if not mode in ABILITIES:
                self.log("habilidad invalida: modo={}".format(mode), LOG_LEVEL_VERBOSE)
                return True

            ability = ABILITIES[mode]

            if 'class' in ability:
                if not entity.class_type in ability['class']:
                    self.log("habilidad no permitida para clase", LOG_LEVEL_VERBOSE)
                    return True

            if 'spec' in ability:
                if entity.specialization != ability['spec']:
                    self.log("habilidad no permitida para especializacion", LOG_LEVEL_VERBOSE)
                    return True

            if 'weapon' in ability:
                weap1 = entity.equipment[6].sub_type
                weap2 = entity.equipment[7].sub_type

                if entity.equipment[6].type == 0:
                    weap1 = -1
                if entity.equipment[7].type == 0:
                    weap2 = -1

                if (not weap1 in ability['weapon'] and not weap2 in ability['weapon']):
                    self.log("habilidad no permitida para arma", LOG_LEVEL_VERBOSE)
                    return True
        except Exception as e:
            self.log("Error verificando modo: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return False

    def use_ability(self, mode):
        """Verifica si se puede usar una habilidad (enfriamiento)"""
        try:
            ability = ABILITIES.get(mode, {})
            if 'cooldown' in ability:
                min_cd = ability['cooldown']
                last_used = self.ability_cooldown.get(mode, 0)

                current_cd = self.loop.time() - last_used
                if current_cd < min_cd - self.cooldown_margin:
                    self.cooldown_strikes += 1
                    if self.cooldown_strikes > self.max_cooldown_strikes:
                        self.log("habilidad usada antes de enfriamiento", LOG_LEVEL_VERBOSE)
                        return False
                else:
                    self.cooldown_strikes = 0

                self.ability_cooldown[mode] = self.loop.time()
        except Exception as e:
            self.log("Error verificando habilidad: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return True

    def has_illegal_class(self):
        """Verifica que la clase del personaje sea legal"""
        try:
            entity = self.connection.entity

            if not entity.class_type in LEGAL_CLASSES:
                self.log("clase invalida: {}".format(entity.class_type), LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando clase: {}".format(str(e)), LOG_LEVEL_VERBOSE)
        return False

    def has_illegal_level(self):
        """Verifica si el nivel del personaje es ilegal"""
        try:
            entity = self.connection.entity
            
            if entity.level < 0:
                self.log("nivel negativo: {}".format(entity.level), LOG_LEVEL_VERBOSE)
                return True
          
            if entity.level > self.level_cap:
                self.log("nivel superior al maximo: {} > {}".format(
                    entity.level, self.level_cap), LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando nivel: {}".format(str(e)), LOG_LEVEL_VERBOSE)
        return False

    def has_illegal_multiplier(self):
        """Verifica si los multiplicadores de atributos son ilegales"""
        try:
            entity = self.connection.entity

            if entity.max_hp_multiplier != 100:
                self.log("multiplicador vida invalido: {}".format(
                    entity.max_hp_multiplier), LOG_LEVEL_VERBOSE)
                return True

            if entity.shoot_speed != 1:
                self.log("multiplicador ataque invalido: {}".format(
                    entity.shoot_speed), LOG_LEVEL_VERBOSE)
                return True

            if entity.damage_multiplier != 1:
                self.log("multiplicador daño invalido: {}".format(
                    entity.damage_multiplier), LOG_LEVEL_VERBOSE)
                return True

            if entity.armor_multiplier != 1:
                self.log("multiplicador armadura invalido: {}".format(
                    entity.armor_multiplier), LOG_LEVEL_VERBOSE)
                return True

            if entity.resi_multiplier != 1:
                self.log("multiplicador resistencia invalido: {}".format(
                    entity.resi_multiplier), LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando multiplicadores: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return False

    def has_illegal_charged_mp(self):
        """Verifica si el mana cargado es ilegal"""
        try:
            entity = self.connection.entity

            if entity.charged_mp > 1:
                self.log("mana cargado superior a 1: {}".format(
                    entity.charged_mp), LOG_LEVEL_VERBOSE)
                return True

            if entity.class_type == 1:
                if entity.charged_mp < -2:
                    self.log("mana cargado inferior a -2: {}".format(
                        entity.charged_mp), LOG_LEVEL_VERBOSE)
                    return True
            else:
                if entity.charged_mp < 0:
                    self.log("mana cargado negativo: {}".format(
                        entity.charged_mp), LOG_LEVEL_VERBOSE)
                    return True
        except Exception as e:
            self.log("Error verificando mana: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return False

    def has_illegal_appearance(self):
        """Verifica si la apariencia del personaje es legal"""
        try:
            entity = self.connection.entity
            appearance = entity.appearance

            if appearance.flags != 0:
                self.log("banderas de apariencia invalidas", LOG_LEVEL_VERBOSE)
                return True

            if entity.entity_type not in APPEARANCES:
                self.log("tipo de entidad invalido: {}".format(
                    entity.entity_type), LOG_LEVEL_VERBOSE)
                return True

            app = APPEARANCES[entity.entity_type]
            
            # Verificar escala
            if not is_similar(appearance.scale.x, app['scale']):
                self.log("escala invalida", LOG_LEVEL_VERBOSE)
                return True

            if not is_similar(appearance.scale.y, app.get('radius', 0.96)):
                self.log("radio invalido", LOG_LEVEL_VERBOSE)
                return True

            if not is_similar(appearance.scale.z, app.get('height', 2.16)):
                self.log("altura invalida", LOG_LEVEL_VERBOSE)
                return True

            # Verificar modelos
            for model_attr, model_key in [
                ('head_model', 'model_head'),
                ('hair_model', 'model_hair'),
                ('hand_model', 'model_hand'),
                ('foot_model', 'model_feet'),
                ('body_model', 'model_body'),
                ('tail_model', 'model_back'),
                ('shoulder2_model', 'model_shoulder'),
                ('wing_model', 'model_wing')
            ]:
                try:
                    model_value = getattr(appearance, model_attr)
                    if model_value not in app.get(model_key, []):
                        self.log("modelo invalido: {}".format(model_attr), LOG_LEVEL_VERBOSE)
                        return True
                except:
                    pass

            # Verificar escalas de modelos
            scale_checks = [
                ('head_scale', 'scale_head'),
                ('hand_scale', 'scale_hand'),
                ('body_scale', 'scale_body'),
                ('foot_scale', 'scale_feet'),
                ('shoulder2_scale', 'scale_shoulder'),
                ('weapon_scale', 'scale_weapon'),
                ('tail_scale', 'scale_back'),
                ('wing_scale', 'scale_wing'),
                ('shoulder_scale', 'scale_unknown')
            ]
            
            for scale_attr, scale_key in scale_checks:
                try:
                    scale_value = getattr(appearance, scale_attr)
                    if not is_similar(scale_value, app.get(scale_key, 1.0)):
                        self.log("escala de modelo invalida: {}".format(scale_attr), LOG_LEVEL_VERBOSE)
                        return True
                except:
                    pass

            # Verificar rotaciones
            rotation_checks = [
                ('body_pitch', 0),
                ('arm_pitch', 0),
                ('arm_roll', 0),
                ('arm_yaw', 0),
                ('feet_pitch', 0),
                ('wing_pitch', 0),
                ('back_pitch', 0)
            ]
            
            for rot_attr, rot_val in rotation_checks:
                try:
                    if getattr(appearance, rot_attr) != rot_val:
                        self.log("rotacion invalida: {}".format(rot_attr), LOG_LEVEL_VERBOSE)
                        return True
                except:
                    pass

        except Exception as e:
            self.log("Error verificando apariencia: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return False

    def has_illegal_flags(self):
        """Verifica si hay banderas ilegales de personaje"""
        try:
            entity = self.connection.entity
            flags = entity.flags

            # Sigilo solo para guardabosque
            if flags & STEALTH_FLAG and entity.class_type != RANGER_CLASS:
                self.log("clase no guardabosque usando sigilo", LOG_LEVEL_VERBOSE)
                return True

            # Contador de ataque/planeo para detectar abuso
            if flags & ATTACKING_FLAG:
                self.last_attacking = self.loop.time()
                self.attack_count += 1

            if flags & GLIDER_FLAG:
                self.last_glider_active = self.loop.time()
                self.glider_count += 1

            # Reiniciar si no ha atacado ni planeado en 0.75s
            if (self.loop.time() - self.last_glider_active > 0.75 or
                    self.loop.time() - self.last_attacking > 0.75):
                self.glider_count = 0
                self.attack_count = 0

            # Detectar abuso de planeo/ataque
            if (self.glider_count > self.glider_abuse_count and
                    self.attack_count > self.glider_abuse_count):
                self.log("abuso de planeo detectado", LOG_LEVEL_VERBOSE)
                return True
        except Exception as e:
            self.log("Error verificando banderas: {}".format(str(e)), LOG_LEVEL_VERBOSE)

        return False

    def check_flying(self):
        """Verifica si el jugador esta volando sin permiso"""
        try:
            entity = self.connection.entity
            flags = entity.flags
            
            # En aire cuando: no planeo, no en tierra, no nadando, no escalando
            if not (flags & GLIDER_FLAG
                    or is_bit_set(entity.physics_flags, 0)
                    or is_bit_set(entity.physics_flags, 1)
                    or is_bit_set(entity.physics_flags, 2)
                    or entity.hp <= 0):
                self.air_time += self.time_since_update

                if self.air_time > self.max_air_time:
                    self.remove_cheater('truco de vuelo')
                    return False
            else:
                self.air_time = 0
        except Exception as e:
            self.log("Error verificando vuelo: {}".format(str(e)), LOG_LEVEL_VERBOSE)
        
        return True

    def check_hit_counter(self):
        """Verifica que el contador de golpes sea consistente"""
        try:
            entity = self.connection.entity

            if entity.hit_counter < 0:
                self.log("contador de golpes negativo", LOG_LEVEL_VERBOSE)
                self.remove_cheater('contador de golpes ilegal')
                return False

            if self.loop.time() - self.last_hit_time > 4 + self.last_hit_margin:
                self.hit_counter = 0

            hit_counter_diff = entity.hit_counter - self.hit_counter
            if hit_counter_diff > self.max_hit_counter_difference:
                self.hit_counter_strikes += 1
                if self.hit_counter_strikes > self.max_hit_counter_strikes:
                    self.log("desajuste de contador de golpes", LOG_LEVEL_VERBOSE)
                    self.remove_cheater('contador de golpes ilegal')
                    return False
            else:
                self.hit_counter_strikes = 0
        except Exception as e:
            self.log("Error verificando contador: {}".format(str(e)), LOG_LEVEL_VERBOSE)
        
        return True

    def check_hostile_type(self):
        """Verifica que el tipo hostil sea correcto"""
        try:
            entity = self.connection.entity
            if entity.hostile_type != 0:
                self.log("tipo hostil invalido: {}".format(entity.hostile_type), LOG_LEVEL_VERBOSE)
                self.remove_cheater('tipo hostil ilegal')
                return False
        except Exception as e:
            self.log("Error verificando tipo hostil: {}".format(str(e)), LOG_LEVEL_VERBOSE)
        
        return True

    def check_last_hit(self):
        """Verifica que el ultimo golpe sea consistente con el tiempo"""
        try:
            entity = self.connection.entity
            if entity.hp <= 0:
                return True

            last_hit_rc = (float(entity.last_hit_time) / 1000.0)
            if self.last_hit_time == 0:
                self.last_hit_time = self.loop.time() - last_hit_rc
            last_hit_pk = self.loop.time() - self.last_hit_time

            time_diff = last_hit_pk - last_hit_rc
            if abs(time_diff) > self.last_hit_margin:
                self.last_hit_strikes += 1
                if self.last_hit_strikes > self.max_last_hit_strikes:
                    self.log("desajuste de tiempo ultimo golpe", LOG_LEVEL_VERBOSE)
                    self.remove_cheater('desajuste de tiempo ultimo golpe')
                    return False

                # Recuperacion permitida cada 15 segundos
                if (self.loop.time() - self.last_hit_time_catchup > 15.0):
                    self.last_hit_time_catchup = self.loop.time()
                    self.last_hit_time_catchup_count = 0

                if (self.last_hit_time_catchup_count < self.max_last_hit_time_catchup):
                    self.last_hit_time_catchup_count += 1
                    self.last_hit_strikes -= 1
                    self.last_hit_time = self.loop.time() - last_hit_rc
            else:
                self.last_hit_strikes = 0

            return self.check_hit_counter()
        except Exception as e:
            self.log("Error verificando ultimo golpe: {}".format(str(e)), LOG_LEVEL_VERBOSE)
            return True


class AntiCheatServer(ServerScript):
    """Script servidor para el antitrampa"""
    connection_class = AntiCheatConnection


def get_class():
    """Retorna la clase del script del servidor"""
    return AntiCheatServer
