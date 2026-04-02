# Plan de Implementación: Agente IA Preventa

## Resumen

Implementación incremental de un chatbot serverless en AWS (Python) para generación de estimaciones de costos de Amazon Quick, Amazon Connect y Amazon Bedrock AgentCore. Cada tarea construye sobre las anteriores, integrando componentes progresivamente hasta el flujo completo.

## Tareas

- [x] 1. Estructura del proyecto y módulos base
  - [x] 1.1 Crear estructura de directorios y archivos de configuración
    - Crear carpetas: `src/`, `src/handlers/`, `src/services/`, `src/models/`, `src/utils/`, `tests/unit/`, `tests/property/`
    - Crear `requirements.txt` con dependencias: `boto3`, `reportlab` (PDF), `hypothesis`, `pytest`, `moto`, `pytest-cov`
    - Crear `conftest.py` con fixtures compartidos y mocks de AWS (DynamoDB, SES, S3, Bedrock)
    - _Requisitos: 15.1, 16.1_

  - [x] 1.2 Definir modelos de datos e interfaces core
    - Crear `src/models/conversation.py` con dataclass `Conversation` (conversation_id, user_id, messages, language, status, created_at, updated_at)
    - Crear `src/models/estimation.py` con dataclass `Estimation` (estimation_id, service, monthly_cost, annual_cost, breakdown, assumptions, partner_data, pricing_date, etc.)
    - Crear `src/models/partner.py` con dataclass `PartnerData` (partner_name, partner_email, region, end_customer)
    - Crear `src/models/pricing.py` con dataclass `PricingEntry` (service_id, component, unit_price, unit, last_updated)
    - Definir constantes `SUPPORTED_SERVICES = ["amazon_quick", "amazon_connect", "bedrock_agentcore"]` y `SUPPORTED_LANGUAGES = ["es", "en", "pt", "de"]`
    - _Requisitos: 3.1, 4.1, 5.1, 6.1, 9.1_

  - [x] 1.3 Implementar módulo de validación (`src/utils/validators.py`)
    - Función `validate_email(email: str) -> bool`: validar formato estándar de email (un `@`, dominio con `.`, sin espacios)
    - Función `validate_partner_data(data: dict) -> tuple[bool, list[str]]`: verificar campos obligatorios (partner_name, partner_email, region, end_customer), retornar campos faltantes
    - Función `validate_service(service: str) -> bool`: verificar que el servicio esté en `SUPPORTED_SERVICES`
    - Función `validate_json_file(content: str) -> tuple[bool, dict | str]`: parsear JSON, retornar datos o error descriptivo, rechazar si supera 1 MB
    - _Requisitos: 10.1, 10.2, 10.3, 11.3, 6.1_

  - [ ]* 1.4 Tests de propiedades para validaciones
    - **Propiedad 11: Validación de formato de correo electrónico** — Generar cadenas aleatorias con `st.emails()` + `st.text()`, verificar que solo emails válidos pasan
    - **Valida: Requisito 10.2**
    - **Propiedad 10: Validación de datos obligatorios del partner** — Generar combinaciones de campos vacíos/presentes con `st.fixed_dictionaries()`, verificar rechazo cuando faltan campos
    - **Valida: Requisitos 10.1, 10.3**
    - **Propiedad 6: Rechazo de servicios no soportados** — Generar nombres de servicio aleatorios excluyendo los 3 válidos, verificar rechazo
    - **Valida: Requisito 6.1**
    - **Propiedad 12: Validación de JSON para estimaciones externas** — Generar cadenas aleatorias y JSON válido, verificar parsing correcto
    - **Valida: Requisito 11.3**

  - [ ]* 1.5 Tests unitarios para validaciones
    - Tests de `validate_email`: emails válidos, inválidos (sin @, sin dominio, con espacios, vacío)
    - Tests de `validate_partner_data`: todos los campos presentes, campos faltantes individuales, campos vacíos
    - Tests de `validate_service`: servicios válidos, servicio no soportado, cadena vacía
    - Tests de `validate_json_file`: JSON válido, JSON inválido, archivo vacío, archivo > 1 MB
    - _Requisitos: 10.1, 10.2, 10.3, 11.3, 6.1_

