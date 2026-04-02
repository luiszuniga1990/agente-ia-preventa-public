# Justificación Técnica

## Nombre del Proyecto
Agente IA Preventa

## Descripción Ejecutiva

El Agente IA Preventa es una solución de chatbot inteligente basada en inteligencia artificial que permite al equipo de preventa generar estimaciones de costos para tres servicios de AWS: Amazon Quick, Amazon Connect y Amazon Bedrock AgentCore. El sistema se accede a través de una aplicación web segura con autenticación mediante Amazon Cognito, soporta cuatro idiomas (español, inglés, portugués y alemán), y entrega las estimaciones por correo electrónico con adjunto PDF. La solución es 100% serverless, escalable y desplegada en la región us-east-1 mediante CI/CD conectado a GitHub.

## Descripción Técnica

La arquitectura se basa en un enfoque serverless sobre AWS, utilizando los siguientes componentes:

- **Frontend**: Aplicación web SPA alojada en Amazon S3 y distribuida mediante Amazon CloudFront. Interfaz de chat responsiva compatible con navegadores modernos.
- **Autenticación**: Amazon Cognito User Pool para gestión de usuarios, login/logout y control de sesiones con JWT tokens.
- **Backend**: AWS Lambda (Python) como capa de cómputo serverless para toda la lógica de negocio (procesamiento de mensajes, cálculo de estimaciones, generación de PDFs, envío de correos).
- **API**: Amazon API Gateway con WebSocket API para comunicación en tiempo real del chat y REST API para operaciones CRUD.
- **Modelo de IA**: Amazon Nova Pro invocado a través de Amazon Bedrock, con prompts optimizados y RAG para inyectar datos de pricing actualizados.
- **Base de Datos**: Amazon DynamoDB en modo on-demand para almacenar historial de conversaciones, estimaciones, datos de partners y caché de precios.
- **Correo Electrónico**: Amazon SES para envío de estimaciones en texto plano con PDF adjunto.
- **Almacenamiento**: Amazon S3 para archivos generados (PDFs), archivos JSON subidos por usuarios y assets estáticos.
- **CI/CD**: Pipeline automatizado conectado a repositorio GitHub para despliegue continuo en us-east-1.

## Desglose de Horas de Implementación por Servicio AWS

La implementación se realizará a través de la consola web de AWS (interfaz web) para la configuración de cada servicio.

| Servicio AWS | Actividad | Horas Estimadas |
|---|---|---|
| **Amazon Cognito** | Crear User Pool, configurar políticas de contraseña, definir atributos de usuario, configurar app client, personalizar pantallas de login | 8 |
| **Amazon S3** | Crear buckets para hosting web y almacenamiento de PDFs/JSONs, configurar políticas de acceso, habilitar versionado y encriptación | 4 |
| **Amazon CloudFront** | Crear distribución, configurar origen S3, certificado SSL, políticas de caché, comportamientos de enrutamiento | 4 |
| **Amazon API Gateway** | Crear WebSocket API para chat, crear REST API para operaciones CRUD, configurar autorizadores Cognito, definir rutas y stages | 12 |
| **AWS Lambda** | Crear funciones en Python para: procesamiento de mensajes, invocación de Bedrock, generación de PDFs, envío de correos, actualización de precios, consolidación de estimaciones. Configurar roles IAM, variables de entorno, layers | 40 |
| **Amazon Bedrock** | Habilitar acceso al modelo Amazon Nova Pro, configurar prompts del sistema, pruebas de prompt engineering, ajuste de parámetros de inferencia | 16 |
| **Amazon DynamoDB** | Crear tablas (conversaciones, estimaciones, precios, partners), definir claves de partición/ordenamiento, configurar TTL, índices secundarios | 8 |
| **Amazon SES** | Verificar dominio/correos, configurar plantillas de correo en texto plano, configurar adjuntos PDF, pruebas de envío | 6 |
| **Amazon EventBridge** | Configurar regla programada para actualización diaria de precios desde URLs oficiales | 3 |
| **AWS IAM** | Crear roles y políticas para Lambda, API Gateway, Bedrock, SES, DynamoDB, S3. Aplicar principio de mínimo privilegio | 6 |
| **CI/CD (GitHub + AWS)** | Configurar conexión GitHub, crear pipeline de despliegue, configurar stages (test, deploy), rollback automático | 10 |
| **Pruebas e Integración** | Pruebas end-to-end de flujo completo, pruebas de autenticación, pruebas de estimaciones por servicio, pruebas de correo, pruebas multiidioma | 20 |
| **Documentación** | Documentación de arquitectura, guía de usuario, runbook operativo | 8 |
| | **TOTAL** | **145** |

