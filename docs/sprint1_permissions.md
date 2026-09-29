# Sprint 1: Authorization and Permissions

## Authorization order

After JWT authentication, resource operations apply checks in this order:

1. Load the referenced resource (if required) and verify its organization matches
   the authenticated user. Creation validates the destination organization and
   related resources before role permissions.
2. Check the role permitted for the operation.
3. For AGENT conversation operations, require
   `conversation.assigned_agent_id == current_user.id`.

Lists without a resource ID use the authenticated user's organization as their
scope. Conversation list queries also filter by assignment for agents. They do
not retrieve unrestricted lists and then filter the response in memory.
Authentication rejects unsupported roles; resource authorization also explicitly
checks allowed roles as defense in depth.

When a resource cannot be found, its service returns 404 before resource permission
checks. Existing forbidden resources return 403. This distinction can disclose
existence; normalizing it is a separate privacy hardening task.

## Current endpoint policy

All permissions in this table are limited to the caller's organization.

| Operation | ADMIN | SUPERVISOR | AGENT |
| --- | --- | --- | --- |
| Users: list/read/create/update/delete | Allowed | Denied | Denied |
| Conversations: list/read/update status | Allowed | Allowed | Assigned only |
| Conversations: create | Allowed | Allowed | Denied |
| Messages: read/history/reply | Allowed | Allowed | Assigned conversation only |
| Customers: list/read/create/update/delete | Allowed | Allowed | Denied |
| Organizations: read own | Allowed | Allowed | Allowed |
| Organizations: update own | Allowed | Denied | Denied |
| Organizations: create/delete | Denied pending onboarding policy | Denied | Denied |

Message creation still requires `sender_type=AGENT` and `sender_id` equal to the
authenticated user's ID; spoofing is denied. Deriving sender fields entirely in
the backend belongs to Sprint 3. Message editing/deletion remain unavailable.

`/auth/me` returns the caller's own account. `/db-health` is an ADMIN-only technical
diagnostic and does not select tenant resources. Neither grants platform-wide
access to business resources.

## Verification

`tests/test_sprint1_permissions.py` exercises the real application and JWTs with
an isolated SQLite database. Positive/negative role matrices cover Users,
Conversations and Messages. Cross-tenant writes are checked for persisted side
effects, and direct tests verify that role checks are not called after a tenant
mismatch. Existing tests cover related Customers and Organizations restrictions.

The suite does not write to the configured MySQL database. MySQL deployment QA
and concurrency between reassignment and message posting remain separate work.
Assignment endpoints are Sprint 2; state-transition integration closure is Sprint 4.
