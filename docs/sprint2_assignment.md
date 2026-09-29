# Sprint 2: asignacion y cierre de observaciones

## Endpoints autenticados

| Metodo y ruta | Permiso | Cuerpo |
| --- | --- | --- |
| PATCH /conversations/{id}/assign | ADMIN o SUPERVISOR, misma organizacion | `{"agent_id": "UUID del agente"}` |
| PATCH /conversations/{id}/unassign | ADMIN o SUPERVISOR, misma organizacion | Sin cuerpo |
| GET /conversations/me | Los tres roles; solo asignadas al usuario actual | Sin cuerpo |
| GET /conversations/by-agent/{id} | ADMIN o SUPERVISOR, agente de su organizacion | Sin cuerpo |

Asignar reemplaza la asignacion anterior. El destinatario debe existir, pertenecer
a la misma organizacion y tener rol AGENT. Un rol de destino diferente devuelve
400. Un AGENT no puede asignar ni desasignar conversaciones. Las asignaciones
conservan status y resolved_at; este sprint no introduce restricciones por estado.

Los recursos inexistentes y los de otra organizacion producen exactamente el mismo
404 y cuerpo: `{"success": false, "message": "Resource not found", "data": null}`.
El 403 sigue indicando permisos insuficientes dentro de la propia organizacion.

## Operaciones simultaneas

Asignar, desasignar, responder y cambiar estado bloquean la fila de conversacion
con SELECT FOR UPDATE antes de validar permisos. La asignacion tambien bloquea
el usuario destinatario al comprobar su rol. Los bloqueos duran hasta commit o
rollback; los errores liberan la transaccion. Se refrescan objetos ORM ya cargados
para evitar autorizar usando una asignacion antigua.

El orden lo determina la adquisicion del bloqueo: si la reasignacion se confirma
primero, la escritura pendiente del agente anterior se rechaza. Si el agente
obtiene el bloqueo primero, su escritura puede completarse antes de la
reasignacion. No se trata de un sistema de versiones ni de notificaciones en vivo.

## Pruebas reproducibles

Suite aislada, sin escribir en MySQL:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Integracion contra la DATABASE_URL configurada para la aplicacion:

```powershell
$env:SUPPORTFLOW_RUN_MYSQL_TESTS = '1'
try {
    & .\.venv\Scripts\python.exe -m unittest discover -s tests/integration -v
} finally {
    Remove-Item Env:SUPPORTFLOW_RUN_MYSQL_TESTS
}
```

Ejecutar esta suite en un proceso separado de las pruebas SQLite. Usa el get_db
real, sin sobrescribir la dependencia, y requiere JWT_SECRET_KEY configurada y
tablas InnoDB. No necesita arrancar Uvicorn: invoca la aplicacion ASGI completa.

Las pruebas crean organizaciones, usuarios, clientes y conversaciones temporales
con UUID exclusivos. Prueban login, roles, privacidad, asignacion, mensajes,
resolved_at y dos conexiones simultaneas con una asignacion antigua en memoria.
El cleanup elimina exclusivamente esos UUID y sus mensajes, y verifica la
eliminacion. No modifica el esquema ni registros preexistentes. Como necesita
commits reales para concurrencia, una interrupcion forzada del proceso puede
impedir ejecutar el cleanup; se recomienda una base dedicada para CI.

Antes de solicitar aprobacion de commit, resolver los hallazgos de QA del alcance
y repetir las pruebas afectadas. Daniel decide el commit y el merge.

## Limites identificados por QA

Las dos observaciones de comportamiento siguientes son no bloqueantes para este
sprint, aceptadas por Daniel para el commit y push. No autorizan merge automatico.

- La comprobacion AGENT se realiza al asignar. Cambiar posteriormente el rol de
  ese usuario no desasigna automaticamente sus conversaciones; sigue sujeto a
  los permisos de su nuevo rol y organizacion.
- El correo sigue siendo unico globalmente. Los errores de correo duplicado al
  crear o actualizar usuarios pueden revelar disponibilidad. El 404 uniforme
  protege consultas de recursos, no cambia esa politica de registro.
- Las pruebas MySQL son optativas y deben ejecutarse explicitamente antes del
  commit cuando un cambio afecte transacciones o consultas especificas de MySQL.
