$(document).ready(function () {
    const ClassArray = {
        0: "Sin Clase",
        1: "Guerrero",
        2: "Ranger",
        3: "Mago",
        4: "Picaro"
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
    let lastChatMessageCount = 0;
    let chatStatusShown = false;
    let chatInitialized = false;
    let currentTab = 'players';
    
    // ============= TAB SWITCHING =============
    $('.nav-item').on('click', function(e) {
        e.preventDefault();
        const tabName = $(this).data('tab');
        currentTab = tabName;
        
        $('.nav-item').removeClass('active');
        $('.tab-content').removeClass('active');
        
        $(this).addClass('active');
        $('#' + tabName).addClass('active');
        
        // Actualizar bans cuando se cambia a la pestana
        if (tabName === 'bans') {
            updateBans();
        }
        
        // Cargar chat cuando se cambia a esa pestana
        if (tabName === 'chat' && !chatInitialized) {
            loadChatHistory();
            chatInitialized = true;
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
                
                // Remover jugadores desconectados con animacion
                disconnectedIds.forEach(playerId => {
                    $(`#playersContainer .player-item[data-player-id="${playerId}"]`).fadeOut(300, function() {
                        $(this).remove();
                        
                        // Si la lista esta vacia, mostrar empty-state
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
                                } else if (labelText.includes('posicion')) {
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
                                                <span class="player-detail-label">Posicion</span>
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
                    
                    // Remover bans que ya no existen con animacion
                    bansContainer.find('.ban-item').each(function() {
                        const ip = $(this).data('ban-ip');
                        if (!serverIps.has(ip)) {
                            $(this).fadeOut(300, function() {
                                $(this).remove();
                                
                                // Si la lista esta vacia despues de remover, mostrar empty-state
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
                            // Actualizar ban existente solo si cambio algo
                            const currentName = existingBan.find('.ban-name').text();
                            const currentReason = existingBan.find('.ban-detail-value:last').text();
                            
                            if (currentName !== (ban.name || 'Desconocido') || currentReason !== (ban.reason || 'Sin razon')) {
                                existingBan.find('.ban-name').text(ban.name || 'Desconocido');
                                existingBan.find('.ban-detail-value:last').text(ban.reason || 'Sin razon');
                            }
                        } else {
                            // Agregar nuevo ban CON animacion
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
                                                <span class="ban-detail-label">Razon</span>
                                                <span class="ban-detail-value">${ban.reason || 'Sin razon'}</span>
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
                    addConsoleMessage('error', `Error de conexion al sanar: HTTP ${xhr.status}`);
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
                    addConsoleMessage('error', `Error de conexion: HTTP ${xhr.status}`);
                }
                console.error('Error details:', xhr);
                updateBans();
            }
        });
    }
    
    $('#kickConfirmBtn').on('click', function() {
        const reason = $('#kickReason').val().trim();
        if (!reason) {
            alert('Por favor, proporciona una razon');
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
                    addConsoleMessage('success', `Jugador ${player.name} expulsado. Razon: ${reason}`);
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
                    addConsoleMessage('error', `Error de conexion al expulsar: HTTP ${xhr.status}`);
                }
                console.error('Error details:', xhr);
            }
        });
    });
    
    $('#banConfirmBtn').on('click', function() {
        const reason = $('#banReason').val().trim() || 'Sin razon especificada';
        
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
                    addConsoleMessage('success', `Jugador ${player.name} baneado correctamente. IP: ${player.ip} Razon: ${reason}`);
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
                    addConsoleMessage('error', `Error de conexion al banear: HTTP ${xhr.status}`);
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
                
                // Si hay mas logs en el servidor, agregar solo los nuevos
                if (totalLogs > currentLogLines) {
                    const newLogs = data.logs.slice(currentLogLines);
                    newLogs.forEach(logLine => {
                        // Detectar simbolo inicial
                        let isError = false;
                        let displayLine = logLine;
                        
                        if (logLine.startsWith('✗')) {
                            isError = true;
                            displayLine = logLine.substring(7).trim();
                        } else if (logLine.startsWith('✓')) {
                            displayLine = logLine.substring(4).trim();
                        }
                        
                        // Aplicar estilos segun el simbolo
                        let symbolClass = isError ? 'console-error' : 'console-success';
                        let lineClass = isError ? 'console-line-error-command' : '';
                        let symbol = isError ? '✗' : '✓';
                        
                        // Detectar si tiene multiples lineas
                        const hasMultipleLines = displayLine.includes('\n');
                        
                        if (hasMultipleLines) {
                            // Usar pre para preservar formato
                            const line = `<div class="console-line ${lineClass}"><span class="${symbolClass}">${symbol}</span><pre class="console-pre">${escapeHtml(displayLine)}</pre></div>`;
                            $('#consoleOutput').append(line);
                        } else {
                            // Formato normal
                            const line = `<div class="console-line ${lineClass}"><span class="${symbolClass}">${symbol}</span> ${escapeHtml(displayLine)}</div>`;
                            $('#consoleOutput').append(line);
                        }
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
                        $('#consoleOutput').html('');
                        data.logs.forEach(logLine => {
                            // Detectar simbolo inicial
                            let isError = false;
                            let displayLine = logLine;
                            
                            if (logLine.startsWith('✗')) {
                                isError = true;
                                displayLine = logLine.substring(7).trim();
                            } else if (logLine.startsWith('✓')) {
                                displayLine = logLine.substring(4).trim();
                            }
                            
                            // Aplicar estilos segun el simbolo
                            let symbolClass = isError ? 'console-error' : 'console-success';
                            let lineClass = isError ? 'console-line-error-command' : '';
                            let symbol = isError ? '✗' : '✓';
                            
                            // Detectar si tiene multiples lineas
                            const hasMultipleLines = displayLine.includes('\n');
                            
                            if (hasMultipleLines) {
                                // Usar pre para preservar formato
                                const line = `<div class="console-line ${lineClass}"><span class="${symbolClass}">${symbol}</span><pre class="console-pre">${escapeHtml(displayLine)}</pre></div>`;
                                $('#consoleOutput').append(line);
                            } else {
                                // Formato normal
                                const line = `<div class="console-line ${lineClass}"><span class="${symbolClass}">${symbol}</span> ${escapeHtml(displayLine)}</div>`;
                                $('#consoleOutput').append(line);
                            }
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
            symbolHTML = '<span class="console-warning">[WARN]</span>';
        }
        
        // Detectar si necesita pre (multiples lineas o contiene espacios alineados)
        const needsPre = text.includes('\n');
        
        if (needsPre) {
            // Usar pre para preservar saltos de linea y espacios
            const line = `<div class="console-line ${lineClass}">${symbolHTML}<pre class="console-pre">${escapeHtml(text)}</pre></div>`;
            $('#consoleOutput').append(line);
        } else {
            // Formato normal para lineas simples
            const line = `<div class="console-line ${lineClass}">${symbolHTML} ${escapeHtml(text)}</div>`;
            $('#consoleOutput').append(line);
        }
        
        $('#consoleOutput').scrollTop($('#consoleOutput')[0].scrollHeight);
    }
    
    $('#consoleInput').on('keypress', function(e) {
        if (e.which === 13) {
            const command = $(this).val().trim();
            if (command) {
                // NO agregar el comando todavia, esperar respuesta
                
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
                        // Ahora mostrar el comando con el simbolo correcto
                        if (response.success) {
                            addConsoleMessage('success', '> ' + command);
                            if (response.output && response.output.trim()) {
                                addConsoleMessage('success', response.output);
                            }
                        } else {
                            // Error en comando - mostrar con simbolo de error
                            addConsoleMessage('error', '> ' + command);
                            if (response.error) {
                                addConsoleMessage('error', response.error);
                            } else {
                                addConsoleMessage('error', 'Error desconocido ejecutando comando');
                            }
                        }
                        // Actualizar logs despues de ejecutar comando
                        setTimeout(updateConsoleLogs, 500);
                    },
                    error: function(xhr) {
                        try {
                            const errorData = JSON.parse(xhr.responseText);
                            addConsoleMessage('error', '> ' + command);
                            addConsoleMessage('error', `Error: ${errorData.error || 'Error desconocido'}`);
                        } catch(e) {
                            addConsoleMessage('error', '> ' + command);
                            addConsoleMessage('error', `Error de conexion: HTTP ${xhr.status}`);
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
    
    function checkChatStatus() {
        $.ajax({
            url: '/api/chat-status',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (data && data.status) {
                    // Agregar mensaje de estado si no existe
                    if ($('#chatMessages .system-status').length === 0) {
                        const statusMessage = `Chat ${data.status}`;
                        const messageHtml = `<div class="chat-message system system-status"><span class="message-author">Sistema:</span> <span class="message-text">${escapeHtml(statusMessage)}</span></div>`;
                        $('#chatMessages').prepend(messageHtml);
                        chatStatusShown = true;
                    }
                }
            },
            error: function() {
                // Silenciar errores
            }
        });
    }
    
    function loadChatHistory() {
        $.ajax({
            url: '/api/chat',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (!data || !Array.isArray(data.messages)) {
                    return;
                }
                
                console.log('Chat history loaded:', data.messages.length, 'messages');
                
                // Limpiar chat actual solo si no tiene el mensaje de estado
                if ($('#chatMessages .system-status').length === 0) {
                    $('#chatMessages').html('');
                    lastChatMessageCount = 0;
                    
                    // Mostrar estado del chat al inicio
                    checkChatStatus();
                }
                
                // Agregar todos los mensajes del historial
                data.messages.forEach(msg => {
                    if (msg && msg.name && msg.message) {
                        // Si el nombre es "cuwo", cambiar el tipo a "user"
                        const type = (msg.name === 'cuwo' || msg.name === 'Server') ? 'user' : 'system';
                        addChatMessage(msg.name, msg.message, type);
                        lastChatMessageCount++;
                    }
                });
                
                console.log('Total chat messages:', lastChatMessageCount);
            },
            error: function(xhr) {
                console.error('Error loading chat history:', xhr.status);
            }
        });
    }
    
    function updateChat() {
        // Solo actualizar si estamos en la pestana de chat
        if (currentTab !== 'chat') {
            return;
        }
        
        $.ajax({
            url: '/api/chat',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (!data || !Array.isArray(data.messages)) {
                    return;
                }
                
                // Si hay mas mensajes que los que tenemos, agregar solo los nuevos
                if (data.messages.length > lastChatMessageCount) {
                    const newMessages = data.messages.slice(lastChatMessageCount);
                    newMessages.forEach(msg => {
                        if (msg && msg.name && msg.message) {
                            // Si el nombre es "cuwo", cambiar el tipo a "user"
                            const type = (msg.name === 'cuwo' || msg.name === 'Server') ? 'user' : 'system';
                            addChatMessage(msg.name, msg.message, type);
                        }
                    });
                    lastChatMessageCount = data.messages.length;
                }
            },
            error: function() {
                // Silenciar errores
            }
        });
    }
    
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
                        lastChatMessageCount++;
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
        // Eliminar espacios excesivos del autor
        author = author.trim();
        text = text.trim();
        
        let authorHtml = author;
        if (author === 'cuwo' || author === 'Server') {
            authorHtml = `<span class="message-author cuwo">${author}:</span>`;
        } else {
            authorHtml = `<span class="message-author">${author}:</span>`;
        }
        
        // Formato compacto sin saltos de linea ni espacios excesivos
        const messageHtml = `<div class="chat-message ${type}">${authorHtml} <span class="message-text">${escapeHtml(text)}</span></div>`;
        
        $('#chatMessages').append(messageHtml);
        $('#chatMessages').scrollTop($('#chatMessages')[0].scrollHeight);
    }
    
    // ============= INITIALIZATION =============
    updatePlayers();
    updateServerInfo();
    updateBans();
    updateConsoleLogs();
    loadInitialConsoleLogs();
    
    // Cargar chat solo cuando se abre la pestaña por primera vez
    const chatTab = $('.nav-item[data-tab="chat"]');
    if (chatTab.hasClass('active')) {
        loadChatHistory();
        chatInitialized = true;
    }
    
    updateInterval = setInterval(() => {
        updatePlayers();
        updateServerInfo();
        updateBans();
        updateConsoleLogs();
    }, 5000);

        // INTERVALO SEPARADO PARA CHAT MÁS RÁPIDO: 1000ms
    const chatInterval = setInterval(() => {
        updateChat();
    }, 1000);
    
    $(window).on('unload', function() {
        if (updateInterval) {
            clearInterval(updateInterval);
        }
        if (chatInterval) {
            clearInterval(chatInterval);
        }
    });
});