- [x] 2. Checkpoint — Verificar que la estructura base y validaciones funcionan
  - Ejecutar todos los tests, preguntar al usuario si hay dudas.

- [x] 3. Capa de acceso a datos (DynamoDB)
  - [x] 3.1 Implementar repositorio de conversaciones (`src/services/conversation_repo.py`)
    - Función `create_conversation(user_id, language) -> Conversation`: crear nueva conversación con UUID, guardar en DynamoDB tabla `conversations`
    - Función `get_conversation(conversation_id) -> Conversation`: obtener conversación por PK
    - Función `add_message(conversation_id, role, content) -> None`: agregar mensaje a la lista de mensajes, actualizar `updated_at`
    - Función `list_conversations(user_id) -> list[Conversation]`: listar conversaciones del usuario usando GSI `user_id-index`, ordenadas por fecha descendente
    - Función `update_status(conversation_id, status) -> None`: actualizar estado (active/completed)
    - _Requisitos: 2.3, 2.4, 8.1, 8.2, 8.3_

  - [x] 3.2 Implementar repositorio de estimaciones (`src/services/estimation_repo.py`)
    - Función `save_estimation(estimation: Estimation) -> str`: guardar estimación en DynamoDB tabla `estimations`, retornar estimation_id
    - Función `get_estimation(estimation_id) -> Estimation`: obtener estimación por PK
    - Función `list_estimations(user_id) -> list[Estimation]`: listar estimaciones del usuario usando GSI `user_id-index`
    - _Requisitos: 3.2, 4.2, 5.2, 7.1_

  - [x] 3.3 Implementar repositorio de pricing cache (`src/services/pricing_repo.py`)
    - Función `get_pricing(service_id) -> list[PricingEntry]`: obtener precios de un servicio desde tabla `pricing_cache`
    - Función `update_pricing(service_id, component, data) -> None`: actualizar/crear entrada de precio con timestamp
    - Función `get_last_updated(service_id) -> str`: obtener fecha de última actualización
    - _Requisitos: 13.1, 13.3, 13.4, 13.5_

  - [ ]* 3.4 Tests de propiedades para capa de datos
    - **Propiedad 8: Round-trip del historial de conversaciones y ordenamiento** — Generar conversaciones, almacenar, recuperar, verificar igualdad y orden descendente por fecha
    - **Valida: Requisitos 8.1, 8.2, 8.3**
    - **Propiedad 3: Aislamiento entre conversaciones** — Generar pares de conversaciones del mismo usuario, verificar que no comparten mensajes
    - **Valida: Requisito 2.4**
    - **Propiedad 16: Registro de timestamp de actualización de precios** — Ejecutar actualizaciones secuenciales, verificar timestamps monotónicamente crecientes
    - **Valida: Requisito 13.4**

- [x] 4. Checkpoint — Verificar capa de datos con moto mocks
  - Ejecutar todos los tests, preguntar al usuario si hay dudas.

- [x] 5. Detección de idioma y sistema de prompts
  - [x] 5.1 Implementar detector de idioma (`src/utils/language_detector.py`)
    - Función `detect_language(text: str) -> str`: detectar idioma del texto entre los 4 soportados (es, en, pt, de), retornar código ISO
    - Función `is_supported_language(lang_code: str) -> bool`: verificar si el idioma está soportado
    - Generar mensaje de idioma no soportado en inglés por defecto, listando los 4 idiomas disponibles
    - _Requisitos: 9.1, 9.2, 9.3_

  - [x] 5.2 Implementar sistema de prompts (`src/services/prompt_builder.py`)
    - Función `build_system_prompt(language, pricing_data) -> str`: construir system prompt para Nova Pro con rol, restricciones de alcance, formato de salida, instrucciones de idioma y datos de pricing (RAG)
    - Incluir instrucciones de guardrail: clasificar cada mensaje como dentro/fuera de alcance antes de responder
    - Incluir mensajes de bloqueo en los 4 idiomas (es, en, pt, de)
    - Incluir few-shot examples para mejorar precisión en cálculos
    - Función `build_estimation_prompt(service, parameters, pricing_data, language) -> str`: prompt específico para generar estimación con desglose
    - _Requisitos: 6.1, 6.2, 6.3, 17.4, 17.5_

  - [ ]* 5.3 Tests de propiedades para detección de idioma
    - **Propiedad 9: Detección y correspondencia de idioma** — Generar textos en idiomas soportados, verificar código de idioma correcto y correspondencia en estimaciones
    - **Valida: Requisitos 9.1, 9.2, 9.4**

