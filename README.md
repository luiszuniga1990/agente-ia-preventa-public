# 🤖 Agente IA Preventa

Chatbot serverless de IA para generación de estimaciones de costos de servicios AWS, diseñado para equipos de preventa.

## Servicios Soportados

- **Amazon Quick** — Espacios de conocimiento, chat/agentes, reportes, analytics, automatización
- **Amazon Connect** — Contact center (voz, chat, grabación, analytics)
- **Amazon Bedrock AgentCore** — Runtime, Gateway, Policy, Identity, Memory, Observability, Evaluations, Browser, Code Interpreter

## Características

- Chat conversacional con IA (Amazon Nova Pro vía Bedrock)
- Autenticación segura con Amazon Cognito
- Soporte multiidioma: español, inglés, portugués, alemán
- Generación de estimaciones con desglose por componente
- Consolidación con estimaciones externas (upload JSON)
- Exportación en PDF y CSV
- Envío automático por correo electrónico (texto plano + PDF adjunto)
- Actualización diaria de precios desde URLs oficiales de AWS
- Guardrail estricto: solo responde sobre estimaciones de los 3 servicios soportados
- Historial de conversaciones y estimaciones
- Datos obligatorios del partner (nombre, email, región, cliente final)

## Arquitectura

Serverless en AWS (us-east-1):

```
Frontend (SPA)          → S3 + CloudFront
Autenticación           → Amazon Cognito
Chat (tiempo real)      → API Gateway WebSocket + Lambda (Python)
API REST                → API Gateway REST + Lambda (Python)
Modelo IA               → Amazon Bedrock (Nova Pro)
Base de datos           → DynamoDB (4 tablas, on-demand)
Almacenamiento          → S3 (PDFs, JSONs)
Email                   → Amazon SES
Actualización precios   → EventBridge (cron diario) + Lambda
CI/CD                   → GitHub Actions + SAM
```

## Estructura del Proyecto

```
├── src/
│   ├── handlers/           # Lambda handlers
│   │   ├── chat_handler.py       # WebSocket $default (chat)
│   │   ├── ws_connect.py         # WebSocket $connect/$disconnect
│   │   ├── rest_api.py           # Router REST API
│   │   ├── pdf_handler.py        # Generación PDF/CSV
│   │   ├── consolidation_handler.py  # Consolidación JSON externo
│   │   ├── email_handler.py      # Envío de correos
│   │   └── pricing_updater.py    # Actualización diaria de precios
│   ├── services/           # Lógica de negocio
│   │   ├── bedrock_client.py     # Cliente Amazon Bedrock (Nova Pro)
│   │   ├── estimation_service.py # Motor de estimaciones
│   │   ├── estimation_repo.py    # Repositorio DynamoDB estimaciones
│   │   ├── conversation_repo.py  # Repositorio DynamoDB conversaciones
│   │   ├── pricing_repo.py       # Repositorio DynamoDB precios
│   │   ├── pricing_scraper.py    # Scraper de precios AWS
│   │   ├── consolidation_service.py  # Consolidación de estimaciones
│   │   ├── email_service.py      # Envío de emails vía SES
│   │   ├── pdf_generator.py      # Generación de PDFs y CSVs
│   │   └── prompt_builder.py     # Sistema de prompts con guardrail
│   ├── models/             # Modelos de datos (dataclasses)
│   │   ├── conversation.py
│   │   ├── estimation.py
│   │   ├── partner.py
│   │   ├── pricing.py
│   │   └── constants.py
│   └── utils/              # Utilidades
│       ├── validators.py         # Validación de email, partner, JSON
│       └── language_detector.py  # Detección de idioma
├── frontend/               # Aplicación web SPA
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── config.js       # Configuración (placeholders)
│       ├── auth.js         # Autenticación Cognito
│       ├── chat.js         # WebSocket chat
│       ├── api.js          # Llamadas REST API
│       └── app.js          # Lógica principal UI
├── tests/
│   ├── unit/               # Tests unitarios (pytest + moto)
│   └── property/           # Tests de propiedades (hypothesis)
├── template.yaml           # Infraestructura SAM (CloudFormation)
├── samconfig.toml          # Configuración de despliegue SAM
├── requirements.txt        # Dependencias Python
├── conftest.py             # Fixtures compartidos para tests
├── .github/workflows/
│   └── deploy.yml          # Pipeline CI/CD (GitHub Actions)
└── .gitignore
```

## Requisitos Previos

- Python 3.12+
- AWS CLI configurado con credenciales
- AWS SAM CLI instalado
- Cuenta de AWS con acceso a Bedrock (modelo Amazon Nova Pro habilitado en us-east-1)
- Repositorio en GitHub

## Instalación Local

```bash
# Clonar el repositorio
git clone https://github.com/TU_USUARIO/agente-ia-preventa.git
cd agente-ia-preventa

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar tests
python -m pytest tests/ -v
```

## Configuración para Despliegue

### 1. Secrets de GitHub

Configurar en Settings → Secrets and variables → Actions:

| Secret | Descripción |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN del rol IAM para despliegue (OIDC) |
| `SES_SENDER_EMAIL` | Email verificado en SES para envío de correos |

### 2. Configurar rol IAM para GitHub Actions (OIDC)

```bash
# Crear el identity provider de GitHub en IAM
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

Crear un rol IAM con permisos para SAM deploy, S3, CloudFront, y los servicios del proyecto.

### 3. Despliegue Manual (primera vez)

```bash
# Build
sam build

# Deploy (interactivo la primera vez)
sam deploy --guided --region us-east-1
```

### 4. Configurar Frontend

Después del primer despliegue, actualizar `frontend/js/config.js` con los valores de los Outputs del stack:

```javascript
const APP_CONFIG = {
    cognito: {
        userPoolId: 'VALOR_DE_CognitoUserPoolId',
        clientId: 'VALOR_DE_CognitoUserPoolClientId',
        region: 'us-east-1'
    },
    websocket: {
        url: 'VALOR_DE_WebSocketApiEndpoint'
    },
    restApi: {
        url: 'VALOR_DE_RestApiEndpoint'
    }
};
```

Luego subir el frontend:

```bash
aws s3 sync frontend/ s3://VALOR_DE_WebBucketName/ --delete
```

### 5. Crear Usuarios

```bash
aws cognito-idp admin-create-user \
  --user-pool-id VALOR_DE_CognitoUserPoolId \
  --username usuario@ejemplo.com \
  --user-attributes Name=email,Value=usuario@ejemplo.com Name=name,Value="Nombre Usuario" \
  --temporary-password "TempPass123!" \
  --region us-east-1
```

## Despliegue Automático (CI/CD)

Después de la configuración inicial, cada push a `main` ejecuta automáticamente:

1. Tests unitarios y de propiedades
2. SAM build y deploy
3. Sync del frontend a S3
4. Invalidación de caché de CloudFront
5. Rollback automático si falla el despliegue

## Tests

```bash
# Todos los tests
python -m pytest tests/ -v

# Solo unitarios
python -m pytest tests/unit/ -v

# Solo propiedades
python -m pytest tests/property/ -v

# Con cobertura
python -m pytest tests/ -v --cov=src --cov-report=html
```

## Licencia

Proyecto interno — uso exclusivo del equipo de preventa.
