# SIPRO - Property Development Operating System

## Original Problem Statement
Continue development on SIPRO. System is a unit-centric operational system for property development including lead management (CRM), sales pipeline, booking & transaction flow, finance integration, and operational workflow. Phase B: Assignment system, stage-based lifecycle, lead response time tracker.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Radix UI (shadcn/ui) + Lucide Icons
- **Backend**: FastAPI (Python) + Motor (async MongoDB driver)
- **Database**: MongoDB (19+ collections, UUID string IDs)
- **Auth**: JWT + bcrypt, httpOnly cookies + Bearer header

## User Personas
- **Super Admin / Management**: Full system oversight
- **Marketing Admin**: Lead distribution, pipeline monitoring
- **Marketing Inhouse / Sales**: Field sales, follow-ups, appointments
- **Finance**: Billing, payments, collections
- **Project Manager**: Construction tracking

## Core Requirements (Static)
1. Lead lifecycle management (stage-based: acquisition -> nurturing -> appointment -> booking -> recycle)
2. Role-based dashboards (management, marketing admin, marketing inhouse, finance, project)
3. Assignment system (manual, auto-assign round-robin, accept/reject)
4. Lead Response Time Tracker
5. Unit lifecycle (available -> reserved -> booked -> sold)
6. Deal management with billing/payment tracking
7. Construction progress tracking with QC

## What's Been Implemented

### Phase A - Foundation (2026-04-05)
1. Stage field consistency - non-destructive migration, all writes set stage explicitly
2. Role-based dashboards - auto-detect from user.role, 5 views
3. Sidebar restructured with Lead Lifecycle navigation
4. UI density improvements
5. CRM stage filtering via URL params

### Phase B - Core Flow + Enhancement (2026-04-05)
1. **Assignment System**
   - POST /api/leads/assign (manual assign with reason)
   - POST /api/leads/auto-assign (round-robin across sales users)
   - POST /api/leads/{id}/assignment/respond (accept/reject with reason)
   - assignment_history tracked on lead document
   - assignment_status field (pending, accepted, rejected)
   - Seed users: sales1, sales2, marketing_admin, finance

2. **Stage Transition System**
   - POST /api/leads/{id}/transition (controlled stage change)
   - Auto-computes response_time_minutes on acquisition -> nurturing
   - Backward-compatible status mapping on transition
   - Event logging for all transitions

3. **Lead Response Time Tracker (Enhancement)**
   - response_time_minutes computed on first contact (stage transition to nurturing)
   - GET /api/leads/response-stats (avg response, waiting count, avg wait)
   - Dashboard shows "Avg Response: Xm" badge in lifecycle funnel
   - CRM page has 4-card response time mini dashboard
   - ResponseTimeBadge component with color coding (green < 30m, yellow < 2h, red > 2h)

4. **Lead Timeline**
   - GET /api/leads/{id}/timeline (combined activities, events, WhatsApp, assignments)
   - Chronological view in lead detail panel
   - Type-based icons and colors

5. **CRM Page Overhaul**
   - Lead table with assignment column, response time column
   - Stage-specific action buttons (Contact, Jadwal, Book, Re-engage)
   - Accept/reject UI for pending assignments
   - Bulk selection with assign modal
   - Lead detail panel with stage transition buttons
   - Auto-assign and manual assign buttons

### Phase C - Task Engine (2026-05-19)
1. **Persistent `tasks` collection** with schema: id, title, description, type, status, priority, related_entity_type, related_entity_id, assigned_to, due_date, source_event, auto_generated, outcome, activity_history[], created_by, created_at, updated_at, completed_at
2. **Task Types**: contact, follow_up, appointment, recycle, custom
3. **API Endpoints**:
   - GET /api/tasks (filters: status, type, assigned_to, related_entity_id, mine, overdue)
   - GET /api/tasks/stats (open, overdue, today, completed, by_type)
   - GET /api/tasks/{id}
   - POST /api/tasks (manual create, role-permission enforced)
   - PUT /api/tasks/{id} (update fields with activity_history append)
   - POST /api/tasks/{id}/complete (outcome required)
   - DELETE /api/tasks/{id} (admin-only)
   - GET/PUT /api/tasks/permissions (configurable allowed_roles)
4. **Auto-task triggers (idempotent via source_event)**:
   - On `lead.created` → contact task, due +1h
   - On stage→nurturing → follow_up task, due +2d
   - On stage→appointment → appointment task, due +1d
   - On stage→booking → urgent follow_up, due +1d
   - On stage→recycle → recycle task, due +7d
   - On appointment.created → reminder task, due 1h before scheduled
