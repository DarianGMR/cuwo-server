# Variables de script de IRC (habilitelas agregando 'irc' a la lista de scripts)
nickname = 'cuwobot'
server = 'irc.esper.net'
password = None
port = 6667
ssl = False
# Falso / "CERT_NONE" / "CERT_OPTIONAL" / "CERT_REQUIRED"
ssl_verify = "CERT_REQUIRED"
channel = '#cuwo.bots'
channel_password = None
commandprefix = '.'
chatprefix = '#'

# Modos de usuario que tienen permiso para chatear y usar comandos.
command_modes = [('@', 'o'), ('&', 'a'), ('~', 'q'), ('%', 'h')]

# Modos de usuario que tienen permiso para chatear con el servidor del juego.
chat_modes = [('+', 'v')]

# Tipos de usuario que admite el bot de IRC. Los comandos disponibles de otros scripts estan restringidos por esta lista.
rights = ['admin', 'irc']
