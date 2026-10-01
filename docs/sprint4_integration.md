# Sprint 4: permisos e integracion de conversaciones

Este cierre verifica el flujo desde login hasta lectura, asignacion, respuesta y
cambios de estado. Conserva la politica operativa existente:

| Operacion dentro de la misma organizacion | ADMIN | SUPERVISOR | AGENT |
| --- | --- | --- | --- |
| Leer conversacion e historial, responder, cambiar estado | Si | Si | Solo asignadas |
| Crear, asignar, reasignar o desasignar | Si | Si | No |

Los recursos ajenos e inexistentes devuelven el mismo 404; la falta de permiso
dentro de la propia organizacion devuelve 403. La lectura individual de mensajes
y las dos rutas de historial aplican el permiso de su conversacion. Tras
reasignar, el agente anterior pierde ese acceso y el nuevo puede operar con su
token existente.

## Cambios de estado

PATCH /conversations/{id} recibe solo `{"status": "RESOLVED"}` (o uno de los
otros tres estados). El servicio valida el acceso al recurso mediante el
usuario ya obtenido del JWT, bloquea la fila y persiste dentro de la misma
transaccion. Los fallos provocan rollback.

| Estado destino | Efecto en resolved_at |
| --- | --- |
| RESOLVED | Establece la fecha de resolucion; repetir RESOLVED conserva la existente |
| CLOSED | Conserva la fecha de resolucion si existe |
| OPEN o ESCALATED | Limpia la fecha de resolucion |

No se agregan restricciones nuevas a la secuencia de estados. No se introduce
borrado fisico ni se modifica la politica de respuesta por estado.

Los cuerpos de creacion y actualizacion rechazan campos adicionales con 422.
Asignaciones se cambian solo mediante /assign y /unassign. Campos como
assigned_agent_id, resolved_at u organization_id no pueden colarse en un PATCH
de estado. La creacion admite exclusivamente organization_id y customer_id.

## Verificacion

- Suite aislada: `python -m unittest discover -s tests -q` usando el Python de
  `.venv`. Incluye login con hashes reales, JWT, matrices por rol/tenant,
  timestamps y consistencia entre rutas relacionadas.
- Suite MySQL optativa: comandos y limpieza de datos temporales en
  [Sprint 2](sprint2_assignment.md#pruebas-reproducibles). Incluye el ciclo de
  estados por rol, reasignacion y bloqueo de escrituras concurrentes.

Las comprobaciones del sprint no requieren invocar proveedores RAG. La ingesta
de documentos queda fuera de este alcance. Siguen vigentes las observaciones no
bloqueantes: cambiar un rol conserva asignaciones anteriores y el correo mantiene
unicidad global. El barrido completo del MVP corresponde al Sprint 6.
