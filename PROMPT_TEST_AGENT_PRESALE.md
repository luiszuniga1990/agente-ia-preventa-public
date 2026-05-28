# 🧪 Prompt Test — Agent Presale

## Resumen

Este documento es una guía de pruebas para el **Agente IA Preventa**. Contiene el flujo paso a paso de cómo un usuario interactúa con la aplicación web, un diagrama ASCII del proceso completo, y una colección de prompts sugeridos para validar todas las funcionalidades del chatbot (estimaciones de costos para Amazon QuickSight, Amazon Connect y Amazon Bedrock AgentCore).

---

## Diagrama del Proceso (Step by Step)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FLUJO DEL USUARIO                                │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│   USUARIO    │────▶│  CloudFront URL   │────▶│   Pantalla de Login     │
│  (Browser)   │     │  (index.html)     │     │   (Cognito Hosted UI)   │
└──────────────┘     └──────────────────┘     └────────────┬────────────┘
                                                           │
                                              ┌────────────▼────────────┐
                                              │  Ingresar credenciales  │
                                              │  (email + contraseña)   │
                                              └────────────┬────────────┘
                                                           │
                                              ┌────────────▼────────────┐
                                              │  Token JWT generado     │
                                              │  (Cognito ID Token)     │
                                              └────────────┬────────────┘
                                                           │
                     ┌─────────────────────────────────────▼──────────────┐
                     │            INTERFAZ PRINCIPAL DEL CHAT              │
                     │                                                     │
                     │  ┌─────────────────────────────────────────────┐   │
                     │  │  Panel lateral: Historial de conversaciones  │   │
                     │  └─────────────────────────────────────────────┘   │
                     │                                                     │
                     │  ┌─────────────────────────────────────────────┐   │
                     │  │  Área de chat: Mensajes del agente + usuario │   │
                     │  └─────────────────────────────────────────────┘   │
                     │                                                     │
                     │  ┌─────────────────────────────────────────────┐   │
                     │  │  Input: Escribir mensaje + botón enviar      │   │
                     │  └─────────────────────────────────────────────┘   │
                     └────────────────────────┬───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FLUJO DE CONVERSACIÓN                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PASO 1: Usuario envía mensaje ──▶ WebSocket ──▶ Lambda chat_handler   │
│                                                                         │
│  PASO 2: Agente solicita datos del partner:                             │
│          • Nombre del partner                                           │
│          • Email del partner                                            │
│          • Región AWS deseada                                           │
│          • Nombre del cliente final                                     │
│                                                                         │
│  PASO 3: Usuario describe su necesidad de estimación                    │
│          (servicio + componentes + cantidades)                          │
│                                                                         │
│  PASO 4: Agente genera estimación con desglose:                         │
│          • Componentes individuales                                     │
│          • Precio unitario mensual                                      │
│          • Cantidad                                                     │
│          • Subtotal por componente                                      │
│          • TOTAL mensual estimado                                       │
│                                                                         │
│  PASO 5: Acciones post-estimación:                                      │
│          ┌────────────┐  ┌────────────┐  ┌──────────────────┐          │
│          │ Exportar   │  │  Enviar    │  │  Consolidar con  │          │
│          │ PDF / CSV  │  │  por Email │  │  JSON externo    │          │
│          └────────────┘  └────────────┘  └──────────────────┘          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     FLUJO TÉCNICO INTERNO                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Browser ──WSS──▶ API Gateway WebSocket ──▶ chat_handler (Lambda)      │
│                                                    │                    │
│                                                    ├──▶ DynamoDB        │
│                                                    │    (conversaciones)│
│                                                    │                    │
│                                                    ├──▶ DynamoDB        │
│                                                    │    (pricing_cache) │
│                                                    │                    │
│                                                    ├──▶ Bedrock         │
│                                                    │    (Nova Pro)      │
│                                                    │                    │
│                                                    └──▶ DynamoDB        │
│                                                         (estimations)   │
│                                                                         │
│  Browser ──HTTPS──▶ API Gateway REST ──▶ rest_api (Lambda)             │
│                                               │                         │
│                                               ├──▶ pdf_handler ──▶ S3  │
│                                               ├──▶ email_handler ──▶SES│
│                                               └──▶ consolidation_handler│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Prompts de Prueba Sugeridos

