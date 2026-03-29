---
date: 2026-03-28T00:00:00Z
researcher: enric
git_commit: 58514db22331979f69343e8fd992697ee4c04c6e
branch: chore/remaining-research
repository: healthie-agent
topic: "How to use Playwright to find patients and create appointments in Healthie"
tags: [research, playwright, healthie, patient-search, appointments, browser-automation]
status: complete
autonomy: critical
last_updated: 2026-03-28
last_updated_by: enric
---

# Research: Playwright UI Automation for Healthie — Find Patients & Create Appointments

**Date**: 2026-03-28
**Researcher**: enric
**Git Commit**: `58514db22331979f69343e8fd992697ee4c04c6e`
**Branch**: `chore/remaining-research`

## Research Question

How can we use Playwright to find patients and create appointments in Healthie staging (`https://securestaging.gethealthie.com`)?

## Summary

The Healthie staging UI at `https://securestaging.gethealthie.com` is a React SPA with a multi-step login flow, a global patient search bar, and a slide-in appointment creation modal accessible from the Calendar page. All key interactions are automatable with Playwright's async Python API.

The login requires two separate form submissions: email first, then password (the password field is hidden until after email submission). After login, a passkey prompt may appear that must be dismissed. Patient search uses a global `input[name="keywords"]` in the header; results appear as React Select async options with patient name and DOB. Appointment creation requires navigating to `/appointments` and clicking the "Add" button, which opens an aside panel with a tabbed form — the "1:1 Session" tab contains all required fields.

Staging environment has 3 active patients: Jeff Mills (ID: 5769986, DOB: 2024-09-01), Alexander Robinson (ID: 5769987), and John Smith (ID: 5769985).

---

## Detailed Findings

### 1. Login Flow

**URL**: `https://securestaging.gethealthie.com/users/sign_in` — redirects to `/account/login`

The login is a **two-step form**: the password field is hidden until after the email is submitted.

**Step 1 — Email:**
```python
await page.goto("https://securestaging.gethealthie.com/users/sign_in",
                wait_until="domcontentloaded", timeout=60000)
await page.wait_for_timeout(2000)
await page.locator('input[name="identifier"]').fill("enricspagnolo@gmail.com")
await page.locator('button[type="submit"]').first.click()
await page.wait_for_timeout(2000)
```

Key selectors on the login page:
- Email input: `input[name="identifier"]` (placeholder: `name@example.com`)
- Submit button: `button[type="submit"]` (first one)

**Step 2 — Password:**
```python
await page.locator('input[name="password"]').wait_for(state="visible", timeout=10000)
await page.locator('input[name="password"]').fill(PASSWORD)
await page.locator('button:has-text("Log In")').click()
await page.wait_for_timeout(5000)
```

Key selectors:
- Password input: `input[name="password"]` (hidden until step 1 completes)
- Submit button: `button:has-text("Log In")`

**Step 3 — Passkey/Continue prompt (optional):**
```python
cont = page.locator('a:has-text("Continue to app")')
if await cont.count() > 0:
    await cont.click()
    await page.wait_for_timeout(3000)
```

**Final state**: URL becomes `https://securestaging.gethealthie.com/` (the dashboard/home page).

**Session persistence**: Playwright's `context.storage_state(path="auth/state.json")` can be used after login to persist cookies. On subsequent runs, pass `storage_state="auth/state.json"` to `browser.new_context()` and verify the URL is not `/account/login` to confirm the session is still valid.

---

### 2. Patient Search

The global search bar lives in the page header and is available on every page after login.

**Selector**: `input[name="keywords"]`
**Attributes**:
- `placeholder`: `"Search Clients..."`
- `aria-label`: `"Search Clients"`
- `data-testid`: `"header-client-search-form"`

> **Important**: On the `/clients` page there are **two** `input[name="keywords"]` inputs (one global header search, one in-page list search). To avoid a strict-mode violation, use `[data-testid="header-client-search-form"]` or `.first` when on that page. From the home page `/` there is only one.

**Usage:**
```python
await page.locator('[data-testid="header-client-search-form"]').fill("Jeff")
await page.wait_for_timeout(2000)  # wait for async results
```

