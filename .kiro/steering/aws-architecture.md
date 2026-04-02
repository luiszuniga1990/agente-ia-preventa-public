---
inclusion: auto
---

# Guía de Arquitectura AWS - Agente IA Preventa

## Región
- Todos los recursos en us-east-1 (N. Virginia)

## Servicios AWS Principales
- Amazon Cognito: autenticación y autorización de usuarios preventa
- Amazon Bedrock: invocación del modelo Amazon Nova Pro
- Amazon Bedrock AgentCore: orquestación del agente de IA
- Amazon SES: envío de correos electrónicos con estimaciones
- Amazon S3: almacenamiento de archivos (PDFs, JSONs, assets web)
- Amazon DynamoDB: almacenamiento de historial de conversaciones y estimaciones
- Amazon CloudFront: distribución de la aplicación web
- AWS Lambda: lógica de backend serverless
- Amazon API Gateway: endpoints REST/WebSocket para el chat

## Patrones de Arquitectura
- Serverless-first: preferir Lambda sobre EC2/ECS
- Event-driven cuando sea posible
- API Gateway + Lambda para endpoints HTTP
- WebSocket para comunicación en tiempo real del chat
- S3 + CloudFront para hosting de la aplicación web estática

## Seguridad
- Cognito User Pool para gestión de usuarios
- JWT tokens para autenticación en API Gateway
- IAM roles con principio de mínimo privilegio
- Encriptar datos en reposo y en tránsito
- No exponer credenciales de AWS en el frontend

## Servicios Soportados para Estimaciones
- Amazon Quick (https://aws.amazon.com/quick/pricing/)
- Amazon Connect (https://aws.amazon.com/es/connect/pricing/)
- Amazon Bedrock AgentCore (https://aws.amazon.com/bedrock/agentcore/pricing/)

## Almacenamiento de Precios
- Actualización diaria de precios desde URLs oficiales
- Caché local en DynamoDB con timestamp de última actualización
- Fallback a datos en caché si las URLs no están disponibles
