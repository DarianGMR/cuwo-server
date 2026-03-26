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
                
                const currentPlayerIds = new Set(data.players.map(p => p.id));
                const disconnectedIds = new Set([...previousPlayerIds].filter(id => !currentPlayerIds.has(id)));
                
                // Remover jugadores desconectados
                disconnectedIds.forEach(playerId => {
                    $(`#playersContainer .player-item[data-player-id="${playerId}"]`).fadeOut(300, function() {
                        $(this).remove();
                    });
                    delete playersData[playerId];
                });
                
                if (data.players.length === 0) {
                    if ($('#playersContainer .player-item').length === 0) {
                        $('#playersContainer').html(`
                            <div class="empty-state">
                                <i class="fas fa-inbox"></i>
                                <p>No hay jugadores conectados</p>
                            </div>
                        `);
                    }
                } else {
                    const emptyState = $('#playersContainer .empty-state');
                    if (emptyState.length > 0) {
                        emptyState.remove();
                    }
                    
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
                                <div class="player-item" data-player-id="${player.id}">
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
                                                <span class="player-detail-label">especialidad</span>
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
                            
                            $('#playersContainer').append(newItem);
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
                    
                    // Remover bans que ya no existen
                    bansContainer.find('.ban-item').each(function() {
                        const ip = $(this).data('ban-ip');
                        if (!serverIps.has(ip)) {
                            $(this).fadeOut(300, function() {
                                $(this).remove();
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
                            // Agregar nuevo ban sin animación
                            const banItem = `
                                <div class="ban-item" data-ban-ip="${ban.ip}">
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
            
            if (confirm(`¿Estás seguro de que deseas desbanear la IP ${banIp}?`)) {
                unbanIp(banIp, banItem);
            }
        });
    }

    function unbanIp(ip, banItem) {
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
                    
                    // Remover el item con animación
                    banItem.fadeOut(300, function() {
                        $(this).remove();
                        
                        // Actualizar contador
                        const newCount = $('#bansContainer .ban-item').length;
                        $('#banCount').text(newCount);
                        
                        // Mostrar mensaje vacío si no hay bans
                        if (newCount === 0) {
                            $('#bansContainer').html(`
                                <div class="empty-state">
                                    <i class="fas fa-check-circle"></i>
                                    <p>No hay jugadores baneados</p>
                                </div>
                            `);
                        }
                        
                        // Actualizar lista después de 1 segundo
                        setTimeout(updateBans, 1000);
                    });
                } else {
                    addConsoleMessage('error', `Error al desbanear ${ip}: ${response.error || 'Error desconocido'}`);
                    // Intentar actualizar de todas formas
                    setTimeout(updateBans, 1500);
                }
            },
            error: function(xhr) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    addConsoleMessage('error', `Error al desbanear (HTTP ${xhr.status}): ${errorData.error || 'Error desconocido'}`);
                } catch(e) {
                    addConsoleMessage('error', `Error de conexión: HTTP ${xhr.status}`);
                }
                // Actualizar lista después de error
                setTimeout(updateBans, 1500);
                console.error('Error details:', xhr);
            }
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
                    $(`#bansContainer .ban-item[data-ban-ip="${ip}"]`).fadeOut(300, function() {
                        $(this).remove();
                        updateBans();
                    });
                } else {
                    addConsoleMessage('error', `Error al desbanear ${ip}: ${response.error || 'Error desconocido'}`);
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
    function addConsoleMessage(type, text) {
        let span = '<span class="console-success">✓</span>';
        if (type === 'error') {
            span = '<span class="console-error">✗</span>';
        } else if (type === 'warning') {
            span = '<span class="console-warning">⚠</span>';
        }
        
        const line = `<div class="console-line">${span} ${text}</div>`;
        $('#consoleOutput').append(line);
        $('#consoleOutput').scrollTop($('#consoleOutput')[0].scrollHeight);
    }
    
    $('#consoleInput').on('keypress', function(e) {
        if (e.which === 13) {
            const command = $(this).val().trim();
            if (command) {
                addConsoleMessage('info', '> ' + command);
                
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
                        if (response.success) {
                            addConsoleMessage('success', 'Comando ejecutado correctamente');
                        } else {
                            addConsoleMessage('error', `Error ejecutando comando: ${response.error || 'Error desconocido'}`);
                        }
                    },
                    error: function(xhr) {
                        try {
                            const errorData = JSON.parse(xhr.responseText);
                            addConsoleMessage('error', `Error de ejecución: ${errorData.error || 'Error desconocido'}`);
                        } catch(e) {
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
        if (confirm('¿Estás seguro de que deseas limpiar el log?')) {
            $('#consoleOutput').html('<div class="console-line"><span class="console-success">✓</span> Log limpiado</div>');
            
            $.ajax({
                url: '/api/command',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    request: 'clear_log',
                    key: auth_key
                }),
                error: function() {
                    addConsoleMessage('error', 'Error al limpiar el log');
                }
            });
        }
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
    
    updateInterval = setInterval(() => {
        updatePlayers();
        updateServerInfo();
        updateBans();
    }, 5000);
    
    $(window).on('unload', function() {
        if (updateInterval) {
            clearInterval(updateInterval);
        }
    });
});