**Results dropdown:**
- Results appear as React Select async paginate options
- Each option has `role="option"` and class `reactSelectAsyncPaginate__option`
- Option text format: `"{First Last} - {YYYY-MM-DD}"` (name + DOB)
- Example: `"Jeff Mills - 2024-09-01"`
- Option element ID: `react-select-user-option-0` (first result)
- No results case: text `"No results..."` or similar appears in the dropdown

**Selecting a result:**
```python
# Click the first option
await page.locator('[id^="react-select-user-option-"]').first.click()
# or more specifically:
await page.locator('.reactSelectAsyncPaginate__option').first.click()
```

**Extracting patient ID from search result:**
The search result links to `/users/{patient_id}`. After clicking, check `page.url` to extract the ID:
```python
patient_id = page.url.split("/users/")[1].split("/")[0]  # e.g. "5769986"
```

Alternatively, navigate directly to `/users/{patient_id}` if the ID is known.

---

### 3. Patient Detail Page

**URL pattern**: `https://securestaging.gethealthie.com/users/{patient_id}`
**Example**: `/users/5769986` → Jeff Mills

**Page structure:**
- Patient name: visible as sidebar text (e.g., "Jeff Mills") — **no `<h1>`** on the page
- Page has tab navigation (class `_tab_1f5h5_1`): Overview, Care Plans, Journal, Metrics, etc.

**Key information fields** (visible on the Overview tab):
- `Date of birth` — label class: `_label_ab2t6_18`; example value: `"Sep 1, 2024"`
- `Unique client ID` — label class: `_label_ab2t6_18`; numeric ID (same as URL path)
- `Phone number`, `Group`, `Current weight`, `Height`, `Location`, `Timezone`, `Last active`, `Client since`

**Extracting DOB:**
```python
# The DOB label and its value are siblings in a container
dob_label = page.locator("text='Date of birth'")
dob_container = dob_label.locator("xpath=..")
container_text = await dob_container.text_content()
dob_value = container_text.replace("Date of birth", "").strip()
# → "Sep 1, 2024"
```

**DOB format on the page**: `"Mon D, YYYY"` (e.g., `"Sep 1, 2024"`)

**Known staging patients:**

| Name | Patient ID | DOB |
|------|-----------|-----|
| Jeff Mills | 5769986 | 2024-09-01 (Sep 1, 2024) |
| Alexander Robinson | 5769987 | unknown |
| John Smith | 5769985 | unknown |
| Provider (Enric S) | — | other_party_id: 5761693 |

---

### 4. Appointment Creation

**Navigate to Calendar page first:**
```python
await page.goto("https://securestaging.gethealthie.com/appointments",
                wait_until="domcontentloaded", timeout=30000)
await page.wait_for_timeout(4000)
```

> **Note**: The "Add New Appointment" text appears in the home page body, but the interactive button that opens the creation modal is the **"Add" button** on the `/appointments` (Calendar) page, not the home page.

**Trigger button**: `button:has-text("Add")` on `/appointments`
Button class: `_buttonWithTextAndIcon_4mc14_1 _primary_4mc14_1`

**Modal container**: `aside-tab-container` (an aside panel, not a `role="dialog"`)

**Modal tabs:**
- `1:1 Session` — `id="activeTab-AddIndividual"` (default active)
- `Group Session` — `id="tab-AddGroup"`
- `Block` — `id="tab-AddBlock"`

---

#### Modal Form Fields (1:1 Session tab)

| Label | Selector | Type | Notes |
|-------|----------|------|-------|
| Invitee* | `#user` | React Select Async | Type name, select option |
| Appointment type* | `#appointment_type_id` | React Select | Options listed below |
| Contact type* | `#contact_type` | React Select | Default: "Healthie Video Call" |
| Video call method* | `#video_service` | React Select | Default: "internal" |
| Start date* | `input[name="date"]` or `#date` | text | Pre-filled: today's date |
| Start time* | `input[name="time"]` or `#time` | text | Pre-filled: "12:00 PM" |
| Timezone* | `#timezone` | React Select | Auto-detected |
| Notes | `textarea[name="notes"]` or `#notes` | textarea | Optional |
| Repeating appointment? | `input[name="is_repeating"]` | checkbox | Optional |

**Appointment types available:**
1. `"Initial Consultation - 60 Minutes"`
2. `"Follow-up Session - 45 Minutes"`

**Submit button**: `button:has-text("Add Individual Session")`

---

#### Filling the Invitee field

