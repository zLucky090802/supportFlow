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

Missing resources and resources belonging to another organization return the same
404 envelope (`Resource not found`). A denied role or assignment within the
caller's organization returns 403. This privacy correction is included in Sprint 2.

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

Since Sprint 3, message creation derives `sender_type=AGENT` and `sender_id` from
the authenticated user. Client-supplied sender fields are rejected with 422.
See [the message contract](sprint3_messages.md). Editing/deletion remain unavailable.

`/auth/me` returns the caller's own account. `/db-health` is an ADMIN-only technical
diagnostic and does not select tenant resources. Neither grants platform-wide
access to business resources.

## Verification

`tests/test_sprint1_permissions.py` exercises the real application and JWTs with
an isolated SQLite database. Positive/negative role matrices cover Users,
Conversations and Messages. Cross-tenant writes are checked for persisted side
effects, and direct tests verify that role checks are not called after a tenant
mismatch. Existing tests cover related Customers and Organizations restrictions.

The default suite does not write to the configured MySQL database. Sprint 2 adds
explicitly enabled MySQL integration and concurrent-write tests; see
[Sprint 2](sprint2_assignment.md). Broader state-transition integration closure
remains Sprint 4.
