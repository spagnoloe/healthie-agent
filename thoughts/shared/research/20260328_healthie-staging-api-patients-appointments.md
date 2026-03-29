---
date: 2026-03-28T00:00:00-05:00
researcher: spagnoloe
git_commit: 58514db22331979f69343e8fd992697ee4c04c6e
branch: chore/remaining-research
repository: healthie-agent
topic: "Healthie Staging API: Finding Patients and Creating Appointments"
tags: [research, healthie, graphql, api, staging, patients, appointments]
status: complete
autonomy: autopilot
last_updated: 2026-03-28
last_updated_by: spagnoloe
---

# Research: Healthie Staging API — Finding Patients and Creating Appointments

**Date**: 2026-03-28
**Researcher**: spagnoloe
**Git Commit**: 58514db22331979f69343e8fd992697ee4c04c6e
**Branch**: chore/remaining-research

## Research Question

How do you use Healthie's Staging (Sandbox) API to find patients and create appointments? What are the setup steps, authentication requirements, GraphQL operations, and field contracts involved?

---

## Summary

Healthie exposes a GraphQL API — the same one powering its own web and mobile apps — through two separate environments: **Production** (`https://api.gethealthie.com/graphql`) and **Sandbox/Staging** (`https://staging-api.gethealthie.com/graphql`). The Sandbox environment is a near-full-feature replica of Production, intended for development and testing with synthetic (non-PHI) data.

Finding a patient uses the `users` query, searching by name via the `keywords` argument. The response includes a `dob` field that can be used for identity verification. Creating an appointment uses the `createAppointment` mutation, which accepts a patient ID (`user_id` or `attendee_ids`), a datetime, a contact type, and optional appointment type metadata.

Both operations authenticate with a static API key passed in the `Authorization` HTTP header as a Bearer token.

---

## Detailed Findings

### 1. Sandbox Account Setup

To gain access to the Staging API, a separate Sandbox account is required — Production credentials cannot be used.

**Steps:**

1. Sign up at `https://securestaging.gethealthie.com/users/sign_up/provider`
   - Select **"Digital Health Startup"** when prompted.
   - Note: `https://secure.gethealthie.com` is the Production sign-up — do not confuse the two.

2. Generate an API Key:
   - Log in to the Sandbox account.
   - Navigate to **Settings → Developer → API Key**.
   - Click **Add API Key**, give it a name, and click **Create API Key**.

3. Each team member who needs a key must be added to the Sandbox environment individually with their own email address.

> **Important:** Marketplace/technology partners must first obtain the Sandbox Terms of Use from `marketplace@gethealthie.com`. Healthie provider customers can self-serve.

---

### 2. Authentication

All API requests are HTTP POSTs to the GraphQL endpoint. The API key is passed as a Bearer token in the `Authorization` header:

```
POST https://staging-api.gethealthie.com/graphql
Content-Type: application/json
Authorization: Bearer {YOUR_SANDBOX_API_KEY}
```

The key is static (no OAuth flow). There is no session management; each request is independently authenticated. The `revokeToken` mutation can be used to invalidate a key programmatically.

---

### 3. Finding a Patient — `users` Query

**Reference:** `https://docs.gethealthie.com/reference/2024-07-01/queries/users`

The `users` query returns a paginated collection of patients (not providers — use `organizationMembers` for providers).

#### Key Arguments

| Argument | Type | Notes |
|---|---|---|
| `keywords` | `String` | Free-text search across patient name; primary search mechanism |
| `id` | `ID` | Fetch a single patient by exact ID |
| `ids` | `[ID]` | Fetch a set of patients by IDs |
| `active_status` | `String` | `"active"` or `"archived"` |
| `show_all_by_default` | `Boolean` | When `false`, returns empty unless `keywords` or `conversation_id` is provided |
| `page_size` | `Int` | Max 100 per page |
| `offset` | `Int` | Pagination offset |
| `sort_by` | `String` | e.g., `last_name_asc`, `first_name_asc`, `created_at_desc` |

> **Note:** The `email` argument is documented but marked as "Does nothing" — do not rely on it for filtering.

#### Minimal Query Example — Search by Name

```graphql
query FindPatients($keywords: String) {
  users(
    keywords: $keywords
    show_all_by_default: false
    active_status: "active"
    page_size: 10
  ) {
    id
    first_name
    last_name
    dob
    email
    phone_number
  }
}
```

Variables:
```json
{
  "keywords": "Jane Doe"
}
```

#### Identity Verification

The `dob` field (date of birth) is available on the `User` type and is commonly used to disambiguate patients with similar names after an initial keyword search.

---

### 4. Creating an Appointment — `createAppointment` Mutation

