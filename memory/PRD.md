# SIPRO - Property Development Operating System
## Development Report & Technical Documentation

**Last Updated:** April 2026 | **Version:** 3.0 | **Status:** Active Development

---

## 1. IMPLEMENTED (Completed & Working)

### 1.1 Authentication & Authorization
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Login/Register with email+password -> JWT token -> httpOnly cookies + Bearer header
- **Features:** bcrypt password hashing, brute force protection (5 attempts/15min lockout), admin seeding on startup, refresh token mechanism
- **Data:** `users` collection (email, password_hash, name, role, status)
- **Roles:** super_admin, owner, general_manager, sales_manager, sales, finance, project_manager, site_engineer, legal_admin
- **Endpoints:** POST /api/auth/login, POST /api/auth/register, POST /api/auth/logout, GET /api/auth/me, POST /api/auth/refresh
- **Integration:** All routes protected via `get_current_user()` middleware

### 1.2 Organization Management
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Create organization -> assign users -> scope data per org
- **Data:** `organizations` collection (id, name, type, address, phone, email, status)
- **Endpoints:** GET /api/organizations, POST /api/organizations
- **Note:** Currently single-org, multi-tenant prepared via org_id field

### 1.3 User Management
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** List users -> view roles -> admin can manage
- **Data:** `users` collection (linked to auth)
- **Endpoints:** GET /api/users
- **Note:** Role assignment works, field-level permission enforcement not yet implemented

### 1.4 Project Management
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Create project -> define structure -> generate units -> track status
- **Data:** `projects` collection (id, name, location, description, total_units, target_revenue, status, units_sold/available/reserved, revenue_realized)
- **Endpoints:** GET /api/projects, POST /api/projects, GET /api/projects/{id}, PUT /api/projects/{id}, POST /api/projects/{id}/generate-units
- **Features:** Search by name, status filter, unit auto-generation from block config
- **Sample Data:** 3 projects (Grand Permata Residence, Bukit Harmoni Village, Riverside Park City)

### 1.5 Unit Management
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Units belong to projects -> status lifecycle (available->reserved->booked->sold) -> linked to deals, construction, finance
- **Data:** `units` collection (id, project_id, block, number, label, unit_type, floor_area, land_area, price, status, deal_status, construction_status, payment_status, coordinates)
- **Endpoints:** GET /api/units, GET /api/units/{id}, PUT /api/units/{id}, GET /api/units/{id}/summary
- **Features:** Filter by project, status, block; search by label; pagination; unit summary across modules
- **Sample Data:** 150 units across 7 blocks (A-G)

### 1.6 Interactive Siteplan
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Select project -> choose view mode -> see color-coded units -> hover for tooltip -> click for detail panel
- **Data:** Reads from `units` collection, optional `siteplan_nodes` for custom layouts
- **Endpoints:** GET /api/siteplan/{project_id}?view_mode=sales|construction|finance|management
- **Features:** 4 view modes with different color mappings, grouped by block, configurable color legends, detail panel with unit info
- **View Modes:**
  - Sales: available(gray), reserved(yellow), booked(orange), sold(green), canceled(red)
  - Construction: not_started(gray), in_progress(blue), qc_hold(orange), completed(green), delayed(red)
  - Finance: unpaid(gray), dp_paid(blue), installment(yellow), overdue(red), paid_off(green)
  - Management: same as sales

### 1.7 CRM / Lead Management
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Lead acquisition -> follow-up -> prospect -> appointment -> booking
- **State Machine:** new -> contacted -> prospect -> no_response -> lost (with re-engagement)
- **Data:** `leads` collection (id, name, phone, email, source, campaign, ad_set, ad_name, notes, project_id, assigned_to, status, quality_score)
- **Data:** `lead_activities` collection (id, lead_id, type, description, outcome)
- **Endpoints:** GET /api/leads, POST /api/leads, PUT /api/leads/{id}, GET /api/leads/{id}, POST /api/leads/{id}/activities
- **Features:** Search by name/phone/email, filter by status/source/project/assignee, lead detail panel with activities, duplicate checking, quality scoring
- **Sources:** meta_ads, google_ads, tiktok_ads, referral, walk_in, website, event, manual, csv_import
- **Sample Data:** 20+ leads from various sources