- [x] 6. Motor de estimación y lógica de cálculo
  - [x] 6.1 Implementar servicio de estimación (`src/services/estimation_service.py`)
    - Función `generate_estimation(user_id, conversation_id, service, parameters, partner_data, language) -> Estimation`: orquestar generación completa
    - Validar datos del partner (invocar `validate_partner_data`), validar servicio (invocar `validate_service`), validar email (invocar `validate_email`)
    - Obtener precios actualizados desde `pricing_repo`
    - Invocar Bedrock (Nova Pro) con prompt de estimación + datos de pricing (RAG)
    - Parsear respuesta del modelo: extraer monthly_cost, annual_cost, breakdown, assumptions
    - Generar estimation_id único (UUID), incluir pricing_date y disclaimer
    - Guardar estimación en DynamoDB vía `estimation_repo`
    - Retornar objeto `Estimation` completo
    - _Requisitos: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 7.1, 7.3, 10.1, 10.2, 10.3, 10.4, 13.5_

  - [x] 6.2 Implementar invocación a Bedrock (`src/services/bedrock_client.py`)
    - Función `invoke_model(prompt, system_prompt, conversation_history) -> str`: invocar Amazon Nova Pro vía `bedrock-runtime` con boto3
    - Configurar parámetros de inferencia (temperature, max_tokens)
    - Implementar retry con backoff exponencial (máx. 3 intentos) para throttling
    - Manejar errores: timeout (>30s), servicio no disponible, respuesta malformada
    - Retornar mensaje amigable sin detalles técnicos cuando Bedrock falla
    - _Requisitos: 17.1, 17.2, 17.3, 2.2_

  - [ ]* 6.3 Tests de propiedades para estimaciones
    - **Propiedad 4: Completitud estructural de estimaciones** — Generar parámetros válidos para cada servicio, verificar que la salida contiene todos los campos requeridos (monthly_cost >= 0, annual_cost >= 0, breakdown no vacío, assumptions no vacío, pricing_date ISO8601, partner_data completo)
    - **Valida: Requisitos 3.2, 4.2, 5.2, 7.1, 10.4, 13.5**
    - **Propiedad 5: Recálculo de estimación al modificar parámetros** — Generar pares de parámetros diferentes, verificar estimation_id diferente y costos distintos
    - **Valida: Requisitos 3.4, 4.4, 5.4**
    - **Propiedad 7: Inclusión de disclaimer en estimaciones** — Generar estimaciones aleatorias, verificar presencia del texto de aviso de costos aproximados
    - **Valida: Requisito 7.3**

  - [ ]* 6.4 Tests de propiedades para Bedrock
    - **Propiedad 17: Error graceful cuando Bedrock no está disponible** — Simular errores de Bedrock (timeout, error de servicio), verificar mensaje amigable sin detalles técnicos internos
    - **Valida: Requisito 17.3**

- [x] 7. Checkpoint — Verificar motor de estimación y prompts
  - Ejecutar todos los tests, preguntar al usuario si hay dudas.

