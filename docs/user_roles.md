# User roles

The user service accepts exactly `ADMIN`, `SUPERVISOR` and `AGENT`.
`OWNER` and all other values are rejected. Roles are case-sensitive.

The following permission model is agreed for the authorization stage:

| Capability | ADMIN | SUPERVISOR | AGENT |
| --- | --- | --- | --- |
| Manage users | Yes | No | No |
| View conversations | All within the organization | Permitted operational conversations within the organization | Assigned conversations |
| Assign/reassign conversations | Yes | Yes, within the team | No |
| Supervise agents | Yes | Yes | No |
| Consult metrics | Yes | Yes | No |
| Manage operational settings | Yes | No critical settings | No |
| Reply and update conversation status | Within defined permissions | Within defined permissions | Assigned conversations, within defined permissions |

JWT establishes the caller's identity and reloads their current role from the
database. User management is ADMIN-only within their organization; agents access
assigned conversations. SUPERVISOR accesses permitted operational conversations
within their organization. Currently there is no additional conversation-level
restriction model, so organization scope defines this operational access.
Reassignment, metrics and advanced settings remain future features.

## User service

- Create/update validate name (1–50 characters after trimming), email syntax
  and length (up to 100 characters), and the allowed roles.
- Emails are normalized to lowercase and checked for uniqueness.
- Creating a user requires an existing organization; updates cannot change it.
- Passwords currently require 15–128 characters and cannot be whitespace-only.
  Password spaces are preserved. This is the initial policy for review.
- Passwords use scrypt with a random 16-byte salt, N=131072, r=8, p=1.
  The stored value contains the algorithm, parameters, salt and digest.
  See [OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
- Response schemas exclude passwords and password hashes.
- Omitted or null update fields preserve current values.
- Deletion is blocked while conversations reference the user.

HTTP routes are registered in `app/routes/api.py` and user exception handlers in
`app/main.py`. Swagger exposes the user operations under `/users`.
Authentication and initial role/resource checks are applied to these operations.
See [authentication setup and limitations](authentication.md).
