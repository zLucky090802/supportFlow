# Sprint 3: mensajes internos con identidad JWT

Con el token obtenido en `/auth/login`, enviar:

```http
POST /conversations/{conversation_id}/messages
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{"content": "Hola, estoy revisando tu solicitud."}
```

El backend establece `sender_id` con el ID del usuario autenticado y
`sender_type=AGENT` para ADMIN, SUPERVISOR y AGENT. Este tipo identifica un
remitente humano interno, no el rol administrativo del usuario.

Se mantiene `POST /messages` con este cuerpo:

```json
{"conversation_id": "UUID de la conversacion", "content": "Hola."}
```

Ambas rutas rechazan campos adicionales con 422, incluidos `sender_id`,
`sender_type` y `organization_id`, incluso si coinciden con el usuario actual.
Los clientes que enviaban el contrato anterior deben quitar los campos de
remitente. En la ruta anidada tampoco se acepta conversation_id en el cuerpo.

## Permisos y lectura

- ADMIN y SUPERVISOR pueden responder en conversaciones de su organizacion.
- AGENT responde solo en conversaciones asignadas a su ID.
- Un recurso ajeno o inexistente devuelve el mismo 404; un permiso insuficiente
  dentro de su organizacion devuelve 403. Sin JWT valido devuelve 401.
- El servicio bloquea la conversacion, valida permisos y guarda el mensaje en la
  misma transaccion; conserva la proteccion de concurrencia del Sprint 2.
- GET /conversations/{id}/messages y GET /messages/by-conversation/{id} devuelven
  el mismo historial con los mismos permisos, ordenado por created_at e id.
- GET /messages/{id} valida el acceso a la conversacion del mensaje.
- No existen rutas normales para modificar o eliminar mensajes, ni rutas para
  crear mensajes AI/CUSTOMER. La funcion interna existente no es un endpoint.

## Validacion

`tests/test_secure_messages.py` cubre identidad JWT por rol, ambos contratos,
suplantacion, aislamiento, historial, autenticacion y ausencia de edicion/borrado.
La suite MySQL comprueba persistencia del remitente derivado, rutas anidadas y
concurrencia con reasignacion. Comandos de ejecucion en
[Sprint 2](sprint2_assignment.md#pruebas-reproducibles).

Las dos observaciones no bloqueantes aceptadas en Sprint 2 siguen vigentes:
cambiar el rol conserva asignaciones previas y el correo mantiene unicidad global.