### 1. Prueba Básica — Saludo y Guardrail

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 1.1 | `Hola, ¿qué puedes hacer?` | El agente se presenta y explica que genera estimaciones para QuickSight, Connect y Bedrock AgentCore |
| 1.2 | `¿Cuánto cuesta un servidor EC2?` | El agente rechaza educadamente — solo soporta los 3 servicios definidos |
| 1.3 | `¿Me puedes ayudar con una receta de cocina?` | El agente rechaza — fuera de alcance |

### 2. Prueba de Datos del Partner

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 2.1 | `Necesito una estimación de Amazon Connect` | El agente solicita datos del partner (nombre, email, región, cliente final) |
| 2.2 | `Mi nombre es Juan Pérez, email juan@empresa.com, región us-east-1, cliente: Banco Nacional` | El agente confirma los datos y pregunta por los detalles de la estimación |

### 3. Prueba de Estimación — Amazon Connect

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 3.1 | `Necesito un contact center con 50 agentes de voz, 20 de chat, grabación de llamadas y analytics` | Estimación desglosada con componentes de Connect, precios unitarios y total mensual |
| 3.2 | `Agrega 10 agentes más de voz` | Actualiza la estimación existente |
| 3.3 | `¿Puedes cambiar la región a eu-west-1?` | Recalcula con precios de la nueva región |

### 4. Prueba de Estimación — Amazon QuickSight

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 4.1 | `Quiero una estimación de QuickSight con 5 autores, 100 lectores, 2 espacios de conocimiento y Q&A habilitado` | Estimación con componentes de QuickSight desglosados |
| 4.2 | `Agrega 3 reportes programados y 1 dashboard embebido` | Actualiza la estimación |

### 5. Prueba de Estimación — Amazon Bedrock AgentCore

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 5.1 | `Necesito estimar Bedrock AgentCore con Runtime para 2 agentes, Gateway, Memory y Observability` | Estimación con componentes de AgentCore |
| 5.2 | `Agrega Code Interpreter y Browser tool` | Actualiza con los componentes adicionales |

### 6. Prueba Multiservicio

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 6.1 | `Necesito una solución completa: Connect con 30 agentes de voz, QuickSight con 10 autores para analytics del contact center, y Bedrock AgentCore con 1 agente para autoservicio` | Estimación combinada de los 3 servicios con total consolidado |

### 7. Prueba de Exportación

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 7.1 | `Exporta la estimación en PDF` | Se genera y descarga un PDF con el desglose completo |
| 7.2 | `Exporta en CSV` | Se genera y descarga un CSV |
| 7.3 | `Envía la estimación por correo a cliente@empresa.com` | Se envía email con PDF adjunto vía SES |

### 8. Prueba de Consolidación

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 8.1 | `Quiero consolidar con una estimación externa` | El agente solicita subir un archivo JSON |
| 8.2 | *(Subir JSON con formato válido)* | Consolida ambas estimaciones y muestra total combinado |

### 9. Prueba Multiidioma

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 9.1 | `I need a cost estimation for Amazon Connect with 20 voice agents` | Responde en inglés con la estimación |
| 9.2 | `Preciso uma estimativa do Amazon QuickSight com 5 autores` | Responde en portugués |
| 9.3 | `Ich brauche eine Schätzung für Bedrock AgentCore` | Responde en alemán |

### 10. Prueba de Historial

| # | Prompt | Resultado Esperado |
|---|--------|-------------------|
| 10.1 | *(Hacer clic en una conversación anterior del panel lateral)* | Se carga el historial completo de esa conversación |
| 10.2 | `¿Cuál fue mi última estimación?` | El agente recuerda el contexto de la conversación actual |

---

## Notas para el Tester

- **URL de acceso:** La URL de CloudFront del entorno desplegado
- **Credenciales:** Solicitar al administrador la creación de un usuario en Cognito
- **Servicios soportados:** Solo Amazon QuickSight, Amazon Connect y Amazon Bedrock AgentCore
- **Guardrail:** El agente NO debe responder preguntas fuera del alcance de estimaciones de estos 3 servicios
- **Idiomas:** Español, Inglés, Portugués, Alemán (responde en el idioma del usuario)
- **Datos del partner:** Son obligatorios antes de generar cualquier estimación