- [x] 8. Chat handler (WebSocket)
  - [x] 8.1 Implementar handler de conexión WebSocket (`src/handlers/ws_connect.py`)
    - Función `handler(event, context)`: manejar eventos `$connect` y `$disconnect`
    - En `$connect`: validar JWT del query string, registrar connectionId en DynamoDB o en memoria
    - En `$disconnect`: limpiar connectionId
    - Retornar 401 si JWT inválido o ausente
    - _Requisitos: 1.1, 1.4_

  - [x] 8.2 Implementar handler de mensajes de chat (`src/handlers/chat_handler.py`)
    - Función `handler(event, context)`: procesar mensajes `$default` del WebSocket
    - Extraer `conversation_id` y `message` del body
    - Obtener o crear conversación en DynamoDB
    - Detectar idioma del mensaje
    - Obtener precios de caché para RAG
    - Construir system prompt con guardrail + pricing data
    - Invocar Bedrock con historial conversacional
    - Guardar mensaje del usuario y respuesta del agente en DynamoDB
    - Enviar respuesta al usuario vía API Gateway Management API (`post_to_connection`)
    - Manejar errores: conexión perdida, timeout de Bedrock, mensaje vacío
    - _Requisitos: 2.1, 2.2, 2.3, 6.1, 6.2, 6.3, 9.2, 17.1, 17.2_

  - [ ]* 8.3 Tests de propiedades para autenticación y contexto
    - **Propiedad 1: Rechazo de solicitudes no autenticadas** — Generar requests con JWT inválidos/ausentes, verificar respuesta 401
    - **Valida: Requisito 1.1**
    - **Propiedad 2: Mantenimiento del contexto conversacional** — Generar secuencias de mensajes, verificar que el contexto almacenado los contiene todos en orden cronológico
    - **Valida: Requisito 2.3**

  - [ ]* 8.4 Tests unitarios para chat handler
    - Test de conexión WebSocket exitosa con JWT válido
    - Test de rechazo de conexión sin JWT (401)
    - Test de procesamiento de mensaje y respuesta
    - Test de mensaje vacío (ignorar)
    - Test de timeout de Bedrock (mensaje de error al usuario)
    - _Requisitos: 1.1, 2.1, 2.2, 17.3_

- [x] 9. Generación de PDF y exportación
  - [x] 9.1 Implementar generador de PDF (`src/services/pdf_generator.py`)
    - Función `generate_pdf(estimation: Estimation, language: str) -> bytes`: generar PDF con reportlab
    - Incluir en el PDF: datos del partner (nombre, email, región, cliente final), tabla de costos con desglose por componente, supuestos, fecha de pricing, disclaimer de costos aproximados
    - Si hay consolidación: incluir sección de estimaciones externas y total consolidado
    - Soportar los 4 idiomas para etiquetas y encabezados del PDF
    - Función `generate_csv(estimation: Estimation) -> str`: generar CSV con desglose de costos
    - _Requisitos: 7.1, 7.2, 7.3, 10.4, 12.2_

  - [x] 9.2 Implementar handler de PDF (`src/handlers/pdf_handler.py`)
    - Función `handler(event, context)`: endpoint REST para generar y descargar PDF/CSV
    - Recibir `estimation_id`, `format` (pdf/csv), `language`
    - Obtener estimación de DynamoDB, generar archivo, subir a S3, retornar URL pre-firmada (expira en 1 hora)
    - Manejar errores: estimación no encontrada, error de generación (ofrecer CSV como alternativa), error de S3 (reintentar 3 veces)
    - _Requisitos: 7.2, 14.5_

  - [ ]* 9.3 Tests unitarios para generación de PDF
    - Test de generación de PDF con estimación completa
    - Test de generación de CSV
    - Test de PDF con consolidación (estimaciones internas + externas)
    - Test de PDF en cada idioma soportado
    - Test de inclusión de disclaimer en PDF
    - _Requisitos: 7.1, 7.2, 7.3_

- [x] 10. Consolidación de estimaciones externas
  - [x] 10.1 Implementar servicio de consolidación (`src/services/consolidation_service.py`)
    - Función `consolidate(estimation_id, external_json: dict) -> Estimation`: consolidar estimación interna con datos externos
    - Validar JSON externo con `validate_json_file`
    - Tomar datos externos tal cual (sin modificar ni recalcular)
    - Calcular totales consolidados (monthly_cost total, annual_cost total)
    - Guardar estimación consolidada en DynamoDB con `is_consolidated=True`
    - _Requisitos: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [x] 10.2 Implementar handler de consolidación (`src/handlers/consolidation_handler.py`)
    - Función `handler(event, context)`: endpoint REST para consolidar estimaciones
    - Recibir `estimation_id` y `external_json` del body
    - Invocar `consolidation_service.consolidate()`
    - Retornar estimación consolidada
    - Manejar errores: JSON inválido (400), archivo > 1 MB (400), estimación no encontrada (404)
    - _Requisitos: 11.2, 11.3_

  - [ ]* 10.3 Tests de propiedades para consolidación
    - **Propiedad 13: Preservación de datos externos en consolidación** — Generar JSON externo, consolidar con estimación interna, verificar que datos externos aparecen sin modificación. Verificar que sin consolidación no hay datos externos
    - **Valida: Requisitos 11.4, 11.5, 11.6**

