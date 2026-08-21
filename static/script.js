/* ════════════════════════════════════════════════════════════ */
/* NEXUS Web Interface — JavaScript */
/* ════════════════════════════════════════════════════════════ */

// ═════════════════════════════════════════════════════════════
// ESTADO GLOBAL
// ═════════════════════════════════════════════════════════════

let ws = null;
let isConnected = false;
let messageCount = 0;
const API_BASE = window.location.origin;

// ═════════════════════════════════════════════════════════════
// INICIALIZAÇÃO
// ═════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    loadStatus();
    loadLearning();
    loadPlugins();
    loadKB();
    setupEventListeners();
    loadTheme();
});

function setupEventListeners() {
    const userInput = document.getElementById('user-input');
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// ═════════════════════════════════════════════════════════════
// WEBSOCKET
// ═════════════════════════════════════════════════════════════

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
    
    ws = new WebSocket(wsUrl);
    
    ws.addEventListener('open', () => {
        console.log('✅ WebSocket conectado');
        isConnected = true;
        updateConnectionStatus(true);
        addSystemMessage('✅ Conectado ao NEXUS!');
    });
    
    ws.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    });
    
    ws.addEventListener('close', () => {
        console.log('❌ WebSocket desconectado');
        isConnected = false;
        updateConnectionStatus(false);
        addSystemMessage('❌ Desconectado. Reconectando em 3s...', 'error');
        setTimeout(initWebSocket, 3000);
    });
    
    ws.addEventListener('error', (error) => {
        console.error('WebSocket erro:', error);
        updateConnectionStatus(false);
    });
}

function handleWebSocketMessage(data) {
    if (data.type === 'status') {
        addSystemMessage(data.message, 'loading');
    } else if (data.type === 'response') {
        removeLastMessage(); // Remove o "Processando..."
        addSystemMessage(data.message);
        document.getElementById('kb-count').textContent = `${data.kb_entries} entradas`;
        updateScore(data.score);
    } else if (data.type === 'error') {
        removeLastMessage();
        addSystemMessage(data.message, 'error');
    }
}

function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connection-status');
    if (connected) {
        indicator.textContent = '● Conectado';
        indicator.classList.remove('offline');
        indicator.classList.add('online');
    } else {
        indicator.textContent = '● Desconectado';
        indicator.classList.remove('online');
        indicator.classList.add('offline');
    }
}

// ═════════════════════════════════════════════════════════════
// CHAT
// ═════════════════════════════════════════════════════════════

function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    
    if (!message) return;
    
    if (!isConnected) {
        addSystemMessage('❌ Não conectado ao NEXUS', 'error');
        return;
    }
    
    // Adicionar mensagem do usuário
    addUserMessage(message);
    userInput.value = '';
    
    // Enviar via WebSocket
    ws.send(JSON.stringify({ message }));
}

function quickCommand(cmd) {
    document.getElementById('user-input').value = cmd;
    sendMessage();
}

function addUserMessage(text) {
    const messagesDiv = document.getElementById('messages');
    const messageEl = document.createElement('div');
    messageEl.className = 'message user';
    messageEl.innerHTML = `
        <div class="message-content">
            ${escapeHtml(text)}
        </div>
    `;
    messagesDiv.appendChild(messageEl);
    scrollToBottom();
    messageCount++;
}