### 1.8 Lead Import from Ads
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Upload CSV or manual entry -> select source/campaign -> validate -> deduplicate -> import to CRM pipeline
- **Data:** Imported into `leads` collection with import_batch tracking
- **Endpoints:** POST /api/leads/import
- **Features:** CSV parsing with auto-header detection, manual row entry, download template, platform selection (Meta/Google/TikTok Ads), duplicate detection by phone/email, import result summary (imported/duplicates/errors)
- **Note:** API integration with actual ad platforms not yet connected (CSV/manual import only)

### 1.9 Deal & Sales Management
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Create deal -> reserve unit -> booking -> active -> completed (with cancel/expire/fail paths)
- **State Machine:** draft -> reserved -> booking_pending -> booked -> active -> completed | canceled | expired | failed
- **Data:** `deals` collection (id, lead_id, customer_name/email/phone, unit_id, unit_label, project_id, price, payment_method, notes, status)
- **Endpoints:** GET /api/deals, POST /api/deals, PUT /api/deals/{id}, POST /api/deals/{id}/reserve, POST /api/deals/{id}/booking
- **Features:** Status pipeline with filter chips, search by customer, unit locking on reserve/book, unit status sync
- **Integration:** Creates events on status change, syncs unit.status and unit.deal_status
- **Sample Data:** 8 deals across different statuses

### 1.10 Finance Module
- **Status:** COMPLETED | **Phase:** 2
- **Flow:** Deal created -> billing schedule generated -> payments recorded -> collection tracked -> overdue detected
- **Data:** `billing_schedules` collection (id, deal_id, unit_id, project_id, customer_name, items[{id,description,amount,due_date,status,paid_amount}], total_amount, paid_amount, outstanding)
- **Data:** `payments` collection (id, deal_id, billing_item_id, amount, payment_date, payment_method, reference, status)
- **Endpoints:** GET /api/finance/billing, POST /api/finance/billing, GET /api/finance/payments, POST /api/finance/payments, GET /api/finance/summary
- **Features:** Billing schedule with itemized breakdown, payment recording linked to billing items, collection rate progress bar, overdue detection, payment status sync to units
- **Payment Statuses:** unpaid -> dp_paid -> installment -> overdue -> paid_off
- **Sample Data:** 4 billing schedules, 6 payment records

### 1.11 Construction Module
- **Status:** COMPLETED | **Phase:** 2
- **Flow:** Create construction record for unit -> default phases generated -> update task status -> QC -> progress calculated
- **Data:** `construction_units` collection (id, unit_id, project_id, unit_label, phases[{id,name,weight,status,progress,tasks[{id,name,weight,status}]}], overall_progress, overall_status, qc_results[], logs[])
- **Endpoints:** GET /api/construction/units, POST /api/construction/units, GET /api/construction/units/{id}, PUT /api/construction/units/{id}/progress, POST /api/construction/units/{id}/qc, GET /api/construction/summary
- **Default Phases:** Pondasi(20%), Struktur(25%), Atap(15%), Finishing(25%), MEP(15%)
- **Features:** Expandable phase/task view, progress auto-calculation from task completion, QC pass/fail, construction status sync to units, action buttons (Mulai/Selesai/Rework)
- **Sample Data:** 6 construction units with varying progress (0%-85%)

### 1.12 Notification Center
- **Status:** COMPLETED | **Phase:** 2
- **Flow:** System events generate notifications -> displayed in inbox -> mark read/unread
- **Data:** `notifications` collection (id, title, message, type, target_user, related_entity_type/id, read, created_at)
- **Endpoints:** GET /api/notifications, POST /api/notifications, PUT /api/notifications/{id}/read, PUT /api/notifications/read-all
- **Types:** info, success, warning, danger, follow_up
- **Sample Data:** 5+ notifications (lead alerts, payment confirmations, survey reminders, construction updates, overdue alerts)

### 1.13 Auto Follow-Up Engine
- **Status:** COMPLETED | **Phase:** 2 (Enhancement)
- **Flow:** Configure rules -> events trigger rules -> auto-send WhatsApp + in-app notification
- **Data:** `auto_followup_rules` collection (id, name, trigger_event, delay_minutes, message_template, channel, is_active, executions)
- **Endpoints:** GET /api/notifications/auto-rules, POST /api/notifications/auto-rules, PUT /api/notifications/auto-rules/{id}, DELETE /api/notifications/auto-rules/{id}, POST /api/notifications/simulate-followup
- **Trigger Events:** lead.created, appointment.no_show, payment.overdue, deal.reserved, deal.booked
- **Channels:** whatsapp, in_app
- **Template Variables:** {name}, {source}, {project}
- **Note:** WhatsApp sending is MOCKED (messages logged in DB, not sent via actual WA API). Simulation endpoint available for testing.
- **Sample Data:** 3 rules (Auto WA for new leads, 24hr reminder, internal notification)

