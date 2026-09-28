# User roles

The user service accepts exactly `ADMIN`, `SUPERVISOR` and `AGENT`.
`OWNER` and all other values are rejected. Roles are case-sensitive.

The following permission model is agreed for the authorization stage:

| Capability | ADMIN | SUPERVISOR | AGENT |
| --- | --- | --- | --- |
| Manage users | Yes | No | No |
| View conversations | All within the organization | Team conversations | Assigned conversations |
| Assign/reassign conversations | Yes | Yes, within the team | No |
| Supervise agents | Yes | Yes | No |
| Consult metrics | Yes | Yes | No |
| Manage operational settings | Yes | No critical settings | No |
| Reply and update conversation status | Within defined permissions | Within defined permissions | Assigned conversations, within defined permissions |

This stage validates stored role values, not caller permissions. Authentication,
team membership, endpoint authorization and organization scoping based on the
authenticated caller must be implemented before exposing these operations as
protected features. No role alone establishes the caller's identity.

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

HTTP routes and registration of user handlers in the application remain for the
following stages. No authentication or permission enforcement is claimed here.
