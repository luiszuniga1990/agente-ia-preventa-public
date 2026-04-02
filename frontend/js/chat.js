/**
 * Módulo de chat WebSocket
 * Gestiona la conexión WebSocket, envío/recepción de mensajes y reconexión automática.
 */
const Chat = (() => {
    let _socket = null;
    let _reconnectAttempts = 0;
    let _reconnectTimer = null;
    let _currentConversationId = null;
    let _onMessageCallback = null;
    let _onStatusChangeCallback = null;
    let _intentionalClose = false;

    /**
     * Conecta al WebSocket API con JWT en query string.
     * @returns {Promise<void>}
     */
    async function connect() {
        try {
            const token = await Auth.getToken();
            const wsUrl = `${APP_CONFIG.websocket.url}?token=${encodeURIComponent(token)}`;

            _intentionalClose = false;
            _socket = new WebSocket(wsUrl);

            _socket.onopen = _handleOpen;
            _socket.onmessage = _handleMessage;
            _socket.onclose = _handleClose;
            _socket.onerror = _handleError;
        } catch (err) {
            console.error('Error al conectar WebSocket:', err);
            _notifyStatus('error', 'No se pudo conectar al chat');
            // Si el token expiró, redirigir a login
            if (err.message && err.message.includes('expirada')) {
                App.showLogin('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
            }
        }
    }

    /**
     * Desconecta el WebSocket de forma intencional.
     */
    function disconnect() {
        _intentionalClose = true;
        _stopReconnect();
        if (_socket) {
            _socket.close();
            _socket = null;
        }
    }

    /**
     * Envía un mensaje al agente vía WebSocket.
     * @param {string} message - Texto del mensaje
     * @param {string} [conversationId] - ID de conversación existente (opcional)
     */
    function sendMessage(message, conversationId) {
        if (!_socket || _socket.readyState !== WebSocket.OPEN) {
            _notifyStatus('error', 'No hay conexión activa. Reconectando...');
            connect();
            return;
        }

        const payload = {
            action: 'sendMessage',
            message: message.trim()
        };

        if (conversationId || _currentConversationId) {
            payload.conversation_id = conversationId || _currentConversationId;
        }

        _socket.send(JSON.stringify(payload));
    }

    /**
     * Establece el ID de conversación actual.
     * @param {string|null} id
     */
    function setConversationId(id) {
        _currentConversationId = id;
    }

    /**
     * Obtiene el ID de conversación actual.
     * @returns {string|null}
     */
    function getConversationId() {
        return _currentConversationId;
    }

    /**
     * Registra callback para mensajes recibidos.
     * @param {Function} callback - Función que recibe el mensaje parseado
     */
    function onMessage(callback) {
        _onMessageCallback = callback;
    }

    /**
     * Registra callback para cambios de estado de conexión.
     * @param {Function} callback - Función que recibe (status, message)
     */
    function onStatusChange(callback) {
        _onStatusChangeCallback = callback;
    }

    /**
     * Verifica si el WebSocket está conectado.
     * @returns {boolean}
     */
    function isConnected() {
        return _socket && _socket.readyState === WebSocket.OPEN;
    }

    // --- Handlers internos ---

    /** @private */
    function _handleOpen() {
        _reconnectAttempts = 0;
        _notifyStatus('connected', 'Conectado al agente');
    }

    /** @private */
    function _handleMessage(event) {
        try {
            const data = JSON.parse(event.data);

            // Actualizar conversation_id si viene en la respuesta
            if (data.conversation_id) {
                _currentConversationId = data.conversation_id;
            }

            if (_onMessageCallback) {
                _onMessageCallback(data);
            }
        } catch (err) {
            console.error('Error al parsear mensaje WebSocket:', err);
        }
    }

    /** @private */
    function _handleClose(event) {
        _socket = null;

        if (_intentionalClose) {
            _notifyStatus('disconnected', 'Desconectado');
            return;
        }

        // Reconexión automática
        _notifyStatus('reconnecting', 'Conexión perdida. Reconectando...');
        _attemptReconnect();
    }

    /** @private */
    function _handleError(event) {
        console.error('Error en WebSocket:', event);
    }

    /**
     * Intenta reconectar con backoff exponencial.
     * @private
     */
    function _attemptReconnect() {
        if (_reconnectAttempts >= APP_CONFIG.app.maxReconnectAttempts) {
            _notifyStatus('error', 'No se pudo reconectar. Por favor, recarga la página.');
            return;
        }

        const delay = APP_CONFIG.app.reconnectBaseDelay * Math.pow(2, _reconnectAttempts);
        _reconnectAttempts++;

        _reconnectTimer = setTimeout(async () => {
            _notifyStatus('reconnecting', `Reconectando (intento ${_reconnectAttempts})...`);
            try {
                await connect();
            } catch (err) {
                // El handler onclose se encargará de reintentar
            }
        }, delay);
    }

    /**
     * Detiene los intentos de reconexión.
     * @private
     */
    function _stopReconnect() {
        if (_reconnectTimer) {
            clearTimeout(_reconnectTimer);
            _reconnectTimer = null;
        }
        _reconnectAttempts = 0;
    }

    /**
     * Notifica cambio de estado de conexión.
     * @private
     */
    function _notifyStatus(status, message) {
        if (_onStatusChangeCallback) {
            _onStatusChangeCallback(status, message);
        }
    }

    return {
        connect,
        disconnect,
        sendMessage,
        setConversationId,
        getConversationId,
        onMessage,
        onStatusChange,
        isConnected
    };
})();