5. **Frontend**:
   - Dedicated `/tasks` page with stats, filters (status/type/mine/overdue), table, complete/snooze/cancel actions
   - CreateTaskModal & PermissionsModal
   - `LeadTasksPanel` reusable component embedded in CRM lead detail panel
   - Sidebar nav under Sales section
   - Dashboard "Task Overdue / Task Aktif" indicators
   - Indonesian language strings
6. **Dashboard**: `my_tasks: { open, overdue, completed }` exposed per user
7. **Tested**: 19/19 backend pytest cases pass; full frontend Playwright verification — no bugs.

### Phase D - Production Hardening (2026-05-19)
1. **Cookie security**: `COOKIE_SECURE` env-driven flag — production sets SameSite=None + Secure=True; dev keeps Lax+False. Centralized via `_set_auth_cookies()`.
2. **Strict RBAC enforcement**: sales/marketing_inhouse roles only see resources where they are `assigned_to`. Endpoints scoped: `/api/leads` (list+get), `/api/tasks` list, `/api/appointments` list, `/api/deals` list. Single-lead GET returns 403 'Lead bukan milik Anda' if not owner.
3. **Booking expiry**: deal `reserved_until = now + BOOKING_HOLD_DAYS` (default 7). New endpoint `POST /api/deals/expire-reservations` (admin-only). Background sweeper `_reservation_sweeper()` runs every 15 min, releases expired deals → unit back to `available` + emits `deal.expired` event.
4. **Atomic unit booking**: `POST /api/deals` uses `find_one_and_update` to atomically transition unit `available→holding`. Eliminates double-booking race condition.
5. **Load-balanced auto-assign**: `POST /api/leads/auto-assign` picks lowest-load eligible user each iteration (replaces naive round-robin). Returns `loads` dict per user.
6. **Phone normalization E.164**: `_normalize_phone()` helper. Applied to lead create/import + deal customer_phone. `0812…`, `812…`, `62812…`, `+62812…` all normalize to `+62812…`. Cross-format dedup works.
7. **Idempotent response time**: new `first_contacted_at` field. `response_time_minutes` computed only ONCE on first acquisition→nurturing transition. Bouncing back and re-contacting does not reset metric.
8. **MongoDB indexes**: added `tasks.{status,assigned_to,type,due_date,related_entity_id,source_event}`, `deals.reserved_until`, `events.entity_id`, `appointments.{lead_id,assigned_to}`.
9. **Tested**: 19/19 Phase D pytest cases pass + Phase C 19/19 regression pass. Frontend smoke verified sales1 sees only own leads, admin sees all.

## Prioritized Backlog

### P0 (Phase F - Legal Documents & KPR)
- [ ] Document workflow: SPK, PPJB, AJB, BAST templates (Bahasa Indonesia formal)
- [ ] Server-side PDF generation (WeasyPrint or reportlab)
- [ ] E-sign placeholder (upload + timestamp)
- [ ] Financing module: bank, plafond, DP, tenor, BI checking, approval status
- [ ] Deal → financing application link
- [ ] Auto-generate billing schedule template (DP% + cicilan + serah terima)

### P1 (Phase G - Original Phase D Enhancements)
- [ ] SLA logic and escalation (Lead Response Time)
- [ ] WhatsApp incoming message detection
- [ ] Broadcast system for acquisition stage (limited to acquisition stage only)
- [ ] Lead scoring engine (quality_score computation)
- [ ] Survey validation (forms, photos, notes)

### P2 (Future)
- [ ] Real WhatsApp Business API integration
- [ ] Document workflow (SPK, PPJB, AJB)
- [ ] Commission engine
- [ ] Customer portal
- [ ] Strict RBAC enforcement
- [ ] Backend modularization (split server.py — currently 3026 lines)
- [ ] Task notifications via WhatsApp / email when overdue
- [ ] Recurring task scheduler

## Next Tasks
1. **Phase F**: Documents (PPJB/AJB) + KPR module + auto billing template
2. **Phase G**: SLA escalation, WhatsApp incoming, Broadcast, marketing ROI, lead scoring

## Reports
- Detailed Development Report: `/app/DEVELOPMENT_REPORT.md`
- Dev Report UI: `/dev-report` page in SIPRO
- Phase C test report: `/app/test_reports/iteration_6.json` (19/19 pytest pass)

