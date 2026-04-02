# Guía de Contribución — Agente IA Preventa

## Convenciones de Código

- **Lenguaje backend**: Python (PEP 8)
- **Naming**: snake_case para archivos, variables y funciones; PascalCase para clases
- **Docstrings**: en español, formato Google style
- **Comentarios**: en español
- **Commits**: mensajes descriptivos en español

## Flujo de Trabajo

1. Crear rama desde `main`: `git checkout -b feature/nombre-descriptivo`
2. Implementar cambios
3. Ejecutar tests: `python -m pytest tests/ -v`
4. Commit y push
5. Crear Pull Request hacia `main`
6. El pipeline CI/CD ejecuta tests automáticamente
7. Merge después de aprobación

## Estructura de Tests

- `tests/unit/` — Tests unitarios con pytest + moto (mocks de AWS)
- `tests/property/` — Tests de propiedades con hypothesis
- Cada módulo en `src/` debe tener su archivo de test correspondiente

## Variables de Entorno

No hardcodear credenciales ni secretos. Usar variables de entorno:

| Variable | Descripción |
|---|---|
| `AWS_REGION` | Región AWS (default: us-east-1) |
| `CONVERSATIONS_TABLE` | Nombre tabla DynamoDB conversaciones |
| `ESTIMATIONS_TABLE` | Nombre tabla DynamoDB estimaciones |
| `PRICING_CACHE_TABLE` | Nombre tabla DynamoDB precios |
| `FILES_BUCKET` | Nombre bucket S3 archivos |
| `SENDER_EMAIL` | Email verificado en SES |
