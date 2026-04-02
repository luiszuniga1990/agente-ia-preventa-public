/**
 * Configuración de la aplicación - Agente IA Preventa
 * Reemplazar los valores placeholder con los valores reales del entorno desplegado.
 */
const APP_CONFIG = {
    // Amazon Cognito
    cognito: {
        userPoolId: 'us-east-1_XXXXXXXXX',       // ID del User Pool de Cognito
        clientId: 'XXXXXXXXXXXXXXXXXXXXXXXXXX',    // ID del cliente de la app
        region: 'us-east-1'
    },

    // WebSocket API (API Gateway)
    websocket: {
        url: 'wss://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod'
    },

    // REST API (API Gateway)
    restApi: {
        url: 'https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod'
    },

    // Configuración general
    app: {
        name: 'Agente IA Preventa',
        maxReconnectAttempts: 5,       // Intentos máximos de reconexión WebSocket
        reconnectBaseDelay: 1000,      // Delay base en ms para reconexión (backoff exponencial)
        tokenRefreshInterval: 300000,  // Refrescar token cada 5 minutos
        maxFileSize: 1048576           // Tamaño máximo de archivo JSON: 1 MB
    }
};
