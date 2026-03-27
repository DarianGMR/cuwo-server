#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Interface Script for cuwo
Sirve la interfaz web con soporte para administración
"""

import os
import webbrowser
import threading
import json
import time
import logging
import sys
import traceback
import io
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from cuwo.script import ServerScript, ConnectionScript, ScriptInterface
from contextlib import redirect_stdout, redirect_stderr

SITE_PATH = 'web'
PLAYTIME_DATA_NAME = 'web_playtimes'
MAX_LOG_LINES = 500
LOG_FILE = 'logs/console.log'
SESSION_MARKER = "=" * 80

# Crear carpeta de logs si no existe
os.makedirs('logs', exist_ok=True)

# Configurar logging global
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    handlers=[
        logging.FileHandler('logs/web.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class WebLogCapture(logging.StreamHandler):
    """Capturar todos los logs incluyendo print()"""
    def __init__(self, web_server):
        super().__init__()
        self.web_server = web_server
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.web_server.add_log_line(msg)
        except Exception:
            self.handleError(record)


class WebConnectionScript(ConnectionScript):
    """Script para trackear tiempo de conexión de jugadores"""
    
    def on_join(self, event):
        """Se ejecuta cuando un jugador entra al servidor"""
        self.connection.web_join_time = time.time()
    
    def on_unload(self):
        """Guardar tiempo de juego cuando el jugador se desconecta"""
        try:
            if hasattr(self.connection, 'web_join_time') and self.connection.name:
                playtime_data = self.server.load_data(PLAYTIME_DATA_NAME, {})
                player_name = self.connection.name.lower()
                
                # Calcular tiempo de juego en segundos
                playtime_seconds = int(time.time() - self.connection.web_join_time)
                
                # Si el jugador ya tenía tiempo registrado, sumarle
                if player_name in playtime_data:
                    playtime_data[player_name] += playtime_seconds
                else:
                    playtime_data[player_name] = playtime_seconds
                
                self.server.save_data(PLAYTIME_DATA_NAME, playtime_data)
        except Exception as e:
            logger.error(f"Error guardando tiempo de juego: {e}\n{traceback.format_exc()}")


class SiteHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Handler para servir archivos desde la carpeta web"""
    
    def translate_path(self, path):
        """Servir desde la carpeta web en lugar de la raiz"""
        translated = super().translate_path(path)
        relpath = os.path.relpath(translated, os.getcwd())
        return os.path.join(os.getcwd(), SITE_PATH, relpath)
    
    def log_message(self, format, *args):
        """Suprimir logs de peticiones HTTP"""
        pass
    
    def end_headers(self):
        """Agregar headers CORS"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def do_GET(self):
        """Manejar peticiones GET"""
        if self.path == '/api/players':
            self.handle_players_api()
            return
        elif self.path == '/api/chat':
            self.handle_chat_api()
            return
        elif self.path == '/api/server':
            self.handle_server_api()
            return
        elif self.path == '/api/bans':
            self.handle_bans_api()
            return
        elif self.path == '/api/logs':
            self.handle_logs_api()
            return
        super().do_GET()
    
    def do_POST(self):
        """Manejar peticiones POST"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
        except:
            self.send_error(400, "Invalid JSON")
            return
        
        if self.path == '/api/command':
            self.handle_command(data)
        elif self.path == '/api/chat':
            self.handle_chat_post(data)
        else:
            self.send_error(404, "Not Found")
    
    def handle_logs_api(self):
        """Devolver logs de la sesión actual"""
        logs = self.server.web_server.get_current_session_logs()
        response_data = {
            'response': 'logs',
            'logs': logs
        }
        
        response = json.dumps(response_data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def handle_players_api(self):
        """Devolver lista de jugadores en JSON"""
        server = self.server.web_server.server
        players_list = []
        current_time = time.time()
        
        # Cargar datos de playtime persistentes
        playtime_data = server.load_data(PLAYTIME_DATA_NAME, {})
        
        try:
            for connection in list(server.players.values()):
                try:
                    if not hasattr(connection, 'entity') or connection.entity is None:
                        continue
                    
                    if not hasattr(connection, 'name') or not connection.name:
                        continue
                    
                    entity = connection.entity
                    
                    # Usar ID simple basado en la conexión
                    player_id = id(connection) % 10000
                    
                    # Calcular tiempo de juego en minutos
                    playtime_minutes = 0
                    if hasattr(connection, 'web_join_time'):
                        session_playtime = int((current_time - connection.web_join_time) / 60)
                        player_name_lower = connection.name.lower()
                        previous_playtime = int(playtime_data.get(player_name_lower, 0) / 60)
                        playtime_minutes = session_playtime + previous_playtime
                    
                    player_data = {
                        'id': player_id,
                        'name': str(connection.name) if connection.name else 'Unknown',
                        'ip': connection.address[0],
                        'level': int(entity.level) if hasattr(entity, 'level') else 0,
                        'klass': int(entity.class_type) if hasattr(entity, 'class_type') else 0,
                        'specialz': int(entity.specialization) if hasattr(entity, 'specialization') else 0,
                        'hp': int(entity.hp) if hasattr(entity, 'hp') else 0,
                        'max_hp': int(entity.max_hp) if hasattr(entity, 'max_hp') else 100,
                        'x': int(entity.x) if hasattr(entity, 'x') else 0,
                        'y': int(entity.y) if hasattr(entity, 'y') else 0,
                        'z': int(entity.z) if hasattr(entity, 'z') else 0,
                        'playtime_minutes': playtime_minutes
                    }
                    players_list.append(player_data)
                    
                except (AttributeError, TypeError, ValueError) as e:
                    continue
                    
        except Exception as e:
            pass
        
        response_data = {
            'response': 'get_players',
            'players': players_list,
            'count': len(players_list)
        }
        
        response = json.dumps(response_data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def handle_bans_api(self):
        """Devolver lista de IPs baneadas con nombre y razón"""
        server = self.server.web_server.server
        
        try:
            ban_script = None
            for item in server.scripts.items.values():
                if hasattr(item, 'banned_ips'):
                    ban_script = item
                    break
            
            if ban_script and hasattr(ban_script, 'banned_ips'):
                bans_list = []
                for ip, ban_data in ban_script.banned_ips.items():
                    if isinstance(ban_data, dict):
                        bans_list.append({
                            'ip': ip,
                            'name': ban_data.get('name', 'Desconocido'),
                            'reason': ban_data.get('reason', 'Sin razón')
                        })
                    else:
                        bans_list.append({
                            'ip': ip,
                            'name': 'Desconocido',
                            'reason': ban_data or 'Sin razón'
                        })
                
                response_data = {
                    'response': 'ban_list',
                    'bans': bans_list,
                    'count': len(bans_list)
                }
            else:
                response_data = {
                    'response': 'ban_list',
                    'bans': [],
                    'count': 0
                }
        except Exception as e:
            response_data = {
                'response': 'ban_list',
                'bans': [],
                'count': 0
            }
        
        response = json.dumps(response_data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def handle_server_api(self):
        """Devolver información del servidor"""
        server = self.server.web_server.server
        
        try:
            server_data = {
                'response': 'server_info',
                'name': 'Cuwo Server',
                'port': 12345,
                'players_online': len(server.players),
                'max_players': 100,
                'uptime': int(time.time() - self.server.web_server.start_time)
            }
        except Exception as e:
            server_data = {
                'response': 'server_info',
                'name': 'Cuwo Server',
                'port': 12345,
                'players_online': 0,
                'max_players': 100,
                'uptime': 0
            }
        
        response = json.dumps(server_data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def handle_chat_api(self):
        """Devolver historial de chat"""
        chat_history = getattr(self.server.web_server, 'chat_history', [])
        response = json.dumps({'response': 'chat_history', 'messages': chat_history})
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def find_player_by_id(self, server, player_id):
        """Encontrar un jugador por su ID"""
        try:
            for connection in list(server.players.values()):
                if id(connection) % 10000 == player_id:
                    return connection
        except Exception as e:
            pass
        
        return None
    
    def handle_command(self, data):
        """Procesar comandos desde la web"""
        server = self.server.web_server.server
        auth_key = self.server.web_server.auth_key
        
        if data.get('key') != auth_key:
            self.send_error(401, "Unauthorized")
            return
        
        request = data.get('request')
        response_msg = {"response": "Success", "success": False, "error": None, "output": ""}
        
        try:
            if request == 'send_message':
                message = data.get('message', '')
                if message:
                    formatted_msg = f"cuwo: {message}"
                    server.send_chat(formatted_msg)
                    chat_history = getattr(self.server.web_server, 'chat_history', [])
                    chat_history.append({'id': 0, 'name': 'Server', 'message': formatted_msg})
                    if len(chat_history) > 100:
                        chat_history.pop(0)
                    response_msg["success"] = True
                    
            elif request == 'execute_command':
                command = data.get('command', '').strip()
                if command:
                    parts = command.split()
                    cmd_name = parts[0].lower()
                    cmd_args = parts[1:] if len(parts) > 1 else []
                    
                    try:
                        # Validar que el comando existe
                        script_interface = ScriptInterface('Web', server, 'admin', 'web')
                        cmd_obj = script_interface.get_command(cmd_name)
                        
                        if cmd_obj is None:
                            response_msg["success"] = False
                            response_msg["error"] = f"Comando inválido: '{cmd_name}' no existe"
                            self.server.web_server.add_log_line(f"> {command}")
                            self.server.web_server.add_log_line(f"ERROR: Comando inválido: '{cmd_name}' no existe")
                        else:
                            # Capturar stdout/stderr
                            output_buffer = io.StringIO()
                            error_occurred = False
                            
                            try:
                                with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                                    # Ejecutar comando
                                    result = server.call_command(script_interface, cmd_name, cmd_args)
                                
                                # Obtener output capturado
                                captured_output = output_buffer.getvalue().strip()
                                
                                if result is not None:
                                    response_msg["success"] = True
                                    response_msg["output"] = str(result)
                                    self.server.web_server.add_log_line(f"> {command}")
                                    self.server.web_server.add_log_line(str(result))
                                elif captured_output:
                                    response_msg["success"] = True
                                    response_msg["output"] = captured_output
                                    self.server.web_server.add_log_line(f"> {command}")
                                    self.server.web_server.add_log_line(captured_output)
                                else:
                                    response_msg["success"] = True
                                    response_msg["output"] = ""
                                    self.server.web_server.add_log_line(f"> {command}")
                                    
                            except Exception as cmd_error:
                                error_occurred = True
                                error_msg = str(cmd_error)
                                error_trace = traceback.format_exc()
                                
                                response_msg["success"] = False
                                response_msg["error"] = f"Error al ejecutar comando: {error_msg}\n\nTraceback:\n{error_trace}"
                                
                                self.server.web_server.add_log_line(f"> {command}")
                                self.server.web_server.add_log_line(f"ERROR: {error_msg}")
                                self.server.web_server.add_log_line(f"Traceback completo:\n{error_trace}")
                        
                    except Exception as e:
                        error_msg = str(e)
                        error_trace = traceback.format_exc()
                        
                        response_msg["success"] = False
                        response_msg["error"] = f"Error al ejecutar comando: {error_msg}\n\nTraceback:\n{error_trace}"
                        
                        self.server.web_server.add_log_line(f"> {command}")
                        self.server.web_server.add_log_line(f"ERROR: {error_msg}")
                        self.server.web_server.add_log_line(f"Traceback completo:\n{error_trace}")
                    
            elif request == 'heal_player':
                player_id = data.get('player_id')
                if player_id is not None:
                    connection = self.find_player_by_id(server, player_id)
                    if connection:
                        try:
                            if hasattr(connection, 'entity') and connection.entity:
                                entity = connection.entity
                                if hasattr(entity, 'damage'):
                                    entity.damage(-1000)
                                    response_msg["success"] = True
                                    msg = f"{connection.name} fue sanado"
                                    self.server.web_server.add_log_line(f"[HEAL] {msg}")
                                    server.send_chat(msg)
                                else:
                                    response_msg["error"] = "Entidad sin método damage()"
                            else:
                                response_msg["error"] = "Conexión sin entidad"
                        except Exception as e:
                            response_msg["error"] = str(e)
                    else:
                        response_msg["error"] = f"Jugador con ID {player_id} no encontrado"
                    
            elif request == 'kick_player':
                player_id = data.get('player_id')
                reason = data.get('reason', 'Sin especificar')
                if player_id is not None:
                    connection = self.find_player_by_id(server, player_id)
                    if connection:
                        try:
                            connection.kick(reason)
                            response_msg["success"] = True
                            self.server.web_server.add_log_line(f"[KICK] Jugador {connection.name} expulsado. Razón: {reason}")
                        except Exception as e:
                            response_msg["error"] = str(e)
                    else:
                        response_msg["error"] = f"Jugador con ID {player_id} no encontrado"
                    
            elif request == 'ban_player':
                player_id = data.get('player_id')
                reason = data.get('reason', 'Sin especificar')
                
                if player_id is not None:
                    connection = self.find_player_by_id(server, player_id)
                    if connection:
                        try:
                            player_name = connection.name
                            player_ip = connection.address[0]
                            
                            ban_script = None
                            for item in server.scripts.items.values():
                                if hasattr(item, 'ban_ip'):
                                    ban_script = item
                                    break
                            
                            if ban_script:
                                ban_script.ban_ip(player_ip, reason, player_name)
                                response_msg["success"] = True
                                self.server.web_server.add_log_line(f"[BAN] Jugador {player_name} baneado por IP {player_ip}. Razón: {reason}")
                                server.send_chat(f"IP {player_ip} ha sido baneada")
                            else:
                                response_msg["error"] = "Script de ban no encontrado"
                                    
                        except Exception as e:
                            response_msg["error"] = str(e)
                    else:
                        response_msg["error"] = f"Jugador con ID {player_id} no encontrado"
                else:
                    response_msg["error"] = "ID de jugador no proporcionado"

            elif request == 'unban_ip':
                ip = data.get('ip')
                
                if ip:
                    try:
                        ban_script = None
                        for item in server.scripts.items.values():
                            if hasattr(item, 'unban_ip'):
                                ban_script = item
                                break
                        
                        if ban_script:
                            if ban_script.unban_ip(ip):
                                response_msg["success"] = True
                                self.server.web_server.add_log_line(f"[UNBAN] IP {ip} desbaneada")
                                server.send_chat(f"IP {ip} ha sido desbaneada")
                            else:
                                response_msg["error"] = f"IP {ip} no encontrada en lista de baneados"
                        else:
                            response_msg["error"] = "Script de ban no encontrado"
                            
                    except Exception as e:
                        response_msg["error"] = str(e)
                else:
                    response_msg["error"] = "IP no proporcionada"
                    
            elif request == 'clear_log':
                self.server.web_server.clear_all_logs()
                response_msg["success"] = True
                
        except Exception as e:
            response_msg["error"] = f"Error procesando comando: {str(e)}\n{traceback.format_exc()}"
        
        response = json.dumps(response_msg)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def handle_chat_post(self, data):
        """Manejar mensajes de chat"""
        self.handle_command(data)


class WebServer(ServerScript):
    """Script del servidor web para cuwo"""
    
    connection_class = WebConnectionScript
    
    def on_load(self):
        """Se ejecuta cuando se carga el script"""
        try:
            self.start_time = time.time()
            self.session_start_time = datetime.now()
            self.current_session_logs = []
            
            config = self.server.config.web
            
            web_port = config.port
            web_host = config.host
            auto_open = config.auto_open
            self.auth_key = config.auth_key
            self.chat_history = []
            
            if not os.path.exists(SITE_PATH):
                logger.error(f"Carpeta '{SITE_PATH}' no encontrada")
                return
            
            self._update_init_js(web_port, self.auth_key)
            
            # Escribir marcador de nueva sesión en archivo
            self._write_session_marker()
            
            handler = SiteHTTPRequestHandler
            self.http_server = HTTPServer((web_host, web_port), handler)
            self.http_server.web_server = self
            
            # Agregar handler para capturar logs
            web_log_capture = WebLogCapture(self)
            logger.addHandler(web_log_capture)
            
            def run_web_server():
                try:
                    self.http_server.serve_forever()
                except Exception as e:
                    logger.error(f"Error en servidor web: {e}\n{traceback.format_exc()}")
            
            web_thread = threading.Thread(target=run_web_server, daemon=True)
            web_thread.start()
            
            if auto_open:
                self.loop.call_later(1, lambda: self._open_browser(web_host, web_port))
        
        except Exception as e:
            logger.error(f"Error inicializando servidor web: {e}\n{traceback.format_exc()}")
    
    def _write_session_marker(self):
        """Escribir marcador de sesión en archivo"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            marker = f"\n{SESSION_MARKER}\nSESIÓN INICIADA: {timestamp}\n{SESSION_MARKER}\n"
            
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(marker)
        except Exception as e:
            logger.error(f"Error escribiendo marcador de sesión: {e}")
    
    def add_log_line(self, line):
        """Agregar línea de log con fecha/hora al archivo y sesión actual"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {line}"
            
            # Agregar a sesión actual (sin timestamp para mostrar en web)
            self.current_session_logs.append(line)
            if len(self.current_session_logs) > MAX_LOG_LINES:
                self.current_session_logs.pop(0)
            
            # Escribir en archivo (con timestamp para persistencia)
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            logger.error(f"Error escribiendo log: {e}")
    
    def get_current_session_logs(self):
        """Obtener logs solo de la sesión actual"""
        return list(self.current_session_logs)
    
    def clear_current_session_logs(self):
        """Limpiar logs de sesión actual (pero mantener archivo)"""
        self.current_session_logs = []

    def clear_all_logs(self):
        """Limpiar archivo de logs completamente"""
        try:
            # Vaciar archivo completamente
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write('')
            # Limpiar sesión actual también
            self.current_session_logs = []
        except Exception as e:
            logger.error(f"Error limpiando logs: {e}")
    
    def _update_init_js(self, port, auth_key):
        """Actualizar archivo init.js"""
        try:
            js_path = os.path.join(SITE_PATH, 'js', 'init.js')
            content = f'var server_port = "{port}";\nvar auth_key = "{auth_key}";\n'
            with open(js_path, 'w') as f:
                f.write(content)
        except Exception as e:
            logger.warning(f"No se pudo actualizar init.js: {e}\n{traceback.format_exc()}")
    
    def _open_browser(self, host, port):
        """Abrir navegador"""
        try:
            url = f"http://{host}:{port}"
            logger.info(f"Abriendo navegador en {url}")
            webbrowser.open(url)
        except Exception as e:
            logger.warning(f"No se pudo abrir navegador: {e}\n{traceback.format_exc()}")
    
    def on_unload(self):
        """Se ejecuta cuando se descarga el script"""
        try:
            if hasattr(self, 'http_server'):
                self.http_server.shutdown()
        except Exception as e:
            logger.error(f"Error deteniendo servidor web: {e}\n{traceback.format_exc()}")


def get_class():
    return WebServer