- [x] 11. Envío de correo electrónico (SES)
  - [x] 11.1 Implementar servicio de email (`src/services/email_service.py`)
    - Función `send_estimation_email(estimation: Estimation, recipient_email: str, pdf_bytes: bytes, language: str) -> dict`: enviar correo vía SES
    - Construir cuerpo en texto plano con: datos del partner, desglose completo de estimaciones, estimaciones externas (si hay consolidación), disclaimer
    - Construir mensaje MIME multipart: texto plano + PDF adjunto
    - Enviar vía SES con boto3 `send_raw_email`
    - Retornar `{message_id, status}`, manejar errores (fallo de envío, bounce)
    - _Requisitos: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 11.2 Implementar handler de email (`src/handlers/email_handler.py`)
    - Función `handler(event, context)`: puede ser invocado internamente por chat_handler o como endpoint REST
    - Recibir `estimation_id`, `recipient_email`, `language`
    - Obtener estimación de DynamoDB, generar PDF, invocar `email_service`
    - Manejar errores: informar al usuario, ofrecer reintento o descarga manual
    - _Requisitos: 12.1, 12.5_

  - [ ]* 11.3 Tests de propiedades para email
    - **Propiedad 14: Completitud del correo electrónico** — Generar estimaciones completas, componer email, verificar que el cuerpo contiene datos del partner, desglose de servicios, estimaciones externas (si aplica), y que el mensaje es multipart con texto plano + PDF adjunto
    - **Valida: Requisitos 12.2, 12.3, 12.4**

- [x] 12. Checkpoint — Verificar PDF, consolidación y email
  - Ejecutar todos los tests, preguntar al usuario si hay dudas.

- [x] 13. Actualización de precios (pricing_updater)
  - [x] 13.1 Implementar scraper de precios (`src/services/pricing_scraper.py`)
    - Función `fetch_pricing(service_id: str, url: str) -> list[dict]`: hacer HTTP GET a la URL oficial, parsear datos de precios
    - Implementar parsers específicos para cada URL:
      - Amazon Quick: `https://aws.amazon.com/quick/pricing/`
      - Amazon Connect: `https://aws.amazon.com/es/connect/pricing/`
      - Bedrock AgentCore: `https://aws.amazon.com/bedrock/agentcore/pricing/`
    - Manejar errores de red: timeout, HTTP errors, parsing fallido
    - _Requisitos: 13.1, 13.2_

  - [x] 13.2 Implementar handler de pricing updater (`src/handlers/pricing_updater.py`)
    - Función `handler(event, context)`: invocado por EventBridge (cron diario)
    - Para cada servicio soportado: invocar `fetch_pricing`, actualizar `pricing_repo` con datos nuevos y timestamp
    - Si falla el fetch de una URL: mantener caché existente, registrar warning en logs
    - Si todas las URLs fallan: mantener caché completo, registrar error crítico
    - Retornar resumen de servicios actualizados y errores
    - _Requisitos: 13.1, 13.2, 13.3, 13.4_

  - [ ]* 13.3 Tests de propiedades para pricing
    - **Propiedad 15: Fallback a caché de precios** — Simular fallos de acceso a URLs, verificar que retorna datos de caché con `last_updated` válido
    - **Valida: Requisito 13.3**

