$(document).ready(function () {
    const ClassArray = {
        0: "Sin Clase",
        1: "Guerrero",
        2: "Ranger",
        3: "Mago",
        4: "Pícaro"
    };
    
    const Specializations = [
        ["Berserker", "Guardian"],
        ["Sniper", "Scout"],
        ["Fire", "Water"],
        ["Assassin", "Ninja"]
    ];
    
    let playersData = {};
    let bansData = {};
    let updateInterval = null;
    let selectedPlayerId = null;
    let selectedUnbanIp = null;
    let previousPlayerIds = new Set();
    
    // ============= TAB SWITCHING =============
    $('.nav-item').on('click', function(e) {
        e.preventDefault();
        const tabName = $(this).data('tab');
        
        $('.nav-item').removeClass('active');
        $('.tab-content').removeClass('active');
        
        $(this).addClass('active');
        $('#' + tabName).addClass('active');
        
        // Actualizar bans cuando se cambia a la pestaña
        if (tabName === 'bans') {
            updateBans();
        }
    });
    
    // ============= MODAL MANAGEMENT =============
    function showModal(modalId) {
        $('#' + modalId).addClass('show');
    }
    
    function hideModal(modalId) {
        $('#' + modalId).removeClass('show');
    }
    
    $('[data-dismiss]').on('click', function() {
        const modalId = $(this).data('dismiss');
        hideModal(modalId);
    });
    
    $(window).on('click', function(event) {
        if (event.target.classList.contains('modal')) {
            $(event.target).removeClass('show');
        }
    });
    
    // ============= CONVERT PLAYTIME =============
    function formatPlaytime(minutes) {
        if (minutes < 60) {
            return minutes + ' min';
        }
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return hours + 'h ' + mins + 'min';
    }
    
    // ============= PLAYERS UPDATE =============
    function updatePlayers() {
        $.ajax({
            url: '/api/players',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (!data || !Array.isArray(data.players)) {
                    return;
                }
                
                const playersContainer = $('#playersContainer');
                const currentPlayerIds = new Set(data.players.map(p => p.id));
                const disconnectedIds = new Set([...previousPlayerIds].filter(id => !currentPlayerIds.has(id)));
                
                // Remover jugadores desconectados con animaci��n
                disconnectedIds.forEach(playerId => {
                    $(`#playersContainer .player-item[data-player-id="${playerId}"]`).fadeOut(300, function() {
                        $(this).remove();
                        
                        // Si la lista está vacía, mostrar empty-state
                        if (playersContainer.find('.player-item').length === 0) {
                            playersContainer.html(`
                                <div class="empty-state">
                                    <i class="fas fa-inbox"></i>
                                    <p>No hay jugadores conectados</p>
                                </div>
                            `);
                        }
                    });
                    delete playersData[playerId];
                });
                
                if (data.players.length === 0) {
                    if (playersContainer.find('.player-item').length === 0) {
                        playersContainer.html(`
                            <div class="empty-state">
                                <i class="fas fa-inbox"></i>
                                <p>No hay jugadores conectados</p>
                            </div>
                        `);
                    }
                } else {
                    // Remover empty-state si existe
                    playersContainer.find('.empty-state').remove();
                    
                    data.players.forEach(player => {
                        playersData[player.id] = player;
                        
                        const className = ClassArray[player.klass] || "Desconocida";
                        const spec = player.klass > 0 && player.klass <= 4 
                            ? Specializations[player.klass - 1][player.specialz] || "Desconocida"
                            : "Desconocida";
                        
                        const playtimeStr = formatPlaytime(player.playtime_minutes || 0);
                        
                        const $existingItem = $(`#playersContainer .player-item[data-player-id="${player.id}"]`);
                        
                        if ($existingItem.length > 0) {
                            $existingItem.find('.player-detail-item').each(function() {
                                const $label = $(this).find('.player-detail-label');
                                const $value = $(this).find('.player-detail-value');
                                const labelText = $label.text().toLowerCase();
                                
                                if (labelText.includes('ip')) {
                                    $value.text(player.ip);
                                } else if (labelText.includes('salud')) {
                                    $value.text(player.hp + ' HP');
                                } else if (labelText.includes('especialidad')) {
                                    $value.text(spec);
                                } else if (labelText.includes('posición')) {
                                    $value.text(`X:${player.x || 0}`);
                                } else if (labelText.includes('tiempo de juego')) {
                                    $value.text(playtimeStr);
                                }
                            });
                        } else {
                            const firstLetter = (player.name || "?")[0].toUpperCase();
                            
                            const newItem = `
                                <div class="player-item" data-player-id="${player.id}" style="animation: slideUp 0.5s ease;">
                                    <div class="player-avatar">${firstLetter}</div>
                                    <div class="player-info">
                                        <div class="player-name">${player.name}</div>
                                        <div class="player-details-row">
                                            <div class="player-detail-item">
                                                <span class="player-detail-label">IP</span>
                                                <span class="player-detail-value">${player.ip}</span>
                                            </div>
                                            <div class="player-detail-item">
                                                <span class="player-detail-label">Clase</span>
                                                <span class="player-detail-value">${className}</span>
                                            </div>
                                            <div class="player-detail-item">
                                                <span class="player-detail-label">Especialidad</span>
                                                <span class="player-detail-value">${spec}</span>
                                            </div>
                                            <div class="player-detail-item">
                                                <span class="player-detail-label">Salud</span>
                                                <span class="player-detail-value">${player.hp} HP</span>
                                            </div>
                                            <div class="player-detail-item">
                                                <span class="player-detail-label">Posición</span>
                                                <span class="player-detail-value">X:${player.x || 0}</span>
                                            </div>
                                            <div class="player-detail-item">
                                                <span class="player-detail-label">Tiempo de juego</span>
                                                <span class="player-detail-value">${playtimeStr}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="player-actions">
                                        <button class="btn-action btn-heal" data-player-id="${player.id}" data-action="heal">
                                            <i class="fas fa-heart"></i> Sanar
                                        </button>
                                        <button class="btn-action btn-kick" data-player-id="${player.id}" data-action="kick">
                                            <i class="fas fa-sign-out-alt"></i> Expulsar
                                        </button>
                                        <button class="btn-action btn-ban" data-player-id="${player.id}" data-action="ban">
                                            <i class="fas fa-ban"></i> Banear
                                        </button>
                                    </div>
                                </div>
                            `;
                            
                            playersContainer.append(newItem);
                        }
                    });
                }
                
                $('#playerCount').text(data.count);
                previousPlayerIds = currentPlayerIds;
                attachPlayerActionHandlers();
                
            },
            error: function(xhr) {
                addConsoleMessage('error', `Error al obtener lista de jugadores: ${xhr.status} ${xhr.statusText}`);
            }
        });
    }

    // ============= BANS UPDATE =============
    function updateBans() {
        $.ajax({
            url: '/api/bans',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (!data || !Array.isArray(data.bans)) {
                    return;
                }
                
                const bansContainer = $('#bansContainer');
                
                if (data.bans.length === 0) {
                    // Solo mostrar empty-state si hay items actualmente
                    if (bansContainer.find('.ban-item').length > 0) {
                        bansContainer.fadeOut(300, function() {
                            bansContainer.html(`
                                <div class="empty-state">
                                    <i class="fas fa-check-circle"></i>
                                    <p>No hay jugadores baneados</p>
                                </div>
                            `);
                            bansContainer.fadeIn(300);
                        });
                    } else if (bansContainer.find('.empty-state').length === 0) {
                        bansContainer.html(`
                            <div class="empty-state">
                                <i class="fas fa-check-circle"></i>
                                <p>No hay jugadores baneados</p>
                            </div>
                        `);
                    }
                } else {
                    // Remover empty-state si existe
                    bansContainer.find('.empty-state').remove();
                    
                    // Crear set de IPs actuales en el servidor
                    const serverIps = new Set(data.bans.map(b => b.ip));
                    
                    // Remover bans que ya no existen con animación
                    bansContainer.find('.ban-item').each(function() {
                        const ip = $(this).data('ban-ip');
                        if (!serverIps.has(ip)) {
                            $(this).fadeOut(300, function() {
                                $(this).remove();
                                
                                // Si la lista está vacía después de remover, mostrar empty-state
                                if (bansContainer.find('.ban-item').length === 0) {
                                    bansContainer.html(`
                                        <div class="empty-state">
                                            <i class="fas fa-check-circle"></i>
                                            <p>No hay jugadores baneados</p>
                                        </div>
                                    `);
                                }
                            });
                        }
                    });
                    
                    // Agregar o actualizar bans existentes
                    data.bans.forEach(ban => {
                        const existingBan = bansContainer.find(`.ban-item[data-ban-ip="${ban.ip}"]`);
                        
                        if (existingBan.length > 0) {
                            // Actualizar ban existente solo si cambió algo
                            const currentName = existingBan.find('.ban-name').text();
                            const currentReason = existingBan.find('.ban-detail-value:last').text();
                            
                            if (currentName !== (ban.name || 'Desconocido') || currentReason !== (ban.reason || 'Sin razón')) {
                                existingBan.find('.ban-name').text(ban.name || 'Desconocido');
                                existingBan.find('.ban-detail-value:last').text(ban.reason || 'Sin razón');
                            }
                        } else {
                            // Agregar nuevo ban CON animación
                            const banItem = `
                                <div class="ban-item" data-ban-ip="${ban.ip}" style="animation: slideUp 0.5s ease;">
                                    <div class="ban-avatar">
                                        <i class="fas fa-ban"></i>
                                    </div>
                                    <div class="ban-info">
                                        <div class="ban-name">${ban.name || 'Desconocido'}</div>
                                        <div class="ban-details-row">
                                            <div class="ban-detail-item">
                                                <span class="ban-detail-label">IP Baneada</span>
                                                <span class="ban-detail-value">${ban.ip}</span>
                                            </div>
                                            <div class="ban-detail-item">
                                                <span class="ban-detail-label">Razón</span>
                                                <span class="ban-detail-value">${ban.reason || 'Sin razón'}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="ban-actions">
                                        <button class="btn-action btn-unban" data-ban-ip="${ban.ip}" data-action="unban">
                                            <i class="fas fa-lock-open"></i> Desbanear
                                        </button>
                                    </div>
                                </div>
                            `;
                            
                            bansContainer.append(banItem);
                        }
                    });
                    
                    // Reattach handlers a los nuevos items
                    attachBanActionHandlers();
                }
                
                $('#banCount').text(data.count || 0);
                
            },
            error: function(xhr) {
                addConsoleMessage('error', `Error al obtener lista de baneados: ${xhr.status} ${xhr.statusText}`);
            }
        });
    }
    
    function attachPlayerActionHandlers() {
        $('.btn-action').off('click').on('click', function(e) {
            e.preventDefault();
            const playerId = $(this).data('player-id');
            const action = $(this).data('action');
            const player = playersData[playerId];
            
            if (!player) return;
            
            if (action === 'heal') {
                healPlayer(playerId, player.name);
            } else if (action === 'kick') {
                selectedPlayerId = playerId;
                $('#kickPlayerName').text('Jugador: ' + player.name + ' (' + player.ip + ')');
                $('#kickReason').val('');
                showModal('kickModal');
            } else if (action === 'ban') {
                selectedPlayerId = playerId;
                $('#banPlayerName').text('Jugador: ' + player.name + ' (' + player.ip + ')');
                $('#banReason').val('');
                showModal('banModal');
            }
        });
    }

    function attachBanActionHandlers() {
        $('.btn-unban').off('click').on('click', function(e) {
            e.preventDefault();
            const banIp = $(this).data('ban-ip');
            const banItem = $(this).closest('.ban-item');
            const banName = banItem.find('.ban-name').text();
            
            selectedUnbanIp = banIp;
            $('#unbanPlayerInfo').text(`Jugador: ${banName} (${banIp})`);
            showModal('unbanModal');
        });
    }
    
    function healPlayer(playerId, playerName) {
        $.ajax({
            url: '/api/command',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                request: 'heal_player',
                player_id: playerId,
                key: auth_key
            }),
            success: function(response) {
                if (response.success) {
                    addConsoleMessage('success', `Jugador ${playerName} sanado completamente`);
                } else {
                    addConsoleMessage('error', `Error al sanar a ${playerName}: ${response.error || 'Error desconocido'}`);
                }
                updatePlayers();
            },
            error: function(xhr) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    addConsoleMessage('error', `Error al sanar (HTTP ${xhr.status}): ${errorData.error || 'Error desconocido'}`);
                } catch(e) {
                    addConsoleMessage('error', `Error de conexión al sanar: HTTP ${xhr.status}`);
                }
                console.error('Error details:', xhr);
            }
        });
    }

    function unbanIp(ip) {
        $.ajax({
            url: '/api/command',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                request: 'unban_ip',
                ip: ip,
                key: auth_key
            }),
            success: function(response) {
                if (response.success) {
                    addConsoleMessage('success', `IP ${ip} desbaneada correctamente`);
                    hideModal('unbanModal');
                    updateBans();
                } else {
                    addConsoleMessage('error', `Error al desbanear ${ip}: ${response.error || 'Error desconocido'}`);
                    updateBans();
                }
            },
            error: function(xhr) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    addConsoleMessage('error', `Error al desbanear (HTTP ${xhr.status}): ${errorData.error || 'Error desconocido'}`);
                } catch(e) {
                    addConsoleMessage('error', `Error de conexión: HTTP ${xhr.status}`);
                }
                console.error('Error details:', xhr);
                updateBans();
            }
        });
    }
    
    $('#kickConfirmBtn').on('click', function() {
        const reason = $('#kickReason').val().trim();
        if (!reason) {
            alert('Por favor, proporciona una razón');
            return;
        }
        
        const player = playersData[selectedPlayerId];
        if (!player) return;
        
        $.ajax({
            url: '/api/command',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                request: 'kick_player',
                player_id: selectedPlayerId,
                reason: reason,
                key: auth_key
            }),
            success: function(response) {
                if (response.success) {
                    addConsoleMessage('success', `Jugador ${player.name} expulsado. Razón: ${reason}`);
                } else {
                    addConsoleMessage('error', `No se pudo expulsar a ${player.name}: ${response.error || 'Error desconocido'}`);
                }
                hideModal('kickModal');
                updatePlayers();
            },
            error: function(xhr) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    addConsoleMessage('error', `Error al expulsar (HTTP ${xhr.status}): ${errorData.error || 'Error desconocido'}`);
                } catch(e) {
                    addConsoleMessage('error', `Error de conexión al expulsar: HTTP ${xhr.status}`);
                }
                console.error('Error details:', xhr);
            }
        });
    });
    
    $('#banConfirmBtn').on('click', function() {
        const reason = $('#banReason').val().trim() || 'Sin razón especificada';
        
        const player = playersData[selectedPlayerId];
        if (!player) return;
        
        $.ajax({
            url: '/api/command',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                request: 'ban_player',
                player_id: selectedPlayerId,
                reason: reason,
                key: auth_key
            }),
            success: function(response) {
                if (response.success) {
                    addConsoleMessage('success', `Jugador ${player.name} baneado correctamente. IP: ${player.ip} Razón: ${reason}`);
                } else {
                    addConsoleMessage('warning', `${player.name} expulsado (no se pudo banear): ${response.error || 'Error desconocido'}`);
                }
                hideModal('banModal');
                updatePlayers();
                updateBans();
            },
            error: function(xhr) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    addConsoleMessage('error', `Error al banear (HTTP ${xhr.status}): ${errorData.error || 'Error desconocido'}`);
                } catch(e) {
                    addConsoleMessage('error', `Error de conexión al banear: HTTP ${xhr.status}`);
                }
                console.error('Error details:', xhr);
            }
        });
    });

    $('#unbanConfirmBtn').on('click', function() {
        if (selectedUnbanIp) {
            unbanIp(selectedUnbanIp);
        }
    });
    
    // ============= SERVER INFO UPDATE =============
    function updateServerInfo() {
        $.ajax({
            url: '/api/server',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (!data) return;
                
                $('#serverPlayers').text(data.players_online + '/' + data.max_players);
                
                const hours = Math.floor(data.uptime / 3600);
                const minutes = Math.floor((data.uptime % 3600) / 60);
                $('#uptime').text(hours + ' horas, ' + minutes + ' minutos');
            },
            error: function(xhr) {
                addConsoleMessage('error', `Error al obtener info del servidor: HTTP ${xhr.status}`);
            }
        });
    }
    
    // ============= CONSOLE =============
    
    function updateConsoleLogs() {
        $.ajax({
            url: '/api/logs',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (!data || !Array.isArray(data.logs)) {
                    return;
                }
                
                // Obtener logs ya mostrados
                const currentLogLines = $('#consoleOutput .console-line:not(:contains("Servidor web conectado"))').length;
                const totalLogs = data.logs.length;
                
                // Si hay más logs en el servidor, agregar solo los nuevos
                if (totalLogs > currentLogLines) {
                    const newLogs = data.logs.slice(currentLogLines);
                    newLogs.forEach(logLine => {
                        // Detectar símbolo inicial
                        let isError = false;
                        let displayLine = logLine;
                        
                        if (logLine.startsWith('✗')) {
                            isError = true;
                            displayLine = logLine.substring(1).trim();
                        } else if (logLine.startsWith('✓')) {
                            displayLine = logLine.substring(1).trim();
                        }
                        
                        // Aplicar estilos según el símbolo
                        let symbolClass = isError ? 'console-error' : 'console-success';
                        let lineClass = isError ? 'console-line-error-command' : '';
                        
                        const line = `<div class="console-line ${lineClass}"><span class="${symbolClass}">${isError ? '✗' : '✓'}</span> ${escapeHtml(displayLine)}</div>`;
                        $('#consoleOutput').append(line);
                    });
                    $('#consoleOutput').scrollTop($('#consoleOutput')[0].scrollHeight);
                }
            },
            error: function() {
                // Silenciar errores
            }
        });
    }
    
    function loadInitialConsoleLogs() {
        $.ajax({
            url: '/api/logs',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (!data || !Array.isArray(data.logs)) {
                    return;
                }
                
                // Si hay logs, mostrarlos
                if (data.logs.length > 0) {
                    // Limpiar el mensaje inicial si ya hay logs
                    const existingLogs = $('#consoleOutput .console-line').length;
                    if (existingLogs <= 1) {
                        // Solo hay "Servidor web conectado", reemplazar con logs reales
                        data.logs.forEach(logLine => {
                            // Detectar símbolo inicial
                            let isError = false;
                            let displayLine = logLine;
                            
                            if (logLine.startsWith('✗')) {
                                isError = true;
                                displayLine = logLine.substring(1).trim();
                            } else if (logLine.startsWith('✓')) {
                                displayLine = logLine.substring(1).trim();
                            }
                            
                            // Aplicar estilos según el símbolo
                            let symbolClass = isError ? 'console-error' : 'console-success';
                            let lineClass = isError ? 'console-line-error-command' : '';
                            
                            const line = `<div class="console-line ${lineClass}"><span class="${symbolClass}">${isError ? '✗' : '✓'}</span> ${escapeHtml(displayLine)}</div>`;
                            $('#consoleOutput').append(line);
                        });
                        $('#consoleOutput').scrollTop($('#consoleOutput')[0].scrollHeight);
                    }
                }
            },
            error: function() {
                // Silenciar errores
            }
        });
    }
    
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    function addConsoleMessage(type, text) {
        let symbolHTML = '<span class="console-success">✓</span>';
        let lineClass = '';
        
        if (type === 'error') {
            symbolHTML = '<span class="console-error">✗</span>';
            lineClass = 'console-line-error-command';
        } else if (type === 'warning') {
            symbolHTML = '<span class="console-warning">⚠</span>';
        }
        
        // Detectar si es output de help o tiene múltiples líneas con formato
        if (text.includes('\n') && (text.includes('COMANDOS') || text.includes('==='))) {
            // Usar pre para preservar saltos de línea y espacios
            const line = `<div class="console-line ${lineClass}">${symbolHTML}<pre class="console-pre">${escapeHtml(text)}</pre></div>`;
            $('#consoleOutput').append(line);
        } else {
            // Formato normal
            const contentClass = lineClass ? 'console-error' : 'console-success';
            const line = `<div class="console-line ${lineClass}">${symbolHTML} ${escapeHtml(text)}</div>`;
            $('#consoleOutput').append(line);
        }
        
        $('#consoleOutput').scrollTop($('#consoleOutput')[0].scrollHeight);
    }
    
    $('#consoleInput').on('keypress', function(e) {
        if (e.which === 13) {
            const command = $(this).val().trim();
            if (command) {
                // NO agregar el comando todavía, esperar respuesta
                
                $.ajax({
                    url: '/api/command',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        request: 'execute_command',
                        command: command,
                        key: auth_key
                    }),
                    success: function(response) {
                        // Ahora mostrar el comando con el símbolo correcto
                        if (response.success) {
                            addConsoleMessage('success', '> ' + command);
                            if (response.output && response.output.trim()) {
                                addConsoleMessage('success', response.output);
                            }
                        } else {
                            // Error en comando - mostrar con símbolo de error
                            addConsoleMessage('error', '> ' + command);
                            if (response.error) {
                                addConsoleMessage('error', response.error);
                            } else {
                                addConsoleMessage('error', 'Error desconocido ejecutando comando');
                            }
                        }
                        // Actualizar logs después de ejecutar comando
                        setTimeout(updateConsoleLogs, 500);
                    },
                    error: function(xhr) {
                        try {
                            const errorData = JSON.parse(xhr.responseText);
                            addConsoleMessage('error', '> ' + command);
                            addConsoleMessage('error', `Error: ${errorData.error || 'Error desconocido'}`);
                        } catch(e) {
                            addConsoleMessage('error', '> ' + command);
                            addConsoleMessage('error', `Error de conexión: HTTP ${xhr.status}`);
                        }
                    }
                });
                
                $(this).val('');
            }
            return false;
        }
    });
    
    $('#clearLogBtn').on('click', function() {
        showModal('clearLogModal');
    });
    
    $('#clearLogConfirmBtn').on('click', function() {
        $.ajax({
            url: '/api/command',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                request: 'clear_log',
                key: auth_key
            }),
            success: function() {
                hideModal('clearLogModal');
                $('#consoleOutput').html('<div class="console-line"><span class="console-success">✓</span> Log limpiado</div>');
            }
        });
    });
    
    // ============= CHAT =============
    $('#chatInput').on('keypress', function(e) {
        if (e.which === 13) {
            const message = $(this).val().trim();
            if (message) {
                $.ajax({
                    url: '/api/command',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        request: 'send_message',
                        message: message,
                        key: auth_key
                    }),
                    success: function() {
                        addChatMessage('cuwo', message, 'user');
                    },
                    error: function(xhr) {
                        addConsoleMessage('error', `Error al enviar mensaje: HTTP ${xhr.status}`);
                    }
                });
                $(this).val('');
            }
            return false;
        }
    });
    
    $('#chatSendBtn').on('click', function() {
        $('#chatInput').trigger('keypress');
    });
    
    function addChatMessage(author, text, type = 'system') {
        let authorHtml = author;
        if (author === 'cuwo') {
            authorHtml = '<span class="message-author cuwo">cuwo:</span>';
        } else {
            authorHtml = `<span class="message-author">${author}:</span>`;
        }
        
        const messageHtml = `
            <div class="chat-message ${type}">
                ${authorHtml}
                <span class="message-text">${text}</span>
            </div>
        `;
        $('#chatMessages').append(messageHtml);
        $('#chatMessages').scrollTop($('#chatMessages')[0].scrollHeight);
    }
    
    // ============= INITIALIZATION =============
    updatePlayers();
    updateServerInfo();
    updateBans();
    updateConsoleLogs();
    loadInitialConsoleLogs();
    
    updateInterval = setInterval(() => {
        updatePlayers();
        updateServerInfo();
        updateBans();
        updateConsoleLogs();
    }, 5000);
    
    $(window).on('unload', function() {
        if (updateInterval) {
            clearInterval(updateInterval);
        }
    });
});
