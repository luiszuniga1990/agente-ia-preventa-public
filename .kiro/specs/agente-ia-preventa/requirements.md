# Documento de Requisitos

## Introducción

El Agente IA Preventa es un chatbot inteligente diseñado para asistir al equipo de preventa en la creación de estimaciones de costos y esfuerzo para tres servicios de AWS: Amazon Quick, Amazon Connect y Amazon Bedrock AgentCore. El sistema utiliza Amazon Cognito para autenticación y control de acceso, garantizando que solo los miembros autorizados del equipo de preventa puedan interactuar con el agente.

## Glosario

- **Agente**: El chatbot de IA que recibe preguntas del Usuario_Preventa y genera estimaciones.
- **Usuario_Preventa**: Miembro del equipo de preventa que interactúa con el Agente para obtener estimaciones.
- **Estimación**: Documento o respuesta generada por el Agente que incluye costos estimados, esfuerzo y consideraciones para un servicio de AWS específico.
- **Servicio_Soportado**: Uno de los tres servicios de AWS para los cuales el Agente puede generar estimaciones: Amazon Quick, Amazon Connect o Amazon Bedrock AgentCore.
- **Sistema_Autenticación**: Componente basado en Amazon Cognito que gestiona la autenticación y autorización de los usuarios.
- **Sesión**: Período de interacción autenticada entre un Usuario_Preventa y el Agente.
- **Contexto_Conversación**: Información acumulada durante una Sesión que el Agente utiliza para refinar las estimaciones.

## Requisitos

### Requisito 1: Autenticación de Usuarios

**Historia de Usuario:** Como Usuario_Preventa, quiero autenticarme de forma segura en el Agente, para que solo personal autorizado pueda acceder a las funcionalidades de estimación.

#### Criterios de Aceptación

1. THE Sistema_Autenticación SHALL autenticar a los usuarios mediante Amazon Cognito antes de permitir el acceso al Agente.
2. WHEN un Usuario_Preventa proporciona credenciales válidas, THE Sistema_Autenticación SHALL crear una Sesión autenticada y redirigir al Usuario_Preventa a la interfaz del Agente.
3. WHEN un Usuario_Preventa proporciona credenciales inválidas, THE Sistema_Autenticación SHALL mostrar un mensaje de error descriptivo indicando que las credenciales son incorrectas.
4. IF la Sesión de un Usuario_Preventa expira, THEN THE Sistema_Autenticación SHALL redirigir al Usuario_Preventa a la pantalla de inicio de sesión.
5. WHEN un Usuario_Preventa solicita cerrar sesión, THE Sistema_Autenticación SHALL invalidar la Sesión activa y redirigir al Usuario_Preventa a la pantalla de inicio de sesión.

### Requisito 2: Interacción Conversacional

**Historia de Usuario:** Como Usuario_Preventa, quiero interactuar con el Agente mediante lenguaje natural, para que pueda hacer preguntas y obtener estimaciones de forma intuitiva.

#### Criterios de Aceptación

1. WHILE un Usuario_Preventa tiene una Sesión activa, THE Agente SHALL aceptar preguntas en lenguaje natural a través de una interfaz de chat.
2. WHEN un Usuario_Preventa envía una pregunta, THE Agente SHALL responder en un tiempo máximo de 30 segundos.
3. WHILE una conversación está en curso, THE Agente SHALL mantener el Contexto_Conversación para proporcionar respuestas coherentes con las preguntas anteriores de la misma Sesión.
4. WHEN un Usuario_Preventa inicia una nueva conversación, THE Agente SHALL crear un nuevo Contexto_Conversación independiente.

### Requisito 3: Generación de Estimaciones para Amazon Quick

**Historia de Usuario:** Como Usuario_Preventa, quiero obtener estimaciones detalladas de Amazon Quick, para que pueda presentar propuestas informadas a los clientes.

#### Criterios de Aceptación

1. WHEN un Usuario_Preventa solicita una estimación de Amazon Quick, THE Agente SHALL solicitar los parámetros necesarios como número de usuarios, funcionalidades requeridas (espacios de conocimiento, chat/agentes, reportes, analytics/dashboards, automatización) y volumen de uso esperado.
2. WHEN el Usuario_Preventa proporciona los parámetros de Amazon Quick, THE Agente SHALL generar una Estimación que incluya costos mensuales estimados, costos anuales estimados y desglose por componente.
3. THE Agente SHALL utilizar los precios públicos vigentes de Amazon Quick como base para las estimaciones.
4. WHEN un Usuario_Preventa solicita modificar parámetros de una Estimación de Amazon Quick existente en la misma Sesión, THE Agente SHALL recalcular la Estimación con los nuevos parámetros.