## Costos Estimados de Servicios AWS (Mensual - us-east-1)

Estimación basada en un uso moderado: ~50 usuarios de preventa activos, ~500 conversaciones/mes, ~1,500 estimaciones generadas/mes.

| Servicio AWS | Detalle de Pricing | Costo Mensual Estimado (USD) |
|---|---|---|
| **Amazon Cognito** | Free tier: 50,000 MAUs incluidos. Con ~50 usuarios activos, queda dentro del free tier | $0.00 |
| **Amazon S3** | Hosting web (~50 MB) + PDFs/JSONs (~500 MB). Storage: $0.023/GB + requests | $0.50 |
| **Amazon CloudFront** | Distribución web. Free tier: 1 TB/mes transferencia. Uso estimado: ~10 GB/mes | $0.00 |
| **Amazon API Gateway (WebSocket)** | ~15,000 mensajes/mes × $1.00/1M mensajes + connection minutes | $0.50 |
| **Amazon API Gateway (REST)** | ~5,000 requests/mes × $3.50/1M requests | $0.02 |
| **AWS Lambda** | ~20,000 invocaciones/mes, 512 MB, ~5s promedio. $0.20/1M requests + $0.0000166667/GB-s. Cómputo: 50,000 GB-s × $0.0000166667 + requests | $0.85 |
| **Amazon Bedrock (Nova Pro)** | Input: $0.80/1M tokens, Output: $3.20/1M tokens. ~2M input tokens + ~500K output tokens/mes | $3.20 |
| **Amazon DynamoDB** | On-demand: $1.25/1M writes, $0.25/1M reads. ~10,000 writes + ~30,000 reads/mes. Storage: $0.25/GB (~1 GB) | $0.27 |
| **Amazon SES** | $0.10/1,000 emails. ~1,500 emails/mes + adjuntos PDF ($0.12/GB, ~0.1 GB) | $0.16 |
| **Amazon EventBridge** | 1 regla programada diaria (30 invocaciones/mes). Free tier cubre hasta 14M eventos | $0.00 |
| **AWS IAM** | Sin costo adicional | $0.00 |
| | **TOTAL MENSUAL ESTIMADO** | **~$5.48** |

### Notas sobre Costos

1. Los costos están calculados para un escenario de uso moderado (~50 usuarios preventa). La arquitectura serverless escala linealmente con el uso.
2. Varios servicios quedan dentro del free tier de AWS para este volumen de uso.
3. El costo más significativo es Amazon Bedrock (Nova Pro) por el procesamiento de tokens. Este costo crece proporcionalmente con el número de conversaciones y la complejidad de las estimaciones.
4. Si el uso crece significativamente (>500 usuarios), se recomienda evaluar Provisioned Throughput para Bedrock y DynamoDB en modo provisionado con Reserved Capacity.
5. Los costos no incluyen el dominio personalizado ni certificados SSL adicionales si se requieren.
6. Precios consultados en abril 2026. Sujetos a cambios según las tarifas vigentes de AWS.

### Fuentes de Pricing
- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/on-demand/)
- [Amazon SES Pricing](https://aws.amazon.com/ses/pricing/)
- [Amazon Cognito Pricing](https://aws.amazon.com/cognito/pricing/)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Amazon S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Amazon CloudFront Pricing](https://aws.amazon.com/cloudfront/pricing/)
