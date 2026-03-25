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
    let updateInterval = null;
    let selectedPlayerId = null;
    
    // ============= TAB SWITCHING =============
    $('.nav-item').on('click', function(e) {
        e.preventDefault();
        const tabName = $(this).data('tab');
        
        $('.nav-item').removeClass('active');
        $('.tab-content').removeClass('active');
        
        $(this).addClass('active');
        $('#' + tabName).addClass('active');
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
                
                playersData = {};
                const html = [];
                
                if (data.players.length === 0) {
                    html.push(`
                        <div class="empty-state">
                            <i class="fas fa-inbox"></i>
                            <p>No hay jugadores conectados</p>
                        </div>
                    `);
                } else {
                    data.players.forEach(player => {
                        playersData[player.id] = player;
                        
                        const className = ClassArray[player.klass] || "Desconocida";
                        const spec = player.klass > 0 && player.klass <= 4 
                            ? Specializations[player.klass - 1][player.specialz] || "Desconocida"
                            : "Desconocida";
                        
                        const firstLetter = (player.name || "?")[0].toUpperCase();
                        
                        html.push(`
                            <div class="player-item">
                                <div class="player-avatar">${firstLetter}</div>
                                <div class="player-info">
                                    <div class="player-name">${player.name} (ID: ${player.id})</div>
                                    <div class="player-details-row">
                                        <div class="player-detail-item">
                                            <span class="player-detail-label">Clase</span>
                                            <span class="player-detail-value">${className}</span>
                                        </div>
                                        <div class="player-detail-item">
                                            <span class="player-detail-label">Especialización</span>
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
                        `);
                    });
                }
                
                $('#playersContainer').html(html.join(''));
                $('#playerCount').text(data.count);
                
                // Attach action handlers
                attachPlayerActionHandlers();
                
            },
            error: function() {
                // Error silencioso, reintentar
            }
        });
    }
    
    function attachPlayerActionHandlers() {
        $('.btn-action').on('click', function() {
            const playerId = $(this).data('player-id');
            const action = $(this).data('action');
            const player = playersData[playerId];
            
            if (!player) return;
            
            if (action === 'heal') {
                healPlayer(playerId, player.name);
            } else if (action === 'kick') {
                selectedPlayerId = playerId;
                $('#kickPlayerName').text('Jugador: ' + player.name);
                $('#kickReason').val('');
                showModal('kickModal');
            } else if (action === 'ban') {
                selectedPlayerId = playerId;
                $('#banPlayerName').text('Jugador: ' + player.name);
                $('#banReason').val('');
                showModal('banModal');
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
            success: function() {
                addConsoleMessage('success', `Jugador ${playerName} sanado completamente`);
                updatePlayers();
            },
            error: function() {
                addConsoleMessage('error', `Error al sanar a ${playerName}`);
            }
        });
    }
    
    $('#kickConfirmBtn').on('click', function() {
        const reason = $('#kickReason').val().trim();
        if (!reason) {
            alert('Por favor, proporciona una razón');
            return;
        }
        
        const playerName = playersData[selectedPlayerId].name;
        
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
            success: function() {
                addConsoleMessage('success', `Jugador ${playerName} expulsado. Razón: ${reason}`);
                hideModal('kickModal');
                updatePlayers();
            },
            error: function() {
                addConsoleMessage('error', `Error al expulsar a ${playerName}`);
            }
        });
    });
    
    $('#banConfirmBtn').on('click', function() {
        const reason = $('#banReason').val().trim();
        if (!reason) {
            alert('Por favor, proporciona una razón');
            return;
        }
        
        const playerName = playersData[selectedPlayerId].name;
        
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
            success: function() {
                addConsoleMessage('success', `Jugador ${playerName} baneado. Razón: ${reason}`);
                hideModal('banModal');
                updatePlayers();
            },
            error: function() {
                addConsoleMessage('error', `Error al banear a ${playerName}`);
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
            error: function() {
                // Error silencioso
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
                        addConsoleMessage('success', 'Comando ejecutado');
                    },
                    error: function() {
                        addConsoleMessage('error', 'Error al ejecutar comando');
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
                    // Error silencioso
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
                        $(this).val('');
                        addChatMessage('cuwo', message, 'user');
                    }
                });
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
    
    updateInterval = setInterval(() => {
        updatePlayers();
        updateServerInfo();
    }, 2000);
    
    // Clean up on unload
    $(window).on('unload', function() {
        if (updateInterval) {
            clearInterval(updateInterval);
        }
    });
});
