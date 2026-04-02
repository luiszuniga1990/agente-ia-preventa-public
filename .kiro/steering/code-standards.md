---
inclusion: auto
---

# Estándares de Código y Convenciones - Agente IA Preventa

## Idioma del Código
- Nombres de variables, funciones y clases en inglés
- Comentarios y documentación en español
- Mensajes de usuario en el idioma detectado (español, inglés, portugués, alemán)

## Estructura del Proyecto
- Frontend: aplicación web SPA (Single Page Application)
- Backend: servicios serverless en AWS
- Infraestructura como código (IaC)
- Separar lógica de negocio, acceso a datos y presentación

## Lenguaje de Backend
- Python como lenguaje principal para todas las funciones Lambda
- Usar boto3 para interacción con servicios AWS
- Seguir PEP 8 para estilo de código

## Naming Conventions
- Archivos y carpetas: snake_case (ej: `pricing_service.py`)
- Variables y funciones: snake_case (ej: `get_estimation`)
- Clases: PascalCase (ej: `EstimationService`)
- Constantes: UPPER_SNAKE_CASE (ej: `MAX_RETRY_COUNT`)
- Variables de entorno: UPPER_SNAKE_CASE (ej: `COGNITO_USER_POOL_ID`)

## Buenas Prácticas
- No hardcodear credenciales ni secretos en el código
- Usar variables de entorno para configuración
- Manejar errores con try/catch y logging apropiado
- Validar inputs del usuario antes de procesarlos
- Escribir tests unitarios para lógica de negocio
- Documentar funciones públicas con JSDoc/docstrings

## Región AWS
- Todos los recursos se despliegan en us-east-1 (N. Virginia)
- No referenciar otras regiones salvo que sea explícitamente necesario

## CI/CD
- Repositorio en GitHub
- Pipeline automatizado: push a main → tests → deploy
- Rollback automático en caso de fallo
