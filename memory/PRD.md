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

## Prioritized Backlog

### P0 (Phase C - Task Engine)
- [ ] Persistent `tasks` collection (follow-up tasks, appointment tasks)
- [ ] Lead timeline/activity log improvements
- [ ] Task assignment and outcome tracking

### P1 (Phase D - Enhancement)
- [ ] SLA logic and escalation
- [ ] WhatsApp incoming message detection
- [ ] Broadcast system for acquisition stage
- [ ] Lead scoring engine (quality_score computation)
- [ ] Survey validation (forms, photos, notes)

### P2 (Future)
- [ ] Real WhatsApp Business API integration
- [ ] Document workflow (SPK, PPJB, AJB)
- [ ] Commission engine
- [ ] Customer portal
- [ ] Strict RBAC enforcement
- [ ] Backend modularization (split server.py)

## Next Tasks
1. Phase C: Persistent task collection for follow-up and appointment tasks
2. Phase C: Task assignment and SLA tracking
3. Phase D: WhatsApp tracking improvements

## Reports
- Detailed Development Report: `/app/DEVELOPMENT_REPORT.md`
- Dev Report UI: `/dev-report` page in SIPRO (34 items, 61% complete)