### 1.14 Appointment Calendar
- **Status:** COMPLETED | **Phase:** 2
- **Flow:** Create appointment for lead -> calendar view -> confirm/complete/no-show -> enriched with lead data
- **Data:** `appointments` collection (id, lead_id, project_id, scheduled_at, location, notes, assigned_to, status)
- **State Machine:** pending -> confirmed -> rescheduled -> completed | no_show | canceled
- **Endpoints:** GET /api/appointments, POST /api/appointments, PUT /api/appointments/{id}, GET /api/appointments/calendar
- **Features:** Monthly calendar grid, appointment markers by status, upcoming sidebar, status management buttons, lead enrichment (name, phone)
- **Sample Data:** 4 appointments

### 1.15 WhatsApp Integration (MOCKED)
- **Status:** COMPLETED (Architecture) | MOCKED (No real API) | **Phase:** 1
- **Flow:** Send message -> logged in DB -> marked as sent (simulated)
- **Data:** `whatsapp_messages` collection (id, recipient_phone, recipient_name, message, message_type, status, sent_by, auto_rule_id)
- **Data:** `whatsapp_templates` collection (id, name, message, type)
- **Endpoints:** GET /api/whatsapp/messages, POST /api/whatsapp/send, GET /api/whatsapp/templates
- **Message Types:** notification, follow_up, reminder, payment_reminder, auto_follow_up
- **Note:** Ready for WhatsApp Business API integration. Messages are stored and displayed but not actually sent.

### 1.16 Development Report Module
- **Status:** COMPLETED | **Phase:** 1
- **Flow:** Add/edit items by module -> track status/priority/milestone/blockers -> overall progress calculation
- **Data:** `dev_report_items` collection (id, module, feature, status, priority, notes, milestone, blockers)
- **Endpoints:** GET /api/dev-report, POST /api/dev-report/items, PUT /api/dev-report/items/{id}, DELETE /api/dev-report/items/{id}, PUT /api/dev-report/meta

### 1.17 Dashboard (Task-Centric)
- **Status:** COMPLETED | **Phase:** 3
- **Flow:** Auto-generate tasks from business data -> display in Task Queue -> quick navigation to relevant pages
- **Features:** 6 KPI cards, Task Queue (auto-generated from leads/finance/notifications/construction/appointments), Unit Summary with progress bars, Lead Sources chart, Recent Activities, Finance/Construction/Notifications overview cards
- **Task Generation:** new leads -> follow-up task, outstanding finance -> collection task, unread notifications, construction in progress, upcoming appointments
- **Endpoint:** GET /api/dashboard (aggregates all module data)

### 1.18 Language Toggle
- **Status:** COMPLETED | **Phase:** 1
- **Languages:** Indonesian (default), English
- **Coverage:** All navigation labels, form labels, status names, page titles, action buttons

### 1.19 Event System
- **Status:** COMPLETED | **Phase:** 1
- **Data:** `events` collection (id, type, entity_type, entity_id, data, created_at)
- **Events:** lead.created, lead.status_changed, leads.imported, deal.created, deal.{status}, payment.completed, construction.progress_updated, qc.passed, qc.failed

---

## 2. IN PROGRESS / PARTIALLY IMPLEMENTED

### 2.1 Role-Based Dashboards
- **Current Stage:** Dashboard shows task-centric view for all roles. Role-specific filtering partially implemented (assigned_to field on leads/appointments).
- **Next Step:** Create dedicated dashboard views per role (Sales, Finance, PM, Site Engineer)
- **Blocker:** Needs role-specific task generation logic

### 2.2 Real WhatsApp Business API Integration
- **Current Stage:** Architecture ready, message templates exist, MOCKED sending
- **Next Step:** Connect actual WhatsApp Business API (Meta Cloud API)
- **Dependency:** Requires WhatsApp Business API key from user
- **Blocker:** API key needed

---

## 3. NOT IMPLEMENTED (Planned)

### 3.1 Commission Engine
- **Priority:** P0 | **Target:** Phase 3
- **Description:** Multi-party fee calculation for agents, referrals, managers
- **Reason Not Started:** Depends on complete finance module

