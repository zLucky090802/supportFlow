# Sprint 6: cierre de integracion de la API

## Alcance

Cierre funcional de la API del MVP: autenticacion, Users, Customers,
Organizations, Conversations y Messages. Orders se excluye por decision de
Daniel. El codigo, configuracion y dependencias de RAG quedan exclusivamente a
su cargo y no forman parte de esta validacion.

## Cobertura

| Objetivo | Evidencia automatizada |
| --- | --- |
| Login y JWT reales; identidad actualizada | test_auth_api, test_auth_core, test_final_api_integration |
| Roles ADMIN, SUPERVISOR y AGENT | test_sprint1_permissions, test_conversation_integration, test_final_api_integration |
| Aislamiento entre organizaciones | test_resource_privacy, test_sprint1_permissions, test_final_api_integration |
| Asignacion y reasignacion | test_conversation_assignment, test_conversation_integration |
| Identidad de mensajes desde JWT | test_secure_messages |
| Estados y resolved_at | test_conversation_integration |
| Users, Customers y Organizations integrados | test_final_api_integration |
| Respuestas sin credenciales ni errores internos | test_final_api_integration, test_message_routes, test_auth_api |
| MySQL real y operaciones simultaneas | integration/test_mysql_permissions |

Las pruebas aisladas usan la aplicacion ASGI y una base SQLite temporal. La
suite MySQL usa DATABASE_URL y get_db reales, sin sobrescribir esa dependencia.
Verifica tambien cambios de rol con un token existente y recursos de otra
organizacion sin efectos persistidos. Su limpieza usa exclusivamente los UUID
de los registros temporales creados por cada prueba.

## Ejecucion

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -q
$env:SUPPORTFLOW_RUN_MYSQL_TESTS = '1'
try {
    & .\.venv\Scripts\python.exe -m unittest discover -s tests/integration -v
} finally {
    Remove-Item Env:SUPPORTFLOW_RUN_MYSQL_TESTS
}
```

MySQL debe estar disponible y usar InnoDB. Ejecutar cada suite en un proceso
separado. No se hacen cambios de esquema ni se prueban proveedores externos.

## Limites del cierre

- Cambiar un rol conserva asignaciones anteriores; el acceso sigue sujeto al
  rol actual. Observacion no bloqueante aceptada en Sprint 2.
- El correo es unico globalmente; un error de duplicado puede revelar su
  disponibilidad. Observacion no bloqueante aceptada en Sprint 2.
- No hay refresh tokens, revocacion por logout/cambio de password, recuperacion
  de password, MFA ni limite de intentos de login. No se certifica despliegue
  publico, carga, HTTPS ni configuracion de infraestructura.
- Errores SQL conocidos usan el sobre JSON de la API. Errores inesperados o de
  validacion de respuesta conservan el 500 generico de FastAPI, en texto plano
  y sin detalles internos; la suite comprueba ambos comportamientos.
- La concurrencia probada cubre reasignacion frente a escritura de mensajes y
  estados con dos sesiones. No equivale a una prueba de carga ni a verificar
  todas las carreras posibles entre administracion de usuarios y operacion.

El cierre confirma el comportamiento cubierto por las pruebas; no constituye
una auditoria exhaustiva de seguridad. Revision y validacion a cargo de backend
y tech lead, sin incorporar QA adicional por defecto.