function addSystemMessage(text, type = 'system') {
    const messagesDiv = document.getElementById('messages');
    const messageEl = document.createElement('div');
    
    if (type === 'loading') {
        messageEl.className = 'message system loading';
        messageEl.innerHTML = `
            <div class="message-content">
                <span>${text}</span>
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
    } else if (type === 'error') {
        messageEl.className = 'message system error';
        messageEl.innerHTML = `
            <div class="message-content">
                ${markdownToHtml(text)}
            </div>
        `;
    } else {
        messageEl.className = 'message system';
        messageEl.innerHTML = `
            <div class="message-content">
                ${markdownToHtml(text)}
            </div>
        `;
    }
    
    messagesDiv.appendChild(messageEl);
    scrollToBottom();
}

function removeLastMessage() {
    const messages = document.getElementById('messages');
    const lastMessage = messages.lastElementChild;
    if (lastMessage && lastMessage.classList.contains('loading')) {
        lastMessage.remove();
    }
}

function scrollToBottom() {
    const chatContainer = document.querySelector('.chat-container');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ═════════════════════════════════════════════════════════════
// STATUS E STATS
// ═════════════════════════════════════════════════════════════

async function loadStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();
        
        const statusContent = `
            <div class="status-item">
                <span class="status-label">LLM:</span>
                <span class="status-value">${data.llm.provider}/${data.llm.model}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Perfil:</span>
                <span class="status-value">${data.profile}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Cores:</span>
                <span class="status-value">${data.hardware.cores}</span>
            </div>
            <div class="status-item">
                <span class="status-label">RAM:</span>
                <span class="status-value">${data.hardware.ram_mb}MB</span>
            </div>
            <div class="status-item">
                <span class="status-label">Uptime:</span>
                <span class="status-value">${data.uptime}</span>
            </div>
        `;
        
        document.getElementById('status-content').innerHTML = statusContent;
    } catch (error) {
        console.error('Erro ao carregar status:', error);
        document.getElementById('status-content').innerHTML = '❌ Erro ao carregar';
    }
}

async function loadLearning() {
    try {
        const response = await fetch(`${API_BASE}/api/learning`);
        const data = await response.json();
        
        const learningContent = `
            <div class="metric">
                <span class="metric-label">Score:</span>
                <span class="metric-value">${(data.score * 100).toFixed(1)}%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Reflexões:</span>
                <span class="metric-value">${data.total_reflections}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Taxa Sucesso:</span>
                <span class="metric-value">${(data.recent_success_rate * 100).toFixed(0)}%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Padrões Erro:</span>
                <span class="metric-value">${data.error_patterns}</span>
            </div>
        `;
        
        document.getElementById('learning-content').innerHTML = learningContent;
    } catch (error) {
        console.error('Erro ao carregar learning:', error);
        document.getElementById('learning-content').innerHTML = '❌ Erro ao carregar';
    }
}

function updateScore(newScore) {
    const scoreElement = document.querySelector('.metric-value');
    if (scoreElement) {
        scoreElement.textContent = `${(newScore * 100).toFixed(1)}%`;
    }
}

// ═════════════════════════════════════════════════════════════
// CONHECIMENTO
// ═════════════════════════════════════════════════════════════

async function loadKB() {
    try {
        const response = await fetch(`${API_BASE}/api/kb`);
        const data = await response.json();
        
        document.getElementById('kb-count').textContent = `${data.total} entradas`;
        
        // Carregar modal
        let kbHtml = '';
        data.recent.forEach(entry => {
            kbHtml += `
                <div class="kb-entry">
                    <div class="kb-entry-title">${escapeHtml(entry.title)}</div>
                    <div class="kb-entry-source">[${entry.source}]</div>
                    <div class="kb-entry-content">${escapeHtml(entry.content.substring(0, 200))}</div>
                </div>
            `;
        });
        
        document.getElementById('kb-modal-content').innerHTML = kbHtml || '<p>Base de conhecimento vazia</p>';
    } catch (error) {
        console.error('Erro ao carregar KB:', error);
        document.getElementById('kb-count').textContent = '? entradas';
    }
}

function toggleKB() {
    const modal = document.getElementById('kb-modal');
    modal.classList.toggle('show');
    if (modal.classList.contains('show')) {
        loadKB();
    }
}

// ═════════════════════════════════════════════════════════════
// PLUGINS
// ═════════════════════════════════════════════════════════════

async function loadPlugins() {
    try {
        const response = await fetch(`${API_BASE}/api/plugins`);
        const data = await response.json();
        
        let pluginsHtml = '';
        data.plugins.forEach(plugin => {
            pluginsHtml += `
                <div class="plugin-item">
                    <span class="plugin-name">${plugin}</span>
                    <button class="plugin-btn" onclick="executePlugin('${plugin}')">Executar</button>
                </div>
            `;
        });
        
        document.getElementById('plugins-list').innerHTML = pluginsHtml || '<p>Nenhum plugin</p>';
    } catch (error) {
        console.error('Erro ao carregar plugins:', error);
        document.getElementById('plugins-list').innerHTML = '❌ Erro ao carregar';
    }
}

async function executePlugin(pluginName) {
    if (!isConnected) {
        addSystemMessage('❌ Não conectado ao NEXUS', 'error');
        return;
    }
    
    addSystemMessage(`Executando plugin: ${pluginName}`, 'loading');
    
    try {
        const response = await fetch(`${API_BASE}/api/plugin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: pluginName })
        });
        const data = await response.json();
        
        removeLastMessage();
        
        if (data.success) {
            const resultText = `\`\`\`json\n${JSON.stringify(data.result, null, 2)}\n\`\`\``;
            addSystemMessage(`✅ **Plugin: ${pluginName}**\n\n${resultText}`);
        } else {
            addSystemMessage(`❌ Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        removeLastMessage();
        addSystemMessage(`❌ Erro ao executar plugin: ${error.message}`, 'error');
    }
}

// ═════════════════════════════════════════════════════════════
// AÇÕES
// ═════════════════════════════════════════════════════════════

async function clearMemory() {
    if (confirm('Limpar memória da sessão?')) {
        try {
            await fetch(`${API_BASE}/api/clear-memory`, { method: 'POST' });
            addSystemMessage('🧹 Memória limpa!');
        } catch (error) {
            addSystemMessage(`❌ Erro: ${error.message}`, 'error');
        }
    }
}

function toggleTheme() {
    const isDark = !document.body.classList.contains('light-mode');
    if (isDark) {
        document.body.classList.add('light-mode');
        localStorage.setItem('theme', 'light');
    } else {
        document.body.classList.remove('light-mode');
        localStorage.setItem('theme', 'dark');
    }
}

function loadTheme() {
    const theme = localStorage.getItem('theme') || 'dark';
    if (theme === 'light') {
        document.body.classList.add('light-mode');
    }
}

// ═════════════════════════════════════════════════════════════
// UTILIDADES
// ═════════════════════════════════════════════════════════════

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

function markdownToHtml(text) {
    // Converter markdown simples para HTML
    
    // Links
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color: var(--primary);">$1</a>');
    
    // Bold
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // Code blocks
    text = text.replace(/```([\s\S]*?)```/g, '<pre style="background: var(--bg-light); padding: 10px; border-radius: 6px; overflow-x: auto;"><code>$1</code></pre>');
    text = text.replace(/`([^`]+)`/g, '<code style="background: var(--bg-light); padding: 2px 6px; border-radius: 3px;">$1</code>');
    
    // Headers
    text = text.replace(/### ([^\n]+)/g, '<h3 style="color: var(--primary); margin-top: 10px;">$1</h3>');
    text = text.replace(/## ([^\n]+)/g, '<h2 style="color: var(--primary); margin-top: 10px;">$1</h2>');
    text = text.replace(/# ([^\n]+)/g, '<h1 style="color: var(--primary); margin-top: 10px;">$1</h1>');
    
    // Lists
    text = text.replace(/\n- ([^\n]+)/g, '<li style="margin-left: 20px;">$1</li>');
    text = text.replace(/(<li[^>]*>.*?<\/li>)/s, '<ul style="margin: 10px 0;">$1</ul>');
    
    // Line breaks
    text = text.replace(/\n\n/g, '</p><p style="margin: 10px 0;">');
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// ═════════════════════════════════════════════════════════════
// AUTO-REFRESH
// ═════════════════════════════════════════════════════════════

setInterval(() => {
    if (messageCount % 5 === 0) {
        loadStatus();
        loadLearning();
    }
}, 10000);