### Requisito 4: Generación de Estimaciones para Amazon Bedrock AgentCore

**Historia de Usuario:** Como Usuario_Preventa, quiero obtener estimaciones detalladas de Amazon Bedrock AgentCore, para que pueda dimensionar correctamente las soluciones propuestas a los clientes.

#### Criterios de Aceptación

1. WHEN un Usuario_Preventa solicita una estimación de Amazon Bedrock AgentCore, THE Agente SHALL solicitar los parámetros necesarios como componentes requeridos (Runtime, Gateway, Policy, Identity, Memory, Observability, Evaluations, Browser, Code Interpreter), número de agentes a desplegar y volumen de invocaciones esperado.
2. WHEN el Usuario_Preventa proporciona los parámetros de Amazon Bedrock AgentCore, THE Agente SHALL generar una Estimación que incluya costos mensuales estimados, costos anuales estimados y desglose por componente utilizado.
3. THE Agente SHALL utilizar los precios públicos vigentes de Amazon Bedrock AgentCore como base para las estimaciones.
4. WHEN un Usuario_Preventa solicita modificar parámetros de una Estimación de Amazon Bedrock AgentCore existente en la misma Sesión, THE Agente SHALL recalcular la Estimación con los nuevos parámetros.

### Requisito 5: Generación de Estimaciones para Amazon Connect

**Historia de Usuario:** Como Usuario_Preventa, quiero obtener estimaciones detalladas de Amazon Connect, para que pueda proponer soluciones de contact center con costos claros a los clientes.

#### Criterios de Aceptación

1. WHEN un Usuario_Preventa solicita una estimación de Amazon Connect, THE Agente SHALL solicitar los parámetros necesarios como número de agentes concurrentes, volumen de llamadas, duración promedio de llamadas y funcionalidades adicionales (grabación, análisis, chat).
2. WHEN el Usuario_Preventa proporciona los parámetros de Amazon Connect, THE Agente SHALL generar una Estimación que incluya costos mensuales estimados, costos anuales estimados y desglose por componente.
3. THE Agente SHALL utilizar los precios públicos vigentes de Amazon Connect como base para las estimaciones.
4. WHEN un Usuario_Preventa solicita modificar parámetros de una Estimación de Amazon Connect existente en la misma Sesión, THE Agente SHALL recalcular la Estimación con los nuevos parámetros.

### Requisito 6: Alcance del Agente

**Historia de Usuario:** Como Usuario_Preventa, quiero que el Agente me informe cuando una consulta está fuera de su alcance, para que no pierda tiempo esperando respuestas que no puede proporcionar.

#### Criterios de Aceptación

1. THE Agente SHALL generar estimaciones únicamente para los tres Servicios_Soportados: Amazon Quick, Amazon Connect y Amazon Bedrock AgentCore.
2. WHEN un Usuario_Preventa solicita una estimación para un servicio que no es un Servicio_Soportado, THE Agente SHALL informar al Usuario_Preventa que el servicio solicitado está fuera del alcance e indicar los tres Servicios_Soportados disponibles.
3. WHEN un Usuario_Preventa realiza una pregunta no relacionada con estimaciones de Servicios_Soportados, THE Agente SHALL bloquear la respuesta y retornar únicamente un mensaje indicando que solo puede asistir con estimaciones de los tres Servicios_Soportados, sin proporcionar información parcial ni intentar responder la consulta fuera de alcance.

### Requisito 7: Formato y Exportación de Estimaciones

**Historia de Usuario:** Como Usuario_Preventa, quiero poder visualizar y exportar las estimaciones generadas, para que pueda incluirlas en propuestas comerciales.

#### Criterios de Aceptación

1. THE Agente SHALL presentar las estimaciones en un formato estructurado que incluya tabla de costos, supuestos utilizados y fecha de generación.
2. WHEN un Usuario_Preventa solicita exportar una Estimación, THE Agente SHALL generar un archivo descargable en formato PDF o CSV.
3. THE Agente SHALL incluir un aviso en cada Estimación indicando que los costos son aproximados y están sujetos a cambios según los precios vigentes del proveedor.

### Requisito 8: Historial de Conversaciones

**Historia de Usuario:** Como Usuario_Preventa, quiero acceder al historial de mis conversaciones anteriores, para que pueda revisar estimaciones previas sin tener que regenerarlas.

#### Criterios de Aceptación

1. THE Agente SHALL almacenar el historial de conversaciones de cada Usuario_Preventa.
2. WHEN un Usuario_Preventa accede a la sección de historial, THE Agente SHALL mostrar una lista de conversaciones anteriores ordenadas por fecha descendente.
3. WHEN un Usuario_Preventa selecciona una conversación del historial, THE Agente SHALL mostrar el contenido completo de la conversación incluyendo las estimaciones generadas.

