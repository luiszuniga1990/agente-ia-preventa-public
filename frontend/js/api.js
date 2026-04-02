/**
 * Módulo de llamadas REST API
 * Gestiona historial de conversaciones, exportación y consolidación.
 */
const Api = (() => {
    const BASE_URL = APP_CONFIG.restApi.url;

    /**
     * Realiza una petición HTTP autenticada con JWT.
     * @param {string} endpoint - Ruta relativa del endpoint
     * @param {object} [options={}] - Opciones de fetch (method, body, etc.)
     * @returns {Promise<object>} Respuesta parseada como JSON
     * @private
     */
    async function _request(endpoint, options = {}) {
        const token = await Auth.getToken();

        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...(options.headers || {})
            }
        };

        const response = await fetch(`${BASE_URL}${endpoint}`, config);

        // Si el token expiró, redirigir a login
        if (response.status === 401) {
            App.showLogin('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
            throw new Error('No autorizado');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error?.message || `Error ${response.status}`);
        }

        return response.json();
    }

    // --- Historial de conversaciones ---

    /**
     * Lista las conversaciones del usuario ordenadas por fecha descendente.
     * @returns {Promise<Array>} Lista de conversaciones
     */
    async function listConversations() {
        return _request('/conversations');
    }

    /**
     * Obtiene el contenido completo de una conversación.
     * @param {string} conversationId - ID de la conversación
     * @returns {Promise<object>} Conversación con mensajes y estimaciones
     */
    async function getConversation(conversationId) {
        return _request(`/conversations/${conversationId}`);
    }

    // --- Estimaciones ---

    /**
     * Lista las estimaciones del usuario.
     * @returns {Promise<Array>} Lista de estimaciones
     */
    async function listEstimations() {
        return _request('/estimations');
    }

    /**
     * Obtiene el detalle de una estimación.
     * @param {string} estimationId - ID de la estimación
     * @returns {Promise<object>} Estimación completa
     */
    async function getEstimation(estimationId) {
        return _request(`/estimations/${estimationId}`);
    }

    // --- Exportación (PDF/CSV) ---

    /**
     * Solicita la exportación de una estimación y descarga el archivo.
     * @param {string} estimationId - ID de la estimación
     * @param {string} [format='pdf'] - Formato: 'pdf' o 'csv'
     * @param {string} [language='es'] - Idioma del documento
     * @returns {Promise<object>} Objeto con file_url para descarga
     */
    async function exportEstimation(estimationId, format = 'pdf', language = 'es') {
        const result = await _request(`/estimations/${estimationId}/export`, {
            method: 'POST',
            body: JSON.stringify({ format, language })
        });

        // Descargar automáticamente usando la URL pre-firmada
        if (result.file_url) {
            _downloadFile(result.file_url, `estimacion_${estimationId}.${format}`);
        }

        return result;
    }

    // --- Consolidación ---

    /**
     * Consolida una estimación con datos externos de un archivo JSON.
     * @param {string} estimationId - ID de la estimación interna
     * @param {object} externalJson - Datos del JSON externo parseado
     * @returns {Promise<object>} Estimación consolidada
     */
    async function consolidateEstimation(estimationId, externalJson) {
        return _request(`/estimations/${estimationId}/consolidate`, {
            method: 'POST',
            body: JSON.stringify({ external_json: externalJson })
        });
    }

    // --- Email ---

    /**
     * Envía una estimación por correo electrónico.
     * @param {string} estimationId - ID de la estimación
     * @param {string} recipientEmail - Correo del destinatario
     * @param {string} [language='es'] - Idioma del correo
     * @returns {Promise<object>} Resultado del envío
     */
    async function sendEstimationEmail(estimationId, recipientEmail, language = 'es') {
        return _request(`/estimations/${estimationId}/email`, {
            method: 'POST',
            body: JSON.stringify({ recipient_email: recipientEmail, language })
        });
    }

    // --- Carga de archivos JSON ---

    /**
     * Lee y valida un archivo JSON seleccionado por el usuario.
     * @param {File} file - Archivo seleccionado del input
     * @returns {Promise<object>} Contenido del JSON parseado
     */
    function readJsonFile(file) {
        return new Promise((resolve, reject) => {
            // Validar tamaño máximo
            if (file.size > APP_CONFIG.app.maxFileSize) {
                reject(new Error('El archivo excede el tamaño máximo permitido (1 MB)'));
                return;
            }

            // Validar extensión
            if (!file.name.toLowerCase().endsWith('.json')) {
                reject(new Error('Solo se permiten archivos con extensión .json'));
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    resolve(data);
                } catch (parseErr) {
                    reject(new Error('El archivo no contiene JSON válido'));
                }
            };
            reader.onerror = () => reject(new Error('Error al leer el archivo'));
            reader.readAsText(file);
        });
    }

    /**
     * Descarga un archivo desde una URL pre-firmada.
     * @param {string} url - URL pre-firmada de S3
     * @param {string} filename - Nombre sugerido para el archivo
     * @private
     */
    function _downloadFile(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    return {
        listConversations,
        getConversation,
        listEstimations,
        getEstimation,
        exportEstimation,
        consolidateEstimation,
        sendEstimationEmail,
        readJsonFile
    };
})();