### 3.2 Document Workflow
- **Priority:** P0 | **Target:** Phase 5
- **Description:** Template-based document lifecycle (SPK, PPJB, AJB, etc.)
- **Reason Not Started:** Complex template system needed

### 3.3 Accounting Module
- **Priority:** P1 | **Target:** Phase 6
- **Description:** Chart of accounts, journal entries, ledger, financial statements

### 3.4 Customer Portal
- **Priority:** P1 | **Target:** Phase 5
- **Description:** Buyer-facing portal with timeline, payment status, progress

### 3.5 Workflow Automation Engine
- **Priority:** P2 | **Target:** Phase 6
- **Description:** Configurable rule engine for business process automation

### 3.6 Advanced Reporting
- **Priority:** P2 | **Target:** Phase 6
- **Description:** KPI dashboards, forecasts, margin analysis, executive reports

### 3.7 After Sales Module
- **Priority:** P3 | **Target:** Phase 5
- **Description:** BAST, defect tracking, warranty, retention management

### 3.8 Transfer Ownership (Over Alih)
- **Priority:** P3 | **Target:** Future
- **Description:** Unit ownership transfer between buyers with history preservation

### 3.9 Real-time Notifications (WebSocket)
- **Priority:** P2 | **Target:** Future
- **Description:** Push notifications via WebSocket for instant updates

### 3.10 PDF Report Generation
- **Priority:** P2 | **Target:** Future
- **Description:** Generate PDF reports for billing, construction progress, deals

---

## 4. CHANGELOG / NOTES

### v3.0 - April 2026
- Complete UI/UX overhaul with modern glassmorphism design
- Gradient background (light blue-gray)
- Stronger translucent cards (55-72% opacity, 20px blur, saturate 180%)
- Compact sidebar (220px width)
- Task-centric dashboard with auto-generated Task Queue
- Denser layout across all pages

### v2.0 - April 2026
- Finance Module: billing schedules, payment recording, collection rate
- Construction Module: phase/task progress, QC management
- Notification Center: inbox, mark read/unread
- Auto Follow-Up Engine: configurable rules, MOCKED WhatsApp sending
- Appointment Calendar: monthly grid, scheduling, status management
- Updated dashboard with finance/construction/notification cards
- Sample data for all new modules

### v1.0 - April 2026
- Initial MVP release
- Auth (JWT + bcrypt + RBAC)
- Organization, Project, Unit management
- Interactive Siteplan (4 view modes)
- CRM Lead Pipeline with state machine
- Lead Import (CSV + Ads platform structure)
- Deal Management with lifecycle
- WhatsApp hooks (MOCKED)
- Development Report module
- Language toggle (ID/EN)
- Event logging system

---

## 5. ARCHITECTURE OVERVIEW

### Tech Stack
- **Frontend:** React 19 + Tailwind CSS + Radix UI + Lucide Icons
- **Backend:** FastAPI (Python) + Motor (async MongoDB driver)
- **Database:** MongoDB (sipro_db)
- **Auth:** JWT (PyJWT) + bcrypt

### Module Integration Map
```
Lead Acquisition (CRM)
  ├── Lead Import (CSV/Ads)
  ├── Follow-Up Tasks → WhatsApp (MOCKED)
  ├── Auto Follow-Up Rules → Notifications
  └── Appointments → Calendar
       └── Survey Outcome → Deal Creation

Deal Management
  ├── Unit Locking (reserve/book)
  ├── Billing Schedule → Finance
  │    ├── Payment Recording
  │    └── Collection/Overdue
  └── Events → Notifications

Project Management
  ├── Unit Generation
  ├── Interactive Siteplan (4 views)
  └── Construction Tracking
       ├── Phase/Task Progress
       └── QC Management

Dashboard (Task-Centric)
  ├── Aggregates all modules
  ├── Auto-generates task queue
  └── Clickable navigation to all pages
```

### Database Collections
- `users`, `organizations`, `projects`, `units`
- `leads`, `lead_activities`, `appointments`
- `deals`, `billing_schedules`, `payments`
- `construction_units`
- `whatsapp_messages`, `whatsapp_templates`
- `notifications`, `auto_followup_rules`
- `dev_report_items`, `dev_report_meta`
- `events`, `login_attempts`

### Credentials
- **Super Admin:** admin@sipro.com / admin123
