# Variables de script de Discord (habilitelas agregando 'discord' a la lista de scripts)
token = None # bot token
channel_id = None # como una cadena de caracteres, por ejemplo, '1234568891'
command_prefix = '!'
chat_prefix = '.'

# Nombres de roles de usuario que tienen permiso para chatear y usar comandos.
command_roles = ['admin']
chat_roles = ['@everyone']

# Tipos de usuario que admite el bot de Discord. Los comandos disponibles de otros scripts estan restringidos por esta lista.
rights = ['admin', 'discord']
