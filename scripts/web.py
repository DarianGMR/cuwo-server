#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Interface Script for cuwo
Sirve la interfaz web con soporte para administracion
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
from io import StringIO
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from cuwo.script import ServerScript, ConnectionScript, ScriptInterface
from contextlib import redirect_stdout, redirect_stderr

SITE_PATH = 'web'
PLAYTIME_DATA_NAME = 'web_playtimes'
MAX_LOG_LINES = 500
LOG_FILE = 'logs/console.log'
CHAT_LOG_FILE = 'logs/chat.log'
SESSION_MARKER = "=" * 80

# Variable global para acceder a la instancia del WebServer
_web_server_instance = None

# Variable para controlar si estamos ejecutando comandos desde la web
_executing_from_web = False

# Crear carpeta de logs si no existe
os.makedirs('logs', exist_ok=True)

# Configurar logging global
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    handlers=[
        logging.FileHandler('logs/web.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Lista de palabras clave que NO deben aparecer en la consola web (solo son logs de inicio)
STARTUP_LOG_KEYWORDS = [
    'Script activado',
    'cuwo funcionando en el puerto',
    'Abriendo navegador en',
    '(using uvloop)'
]

# Palabras clave que indican que es un mensaje de jugador
PLAYER_MESSAGE_KEYWORDS = [
    'PM):',  # Mensajes privados
    'fue asesinado',
    'fue sanado',
    'fue aturdido',
    'expulsado',
    'fue baneado',
    'baneada',
    'desbaneada',
    'ha sido baneado'
]


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


class ErrorCapture(logging.Handler):
    """Capturar errores de logging y mostrarlos con traceback"""
    def __init__(self, web_server):
        super().__init__()
        self.web_server = web_server
        self.setLevel(logging.ERROR)
    
    def emit(self, record):
        try:
            if record.exc_info:
                exc_type, exc_value, exc_traceback = record.exc_info
                full_traceback = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.web_server.add_error_line(full_traceback)
            else:
                msg = self.format(record)
                self.web_server.add_error_line(msg)
        except Exception:
            self.handleError(record)


class WebConnectionScript(ConnectionScript):
    """Script para trackear tiempo de conexion de jugadores"""
    
    def on_join(self, event):
        """Se ejecuta cuando un jugador entra al servidor"""
        self.connection.web_join_time = time.time()
    
    def on_unload(self):
        """Guardar tiempo de juego cuando el jugador se desconecta"""
        try:
            if hasattr(self.connection, 'web_join_time') and self.connection.name:
                playtime_data = self.server.load_data(PLAYTIME_DATA_NAME, {})
                player_name = self.connection.name.lower()
                
                playtime_seconds = int(time.time() - self.connection.web_join_time)
                
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
        elif self.path == '/api/chat-status':
            self.handle_chat_status_api()
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
    
    def handle_chat_status_api(self):
        """Devolver estado del chat"""
        global _web_server_instance
        
        status = "funcionando correctamente"
        if _web_server_instance is None:
            status = "no funcionando correctamente"
        
        response_data = {
            'response': 'chat_status',
            'status': status
        }
        
        response = json.dumps(response_data, ensure_ascii=False)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(response.encode('utf-8')))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def handle_logs_api(self):
        """Devolver logs recientes desde archivo"""
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
        
        playtime_data = server.load_data(PLAYTIME_DATA_NAME, {})
        
        try:
            for connection in list(server.players.values()):
                try:
                    if not hasattr(connection, 'entity') or connection.entity is None:
                        continue
                    
                    if not hasattr(connection, 'name') or not connection.name:
                        continue
                    
                    entity = connection.entity
                    player_id = id(connection) % 10000
                    
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
        """Devolver lista de IPs baneadas con nombre, razon y quien banea"""
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
                            'reason': ban_data.get('reason', 'Sin razon'),
                            'banned_by': ban_data.get('banned_by', 'administrador')
                        })
                    else:
                        bans_list.append({
                            'ip': ip,
                            'name': 'Desconocido',
                            'reason': ban_data or 'Sin razon',
                            'banned_by': 'administrador'
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
        """Devolver informacion del servidor"""
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
        """Devolver historial completo de chat desde archivo de la sesion actual"""
        global _web_server_instance
        
        chat_history = []
        if _web_server_instance is not None:
            chat_history = _web_server_instance.load_chat_history()
        
        response_data = {
            'response': 'chat_history',
            'messages': chat_history,
            'count': len(chat_history)
        }
        
        response = json.dumps(response_data, ensure_ascii=False)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(response.encode('utf-8')))
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
        global _executing_from_web
        
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
                    global _web_server_instance
                    if _web_server_instance is not None:
                        _web_server_instance.add_chat_message('cuwo', message)
                    response_msg["success"] = True
                    
            elif request == 'execute_command':
                command = data.get('command', '').strip()
                if command:
                    parts = command.split()
                    cmd_name = parts[0].lower()
                    cmd_args = parts[1:] if len(parts) > 1 else []
                    
                    try:
                        script_interface = ScriptInterface('Web', server, 'admin', 'web')
                        cmd_obj = script_interface.get_command(cmd_name)
                        
                        if cmd_obj is None:
                            error_msg = f"Comando invalido: '{cmd_name}' no existe"
                            response_msg["success"] = False
                            response_msg["error"] = error_msg
                            self.server.web_server.add_log_line(f"> {command}")
                            self.server.web_server.add_log_line(error_msg)
                        else:
                            output_buffer = io.StringIO()
                            error_buffer = io.StringIO()
                            
                            try:
                                _executing_from_web = True
                                with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                                    result = server.call_command(script_interface, cmd_name, cmd_args)
                                _executing_from_web = False
                                
                                captured_output = output_buffer.getvalue().strip()
                                captured_error = error_buffer.getvalue().strip()
                                
                                # Si capturamos error de stderr
                                if captured_error:
                                    response_msg["success"] = False
                                    response_msg["error"] = captured_error
                                    self.server.web_server.add_log_line(f"> {command}")
                                    self.server.web_server.add_log_line(captured_error)
                                # Si el resultado contiene error (incluyendo Traceback)
                                elif result is not None and str(result).strip():
                                    result_str = str(result).strip()
                                    
                                    # Detectar si es un Traceback (error completo de Python)
                                    if 'Traceback' in result_str:
                                        # Es un traceback - enviarlo directamente a add_error_line para que se trate como bloque único
                                        response_msg["success"] = False
                                        response_msg["error"] = result_str
                                        self.server.web_server.add_log_line(f"> {command}")
                                        self.server.web_server.add_error_line(result_str)
                                    else:
                                        # Verificar si contiene otras palabras clave de error
                                        error_keywords = [
                                            "Error:",
                                            "error",
                                            "Jugador invalido",
                                            "No existe",
                                            "no encontrado",
                                            "AttributeError",
                                            "TypeError",
                                            "ValueError",
                                            "KeyError",
                                            "Exception",
                                            "failed",
                                            "invalid",
                                        ]
                                        
                                        is_error = any(keyword.lower() in result_str.lower() for keyword in error_keywords)
                                        
                                        if is_error:
                                            response_msg["success"] = False
                                            response_msg["error"] = result_str
                                            self.server.web_server.add_log_line(f"> {command}")
                                            self.server.web_server.add_log_line(result_str)
                                        else:
                                            response_msg["success"] = True
                                            response_msg["output"] = result_str
                                            self.server.web_server.add_log_line(f"> {command}")
                                            self.server.web_server.add_log_line(result_str)
                                # Si no hay salida
                                elif captured_output:
                                    response_msg["success"] = True
                                    response_msg["output"] = captured_output
                                    self.server.web_server.add_log_line(f"> {command}")
                                    self.server.web_server.add_log_line(captured_output)
                                else:
                                    response_msg["success"] = True
                                    response_msg["output"] = f"Comando '{cmd_name}' ejecutado correctamente"
                                    self.server.web_server.add_log_line(f"> {command}")
                                    self.server.web_server.add_log_line(f"Comando '{cmd_name}' ejecutado correctamente")
                                        
                            except Exception as cmd_error:
                                _executing_from_web = False
                                error_trace = traceback.format_exc()
                                
                                response_msg["success"] = False
                                response_msg["error"] = error_trace
                                
                                self.server.web_server.add_log_line(f"> {command}")
                                # Usar add_error_line para que sea un bloque único con símbolo ✗
                                self.server.web_server.add_error_line(error_trace)
                        
                    except Exception as e:
                        error_trace = traceback.format_exc()
                        
                        response_msg["success"] = False
                        response_msg["error"] = error_trace
                        
                        self.server.web_server.add_log_line(f"> {command}")
                        # Usar add_error_line para que sea un bloque único con símbolo ✗
                        self.server.web_server.add_error_line(error_trace)
                
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
                                    self.server.web_server.add_log_line(msg)
                                    server.send_chat(msg)
                                else:
                                    response_msg["error"] = "Entidad sin metodo damage()"
                            else:
                                response_msg["error"] = "Conexion sin entidad"
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
                            self.server.web_server.add_log_line(f"Jugador {connection.name} expulsado. Razon: {reason}")
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
                                ban_script.ban_ip(player_ip, reason, player_name, ban_by='administrador', send_message=True)
                                response_msg["success"] = True
                                self.server.web_server.add_log_line(f"Jugador {player_name} baneado por IP {player_ip}. Razon: {reason}")
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
                                self.server.web_server.add_log_line(f"IP {ip} desbaneada")
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
    
    def __init__(self, server):
        """Inicializar el script y guardar la referencia global"""
        super().__init__(server)
        global _web_server_instance
        _web_server_instance = self
    
    def on_load(self):
        """Se ejecuta cuando se carga el script"""
        try:
            self.start_time = time.time()
            self.session_start_time = datetime.now()
            self.current_session_logs = []
            self.session_start_marker = None
            
            config = self.server.config.web
            
            web_port = config.port
            web_host = config.host
            auto_open = config.auto_open
            self.auth_key = config.auth_key
            
            # Escribir marcador de sesion de chat
            self.session_start_marker = self._write_chat_session_marker()
            
            # Parchar el sistema de chat Y logging
            self._patch_chat_system()
            
            if not os.path.exists(SITE_PATH):
                logger.error(f"Carpeta '{SITE_PATH}' no encontrada")
                return
            
            self._update_init_js(web_port, self.auth_key)
            
            handler = SiteHTTPRequestHandler
            self.http_server = HTTPServer((web_host, web_port), handler)
            self.http_server.web_server = self
            
            web_log_capture = WebLogCapture(self)
            logger.addHandler(web_log_capture)
            
            error_capture = ErrorCapture(self)
            logging.getLogger().addHandler(error_capture)
            
            def run_web_server():
                try:
                    self.http_server.serve_forever()
                except Exception as e:
                    logger.error(f"Error en servidor web: {e}\n{traceback.format_exc()}")
            
            web_thread = threading.Thread(target=run_web_server, daemon=True)
            web_thread.start()
            
            self._write_session_marker()
            
            if auto_open:
                self.loop.call_later(1, lambda: self._open_browser(web_host, web_port))
        
        except Exception as e:
            logger.error(f"Error inicializando servidor web: {e}\n{traceback.format_exc()}")
    
    def _patch_chat_system(self):
        """Reemplazar print() con una version que guarde en chat.log y consola.log"""
        import builtins
        
        original_print = builtins.print
        web_server = self
        
        def patched_print(*args, **kwargs):
            """Print parcheado que captura mensajes de chat y consola"""
            global _executing_from_web
            
            # Convertir args a string
            if args:
                message_str = ' '.join(str(arg) for arg in args)
            else:
                message_str = ''
            
            # Llamar al print original
            original_print(*args, **kwargs)
            
            # Filtrar logs de inicio que no deben aparecer en la consola web
            should_skip_console = any(keyword in message_str for keyword in STARTUP_LOG_KEYWORDS)
            
            # Filtrar mensajes de jugadores que no deben aparecer en consola
            is_player_message = ':' in message_str and not any(keyword in message_str for keyword in PLAYER_MESSAGE_KEYWORDS)
            
            # NO agregar a consola web si está activa la ejecución de comandos desde web (para evitar duplicados)
            if _executing_from_web:
                should_skip_console = True
            
            # Agregar a consola web SOLO si no es un log de inicio ni es un mensaje de jugador puro
            if not should_skip_console and not is_player_message:
                web_server.add_log_line(message_str)
            
            # Intentar extraer el mensaje de chat si tiene el formato "nombre: mensaje"
            # PERO EXCLUIR mensajes del anticheat y logs del sistema
            if ':' in message_str and len(message_str) > 3:
                # Excluir mensajes que contienen caracteres especiales del sistema
                exclude_keywords = [
                    '[', ']', '(', ')', 'anticheat', 'Jugador', 'cuwo anti-cheat', 
                    'Script', 'Se recibieron', 'cambio de nombre', 'IP', 'Tu IP', 
                    'Razon', 'fue baneado', 'expulsado', 'conectado', 'desconectado',
                    'Deteniendo', 'funcionando', 'navegador', 'uvloop', 'activado',
                    'desactivado', 'asesinado', 'sanado', 'aturdido', 'baneada',
                    '> ', 'PM)', 'Jugador'
                ]
                
                if not any(x in message_str for x in exclude_keywords):
                    parts = message_str.split(':', 1)
                    if len(parts) == 2:
                        player_name = parts[0].strip()
                        chat_message = parts[1].strip()
                        
                        # Validar que el nombre solo contiene caracteres validos (no es un log del sistema)
                        if player_name and all(c.isalnum() or c in ' -_' for c in player_name):
                            if chat_message and len(player_name) < 50 and len(chat_message) > 0:
                                try:
                                    web_server.add_chat_message(player_name, chat_message)
                                except Exception as e:
                                    original_print(f"Error guardando chat: {e}")
        
        builtins.print = patched_print
    
    def add_chat_message(self, player_name, message):
        """Agregar un mensaje al log de chat - SOLO si es de la sesion actual"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            chat_entry = f"[{timestamp}] {player_name}: {message}"
            
            # Escribir en archivo chat.log
            with open(CHAT_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(chat_entry + '\n')
            
            logger.debug(f"Mensaje de chat guardado: {player_name}: {message}")
        except Exception as e:
            logger.error(f"Error guardando mensaje de chat: {e}\n{traceback.format_exc()}")
    
    def load_chat_history(self):
        """Cargar SOLO los mensajes de la sesion actual desde el archivo"""
        chat_history = []
        try:
            if os.path.exists(CHAT_LOG_FILE):
                with open(CHAT_LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Encontrar el ultimo marcador de sesion
                last_session_marker_idx = -1
                for i in range(len(lines) - 1, -1, -1):
                    if SESSION_MARKER in lines[i]:
                        last_session_marker_idx = i
                        break
                
                # Procesar solo desde el ultimo marcador hasta el final
                start_idx = last_session_marker_idx + 1 if last_session_marker_idx >= 0 else 0
                
                for line in lines[start_idx:]:
                    line = line.strip()
                    if line and '[' in line and ']' in line and ':' in line:
                        try:
                            # Formato: [YYYY-MM-DD HH:MM:SS] nombre: mensaje
                            timestamp_end = line.find(']')
                            if timestamp_end > 0:
                                timestamp = line[1:timestamp_end]
                                rest = line[timestamp_end+2:]  # Skip '] '
                                
                                if ':' in rest:
                                    name, message = rest.split(':', 1)
                                    name = name.strip()
                                    message = message.strip()
                                    
                                    if name and message:  # Solo si ambos existen
                                        chat_history.append({
                                            'timestamp': timestamp,
                                            'name': name,
                                            'message': message
                                        })
                        except Exception as parse_error:
                            pass
        except Exception as e:
            logger.error(f"Error cargando historial de chat: {e}")
        
        return chat_history
    
    def _write_chat_session_marker(self):
        """Escribir marcador de sesion en chat.log - retorna el timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            marker = f"{SESSION_MARKER}\n[{timestamp}] SESION INICIADA\n{SESSION_MARKER}\n"
            
            with open(CHAT_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(marker)
            
            return timestamp
        except Exception as e:
            logger.error(f"Error escribiendo marcador de sesion de chat: {e}")
            return None
    
    def _write_session_marker(self):
        """Escribir marcador de sesion en archivo"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            marker = f"\n{SESSION_MARKER}\nSESION INICIADA: {timestamp}\n{SESSION_MARKER}\n"
            
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(marker)
        except Exception as e:
            logger.error(f"Error escribiendo marcador de sesion: {e}")
    
    def add_log_line(self, line):
        """Agregar linea de log al archivo y memoria"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {line}"
            
            self.current_session_logs.append(line)
            if len(self.current_session_logs) > MAX_LOG_LINES:
                self.current_session_logs.pop(0)
            
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            logger.error(f"Error escribiendo log: {e}")
    
    def add_error_line(self, error_text):
        """Agregar línea de error como un bloque completo (traceback completo como un log)"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Agregar el traceback COMPLETO como UN SOLO log
            self.current_session_logs.append(error_text)
            if len(self.current_session_logs) > MAX_LOG_LINES:
                self.current_session_logs.pop(0)
            
            # Escribir en archivo con timestamp
            log_entry = f"[{timestamp}] {error_text}"
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            logger.error(f"Error escribiendo error: {e}")
    
    def get_current_session_logs(self):
        """Obtener logs solo de la sesion actual"""
        return list(self.current_session_logs)
    
    def clear_all_logs(self):
        """Limpiar archivo de logs completamente y regenerar marcador de sesion"""
        try:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write('')
            
            self._write_session_marker()
            
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
            print(f"Abriendo navegador en {url}")
            webbrowser.open(url)
        except Exception as e:
            logger.warning(f"No se pudo abrir navegador: {e}\n{traceback.format_exc()}")
    
    def on_unload(self):
        """Se ejecuta cuando se descarga el script"""
        global _web_server_instance
        try:
            _web_server_instance = None
            if hasattr(self, 'http_server'):
                self.http_server.shutdown()
        except Exception as e:
            logger.error(f"Error deteniendo servidor web: {e}\n{traceback.format_exc()}")


def get_class():
    return WebServer