### Requisito 9: Soporte Multiidioma

**Historia de Usuario:** Como Usuario_Preventa, quiero interactuar con el Agente en mi idioma preferido, para que pueda comunicarme de forma natural y generar estimaciones en el idioma adecuado para cada cliente.

#### Criterios de Aceptación

1. THE Agente SHALL soportar conversaciones únicamente en los siguientes cuatro idiomas: español, inglés, portugués y alemán.
2. WHEN un Usuario_Preventa escribe en uno de los cuatro idiomas soportados, THE Agente SHALL responder en el mismo idioma detectado.
3. WHEN un Usuario_Preventa escribe en un idioma no soportado, THE Agente SHALL informar al Usuario_Preventa que el idioma no está disponible e indicar los cuatro idiomas soportados.
4. THE Agente SHALL generar las Estimaciones en el mismo idioma en el que se está llevando a cabo la conversación.

### Requisito 10: Datos del Partner y Cliente Final

**Historia de Usuario:** Como Usuario_Preventa, quiero registrar los datos del partner y del cliente final antes de generar una estimación, para que cada estimación quede asociada a un contexto comercial específico.

#### Criterios de Aceptación

1. BEFORE generar una Estimación, THE Agente SHALL solicitar al Usuario_Preventa los siguientes datos obligatorios: nombre del partner o socio de negocio, correo electrónico del partner, región o país de procedencia y nombre del cliente final.
2. THE Agente SHALL validar que el correo electrónico del partner tenga un formato válido antes de proceder con la generación de la Estimación.
3. WHEN el Usuario_Preventa no proporciona alguno de los datos obligatorios, THE Agente SHALL indicar cuáles datos faltan y no proceder con la generación de la Estimación hasta que estén completos.
4. THE Agente SHALL incluir los datos del partner y del cliente final en cada Estimación generada y en los archivos exportados.

### Requisito 11: Consolidación de Estimaciones Externas

**Historia de Usuario:** Como Usuario_Preventa, quiero consolidar estimaciones de otros servicios externos con las estimaciones generadas por el Agente, para que pueda entregar una estimación final unificada al cliente.

#### Criterios de Aceptación

1. WHEN el Agente finaliza la generación de una Estimación para los Servicios_Soportados, THE Agente SHALL preguntar al Usuario_Preventa si desea consolidar estimaciones externas.
2. WHEN el Usuario_Preventa acepta consolidar, THE Agente SHALL permitir al Usuario_Preventa subir un archivo en formato JSON que contenga estimaciones de otros servicios fuera de los Servicios_Soportados de AWS.
3. THE Agente SHALL validar que el archivo subido sea un JSON válido antes de procesarlo.
4. WHEN el archivo JSON es válido, THE Agente SHALL tomar la información del archivo tal cual y agregarla a la Estimación generada sin modificar ni recalcular los datos externos.
5. THE Agente SHALL generar una Estimación final consolidada que incluya las estimaciones de los Servicios_Soportados generadas por el Agente junto con las estimaciones externas del archivo JSON.
6. WHEN el Usuario_Preventa no desea consolidar, THE Agente SHALL entregar únicamente la Estimación de los Servicios_Soportados como versión final.

### Requisito 12: Envío de Estimación por Correo Electrónico

**Historia de Usuario:** Como Usuario_Preventa, quiero recibir la estimación final por correo electrónico, para que tenga un registro formal y pueda reenviarla fácilmente al cliente o al partner.

#### Criterios de Aceptación

1. WHEN la Estimación final está lista (con o sin consolidación de estimaciones externas), THE Agente SHALL enviar automáticamente un correo electrónico al Usuario_Preventa con la Estimación completa.
2. THE correo electrónico SHALL enviarse en formato de texto plano e incluir el detalle completo de la Estimación directamente en el cuerpo del mensaje, y además adjuntar la Estimación en formato PDF.
3. THE correo electrónico SHALL incluir las estimaciones de todos los Servicios_Soportados solicitados (Amazon Connect, Amazon Bedrock AgentCore y/o Amazon Quick) junto con las estimaciones externas consolidadas si las hubiera.
4. THE correo electrónico SHALL incluir los datos del partner, región de procedencia y nombre del cliente final en el encabezado de la Estimación.
5. WHEN el envío del correo falla, THE Agente SHALL informar al Usuario_Preventa del error y ofrecer la opción de reintentar el envío o descargar la Estimación manualmente.

### Requisito 13: Actualización de Precios desde Fuentes Oficiales

**Historia de Usuario:** Como Usuario_Preventa, quiero que el Agente utilice datos de precios actualizados de las fuentes oficiales de AWS, para que las estimaciones que genere sean precisas y reflejen los costos vigentes.

