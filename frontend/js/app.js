/**
 * Módulo principal de la aplicación - Agente IA Preventa
 * Gestiona la inicialización, navegación entre vistas y lógica de UI.
 */
const App = (() => {
    // --- Referencias a elementos del DOM ---
    let _els = {};

    /**
     * Inicializa la aplicación: auth, eventos y estado inicial.
     */
    async function init() {
        _cacheElements();
        _bindEvents();
        Auth.init();

        // Verificar si hay sesión activa
        const authenticated = await Auth.isAuthenticated();
        if (authenticated) {
            await _enterApp();
        } else {
            showLogin();
        }
    }

    /**
     * Cachea referencias a elementos del DOM para evitar queries repetidas.
     * @private
     */
    function _cacheElements() {
        _els = {
            // Vistas principales
            loginView: document.getElementById('login-view'),
            appView: document.getElementById('app-view'),

            // Login
            loginForm: document.getElementById('login-form'),
            loginUsername: document.getElementById('login-username'),
            loginPassword: document.getElementById('login-password'),
            loginError: document.getElementById('login-error'),
            loginBtn: document.getElementById('login-btn'),

            // Header
            userEmail: document.getElementById('user-email'),
            logoutBtn: document.getElementById('logout-btn'),

            // Sidebar
            newChatBtn: document.getElementById('new-chat-btn'),
            conversationList: document.getElementById('conversation-list'),
            historyBtn: document.getElementById('history-btn'),

            // Chat
            chatMessages: document.getElementById('chat-messages'),
            chatInput: document.getElementById('chat-input'),
            sendBtn: document.getElementById('send-btn'),
            connectionStatus: document.getElementById('connection-status'),

            // Panel de acciones (exportar, consolidar)
            actionsPanel: document.getElementById('actions-panel'),
            exportPdfBtn: document.getElementById('export-pdf-btn'),
            exportCsvBtn: document.getElementById('export-csv-btn'),
            uploadJsonBtn: document.getElementById('upload-json-btn'),
            jsonFileInput: document.getElementById('json-file-input'),

            // Modal / notificaciones
            notification: document.getElementById('notification')
        };
    }

    /**
     * Vincula eventos de UI a sus handlers.
     * @private
     */
    function _bindEvents() {
        // Login
        _els.loginForm?.addEventListener('submit', _handleLogin);

        // Logout
        _els.logoutBtn?.addEventListener('click', _handleLogout);

        // Chat
        _els.sendBtn?.addEventListener('click', _handleSendMessage);
        _els.chatInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                _handleSendMessage();
            }
        });

        // Nueva conversación
        _els.newChatBtn?.addEventListener('click', _handleNewChat);

        // Historial
        _els.historyBtn?.addEventListener('click', _handleLoadHistory);

        // Exportación
        _els.exportPdfBtn?.addEventListener('click', () => _handleExport('pdf'));
        _els.exportCsvBtn?.addEventListener('click', () => _handleExport('csv'));

        // Consolidación (carga de JSON)
        _els.uploadJsonBtn?.addEventListener('click', () => _els.jsonFileInput?.click());
        _els.jsonFileInput?.addEventListener('change', _handleJsonUpload);

        // Callbacks del chat WebSocket
        Chat.onMessage(_handleIncomingMessage);
        Chat.onStatusChange(_handleConnectionStatus);
    }

    // --- Gestión de vistas ---

    /**
     * Muestra la vista de login con mensaje opcional.
     * @param {string} [message] - Mensaje informativo (ej: sesión expirada)
     */
    function showLogin(message) {
        _els.loginView.classList.remove('hidden');
        _els.appView.classList.add('hidden');
        _els.loginError.textContent = message || '';
        _els.loginError.classList.toggle('hidden', !message);
        _els.loginUsername.value = '';
        _els.loginPassword.value = '';
        Chat.disconnect();
    }

    /**
     * Entra a la aplicación principal después de autenticarse.
     * @private
     */
    async function _enterApp() {
        _els.loginView.classList.add('hidden');
        _els.appView.classList.remove('hidden');

        // Mostrar email del usuario
        try {
            const userInfo = await Auth.getUserInfo();
            _els.userEmail.textContent = userInfo.email || userInfo.sub || 'Usuario';
        } catch {
            _els.userEmail.textContent = 'Usuario';
        }

        // Conectar WebSocket
        await Chat.connect();

        // Cargar historial de conversaciones en sidebar
        _loadConversationsSidebar();
    }

    // --- Handlers de eventos ---

    /**
     * Maneja el envío del formulario de login.
     * @param {Event} e
     * @private
     */
    async function _handleLogin(e) {
        e.preventDefault();
        const username = _els.loginUsername.value.trim();
        const password = _els.loginPassword.value;

        if (!username || !password) {
            _showLoginError('Por favor, ingresa usuario y contraseña.');
            return;
        }

        _els.loginBtn.disabled = true;
        _els.loginBtn.textContent = 'Iniciando sesión...';
        _els.loginError.classList.add('hidden');

        try {
            await Auth.login(username, password);
            await _enterApp();
        } catch (err) {
            let msg = 'Error al iniciar sesión.';
            if (err.code === 'NotAuthorizedException') {
                msg = 'Credenciales incorrectas. Verifica tu usuario y contraseña.';
            } else if (err.code === 'UserNotFoundException') {
                msg = 'Usuario no encontrado.';
            } else if (err.code === 'NewPasswordRequired') {
                msg = 'Se requiere cambiar la contraseña en el primer inicio de sesión.';
            } else if (err.message) {
                msg = err.message;
            }
            _showLoginError(msg);
        } finally {
            _els.loginBtn.disabled = false;
            _els.loginBtn.textContent = 'Iniciar Sesión';
        }
    }

    /**
     * Maneja el cierre de sesión.
     * @private
     */
    function _handleLogout() {
        Auth.logout();
        Chat.disconnect();
        showLogin();
    }

    /**
     * Maneja el envío de un mensaje de chat.
     * @private
     */
    function _handleSendMessage() {
        const message = _els.chatInput.value.trim();
        if (!message) return;

        // Mostrar mensaje del usuario en la UI
        _appendMessage('user', message);
        _els.chatInput.value = '';
        _els.chatInput.focus();

        // Mostrar indicador de escritura
        _showTypingIndicator();

        // Enviar por WebSocket
        Chat.sendMessage(message);
    }

    /**
     * Maneja mensajes recibidos del agente vía WebSocket.
     * @param {object} data - Mensaje parseado del WebSocket
     * @private
     */
    function _handleIncomingMessage(data) {
        _hideTypingIndicator();

        if (data.type === 'error') {
            _appendMessage('system', `Error: ${data.error?.message || 'Error desconocido'}`);
            return;
        }

        // Respuesta normal del agente
        const response = data.response || data.message || '';
        _appendMessage('agent', response);

        // Si la respuesta incluye una estimación, mostrar panel de acciones
        if (data.estimation_id) {
            _showActionsPanel(data.estimation_id);
        }
    }

    /**
     * Maneja cambios de estado de la conexión WebSocket.
     * @param {string} status - Estado: connected, disconnected, reconnecting, error
     * @param {string} message - Mensaje descriptivo
     * @private
     */
    function _handleConnectionStatus(status, message) {
        const el = _els.connectionStatus;
        el.textContent = message;
        el.className = 'connection-status';

        switch (status) {
            case 'connected':
                el.classList.add('status-connected');
                break;
            case 'reconnecting':
                el.classList.add('status-reconnecting');
                break;
            case 'error':
            case 'disconnected':
                el.classList.add('status-error');
                break;
        }
    }

    /**
     * Inicia una nueva conversación.
     * @private
     */
    function _handleNewChat() {
        Chat.setConversationId(null);
        _els.chatMessages.innerHTML = '';
        _hideActionsPanel();
        _appendMessage('system', '¡Nueva conversación iniciada! ¿En qué servicio te puedo ayudar? (Amazon Quick, Amazon Connect, Amazon Bedrock AgentCore)');
        _els.chatInput.focus();
    }

    /**
     * Carga el historial de conversaciones en el sidebar.
     * @private
     */
    async function _handleLoadHistory() {
        try {
            const conversations = await Api.listConversations();
            _renderConversationList(conversations);
        } catch (err) {
            _showNotification('Error al cargar historial: ' + err.message, 'error');
        }
    }

    /**
     * Maneja la exportación de estimaciones.
     * @param {string} format - 'pdf' o 'csv'
     * @private
     */
    async function _handleExport(format) {
        const estimationId = _els.actionsPanel?.dataset.estimationId;
        if (!estimationId) {
            _showNotification('No hay estimación para exportar.', 'error');
            return;
        }

        try {
            _showNotification(`Generando ${format.toUpperCase()}...`, 'info');
            await Api.exportEstimation(estimationId, format);
            _showNotification(`${format.toUpperCase()} descargado correctamente.`, 'success');
        } catch (err) {
            _showNotification('Error al exportar: ' + err.message, 'error');
        }
    }

    /**
     * Maneja la carga de un archivo JSON para consolidación.
     * @param {Event} e
     * @private
     */
    async function _handleJsonUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const estimationId = _els.actionsPanel?.dataset.estimationId;
        if (!estimationId) {
            _showNotification('No hay estimación para consolidar.', 'error');
            return;
        }

        try {
            _showNotification('Procesando archivo JSON...', 'info');
            const jsonData = await Api.readJsonFile(file);
            const result = await Api.consolidateEstimation(estimationId, jsonData);
            _showNotification('Estimación consolidada correctamente.', 'success');

            // Mostrar resumen de consolidación en el chat
            _appendMessage('system', _formatConsolidationSummary(result));
        } catch (err) {
            _showNotification('Error al consolidar: ' + err.message, 'error');
        } finally {
            // Limpiar input para permitir subir el mismo archivo de nuevo
            e.target.value = '';
        }
    }

    // --- Funciones de renderizado ---

    /**
     * Agrega un mensaje al área de chat.
     * @param {string} role - 'user', 'agent' o 'system'
     * @param {string} content - Contenido del mensaje
     */
    function _appendMessage(role, content) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message message-${role}`;
        msgDiv.setAttribute('role', 'log');

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = _formatMessageContent(content, role);

        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = new Date().toLocaleTimeString();

        msgDiv.appendChild(contentDiv);
        msgDiv.appendChild(timeSpan);
        _els.chatMessages.appendChild(msgDiv);

        // Auto-scroll al último mensaje
        _els.chatMessages.scrollTop = _els.chatMessages.scrollHeight;
    }

    /**
     * Formatea el contenido del mensaje para mostrar tablas, listas, etc.
     * @param {string} content - Texto del mensaje
     * @param {string} role - Rol del emisor
     * @returns {string} HTML formateado
     * @private
     */
    function _formatMessageContent(content, role) {
        if (role === 'user') {
            return _escapeHtml(content);
        }

        // Para mensajes del agente, formatear markdown básico
        let html = _escapeHtml(content);

        // Tablas simples (detectar líneas con |)
        html = html.replace(/^(\|.+\|)$/gm, (match) => {
            return `<span class="table-row">${match}</span>`;
        });

        // Negritas **texto**
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Listas con -
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

        // Saltos de línea
        html = html.replace(/\n/g, '<br>');

        return html;
    }

    /**
     * Escapa caracteres HTML para prevenir XSS.
     * @param {string} text
     * @returns {string}
     * @private
     */
    function _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Muestra el indicador de que el agente está escribiendo.
     * @private
     */
    function _showTypingIndicator() {
        _hideTypingIndicator();
        const indicator = document.createElement('div');
        indicator.id = 'typing-indicator';
        indicator.className = 'message message-agent typing';
        indicator.setAttribute('aria-live', 'polite');
        indicator.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
        _els.chatMessages.appendChild(indicator);
        _els.chatMessages.scrollTop = _els.chatMessages.scrollHeight;
    }

    /**
     * Oculta el indicador de escritura.
     * @private
     */
    function _hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    }

    /**
     * Renderiza la lista de conversaciones en el sidebar.
     * @param {Array} conversations
     * @private
     */
    function _renderConversationList(conversations) {
        _els.conversationList.innerHTML = '';

        if (!conversations || conversations.length === 0) {
            _els.conversationList.innerHTML = '<p class="empty-list">No hay conversaciones anteriores.</p>';
            return;
        }

        conversations.forEach(conv => {
            const item = document.createElement('button');
            item.className = 'conversation-item';
            item.setAttribute('aria-label', `Conversación del ${new Date(conv.created_at).toLocaleDateString()}`);

            const date = new Date(conv.created_at).toLocaleDateString('es-ES', {
                day: '2-digit', month: 'short', year: 'numeric'
            });
            const preview = conv.messages?.[0]?.content?.substring(0, 50) || 'Sin mensajes';

            item.innerHTML = `
                <span class="conv-date">${date}</span>
                <span class="conv-preview">${_escapeHtml(preview)}...</span>
            `;

            item.addEventListener('click', () => _loadConversation(conv.conversation_id));
            _els.conversationList.appendChild(item);
        });
    }

    /**
     * Carga una conversación completa del historial.
     * @param {string} conversationId
     * @private
     */
    async function _loadConversation(conversationId) {
        try {
            const conv = await Api.getConversation(conversationId);
            Chat.setConversationId(conversationId);
            _els.chatMessages.innerHTML = '';

            // Renderizar todos los mensajes de la conversación
            if (conv.messages) {
                conv.messages.forEach(msg => {
                    _appendMessage(msg.role === 'user' ? 'user' : 'agent', msg.content);
                });
            }
        } catch (err) {
            _showNotification('Error al cargar conversación: ' + err.message, 'error');
        }
    }

    /**
     * Carga las conversaciones recientes en el sidebar.
     * @private
     */
    async function _loadConversationsSidebar() {
        try {
            const conversations = await Api.listConversations();
            _renderConversationList(conversations);
        } catch {
            // Silenciar error en carga inicial del sidebar
        }
    }

    /**
     * Muestra el panel de acciones (exportar, consolidar).
     * @param {string} estimationId
     * @private
     */
    function _showActionsPanel(estimationId) {
        if (_els.actionsPanel) {
            _els.actionsPanel.classList.remove('hidden');
            _els.actionsPanel.dataset.estimationId = estimationId;
        }
    }

    /**
     * Oculta el panel de acciones.
     * @private
     */
    function _hideActionsPanel() {
        if (_els.actionsPanel) {
            _els.actionsPanel.classList.add('hidden');
            delete _els.actionsPanel.dataset.estimationId;
        }
    }

    /**
     * Formatea el resumen de consolidación para mostrar en el chat.
     * @param {object} result - Resultado de la consolidación
     * @returns {string}
     * @private
     */
    function _formatConsolidationSummary(result) {
        let summary = '📊 **Estimación consolidada:**\n';
        summary += `- Costo mensual total: $${result.total_monthly_cost?.toFixed(2) || 'N/A'}\n`;
        summary += `- Costo anual total: $${result.total_annual_cost?.toFixed(2) || 'N/A'}\n`;

        if (result.external_estimations?.length) {
            summary += '\nEstimaciones externas incluidas:\n';
            result.external_estimations.forEach(ext => {
                summary += `- ${ext.service_name}: $${ext.monthly_cost?.toFixed(2)}/mes\n`;
            });
        }

        return summary;
    }

    /**
     * Muestra una notificación temporal.
     * @param {string} message - Texto de la notificación
     * @param {string} [type='info'] - Tipo: 'info', 'success', 'error'
     */
    function _showNotification(message, type = 'info') {
        const el = _els.notification;
        if (!el) return;

        el.textContent = message;
        el.className = `notification notification-${type}`;
        el.classList.remove('hidden');
        el.setAttribute('role', 'alert');

        // Ocultar después de 4 segundos
        setTimeout(() => {
            el.classList.add('hidden');
        }, 4000);
    }

    /**
     * Muestra un error en el formulario de login.
     * @param {string} message
     * @private
     */
    function _showLoginError(message) {
        _els.loginError.textContent = message;
        _els.loginError.classList.remove('hidden');
    }

    return {
        init,
        showLogin
    };
})();

// Inicializar la aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => App.init());
