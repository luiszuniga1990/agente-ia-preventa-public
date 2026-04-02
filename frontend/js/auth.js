/**
 * Módulo de autenticación con Amazon Cognito
 * Gestiona login, logout, tokens JWT y refresh automático.
 */
const Auth = (() => {
    let _userPool = null;
    let _currentUser = null;
    let _refreshTimer = null;

    /**
     * Inicializa el User Pool de Cognito con la configuración.
     */
    function init() {
        const poolData = {
            UserPoolId: APP_CONFIG.cognito.userPoolId,
            ClientId: APP_CONFIG.cognito.clientId
        };
        _userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);
        _currentUser = _userPool.getCurrentUser();
    }

    /**
     * Inicia sesión con usuario y contraseña.
     * @param {string} username - Nombre de usuario
     * @param {string} password - Contraseña
     * @returns {Promise<object>} Resultado de autenticación con tokens
     */
    function login(username, password) {
        return new Promise((resolve, reject) => {
            const authDetails = new AmazonCognitoIdentity.AuthenticationDetails({
                Username: username,
                Password: password
            });

            const userData = {
                Username: username,
                Pool: _userPool
            };

            const cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);

            cognitoUser.authenticateUser(authDetails, {
                onSuccess: (result) => {
                    _currentUser = cognitoUser;
                    _startTokenRefresh();
                    resolve({
                        idToken: result.getIdToken().getJwtToken(),
                        accessToken: result.getAccessToken().getJwtToken(),
                        refreshToken: result.getRefreshToken().getToken()
                    });
                },
                onFailure: (err) => {
                    reject(err);
                },
                // Manejar caso de nuevo password requerido (primer login)
                newPasswordRequired: (userAttributes) => {
                    reject({
                        code: 'NewPasswordRequired',
                        message: 'Se requiere cambiar la contraseña.',
                        userAttributes,
                        cognitoUser
                    });
                }
            });
        });
    }

    /**
     * Cierra la sesión del usuario actual.
     */
    function logout() {
        if (_currentUser) {
            _currentUser.signOut();
        }
        _currentUser = null;
        _stopTokenRefresh();
    }

    /**
     * Obtiene el token JWT (ID Token) de la sesión actual.
     * @returns {Promise<string>} Token JWT
     */
    function getToken() {
        return new Promise((resolve, reject) => {
            if (!_currentUser) {
                _currentUser = _userPool.getCurrentUser();
            }

            if (!_currentUser) {
                reject(new Error('No hay sesión activa'));
                return;
            }

            _currentUser.getSession((err, session) => {
                if (err || !session || !session.isValid()) {
                    reject(new Error('Sesión expirada'));
                    return;
                }
                resolve(session.getIdToken().getJwtToken());
            });
        });
    }

    /**
     * Refresca el token JWT usando el refresh token.
     * @returns {Promise<string>} Nuevo token JWT
     */
    function refreshToken() {
        return new Promise((resolve, reject) => {
            if (!_currentUser) {
                reject(new Error('No hay sesión activa'));
                return;
            }

            _currentUser.getSession((err, session) => {
                if (err) {
                    reject(err);
                    return;
                }

                const refreshTokenObj = session.getRefreshToken();
                _currentUser.refreshSession(refreshTokenObj, (refreshErr, newSession) => {
                    if (refreshErr) {
                        reject(refreshErr);
                        return;
                    }
                    resolve(newSession.getIdToken().getJwtToken());
                });
            });
        });
    }

    /**
     * Verifica si hay una sesión activa válida.
     * @returns {Promise<boolean>}
     */
    function isAuthenticated() {
        return getToken()
            .then(() => true)
            .catch(() => false);
    }

    /**
     * Obtiene información del usuario actual desde el token.
     * @returns {Promise<object>} Datos del usuario (email, sub, etc.)
     */
    function getUserInfo() {
        return new Promise((resolve, reject) => {
            if (!_currentUser) {
                reject(new Error('No hay sesión activa'));
                return;
            }

            _currentUser.getUserAttributes((err, attributes) => {
                if (err) {
                    reject(err);
                    return;
                }

                const userInfo = {};
                attributes.forEach(attr => {
                    userInfo[attr.getName()] = attr.getValue();
                });
                resolve(userInfo);
            });
        });
    }

    /**
     * Inicia el temporizador de refresh automático de tokens.
     * @private
     */
    function _startTokenRefresh() {
        _stopTokenRefresh();
        _refreshTimer = setInterval(async () => {
            try {
                await refreshToken();
            } catch (err) {
                console.error('Error al refrescar token:', err);
                // Si falla el refresh, redirigir a login
                _stopTokenRefresh();
                if (typeof App !== 'undefined' && App.showLogin) {
                    App.showLogin('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
                }
            }
        }, APP_CONFIG.app.tokenRefreshInterval);
    }

    /**
     * Detiene el temporizador de refresh.
     * @private
     */
    function _stopTokenRefresh() {
        if (_refreshTimer) {
            clearInterval(_refreshTimer);
            _refreshTimer = null;
        }
    }

    return {
        init,
        login,
        logout,
        getToken,
        refreshToken,
        isAuthenticated,
        getUserInfo
    };
})();