- [x] 14. Integración de flujo completo y REST API
  - [x] 14.1 Implementar handler REST principal (`src/handlers/rest_api.py`)
    - Función `handler(event, context)`: router para endpoints REST
    - Rutas: `GET /estimations` (listar), `GET /estimations/{id}` (detalle), `POST /estimations/{id}/export` (PDF/CSV), `POST /estimations/{id}/consolidate`, `POST /estimations/{id}/email`, `GET /conversations` (historial), `GET /conversations/{id}` (detalle)
    - Validar JWT en cada request (Cognito authorizer en API Gateway)
    - _Requisitos: 7.2, 8.1, 8.2, 8.3, 14.2, 14.5_

  - [x] 14.2 Conectar flujo completo en chat_handler
    - Integrar en `chat_handler`: cuando el agente detecta que tiene todos los datos para generar estimación → invocar `estimation_service`
    - Después de generar estimación: preguntar al usuario si desea consolidar estimaciones externas (Requisito 11.1)
    - Después de consolidación (o si no desea): generar PDF, enviar email automáticamente
    - Manejar flujo de recálculo cuando el usuario modifica parámetros en la misma sesión
    - _Requisitos: 3.4, 4.4, 5.4, 11.1, 11.6, 12.1_

  - [ ]* 14.3 Tests unitarios de integración del flujo
    - Test del flujo completo: mensaje → estimación → consolidación → PDF → email
    - Test de recálculo de estimación con parámetros modificados
    - Test de flujo sin consolidación (solo estimación interna)
    - Test de manejo de errores en cada paso del flujo
    - _Requisitos: 3.4, 11.1, 11.6, 12.1_

- [x] 15. Checkpoint — Verificar integración completa del backend
  - Ejecutar todos los tests, preguntar al usuario si hay dudas.

- [x] 16. Frontend SPA
  - [x] 16.1 Crear aplicación web base con autenticación Cognito
    - Crear SPA con interfaz de chat como canal principal
    - Integrar Cognito SDK: login, logout, obtención de JWT, refresh de tokens
    - Implementar redirección a login cuando sesión expira
    - Diseño responsivo para escritorio y tablet
    - _Requisitos: 1.1, 1.2, 1.3, 1.4, 1.5, 14.1, 14.2, 14.3, 14.4_

  - [x] 16.2 Implementar interfaz de chat WebSocket
    - Conectar al WebSocket API con JWT en query string
    - Enviar/recibir mensajes en tiempo real
    - Mostrar respuestas del agente con formato (tablas de costos, desglose)
    - Reconexión automática si se pierde la conexión WebSocket
    - _Requisitos: 2.1, 14.2_

  - [x] 16.3 Implementar funcionalidades de historial y exportación
    - Sección de historial: listar conversaciones anteriores (REST API), mostrar contenido completo al seleccionar
    - Carga de archivos JSON para consolidación (REST API)
    - Descarga de estimaciones en PDF/CSV (REST API, URL pre-firmada)
    - _Requisitos: 8.1, 8.2, 8.3, 11.2, 14.5_

- [x] 17. Infraestructura como código y CI/CD
  - [x] 17.1 Crear plantilla de infraestructura (SAM/CloudFormation o CDK)
    - Definir recursos: Cognito User Pool, DynamoDB (4 tablas con GSIs), S3 (2 buckets: web + archivos), CloudFront, API Gateway (WebSocket + REST con autorizador Cognito), Lambda (7 funciones con roles IAM mínimo privilegio), SES, EventBridge (regla cron diaria)
    - Configurar variables de entorno para cada Lambda
    - Región: us-east-1
    - _Requisitos: 15.1, 15.2_

  - [x] 17.2 Configurar pipeline CI/CD con GitHub Actions
    - Crear `.github/workflows/deploy.yml`: trigger en push a main
    - Steps: instalar dependencias → ejecutar tests unitarios (`pytest tests/unit/`) → ejecutar tests de propiedades (`pytest tests/property/`) → deploy a us-east-1
    - Configurar rollback automático en caso de fallo de despliegue
    - _Requisitos: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 18. Checkpoint final — Verificar despliegue completo
  - Ejecutar todos los tests, preguntar al usuario si hay dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints aseguran validación incremental
- Los tests de propiedades validan propiedades universales de correctitud (Hypothesis)
- Los tests unitarios validan ejemplos específicos y casos borde (pytest + moto)
- El código usa Python con boto3, siguiendo PEP 8 y las convenciones del proyecto (snake_case para archivos/funciones, PascalCase para clases)