**Reference:** `https://docs.gethealthie.com/reference/2024-07-01/mutations/createappointment`
**Input type:** `https://docs.gethealthie.com/reference/2024-07-01/input-objects/createappointmentinput`

> This mutation is for **providers**. Patients booking through a consumer-facing flow use `completeCheckout` instead.

#### Key Input Fields

| Field | Type | Notes |
|---|---|---|
| `user_id` | `ID` | The patient (client) being scheduled |
| `attendee_ids` | `[ID]` | Alternative way to specify patient(s) |
| `datetime` | `String` | Preferred field. Format: `YYYY-MM-DD HH:MM:SS` or ISO8601. Supersedes `date`+`time`. |
| `date` | `ISO8601DateTime` | Used when `datetime` is not provided |
| `time` | `String` | Used alongside `date` when `datetime` is not provided |
| `contact_type` | `String` | Required (unless `is_blocker: true`). Values: `"Video Call"`, `"In Person"`, `"Phone Call"`, etc. |
| `appointment_type_id` | `ID` | Optional — associates the appointment with a configured appointment type |
| `timezone` | `String` | Overrides the current user's timezone for interpreting `date`/`time` fields |
| `notes` | `String` | Optional appointment notes |
| `is_blocker` | `Boolean` | If `true`, creates a blocked time slot rather than a patient appointment |
| `enforce_availability` | `Boolean` | When `true`, checks if the time slot is available before creating. Incompatible with recurring appointments. |
| `suppress_webhook_notifications` | `Boolean` | When `true`, suppresses `appointment.created` webhook events for this call. Incompatible with recurring appointments. |

#### Minimal Mutation Example

```graphql
mutation CreateAppointment($input: createAppointmentInput) {
  createAppointment(input: $input) {
    appointment {
      id
      date
      time
      contact_type
      status
    }
    messages {
      field
      message
    }
  }
}
```

Variables:
```json
{
  "input": {
    "user_id": "12345",
    "datetime": "2026-04-15 10:00:00",
    "contact_type": "Phone Call",
    "timezone": "America/New_York"
  }
}
```

#### Response Structure

The mutation returns a `createAppointmentPayload`:

| Field | Type | Notes |
|---|---|---|
| `appointment` | `Appointment` | The created appointment object (includes `id`, `date`, `time`, `contact_type`, etc.) |
| `messages` | `[FieldError]` | List of validation errors, if any. Each has `field` and `message`. |

A successful response has a non-null `appointment.id` and an empty `messages` array. On failure, `appointment` may be null and `messages` will contain structured error details.

---

### 5. Sandbox Environment Constraints

| Constraint | Detail |
|---|---|
| No real PHI | All test data must be synthetic — no HIPAA identifiers |
| Some integrations unavailable | Zoom, Outlook, and iCal syncs are not available in Sandbox |
| Lower resources | Sandbox may have higher latency than Production |
| API Explorer available | `https://docs.gethealthie.com/explorer` — requires a valid API key |

---

### 6. API Explorer and Tooling

Healthie provides a GraphiQL-based API Explorer at `https://docs.gethealthie.com/explorer` for interactive query development. A valid API key must be configured before use.

For programmatic HTTP usage, Healthie recommends:
- **Postman** or **Insomnia** for manual testing
- **Apollo Client** (JavaScript) or **GraphQL-Client** (Ruby) for application code
- **Healthie Dev Assist MCP** — an MCP tool that connects Healthie's GraphQL API to AI assistants (Claude, Cursor) for schema exploration and query writing

---

## Architecture Documentation

- **Protocol**: GraphQL over HTTPS POST. All operations (queries and mutations) go to a single endpoint.
- **Versioning**: The current schema version is `2024-07-01`, reflected in the reference URL path.
- **Error model**: Errors surface in two places: HTTP-level errors (e.g., 401 unauthorized) and GraphQL-level `messages` arrays on mutation payloads. Queries surface errors in the standard GraphQL `errors` top-level key.
- **Pagination**: The `users` query supports `offset`/`page_size` pagination as well as cursor-based pagination via `after: Cursor`.
- **Backwards compatibility**: Healthie commits to backwards-compatible API updates — existing queries should continue to work as the platform evolves.

---

## Open Questions

- What is the exact `contact_type` enum accepted by the Staging environment? The docs describe it as a free-text string (e.g., `"Video Call"`, `"In Person"`, `"Phone Call"`), but acceptable values may depend on the account's appointment type configuration.
- Is `appointment_type_id` required in practice on Sandbox, or does the API accept appointments without one?
- What is the exact `Authorization` header format confirmed by Healthie's documentation? The Bearer token pattern is standard for this class of API but was not explicitly documented on the pages available.
