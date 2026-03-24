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
    
    // ============= TAB SWITCHING =============
    $('.nav-item').on('click', function(e) {
        e.preventDefault();
        const tabName = $(this).data('tab');
        
        // Remove active class from all
        $('.nav-item').removeClass('active');
        $('.tab-content').removeClass('active');
        
        // Add active class
        $(this).addClass('active');
        $('#' + tabName).addClass('active');
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
                            <div class="player-card">
                                <div class="player-header">
                                    <div class="player-avatar">${firstLetter}</div>
                                    <div class="player-name">
                                        <div class="name">${player.name}</div>
                                        <div class="id">ID: ${player.id}</div>
                                    </div>
                                    <div class="player-level">Lv. ${player.level}</div>
                                </div>
                                <div class="player-details">
                                    <div class="detail-item">
                                        <div class="label">Clase</div>
                                        <div class="value">${className}</div>
                                    </div>
                                    <div class="detail-item">
                                        <div class="label">Especialización</div>
                                        <div class="value">${spec}</div>
                                    </div>
                                    <div class="detail-item">
                                        <div class="label">Salud</div>
                                        <div class="value">${player.hp} HP</div>
                                    </div>
                                    <div class="detail-item">
                                        <div class="label">Posición</div>
                                        <div class="value">X:${player.x || 0}</div>
                                    </div>
                                </div>
                            </div>
                        `);
                    });
                }
                
                $('#playersContainer').html(html.join(''));
                $('#playerCount').text(data.count);
                
            },
            error: function() {
                // Error silencioso, reintentar
            }
        });
    }
    
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
                        $('#chatInput').val('');
                        addChatMessage('TU', message, 'user');
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
        const messageHtml = `
            <div class="chat-message ${type}">
                <span class="message-author">${author}</span>
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