The Invitee field (`#user`) is a React Select Async Paginate component. Type the patient name and select from the dropdown:

```python
await page.locator('#user').fill("Jeff")
await page.wait_for_timeout(2000)
# Dropdown shows: "Jeff Mills - 2024-09-01"
await page.locator('[id^="react-select-user-option-"]').first.click()
```

The dropdown option format is `"{Name} - {YYYY-MM-DD}"`, the same format as the global search bar results.

#### Filling the Appointment Type field

The appointment type is also a React Select component:

```python
await page.locator('#appointment_type_id').click()
await page.wait_for_timeout(1000)
# Click first option (css-178xa9x-option = non-focused, css-1uagbn1-option = focused)
await page.locator('[class*="css-"][class*="-option"]').first.click()
```

#### Filling date and time

The date and time fields accept text input directly. Their current values are pre-filled:

- Date format: `"March 29, 2026"` (Month DD, YYYY)
- Time format: `"12:00 PM"` (H:MM AM/PM)

```python
# Clear and set date
await page.locator('#date').triple_click()
await page.locator('#date').fill("April 1, 2026")

# Clear and set time
await page.locator('#time').triple_click()
await page.locator('#time').fill("2:30 PM")
```

#### Submitting

```python
await page.locator('button:has-text("Add Individual Session")').click()
await page.wait_for_timeout(3000)
# Modal closes on success; no explicit confirmation element captured
```

---

### 5. Navigation Overview

Key URLs after login:

| URL | Description |
|-----|-------------|
| `/` | Home/dashboard — appointments widget, task list |
| `/clients/active` | Active clients list — table with Jeff Mills, Alexander Robinson, John Smith |
| `/appointments` | Calendar view — "Add" button opens appointment creation modal |
| `/users/{id}` | Patient detail — DOB, phone, demographics |
| `/conversations/...` | Chat |
| `/courses` | Education/Programs |
| `/settings/account` | Account settings |

Sidebar nav links (from any page): Home, Chat, Education, Organization, Clients, Calendar, Documents, Forms, Superbills, Payments, Client Packages, Insurance, Faxing, Labs, Marketing, Visualize, Workflows, Settings.

---

## Code References

| File | Description |
|------|-------------|
| `scripts/explore_healthie_ui.py` | Playwright exploration script targeting `/users/5769986` (Jeff Mills) |
| `scripts/screenshots/` | 40+ PNG screenshots from staging UI exploration |
| `scripts/screenshots/01_login_page.png` | Login page with `input[name="identifier"]` visible |
| `scripts/screenshots/30_add_appointment_click.png` through `44_appointment_type.png` | Appointment modal exploration sequence |
| `scripts/screenshots/50_jeff_mills_detail.png` | Jeff Mills patient detail page |

---

## Architecture Documentation

The Healthie staging UI is a **React SPA** with:

- **React Select / React Select Async Paginate** for dropdown fields (Invitee, Appointment type, Contact type, Timezone). These use custom CSS class names (e.g., `reactSelectAsyncPaginate__option`, `reactSelectAsyncPaginate__input`) and `role="option"` for items.
- **CSS Modules** for component styles (hashed class names like `_buttonWithText_4mc14_1`, `_label_ab2t6_18`). These are **stable between sessions** but may change between deployments.
- **`data-testid` attributes** present on some elements (`header-client-search-form`, `search-input`) — these are more stable than CSS module class names for targeting.
- **SPA navigation**: Page transitions don't cause full reloads; use `wait_for_timeout` or `wait_for_load_state` after navigation actions.
- **Hidden inputs**: Many React Select fields have a visible text input + a hidden input pair (e.g., `name="contact_type"` hidden has value `"Healthie Video Call"`).

---

## Open Questions

- The `"Add New Appointment"` text visible in the home page DOM body does not correspond to a clickable button element. The actual trigger is the **"Add" button on `/appointments`**. The exact home page element showing this text was not fully resolved.
- Appointment ID after creation: the modal closes but no explicit ID or confirmation was observed in the DOM. The appointment may need to be verified by querying the appointments list or via the API.
- DOB for Alexander Robinson (5769987) and John Smith (5769985) were not captured — only Jeff Mills (2024-09-01) was confirmed.
- The provider's `other_party_id` (`5761693`) is hardcoded in the hidden field — this is the logged-in provider's ID for Enric Spagnolo.
