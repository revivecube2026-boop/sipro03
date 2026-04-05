# SIPRO - Property Development Operating System

## Original Problem Statement
Continue development on SIPRO from GitHub repo. System is a unit-centric operational system for property development including lead management (CRM), sales pipeline, booking & transaction flow, finance integration, and operational workflow.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Radix UI (shadcn/ui) + Lucide Icons
- **Backend**: FastAPI (Python) + Motor (async MongoDB driver)
- **Database**: MongoDB (19 collections, UUID string IDs)
- **Auth**: JWT + bcrypt, httpOnly cookies + Bearer header

## User Personas
- **Super Admin / Management**: Full system oversight
- **Marketing Admin**: Lead distribution, pipeline monitoring
- **Marketing Inhouse**: Field sales, follow-ups, appointments
- **Finance**: Billing, payments, collections
- **Project Manager**: Construction tracking

## Core Requirements (Static)
1. Lead lifecycle management (stage-based: acquisition → nurturing → appointment → booking → recycle)
2. Role-based dashboards (management, marketing admin, marketing inhouse, finance, project)
3. Unit lifecycle (available → reserved → booked → sold)
4. Deal management with billing/payment tracking
5. Construction progress tracking with QC
6. WhatsApp integration (currently mocked)
7. CSV lead import with deduplication
8. Event logging system

## What's Been Implemented

### Phase A — Foundation (2026-04-05)
1. **Stage Field Consistency**
   - Non-destructive migration: populated `stage` for all 20 existing leads based on status-to-stage mapping
   - All lead create/update/import endpoints now set `stage` explicitly
   - Stage is now the PRIMARY lifecycle field (status kept for backward compatibility)
   - Added DB indexes for `stage` and `assigned_to`
   - Added mismatch logging on lead updates

2. **Role-Based Dashboards**
   - Auto-detects dashboard mode from user role (no manual switching)
   - 5 distinct views: Management, Marketing Admin, Marketing Inhouse, Finance, Project
   - Each view shows role-appropriate KPIs, task queue, and action cards
   - Dashboard API returns: lead_stages, my_leads, unassigned_leads, my_appointments
   - Actionable cards linking to filtered data

3. **Sidebar Navigation Restructure**
   - Added "Lead Lifecycle" section: Overview, Akuisisi, Nurturing, Appointment, Booking, Recycle
   - Organized sections: Property, Sales, Operations, Comms, System
   - Narrower sidebar (200px) for more content area

4. **UI Density Improvements**
   - Reduced padding/margins across cards, tables, modals, sidebar items
   - Tighter font sizes and spacing
   - Maintained glassmorphism aesthetic
   - Compact task cards and KPI numbers

5. **CRM Stage Filtering**
   - URL search params sync with filters (sidebar navigation works)
   - Stage-filtered views show correct lead counts

## Prioritized Backlog

### P0 (Phase B — Core Flow)
- [ ] Upgrade assignment system (auto-assign round-robin, manual assign, accept/reject with reason)
- [ ] Implement full lead lifecycle UI (stage-based pages with stage-specific logic, actions, filters)
- [ ] Controlled stage transitions with validation

### P1 (Phase C — Task Engine)
- [ ] Persistent `tasks` collection (follow-up tasks, appointment tasks)
- [ ] Lead timeline/activity log (separate from tasks)
- [ ] Task assignment and outcome tracking

### P2 (Phase D — Enhancement)
- [ ] SLA logic and escalation
- [ ] WhatsApp incoming message detection and tracking
- [ ] Broadcast system for acquisition stage
- [ ] Lead scoring engine (quality_score computation)

### Future / P3
- [ ] Real WhatsApp Business API integration
- [ ] Document workflow (SPK, PPJB, AJB)
- [ ] Commission engine
- [ ] Customer portal
- [ ] Strict RBAC enforcement
- [ ] Backend modularization (split server.py)

## Next Tasks
1. Phase B: Assignment system upgrade (round-robin, accept/reject)
2. Phase B: Stage-based separate pages with full logic per stage
3. Phase C: Persistent task collection for follow-up and appointment tasks
