# SIPRO — Detailed Development Report
**Property Development Operating System**
**Report Date: April 5, 2026**
**Version: Phase B Complete**

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Database Architecture](#4-database-architecture)
5. [Feature Modules — Detailed Breakdown](#5-feature-modules)
   - 5.1 Authentication & User Management
   - 5.2 Lead Lifecycle Management (CRM)
   - 5.3 Assignment System
   - 5.4 Lead Response Time Tracker
   - 5.5 Project Management
   - 5.6 Unit Management
   - 5.7 Siteplan & Visual Layout
   - 5.8 Deal Management & Sales Pipeline
   - 5.9 Finance Module
   - 5.10 Construction Tracking
   - 5.11 WhatsApp Integration
   - 5.12 Notification System
   - 5.13 Appointment & Calendar
   - 5.14 Dashboard System
   - 5.15 Development Report (Internal)
6. [Implementation Status Summary](#6-implementation-status)
7. [Risk & Technical Debt](#7-risk-technical-debt)
8. [Future Development Recommendations](#8-future-recommendations)

---

## 1. EXECUTIVE SUMMARY

SIPRO is a property development operating system designed to manage the full lifecycle of property sales — from lead acquisition through construction handover. The system serves multiple operational roles: Marketing Admin, Marketing Inhouse (sales), Finance, and Management.

**Current State**: The system has 15 functional modules with 65+ API endpoints, 20 MongoDB collections, and 14 frontend page components. Core CRM, sales, finance, and construction workflows are operational. Phase A (foundation) and Phase B (core flow + enhancement) have been completed.

**Key Achievements (Phase A + B)**:
- Stage-based lead lifecycle fully operational
- Role-based dashboards with auto-detection
- Assignment system with round-robin auto-assign and accept/reject
- Lead response time tracking for sales performance measurement
- Lead timeline with cross-module event aggregation
- Non-destructive data migration for backward compatibility

---

## 2. SYSTEM ARCHITECTURE

### 2.1 High-Level Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend    │────>│   Backend    │────>│   MongoDB    │
│   React 19   │<────│   FastAPI    │<────│  20 Collections│
│  Port 3000   │     │  Port 8001   │     │  Port 27017  │
└──────────────┘     └──────────────┘     └──────────────┘
       │                     │
       │    Kubernetes Ingress (prefix routing)
       │    /api/* → Backend:8001
       │    /*     → Frontend:3000
```

### 2.2 Backend Architecture

The backend is a **monolithic FastAPI application** (server.py, ~2,656 lines) with all routes, models, seed data, and business logic in a single file. There is an `auth.py` module for authentication helpers (bcrypt, JWT, token management).

**Route Organization** (within server.py):
- Auth Routes (register, login, logout, refresh, me)
- Organization Routes
- User Management Routes
- Project Routes (CRUD + unit generation)
- Unit Routes (CRUD + summary)
- Lead Routes (CRUD, pipeline, import, assign, transition, timeline, response-stats)
- Appointment Routes (CRUD, calendar)
- Deal Routes (CRUD, reserve, booking)
- WhatsApp Routes (messages, send, templates)
- Dev Report Routes (CRUD, meta)
- Siteplan Routes (interactive node layout)
- Finance Routes (billing, payments, summary)
- Construction Routes (units, progress, QC, summary)
- Notification Routes (CRUD, auto-rules, simulate followup)
- Dashboard Route (aggregated metrics)

**API Convention**: All endpoints are prefixed with `/api` via APIRouter. Responses follow `{"data": {...}}` or `{"data": [...], "total": N}` format consistently.

### 2.3 Frontend Architecture

React 19 application using:
- **Routing**: React Router v6 (BrowserRouter, protected routes)
- **State Management**: React Context API (AuthContext, LanguageContext)
- **HTTP Client**: Axios with interceptor for auth tokens
- **Styling**: Custom CSS with CSS variables (glassmorphism theme) + Tailwind utilities
- **UI Components**: ~40 Radix UI (shadcn/ui) primitives in `/components/ui/`
- **Icons**: Lucide React

**Component Structure**:
```
/src
├── App.js                    (Router, ProtectedRoute, AppLayout)
├── contexts/
│   ├── AuthContext.js         (login, logout, user state, token refresh)
│   └── LanguageContext.js     (ID/EN toggle with translation map)
├── lib/
│   ├── api.js                 (Axios instance with auth interceptor)
│   └── utils.js               (shadcn/ui utility: cn())
├── components/
│   ├── layout/Sidebar.jsx     (Navigation with Lead Lifecycle sections)
│   ├── dashboard/DashboardPage.jsx   (Role-based multi-view dashboard)
│   ├── crm/CRMPage.jsx              (Lead lifecycle management)
│   ├── crm/LeadImportPage.jsx       (CSV import & manual entry)
│   ├── projects/ProjectsPage.jsx    (Project CRUD)
│   ├── units/UnitsPage.jsx          (Unit management)
│   ├── siteplan/SiteplanPage.jsx    (Interactive visual layout)
│   ├── deals/DealsPage.jsx          (Sales pipeline)
│   ├── finance/FinancePage.jsx      (Billing & payments)
│   ├── construction/ConstructionPage.jsx (Progress & QC)
│   ├── whatsapp/WhatsAppPage.jsx    (Message sending)
│   ├── appointments/AppointmentsPage.jsx (Calendar & scheduling)
│   ├── notifications/NotificationsPage.jsx (Notification center)
│   ├── dev-report/DevReportPage.jsx (Internal dev tracking)
│   └── auth/LoginPage.jsx          (Login form)
```

### 2.4 Design System

- **Theme**: Glassmorphism with frosted glass cards, backdrop-filter blur
- **Font**: Plus Jakarta Sans (via Google Fonts)
- **Color Palette**: 
  - Primary: `#2563eb` (blue)
  - Success: `#10b981` (green)
  - Warning: `#f59e0b` (amber)
  - Danger: `#ef4444` (red)
  - Purple: `#7c3aed`
  - Sidebar: `#0f1729` (dark navy)
- **Layout**: Fixed sidebar (200px) + fluid content area
- **Responsive**: Desktop-first, sidebar collapsible

---

## 3. TECHNOLOGY STACK

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React | 19 | UI framework |
| Frontend | React Router | 6 | Client-side routing |
| Frontend | Tailwind CSS | 3.x | Utility CSS |
| Frontend | Radix UI | Latest | Accessible primitives |
| Frontend | Lucide React | Latest | Icon library |
| Frontend | Axios | 1.x | HTTP client |
| Frontend | CRACO | 7.x | CRA config override |
| Backend | FastAPI | 0.109+ | API framework |
| Backend | Motor | 3.3+ | Async MongoDB driver |
| Backend | Pydantic | 2.x | Data validation |
| Backend | PyJWT | 2.8+ | JWT tokens |
| Backend | bcrypt | 4.1+ | Password hashing |
| Backend | Uvicorn | 0.25 | ASGI server |
| Database | MongoDB | 6.x+ | Document store |
| Infra | Supervisor | - | Process management |
| Infra | Kubernetes | - | Container orchestration |

---

## 4. DATABASE ARCHITECTURE

### 4.1 Collections Overview (20 Collections)

| Collection | Records | Purpose | Status |
|-----------|---------|---------|--------|
| `users` | 5 | Authentication, roles, profiles | ACTIVE |
| `organizations` | 1 | Multi-tenant org structure | ACTIVE (unused scope) |
| `projects` | 2 | Property development projects | ACTIVE |
| `units` | 150 | Individual property units | ACTIVE |
| `leads` | 22+ | CRM lead records | ACTIVE - PRIMARY |
| `lead_activities` | ~5 | Lead interaction logs | ACTIVE |
| `appointments` | 4 | Survey/meeting schedules | ACTIVE |
| `deals` | 8 | Sales transactions | ACTIVE |
| `billing_schedules` | 4 | Finance billing records | ACTIVE |
| `payments` | ~3 | Payment records | ACTIVE |
| `construction_units` | 5 | Construction tracking per unit | ACTIVE |
| `whatsapp_messages` | ~5 | WA message log (MOCKED) | ACTIVE |
| `whatsapp_templates` | 0 | WA message templates | EMPTY |
| `notifications` | 6+ | In-app notifications | ACTIVE |
| `auto_followup_rules` | 0 | Auto follow-up config | EMPTY |
| `events` | 30+ | System event audit log | ACTIVE |
| `login_attempts` | 0-1 | Brute-force protection | ACTIVE |
| `dev_report_items` | 3 | Dev tracking items | ACTIVE |
| `dev_report_meta` | 0-1 | Dev report metadata | ACTIVE |
| `siteplan_nodes` | 0 | Custom siteplan layouts | EMPTY |

### 4.2 Key Data Models

#### Lead Document (Primary Entity)
```json
{
  "id": "lead-001",                    // UUID string
  "name": "Budi Santoso",
  "phone": "+62812000000",
  "email": "budi@email.com",
  "source": "meta_ads",               // meta_ads|google_ads|tiktok_ads|referral|walk_in|website|event|manual|csv_import
  "campaign": "Campaign Q1 2026",
  "ad_set": "Ad Set A",
  "ad_name": "Ad Creative 1",
  "notes": "",
  "project_id": "proj-001",
  "assigned_to": "sales1@sipro.com",   // User email
  "assignment_status": "pending",       // pending|accepted|rejected (NEW Phase B)
  "assignment_history": [               // (NEW Phase B)
    {
      "from": null,
      "to": "sales1@sipro.com",
      "assigned_by": "system:auto-assign",
      "reason": "Round-robin auto-assignment",
      "action": "auto_assigned",
      "timestamp": "2026-04-05T09:55:00Z"
    }
  ],
  "status": "new",                     // LEGACY: new|contacted|prospect|no_response|lost
  "stage": "acquisition",             // PRIMARY: acquisition|nurturing|appointment|booking|recycle
  "quality_score": 47,
  "follow_up_count": 0,
  "last_contacted_at": null,
  "nurturing_outcome": null,           // NOT YET USED
  "response_time_minutes": 17,         // (NEW Phase B Enhancement) - computed on first contact
  "import_batch": null,
  "created_by": "admin@sipro.com",
  "created_at": "2026-04-05T09:30:00Z",
  "updated_at": "2026-04-05T09:45:00Z"
}
```

#### Unit Document
```json
{
  "id": "uuid",
  "project_id": "proj-001",
  "block": "A", "number": "1", "label": "A-1",
  "unit_type": "standard",
  "floor_area": 36, "land_area": 72,
  "price": 500000000,
  "status": "available",               // available|reserved|booked|sold
  "deal_status": null,                 // Synced from deal lifecycle
  "construction_status": "not_started", // Synced from construction module
  "payment_status": null,              // Synced from finance module
  "coordinates": {"x": 20, "y": 20}   // For siteplan rendering
}
```

#### Deal Document
```json
{
  "id": "uuid",
  "lead_id": "lead-001",
  "customer_name": "Budi",
  "customer_email": "...", "customer_phone": "...",
  "unit_id": "uuid", "unit_label": "A-1",
  "project_id": "proj-001",
  "price": 500000000,
  "payment_method": "cash",
  "notes": "",
  "status": "draft"                    // draft|reserved|booked|active|completed|canceled|expired|failed
}
```

### 4.3 Entity Relationships

```
Organization (1) ──> (*) Projects ──> (*) Units
                                         │
Lead ──> (*) Activities                  │
Lead ──> (*) Appointments                │
Lead ──> (0..1) Deal ─────────────────> Unit
                  │
           Deal ──> (0..1) BillingSchedule ──> (*) Payments
                                    
Unit ──> (0..1) ConstructionUnit ──> (*) Phases ──> (*) Tasks

Events <── all entity changes (audit trail)
Notifications ──> target_user (email or "all")
```

**Important**: All relationships use UUID **string IDs**, not MongoDB ObjectId. No foreign key enforcement. No referential integrity checks.

### 4.4 Database Indexes

The following indexes are created on startup:
- `users.email` (unique)
- `leads.phone`, `leads.email`, `leads.status`, `leads.stage`, `leads.assigned_to`, `leads.source`, `leads.project_id`
- `units.project_id`, `units.status`
- `deals.project_id`, `deals.status`, `deals.unit_id`
- `events.created_at` (descending)
- `billing_schedules.deal_id`, `payments.deal_id`
- `construction_units.unit_id`, `construction_units.project_id`
- `notifications.created_at` (descending), `notifications.target_user`
- `appointments.scheduled_at`
- `login_attempts.identifier`

---

## 5. FEATURE MODULES — DETAILED BREAKDOWN

---

### 5.1 Authentication & User Management

**Status**: IMPLEMENTED

**Architecture**:
- JWT-based authentication (access + refresh tokens)
- httpOnly cookies + Bearer header (dual transport)
- bcrypt password hashing (12 rounds)
- Brute-force protection (5 attempts, 15-minute lockout)
- Role-based user model (but no route-level RBAC enforcement yet)

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login with email/password |
| `/api/auth/logout` | POST | Clear auth cookies |
| `/api/auth/me` | GET | Get current user profile |
| `/api/auth/refresh` | POST | Refresh access token |
| `/api/users` | GET | List all users |

**Roles Defined**:
| Role | Label | Intended Access |
|------|-------|----------------|
| `super_admin` | Super Admin | Full system access |
| `owner` | Owner | Full system access |
| `general_manager` | General Manager | Full system access |
| `sales_manager` / `marketing_admin` | Marketing Admin | Lead management, distribution |
| `sales` / `marketing_inhouse` | Marketing Inhouse | Assigned leads, follow-ups |
| `finance` | Finance | Billing, payments, collections |
| `accounting` | Accounting | Finance access |
| `collection` | Collection | Payment collection |
| `project_manager` | Project Manager | Construction tracking |
| `site_engineer` | Site Engineer | Construction tracking |

**Seeded Users**:
| Email | Password | Role |
|-------|----------|------|
| admin@sipro.com | admin123 | super_admin |
| marketing_admin@sipro.com | sipro123 | marketing_admin |
| sales1@sipro.com | sipro123 | sales |
| sales2@sipro.com | sipro123 | sales |
| finance@sipro.com | sipro123 | finance |

**What's NOT Implemented**:
- No route-level RBAC enforcement (any authenticated user can access any endpoint)
- No user profile editing UI
- No password reset flow (endpoint exists but untested)
- No user invitation workflow
- No organization-scoped multi-tenancy

---

### 5.2 Lead Lifecycle Management (CRM)

**Status**: IMPLEMENTED (Phase A + B)

This is the **core module** of SIPRO. It manages leads through a 5-stage lifecycle.

**Lead Lifecycle Stages**:
```
acquisition → nurturing → appointment → booking → recycle
    │              │            │            │         │
    │              │            │            │         └─ Inactive/failed leads
    │              │            │            └─ Reserve, booking fee, conversion
    │              │            └─ Survey scheduling & completion
    │              └─ Follow-up, prospecting, response tracking
    └─ Lead capture (manual, CSV import, ads)
```

**Stage Transition Logic**:
- Stage transitions are controlled via `POST /api/leads/{id}/transition`
- When transitioning from `acquisition` → `nurturing`, the system automatically:
  - Sets `status = "contacted"` (backward compatibility)
  - Increments `follow_up_count`
  - Sets `last_contacted_at`
  - Computes `response_time_minutes` (time from lead creation to first contact)
- Each stage transition is logged as an event in the `events` collection
- Stage-to-status backward mapping is applied automatically for legacy compatibility

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/leads` | GET | List leads with filters (stage, status, source, project_id, search) |
| `/api/leads` | POST | Create new lead |
| `/api/leads/{id}` | GET | Get single lead |
| `/api/leads/{id}` | PUT | Update lead fields |
| `/api/leads/{id}/activities` | POST | Add activity log |
| `/api/leads/{id}/transition` | POST | Controlled stage transition |
| `/api/leads/{id}/timeline` | GET | Combined timeline (activities + events + WA + assignments) |
| `/api/leads/pipeline` | GET | Stage-based pipeline funnel data |
| `/api/leads/response-stats` | GET | Response time analytics |
| `/api/leads/import` | POST | CSV batch import |

**Frontend (CRMPage.jsx)**:
- Response time mini dashboard (4 KPI cards: avg response, contacted, waiting, avg wait)
- Interactive Lead Lifecycle funnel (clickable stage filters)
- Search + source/project filters
- Leads table with columns: Name, Phone, Stage, Assigned, Source, Response, Actions
- Stage-specific action buttons:
  - Acquisition: "Contact" → transitions to nurturing
  - Nurturing: "Jadwal" → transitions to appointment
  - Appointment: "Book" → transitions to booking
  - Recycle: "Re-engage" → transitions back to acquisition
- Bulk selection with multi-assign modal
- Lead detail panel with:
  - Lead info grid (stage, phone, email, source, follow-up count, response time)
  - Stage transition buttons (all 5 stages clickable)
  - Expandable timeline viewer
  - Notes display

**Lead Import (LeadImportPage.jsx)**:
- CSV upload with auto-header detection
- Supported headers: name/nama, phone/telepon/hp, email, notes/catatan, ad_set/adset, ad_name
- Batch tracking via `import_batch` field
- Deduplication: exact match on phone OR email
- Manual entry via inline table rows
- Platform selection (Meta/Google/TikTok) — UI only, no real API integration

**Data Migration**:
- Non-destructive migration runs on startup (`migrate_lead_stages()`)
- Populates `stage` field for any leads missing it (based on status-to-stage mapping)
- Also ensures `follow_up_count`, `last_contacted_at`, `nurturing_outcome` fields exist

**What's NOT Implemented**:
- Separate dedicated pages per stage (currently uses CRM page with stage filter)
- Nurturing outcome tags (no_response, interested, not_interested, busy, invalid)
- Survey validation (form input, photo upload, notes)
- Booking sub-statuses (pending, partial, paid, expired, cancelled)
- Unit lock on booking
- 7-day auto-recycle rule for no-response appointment leads
- Real ads platform integration (Meta/Google/TikTok API)
- Phone number normalization for deduplication
- Lead scoring engine (quality_score always 0 or random from seed)

---

### 5.3 Assignment System

**Status**: IMPLEMENTED (Phase B)

**Architecture**:
- 1 lead = 1 owner at a time (single assignment model)
- Assignment creates a history record on the lead document
- Assignment has status lifecycle: pending → accepted/rejected
- Auto-assign uses round-robin across eligible users (role: sales, marketing_inhouse)

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/leads/assign` | POST | Manual assign leads to user (bulk) |
| `/api/leads/auto-assign` | POST | Round-robin auto-assign unassigned leads |
| `/api/leads/{id}/assignment/respond` | POST | Accept or reject assignment |

**Manual Assignment Flow**:
```
Marketing Admin selects leads → clicks "Assign" →
  picks target user from dropdown → adds reason (optional) →
  confirms → leads get assigned_to set, assignment_status = "pending"
```

**Auto-Assignment Flow**:
```
Marketing Admin clicks "Auto Assign" →
  system finds unassigned leads in specified stage →
  round-robin distributes to active users with sales/marketing_inhouse role →
  each lead gets assignment_status = "pending"
```

**Accept/Reject Flow**:
```
Sales user sees "PENDING" badge on their assigned leads →
  clicks green check (accept) → assignment_status = "accepted"
  clicks red X (reject) → modal asks for reason → 
  assignment_status = "rejected", assigned_to = null
```

**Frontend UI**:
- "Auto Assign" button in CRM page header
- "Assign (N)" button appears when leads are selected via checkboxes
- Assign modal with user dropdown + reason input
- Accept/reject buttons visible on pending-status leads (only for the assigned user)
- Reject modal with reason textarea
- Assignment status badge on each lead row (color-coded: green=accepted, yellow=pending, red=rejected)

**What's NOT Implemented**:
- Workload-based assignment (capacity tracking per user)
- Marketing inhouse reassignment request flow
- Ownership transfer log as a first-class entity
- Assignment notification (no push/email notification when assigned)
- Assignment SLA (time to accept/reject)

---

### 5.4 Lead Response Time Tracker (Enhancement)

**Status**: IMPLEMENTED (Phase B)

**Purpose**: Measures the time between lead creation and first contact to help management monitor sales team performance and optimize conversion rates.

**How It Works**:
1. When a lead is created, `created_at` timestamp is stored
2. When the lead transitions from `acquisition` → `nurturing` (first contact), the system:
   - Computes `response_time_minutes = (now - created_at) / 60`
   - Stores this value on the lead document
3. The dashboard and CRM page display this metric with color coding:
   - Green (< 30 minutes): Fast response
   - Yellow (30-120 minutes): Acceptable response
   - Red (> 120 minutes): Slow response, needs improvement

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/leads/response-stats` | GET | Aggregated response time analytics |
| `/api/dashboard` | GET | Includes `avg_response_minutes`, `responded_leads` |

**Response Stats Data**:
```json
{
  "avg_response_minutes": 17.0,
  "min_response_minutes": 17,
  "max_response_minutes": 17,
  "count": 1,
  "waiting_for_contact": 4,
  "avg_wait_minutes": 16
}
```

**Frontend Display**:
- Dashboard: "Avg Response: 17m" badge in Lead Lifecycle funnel header
- CRM Page: 4-card mini dashboard (Avg Response Time, Contacted count, Waiting Contact count, Avg Wait Time)
- Lead row: `ResponseTimeBadge` component showing time with color coding
- Lead detail panel: Response time displayed alongside follow-up count

---

### 5.5 Project Management

**Status**: IMPLEMENTED

Manages property development projects as the top-level organizational unit.

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | List projects (with status/search filters) |
| `/api/projects` | POST | Create project |
| `/api/projects/{id}` | GET | Get single project |
| `/api/projects/{id}` | PUT | Update project |
| `/api/projects/{id}/generate-units` | POST | Batch generate units with block config |

**Project Fields**: id, name, organization_id, location, description, total_units, target_revenue, status (planning/active/completed/archived), units_sold, units_available, units_reserved, revenue_realized.

**Unit Generation**: Supports batch creation with configurable blocks (block name, count, type, base price, land area, floor area). Auto-generates coordinates for siteplan rendering.

**Seed Data**: 2 projects seeded (Grand Permata Residence — 100 units; Bukit Harmoni Village — 50 units).

---

### 5.6 Unit Management

**Status**: IMPLEMENTED

**Unit Lifecycle**:
```
available → reserved → booked → sold
                                  │
              ← canceled/expired ←┘ (reverts to available)
```

**Status Synchronization**: Units are synced across 3 modules:
- `status`: Synced from Deal lifecycle (available → reserved → booked → sold)
- `construction_status`: Synced from Construction module
- `payment_status`: Synced from Finance module (dp_paid, installment, overdue, paid_off)

**Endpoints**: CRUD for units with filters (project_id, status, block, search). Unit summary endpoint returns aggregated counts.

---

### 5.7 Siteplan & Visual Layout

**Status**: IMPLEMENTED

Interactive visual map of property units organized by blocks. Renders units as draggable/clickable nodes with color coding based on current view mode.

**View Modes** (4 views):
1. **Sales View**: Colors by unit availability (available=gray, reserved=amber, booked=orange, sold=green)
2. **Construction View**: Colors by construction progress (not_started=gray, in_progress=blue, completed=green, qc_hold=red)
3. **Finance View**: Colors by payment status (not_set=gray, dp_paid=blue, installment=amber, overdue=red, paid_off=green)
4. **Combined View**: Shows all status indicators simultaneously

**Custom Nodes**: Supports custom siteplan_nodes collection for manual layout, but defaults to auto-generated grid from unit coordinates.

---

### 5.8 Deal Management & Sales Pipeline

**Status**: IMPLEMENTED

**Deal Lifecycle**:
```
draft → reserved → booked → active → completed
                                        │
              canceled / expired / failed (all revert unit to available)
```

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/deals` | GET/POST | List/create deals |
| `/api/deals/{id}` | PUT | Update deal |
| `/api/deals/{id}/reserve` | POST | Reserve (draft → reserved) |
| `/api/deals/{id}/booking` | POST | Book (draft/reserved → booked) |

**Unit-Deal Sync**: When deal status changes, the corresponding unit status is automatically updated via `unit_status_map`. Canceled/expired/failed deals revert units to "available".

**Frontend (DealsPage.jsx)**: Deal cards with status badges, search/filter, create deal modal, status transition buttons.

**What's NOT Implemented**:
- SPR (Surat Pemesanan Rumah) document generation
- Booking fee tracking
- Deal expiration timer
- Down payment scheduling
- Commission calculation

---

### 5.9 Finance Module

**Status**: IMPLEMENTED

**Architecture**:
```
Deal → BillingSchedule → BillingItems[] → Payments
```

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/finance/billing` | GET/POST | List/create billing schedules |
| `/api/finance/payments` | GET/POST | List/record payments |
| `/api/finance/summary` | GET | Aggregated finance metrics |

**Payment Processing**: When a payment is recorded:
1. Finds the matching billing item by `billing_item_id`
2. Updates item's `paid_amount` and status (pending → partial → paid)
3. Recalculates billing schedule totals
4. Updates unit's `payment_status` (dp_paid → installment → overdue → paid_off)
5. Logs event to events collection

**Frontend (FinancePage.jsx)**: Summary KPIs (total billing, paid, outstanding, overdue), billing schedule table, payment recording modal.

**What's NOT Implemented**:
- Invoice/receipt PDF generation
- Payment reminder automation
- Penalty/late fee calculation
- Bank integration
- Accounting journal entries
- Tax calculation

---

### 5.10 Construction Tracking

**Status**: IMPLEMENTED

**Architecture**: Each unit gets a `construction_unit` document with a hierarchical structure:
```
ConstructionUnit
├── Phase 1: Pondasi (20% weight)
│   ├── Task: Galian tanah (30%)
│   ├── Task: Pemasangan besi (35%)
│   └── Task: Pengecoran (35%)
├── Phase 2: Struktur (25% weight)
│   ├── Task: Kolom & balok (40%)
│   ├── Task: Dinding bata (30%)
│   └── Task: Plat lantai (30%)
├── Phase 3: Atap (15% weight)
├── Phase 4: Finishing (25% weight)
└── Phase 5: MEP & Elektrikal (15% weight)
```

**Progress Calculation**: Weighted aggregation:
- Task completion → Phase progress (task_weight-based)
- Phase progress → Overall progress (phase_weight-based)

**QC System**: Quality control inspectors can submit pass/fail results per task. Failed tasks set phase to "qc_hold" status.

**Endpoints**: CRUD for construction units, progress updates, QC submission, summary.

**What's NOT Implemented**:
- Photo documentation upload
- Contractor management
- Material tracking
- Cost tracking per construction phase
- Gantt chart or timeline view
- Auto-notification on progress milestones

---

### 5.11 WhatsApp Integration

**Status**: MOCKED (Architecture Ready)

**Current State**: The system has full architecture for WhatsApp messaging but uses **simulated sending**. Messages are stored in `whatsapp_messages` collection and immediately marked as "sent" without actually calling any WhatsApp API.

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/whatsapp/messages` | GET | List sent messages |
| `/api/whatsapp/send` | POST | Send message (SIMULATED) |
| `/api/whatsapp/templates` | GET | List message templates |

**Frontend (WhatsAppPage.jsx)**: Message compose form, message history table, template management (view only).

**What's NOT Implemented**:
- Real WhatsApp Business API integration (requires Meta Business account)
- Incoming message tracking
- Read receipt tracking
- Template creation/editing UI
- Broadcast messaging
- Message scheduling
- Rich media messages (images, documents)
- Quick reply buttons

---

### 5.12 Notification System

**Status**: IMPLEMENTED

**Types**: info, success, warning, danger, follow_up

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notifications` | GET/POST | List/create notifications |
| `/api/notifications/{id}/read` | PUT | Mark as read |
| `/api/notifications/read-all` | PUT | Mark all as read |
| `/api/notifications/auto-rules` | GET/POST/PUT/DELETE | Auto follow-up rules CRUD |
| `/api/notifications/simulate-followup` | POST | Trigger follow-up simulation |

**Auto Follow-Up Engine**: Rules can be configured with trigger events (lead.created, appointment.no_show, payment.overdue), delay, message template with variable substitution ({name}, {source}, {project}), and channel (whatsapp or in_app). However, this is NOT automatically triggered — requires manual API call to `/simulate-followup`.

**What's NOT Implemented**:
- Real-time notifications (WebSocket/SSE)
- Push notifications
- Email notifications
- Auto-trigger on events (currently manual simulation only)
- Notification preferences per user

---

### 5.13 Appointment & Calendar

**Status**: IMPLEMENTED

**Appointment Statuses**: pending, confirmed, rescheduled, no_show, completed

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/appointments` | GET/POST | List/create appointments |
| `/api/appointments/{id}` | PUT | Update appointment |
| `/api/appointments/calendar` | GET | Calendar-formatted data |

**Frontend (AppointmentsPage.jsx)**: Calendar view, appointment creation form (linked to lead + project), status management.

**What's NOT Implemented**:
- Google Calendar integration
- Recurring appointments
- Survey validation form (photos, notes, checklist)
- Auto-create follow-up task on appointment completion
- No-show auto-recycle (7-day rule)

---

### 5.14 Dashboard System

**Status**: IMPLEMENTED (Phase A + B)

**Architecture**: Role-based auto-detection with 5 distinct views. Each view shows role-appropriate KPIs, task queue, and action cards.

**Role-View Mapping**:
| User Role | Dashboard View | Key Metrics |
|-----------|---------------|-------------|
| super_admin, owner, general_manager | Management | All KPIs (projects, units, leads, deals, revenue, collection) |
| sales_manager, marketing_admin | Marketing Admin | Stage-based lead counts, source distribution |
| sales, marketing_inhouse | Marketing Inhouse | My leads, my appointments, personal task queue |
| finance, accounting, collection | Finance | Total billing, paid, outstanding, overdue, collection rate |
| project_manager, site_engineer | Project | Projects, construction progress, unit counts |

**Data Sources** (single `/api/dashboard` endpoint):
- 15+ MongoDB queries aggregated into single response
- Lead stage counts (acquisition, nurturing, appointment, booking, recycle)
- User-specific metrics (my_leads, my_appointments, pending_assignments)
- Finance totals (billing, paid, outstanding)
- Construction progress (in_progress, completed)
- Recent events and lead sources
- Response time stats (avg_response_minutes, responded_leads)

**Task Queue**: Computed client-side from dashboard data. Generates contextual, actionable task cards:
- Management/Marketing Admin: Unassigned leads, leads not contacted, nurturing count, outstanding finance
- Marketing Inhouse: Leads needing contact, nurturing follow-ups, active appointments
- Finance: Outstanding amount, overdue billing
- All: Construction in progress, unread notifications, upcoming appointments

**What's NOT Implemented**:
- Dashboard mode is NOT locked to role (any user can technically switch via browser dev tools)
- No data-level access filtering at API (all data returned to all roles)
- No date-range filtering for dashboard metrics
- No comparison/trend data (this week vs last week)
- No target/goal tracking visualization

---

### 5.15 Development Report (Internal)

**Status**: IMPLEMENTED

Internal development tracking tool within the system itself. Tracks modules, features, status, priority, milestone, blockers.

**Endpoints**: Full CRUD for dev report items + meta information.

---

## 6. IMPLEMENTATION STATUS SUMMARY

### Legend
- DONE = Fully implemented and tested
- PARTIAL = Architecture exists, partially functional
- NOT STARTED = Planned but not yet built
- MOCKED = Simulated, not real integration

| Module | Feature | Status | Notes |
|--------|---------|--------|-------|
| **Auth** | Login/Register | DONE | JWT + bcrypt |
| **Auth** | Brute-force protection | DONE | 5 attempts, 15min lockout |
| **Auth** | Token refresh | DONE | httpOnly cookies |
| **Auth** | Route-level RBAC | NOT STARTED | All routes accessible to all |
| **Auth** | Password reset | PARTIAL | Endpoint exists, no email sending |
| **Lead** | Stage-based lifecycle | DONE | 5 stages, primary field |
| **Lead** | Stage transitions | DONE | Controlled + event logging |
| **Lead** | Lead CRUD | DONE | Create, read, update, filter |
| **Lead** | CSV Import | DONE | With deduplication |
| **Lead** | Lead pipeline/funnel | DONE | Stage-based visualization |
| **Lead** | Lead timeline | DONE | Cross-module event aggregation |
| **Lead** | Response time tracking | DONE | Computed on first contact |
| **Lead** | Nurturing outcome tags | NOT STARTED | Field exists, no UI |
| **Lead** | Lead scoring | NOT STARTED | quality_score field exists |
| **Lead** | Stage-specific dedicated pages | NOT STARTED | Uses CRM page + filter |
| **Assignment** | Manual assign | DONE | Bulk assign with reason |
| **Assignment** | Auto-assign (round-robin) | DONE | Round-robin across sales |
| **Assignment** | Accept/Reject | DONE | With reject reason |
| **Assignment** | Assignment history | DONE | Stored on lead document |
| **Assignment** | Reassignment request | NOT STARTED | From marketing inhouse |
| **Assignment** | Notification on assign | NOT STARTED | No notification sent |
| **Project** | CRUD | DONE | Full lifecycle |
| **Project** | Unit generation | DONE | Batch with block config |
| **Unit** | CRUD + Status sync | DONE | 3-way sync (deal/construction/finance) |
| **Siteplan** | Interactive view | DONE | 4 view modes |
| **Deal** | CRUD + Lifecycle | DONE | 7 status transitions |
| **Deal** | Unit-deal sync | DONE | Auto-update unit status |
| **Deal** | SPR/documents | NOT STARTED | Planned |
| **Finance** | Billing CRUD | DONE | Line-item tracking |
| **Finance** | Payment recording | DONE | Auto-updates billing + unit |
| **Finance** | Finance summary | DONE | Aggregated metrics |
| **Finance** | Invoice PDF | NOT STARTED | Planned |
| **Construction** | Phase/task tracking | DONE | Weighted progress |
| **Construction** | QC system | DONE | Pass/fail per task |
| **Construction** | Photo upload | NOT STARTED | Planned |
| **WhatsApp** | Message sending | MOCKED | Simulated, not real API |
| **WhatsApp** | Templates | PARTIAL | Collection exists, no seed/UI |
| **WhatsApp** | Incoming tracking | NOT STARTED | Planned |
| **WhatsApp** | Broadcast | NOT STARTED | For acquisition stage |
| **Notification** | In-app notifications | DONE | CRUD + read management |
| **Notification** | Auto follow-up rules | PARTIAL | Config exists, manual trigger |
| **Notification** | Real-time (WebSocket) | NOT STARTED | Planned |
| **Appointment** | CRUD + Calendar | DONE | With lead/project linking |
| **Appointment** | Survey validation | NOT STARTED | Forms, photos, notes |
| **Dashboard** | Role-based views | DONE | 5 views, auto-detect |
| **Dashboard** | Task queue | DONE | Computed, actionable |
| **Dashboard** | Response time metric | DONE | Avg + badge indicator |
| **Dashboard** | Date-range filtering | NOT STARTED | Planned |
| **Task Engine** | Persistent tasks | NOT STARTED | Phase C planned |
| **Task Engine** | SLA tracking | NOT STARTED | Phase D planned |

---

## 7. RISK & TECHNICAL DEBT

### 7.1 Architectural Risks

| Risk | Severity | Description |
|------|----------|-------------|
| Monolithic backend | MEDIUM | server.py is 2,656 lines. Adding more features will slow development. Plan modularization when domain logic stabilizes. |
| No RBAC enforcement | HIGH | Any authenticated user can access any API endpoint. Must be addressed before production deployment. |
| No referential integrity | MEDIUM | String UUID references with no FK enforcement. Orphaned records possible. |
| No input validation on PUT | LOW | PUT endpoints accept raw JSON without Pydantic model validation. |
| Status/Stage dual state | LOW (mitigated) | Stage is now primary. Status kept for backward compat. Migration ensures consistency. |

### 7.2 Technical Debt

| Debt Item | Impact | Recommendation |
|-----------|--------|---------------|
| Seed data runs every startup | LOW | Already guarded by `count_documents({})` check. Safe but creates test data on fresh DB. |
| Dashboard makes 15+ queries | MEDIUM | Consider caching or pre-computing dashboard aggregates. |
| No database migration system | MEDIUM | Using startup hooks. Need a proper migration framework for production. |
| No automated testing | MEDIUM | Tests run via external testing agent. Need integration into CI/CD. |
| No rate limiting | LOW | Only brute-force protection on login. Need API-wide rate limiting. |
| No file upload | LOW | No photo/document upload capability yet. Need cloud storage integration. |

### 7.3 Data Risks for Future Changes

| Change | Risk Level | Mitigation |
|--------|-----------|------------|
| Adding `tasks` collection | LOW | No conflict — clean slate. Must avoid duplication with computed tasks. |
| Enforcing RBAC | HIGH | Will break existing user experience. Must implement gradually with soft enforcement first. |
| Adding real WhatsApp API | LOW | Architecture ready. Swap simulated send with real API call. |
| Splitting server.py | MEDIUM | Must maintain same API contract. Test thoroughly after split. |

---

## 8. FUTURE DEVELOPMENT RECOMMENDATIONS

### Phase C — Task Engine (NEXT PRIORITY)

**Objective**: Introduce persistent task management without disrupting existing computed tasks.

**Recommended Approach**:
1. Create `tasks` collection with schema: id, title, type (follow_up, appointment, survey, payment), related_entity_type, related_entity_id, assigned_to, status (pending, in_progress, completed, cancelled), due_date, outcome, source_event, created_at
2. Start with two task types only: follow-up tasks and appointment tasks
3. Auto-generate tasks when:
   - Lead moves to nurturing → create "Follow-up" task assigned to lead owner
   - Appointment is created → create "Prepare Survey" task assigned to appointment owner
4. Keep computed dashboard tasks temporarily (merge both sources)
5. Add task detail page and task assignment UI

### Phase D — Enhancement

**Recommended Features** (in priority order):
1. **Lead Scoring Engine**: Compute `quality_score` based on source weight, engagement level, follow-up responsiveness, stage progression speed. The field already exists.
2. **WhatsApp Tracking Improvement**: Track outgoing messages per lead. Add "last_message_sent" and "messages_count" to lead. Detect response (manual validation).
3. **Broadcast System**: For acquisition stage — send template messages to multiple leads. Requires template management UI.
4. **SLA Logic**: Define acceptable response times per stage. Auto-escalate to marketing admin when SLA is breached.
5. **Survey Validation**: Add photo upload (Cloudinary/S3), form builder for survey checklist, notes field with rich text.

### Phase E — Production Readiness

**Recommended Before Production**:
1. **RBAC Enforcement**: Implement middleware that checks user role against endpoint requirements. Start soft (log violations), then hard (block access).
2. **Backend Modularization**: Split server.py into route modules (auth/, leads/, deals/, finance/, construction/, notifications/).
3. **Database Migrations**: Adopt a migration framework (e.g., custom scripts with version tracking).
4. **API Rate Limiting**: Add per-user and per-IP rate limiting.
5. **Error Monitoring**: Integrate Sentry or similar error tracking.
6. **Audit Trail UI**: The `events` collection has rich data. Build a searchable audit log viewer.
7. **File Upload**: Integrate Cloudinary or S3 for photo/document uploads (construction, survey, documents).

### Long-Term Vision Features

| Feature | Complexity | Business Value |
|---------|-----------|---------------|
| Customer Portal | HIGH | Allow buyers to track their unit status, payments, construction progress |
| Commission Engine | MEDIUM | Calculate and track sales commissions per deal |
| Document Workflow (SPK, PPJB, AJB) | HIGH | Legal document generation and signing workflow |
| Real WhatsApp Business API | MEDIUM | Requires Meta Business verification |
| Google Calendar Integration | LOW | Sync appointments with team calendars |
| PDF Report Generation | MEDIUM | Downloadable reports for management |
| Mobile App (React Native) | HIGH | Field sales need mobile access for surveys and follow-ups |
| Team Performance Leaderboard | LOW | Rank sales users by response time, conversion rate, lead progression |
| Multi-organization Multi-tenancy | HIGH | Support multiple property developers on single platform |
| AI-Powered Lead Prioritization | MEDIUM | Use response patterns and engagement data to predict conversion probability |

---

**End of Report**

*Generated by SIPRO Development System*
*Last Updated: April 5, 2026*