#### Criterios de Aceptación

1. THE Agente SHALL obtener y actualizar los datos de precios de cada Servicio_Soportado consultando las siguientes URLs oficiales de pricing:
   - Amazon Quick: https://aws.amazon.com/quick/pricing/
   - Amazon Connect: https://aws.amazon.com/es/connect/pricing/
   - Amazon Bedrock AgentCore: https://aws.amazon.com/bedrock/agentcore/pricing/
2. THE Agente SHALL ejecutar un proceso de actualización profunda de precios de forma periódica (al menos una vez al día) para garantizar que los datos estén vigentes.
3. WHEN el Agente no pueda acceder a alguna de las URLs de pricing, THE Agente SHALL utilizar los últimos datos de precios disponibles en caché e informar al Usuario_Preventa que los precios podrían no estar completamente actualizados.
4. THE Agente SHALL registrar la fecha y hora de la última actualización exitosa de precios para cada Servicio_Soportado.
5. THE Agente SHALL incluir en cada Estimación la fecha de la última actualización de precios utilizada como referencia.

### Requisito 14: Interfaz Web

**Historia de Usuario:** Como Usuario_Preventa, quiero acceder al Agente a través de una aplicación web, para que pueda utilizarlo desde cualquier navegador sin necesidad de instalar software adicional.

#### Criterios de Aceptación

1. THE Agente SHALL estar disponible a través de una aplicación web accesible desde navegadores modernos (Chrome, Firefox, Edge, Safari).
2. THE aplicación web SHALL presentar una interfaz de chat como canal principal de interacción con el Agente.
3. THE aplicación web SHALL ser responsiva y adaptarse a diferentes tamaños de pantalla (escritorio y tablet).
4. THE aplicación web SHALL integrarse con Amazon Cognito para gestionar el inicio de sesión y la autenticación de los usuarios directamente desde el navegador.
5. THE aplicación web SHALL permitir la carga de archivos JSON para la consolidación de estimaciones externas y la descarga de estimaciones en formato PDF.

### Requisito 15: Despliegue en AWS

**Historia de Usuario:** Como equipo de operaciones, quiero que el Agente se despliegue en una región específica de AWS, para que cumpla con los requisitos de latencia y gobernanza de la organización.

#### Criterios de Aceptación

1. THE Agente y todos sus componentes de infraestructura SHALL desplegarse en la región de AWS US East (N. Virginia) - us-east-1.
2. THE todos los servicios utilizados por el Agente (Cognito, almacenamiento, cómputo, envío de correos) SHALL estar configurados en la región us-east-1.

### Requisito 16: CI/CD y Control de Versiones

**Historia de Usuario:** Como equipo de desarrollo, quiero que el Agente se despliegue mediante un pipeline de CI/CD conectado a un repositorio de GitHub, para que los cambios y actualizaciones se gestionen de forma automatizada y controlada.

#### Criterios de Aceptación

1. THE código fuente del Agente SHALL estar alojado en un repositorio de GitHub.
2. THE sistema SHALL contar con un pipeline de CI/CD que se active automáticamente cuando se realicen cambios en la rama principal del repositorio.
3. THE pipeline de CI/CD SHALL ejecutar pruebas automatizadas antes de desplegar los cambios en el ambiente de producción.
4. THE pipeline de CI/CD SHALL desplegar los cambios en la región us-east-1 de forma automatizada tras la aprobación de las pruebas.
5. WHEN un despliegue falla, THE pipeline SHALL revertir automáticamente al último despliegue exitoso y notificar al equipo de desarrollo.

### Requisito 17: Modelo de IA

**Historia de Usuario:** Como equipo de desarrollo, quiero que el Agente utilice un modelo de IA específico, para que las respuestas y estimaciones sean consistentes y de alta calidad.

#### Criterios de Aceptación

1. THE Agente SHALL utilizar el modelo Amazon Nova Pro a través de Amazon Bedrock como motor de procesamiento de lenguaje natural.
2. THE Agente SHALL invocar el modelo Amazon Nova Pro para interpretar las preguntas del Usuario_Preventa, generar estimaciones y mantener el contexto conversacional.
3. WHEN el modelo Amazon Nova Pro no esté disponible, THE Agente SHALL informar al Usuario_Preventa que el servicio está temporalmente fuera de servicio.
4. THE Agente SHALL utilizar prompts optimizados mediante técnicas de prompt engineering para obtener resultados de alta precisión en la interpretación de preguntas, cálculo de estimaciones y generación de respuestas.
5. THE prompts del Agente SHALL incluir instrucciones específicas de contexto, formato de salida esperado y restricciones de alcance para minimizar respuestas imprecisas o fuera de tema.
