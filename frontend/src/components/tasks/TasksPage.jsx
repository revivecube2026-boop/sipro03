import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../lib/api';
import {
  CheckSquare, Clock, AlertTriangle, Plus, Filter, RefreshCw,
  Phone, Calendar, RotateCcw, Target, MoreHorizontal, X, Settings,
  CheckCircle2, Pause, XCircle
} from 'lucide-react';

const TYPE_CONFIG = {
  contact: { label: 'Kontak', color: '#2563eb', icon: Phone },
  follow_up: { label: 'Follow-up', color: '#f59e0b', icon: Target },
  appointment: { label: 'Appointment', color: '#7c3aed', icon: Calendar },
  recycle: { label: 'Recycle', color: '#8896ab', icon: RotateCcw },
  custom: { label: 'Lainnya', color: '#10b981', icon: CheckSquare },
};

const PRIORITY_CONFIG = {
  urgent: { label: 'Urgent', color: '#ef4444' },
  high: { label: 'High', color: '#f59e0b' },
  medium: { label: 'Medium', color: '#2563eb' },
  low: { label: 'Low', color: '#8896ab' },
};

const STATUS_CONFIG = {
  open: { label: 'Terbuka', color: '#2563eb' },
  in_progress: { label: 'Berjalan', color: '#f59e0b' },
  snoozed: { label: 'Ditunda', color: '#8896ab' },
  completed: { label: 'Selesai', color: '#10b981' },
  canceled: { label: 'Dibatalkan', color: '#94a3b8' },
};

function TaskTypeBadge({ type }) {
  const c = TYPE_CONFIG[type] || TYPE_CONFIG.custom;
  return (
    <span data-testid={`task-type-${type}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 9, fontWeight: 700, color: c.color, background: `${c.color}15`, padding: '2px 6px', borderRadius: 6 }}>
      <c.icon size={10} />{c.label}
    </span>
  );
}

function PriorityDot({ priority }) {
  const p = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.medium;
  return <span title={p.label} style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: p.color }} />;
}

function StatusPill({ status }) {
  const s = STATUS_CONFIG[status] || STATUS_CONFIG.open;
  return <span style={{ fontSize: 8, fontWeight: 800, color: s.color, background: `${s.color}15`, padding: '1px 6px', borderRadius: 4, textTransform: 'uppercase' }}>{s.label}</span>;
}

function isOverdue(task) {
  if (!task.due_date) return false;
  if (!['open', 'in_progress', 'snoozed'].includes(task.status)) return false;
  return new Date(task.due_date).getTime() < Date.now();
}

function formatDue(due) {
  if (!due) return '-';
  const d = new Date(due);
  const now = new Date();
  const diffH = Math.round((d - now) / 36e5);
  const txt = d.toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  if (diffH < 0) return `${txt} (telat ${Math.abs(diffH)}j)`;
  if (diffH < 24) return `${txt} (${diffH}j lagi)`;
  return txt;
}

export default function TasksPage() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: 'open,in_progress,snoozed', type: '', mine: false, overdue: false });
  const [showForm, setShowForm] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [completing, setCompleting] = useState(null);
  const [completionOutcome, setCompletionOutcome] = useState('');
  const [permissions, setPermissions] = useState(null);
  const [users, setUsers] = useState([]);

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.type) params.type = filters.type;
      if (filters.mine) params.mine = true;
      if (filters.overdue) params.overdue = true;
      params.limit = 200;
      const { data } = await api.get('/tasks', { params });
      setTasks(data.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filters]);

  const loadStats = useCallback(async () => {
    try {
      const { data } = await api.get('/tasks/stats', { params: { mine: filters.mine } });
      setStats(data.data);
    } catch (e) { console.error(e); }
  }, [filters.mine]);

  const loadPermissions = async () => {
    try {
      const [{ data: perm }, { data: u }] = await Promise.all([
        api.get('/tasks/permissions'),
        api.get('/users'),
      ]);
      setPermissions(perm.data);
      setUsers(u.data || []);
    } catch {}
  };

  useEffect(() => { loadTasks(); loadStats(); }, [loadTasks, loadStats]);
  useEffect(() => { loadPermissions(); }, []);

  const completeTask = async (taskId, outcome) => {
    try {
      await api.post(`/tasks/${taskId}/complete`, { outcome });
      setCompleting(null); setCompletionOutcome('');
      loadTasks(); loadStats();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const updateTaskStatus = async (taskId, status) => {
    try {
      await api.put(`/tasks/${taskId}`, { status });
      loadTasks(); loadStats();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="animate-fade-in" data-testid="tasks-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>Tasks</h1>
          <p style={{ color: '#8896ab', fontSize: 10, marginTop: 1 }}>Tugas operasional & follow-up lead</p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn-pill btn-pill-secondary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={() => { loadTasks(); loadStats(); }} data-testid="tasks-refresh-btn">
            <RefreshCw size={12} style={{ display: 'inline', marginRight: 3 }} />Refresh
          </button>
          {(user?.role === 'super_admin' || user?.role === 'marketing_admin') && (
            <button className="btn-pill btn-pill-secondary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={() => setShowSettings(true)} data-testid="tasks-settings-btn">
              <Settings size={12} style={{ display: 'inline', marginRight: 3 }} />Permissions
            </button>
          )}
          <button className="btn-pill btn-pill-primary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={() => setShowForm(true)} data-testid="tasks-add-btn">
            <Plus size={12} style={{ display: 'inline', marginRight: 3 }} />Tambah Task
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 8 }}>
          <div className="mini-dashboard-card" style={{ padding: '6px 10px' }} data-testid="stats-open">
            <CheckSquare size={11} color="#2563eb" />
            <div className="kpi-number" style={{ fontSize: 16 }}>{stats.total_open}</div>
            <div className="kpi-label" style={{ fontSize: 8 }}>Open Tasks</div>
          </div>
          <div className="mini-dashboard-card" style={{ padding: '6px 10px' }} data-testid="stats-overdue">
            <AlertTriangle size={11} color="#ef4444" />
            <div className="kpi-number" style={{ fontSize: 16, color: stats.overdue > 0 ? '#ef4444' : undefined }}>{stats.overdue}</div>
            <div className="kpi-label" style={{ fontSize: 8 }}>Overdue</div>
          </div>
          <div className="mini-dashboard-card" style={{ padding: '6px 10px' }} data-testid="stats-today">
            <Clock size={11} color="#f59e0b" />
            <div className="kpi-number" style={{ fontSize: 16 }}>{stats.today}</div>
            <div className="kpi-label" style={{ fontSize: 8 }}>Hari Ini</div>
          </div>
          <div className="mini-dashboard-card" style={{ padding: '6px 10px' }} data-testid="stats-completed">
            <CheckCircle2 size={11} color="#10b981" />
            <div className="kpi-number" style={{ fontSize: 16 }}>{stats.completed}</div>
            <div className="kpi-label" style={{ fontSize: 8 }}>Selesai</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="glass-card" style={{ padding: 8, marginBottom: 8, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <Filter size={12} color="#8896ab" />
        <select value={filters.status} onChange={e => setFilters({ ...filters, status: e.target.value })} data-testid="filter-status"
          style={{ fontSize: 10, padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(0,0,0,0.08)' }}>
          <option value="open,in_progress,snoozed">Aktif</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="snoozed">Snoozed</option>
          <option value="completed">Completed</option>
          <option value="canceled">Canceled</option>
          <option value="">Semua Status</option>
        </select>
        <select value={filters.type} onChange={e => setFilters({ ...filters, type: e.target.value })} data-testid="filter-type"
          style={{ fontSize: 10, padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(0,0,0,0.08)' }}>
          <option value="">Semua Tipe</option>
          {Object.entries(TYPE_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <label style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }} data-testid="filter-mine-label">
          <input type="checkbox" checked={filters.mine} onChange={e => setFilters({ ...filters, mine: e.target.checked })} data-testid="filter-mine" /> Task saya
        </label>
        <label style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }} data-testid="filter-overdue-label">
          <input type="checkbox" checked={filters.overdue} onChange={e => setFilters({ ...filters, overdue: e.target.checked })} data-testid="filter-overdue" /> Hanya overdue
        </label>
      </div>

      {/* Table */}
      <div className="glass-card" style={{ padding: 0, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }} data-testid="tasks-table">
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.02)', textAlign: 'left' }}>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>P</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Tipe</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Task</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Lead/Entity</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Assigned</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Due</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Status</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab', textAlign: 'right' }}>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map(t => (
              <tr key={t.id} style={{ borderTop: '1px solid rgba(0,0,0,0.04)', background: isOverdue(t) ? 'rgba(239,68,68,0.04)' : undefined }} data-testid={`task-row-${t.id}`}>
                <td style={{ padding: '5px 10px' }}><PriorityDot priority={t.priority} /></td>
                <td style={{ padding: '5px 10px' }}><TaskTypeBadge type={t.type} /></td>
                <td style={{ padding: '5px 10px', maxWidth: 280 }}>
                  <div style={{ fontWeight: 700, fontSize: 11 }}>{t.title}</div>
                  {t.description && <div style={{ fontSize: 9, color: '#8896ab', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.description}</div>}
                </td>
                <td style={{ padding: '5px 10px', fontSize: 10 }}>
                  {t.related_lead_name ? (
                    <div>
                      <div style={{ fontWeight: 600 }}>{t.related_lead_name}</div>
                      <div style={{ fontSize: 8, color: '#8896ab' }}>{t.related_lead_stage}</div>
                    </div>
                  ) : t.related_entity_type ? <span style={{ fontSize: 9, color: '#8896ab' }}>{t.related_entity_type}</span> : '-'}
                </td>
                <td style={{ padding: '5px 10px', fontSize: 10, color: '#556680' }}>{t.assigned_to ? t.assigned_to.split('@')[0] : '-'}</td>
                <td style={{ padding: '5px 10px', fontSize: 9, color: isOverdue(t) ? '#ef4444' : '#556680', fontWeight: isOverdue(t) ? 700 : 500 }}>{formatDue(t.due_date)}</td>
                <td style={{ padding: '5px 10px' }}><StatusPill status={t.status} /></td>
                <td style={{ padding: '5px 10px', textAlign: 'right' }}>
                  <div style={{ display: 'inline-flex', gap: 4 }}>
                    {['open', 'in_progress', 'snoozed'].includes(t.status) && (
                      <>
                        <button onClick={() => setCompleting(t)} title="Tandai selesai" data-testid={`complete-${t.id}`}
                          style={{ background: 'rgba(16,185,129,0.12)', color: '#10b981', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', fontSize: 10 }}>
                          <CheckCircle2 size={11} />
                        </button>
                        {t.status !== 'snoozed' && (
                          <button onClick={() => updateTaskStatus(t.id, 'snoozed')} title="Tunda" data-testid={`snooze-${t.id}`}
                            style={{ background: 'rgba(245,158,11,0.12)', color: '#f59e0b', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', fontSize: 10 }}>
                            <Pause size={11} />
                          </button>
                        )}
                        <button onClick={() => updateTaskStatus(t.id, 'canceled')} title="Batalkan" data-testid={`cancel-${t.id}`}
                          style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', fontSize: 10 }}>
                          <XCircle size={11} />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {tasks.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }} data-testid="tasks-empty">Tidak ada task.</div>
        )}
        {loading && <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }}>Memuat...</div>}
      </div>

      {/* Complete Modal */}
      {completing && (
        <div className="modal-overlay" onClick={() => setCompleting(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="complete-modal">
            <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Selesaikan Task</h2>
            <div style={{ fontSize: 11, color: '#556680', marginBottom: 8 }}>{completing.title}</div>
            <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Outcome / Catatan</label>
            <textarea value={completionOutcome} onChange={e => setCompletionOutcome(e.target.value)} data-testid="complete-outcome"
              placeholder="Hasil dari task ini..." style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit', minHeight: 60 }} />
            <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
              <button className="btn-pill btn-pill-primary" onClick={() => completeTask(completing.id, completionOutcome)} data-testid="confirm-complete" style={{ fontSize: 11 }}>Selesai</button>
              <button className="btn-pill btn-pill-secondary" onClick={() => setCompleting(null)} style={{ fontSize: 11 }}>Batal</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Task Modal */}
      {showForm && (
        <CreateTaskModal users={users} onClose={() => setShowForm(false)} onSaved={() => { setShowForm(false); loadTasks(); loadStats(); }} />
      )}

      {/* Permissions Modal */}
      {showSettings && permissions && (
        <PermissionsModal current={permissions} onClose={() => setShowSettings(false)} onSaved={(p) => { setPermissions(p); setShowSettings(false); }} />
      )}
    </div>
  );
}

function CreateTaskModal({ users, onClose, onSaved, defaults = {} }) {
  const [form, setForm] = useState({
    title: '', description: '', type: 'custom', priority: 'medium',
    assigned_to: '', due_date: '', related_entity_type: '', related_entity_id: '',
    ...defaults,
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true); setErr('');
    try {
      const payload = { ...form };
      if (!payload.assigned_to) delete payload.assigned_to;
      if (!payload.due_date) delete payload.due_date;
      if (!payload.related_entity_type) { delete payload.related_entity_type; delete payload.related_entity_id; }
      await api.post('/tasks', payload);
      onSaved && onSaved();
    } catch (e2) {
      setErr(e2.response?.data?.detail || e2.message);
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="create-task-modal">
        <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Tambah Task</h2>
        <form onSubmit={submit}>
          <div style={{ marginBottom: 8 }}>
            <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Judul *</label>
            <input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} data-testid="task-title"
              style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
            <div>
              <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Tipe</label>
              <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} data-testid="task-type-select"
                style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit' }}>
                {Object.entries(TYPE_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Prioritas</label>
              <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} data-testid="task-priority-select"
                style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit' }}>
                {Object.entries(PRIORITY_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
            <div>
              <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Assigned To</label>
              <select value={form.assigned_to} onChange={e => setForm({ ...form, assigned_to: e.target.value })} data-testid="task-assign-select"
                style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit' }}>
                <option value="">-- Saya sendiri --</option>
                {(users || []).filter(u => u.status === 'active').map(u => <option key={u.email} value={u.email}>{u.name || u.email}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Due Date</label>
              <input type="datetime-local" value={form.due_date ? form.due_date.slice(0, 16) : ''} onChange={e => setForm({ ...form, due_date: e.target.value ? new Date(e.target.value).toISOString() : '' })}
                data-testid="task-due"
                style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit' }} />
            </div>
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Deskripsi</label>
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} data-testid="task-desc"
              style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit', minHeight: 60 }} />
          </div>
          {err && <div style={{ color: '#ef4444', fontSize: 10, marginBottom: 6 }}>{err}</div>}
          <div style={{ display: 'flex', gap: 6 }}>
            <button type="submit" className="btn-pill btn-pill-primary" disabled={saving} data-testid="task-submit" style={{ fontSize: 11 }}>{saving ? 'Menyimpan...' : 'Simpan'}</button>
            <button type="button" className="btn-pill btn-pill-secondary" onClick={onClose} style={{ fontSize: 11 }}>Batal</button>
          </div>
        </form>
      </div>
    </div>
  );
}

const ALL_ROLES = ['super_admin', 'management', 'marketing_admin', 'marketing_inhouse', 'sales', 'finance', 'project_manager'];

function PermissionsModal({ current, onClose, onSaved }) {
  const [allowed, setAllowed] = useState(current.allowed_roles || []);
  const [saving, setSaving] = useState(false);
  const toggle = (role) => setAllowed(prev => prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]);
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put('/tasks/permissions', { allowed_roles: allowed });
      onSaved && onSaved(data.data);
    } catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setSaving(false); }
  };
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="permissions-modal">
        <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 4 }}>Konfigurasi Izin Task</h2>
        <p style={{ fontSize: 10, color: '#8896ab', marginBottom: 10 }}>Pilih role yang boleh membuat task. Super admin selalu diizinkan.</p>
        {ALL_ROLES.map(r => (
          <label key={r} style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 11, padding: '4px 0' }} data-testid={`perm-${r}`}>
            <input type="checkbox" checked={allowed.includes(r)} onChange={() => toggle(r)} /> {r.replace('_', ' ')}
          </label>
        ))}
        <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
          <button className="btn-pill btn-pill-primary" onClick={save} disabled={saving} data-testid="save-perms" style={{ fontSize: 11 }}>{saving ? 'Menyimpan...' : 'Simpan'}</button>
          <button className="btn-pill btn-pill-secondary" onClick={onClose} style={{ fontSize: 11 }}>Batal</button>
        </div>
      </div>
    </div>
  );
}

// Reusable inline panel for lead detail page
export function LeadTasksPanel({ leadId, leadName, currentUser }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [completing, setCompleting] = useState(null);
  const [completionOutcome, setCompletionOutcome] = useState('');

  const load = useCallback(async () => {
    if (!leadId) return;
    setLoading(true);
    try {
      const { data } = await api.get('/tasks', { params: { related_entity_id: leadId, status: 'open,in_progress,snoozed,completed', limit: 50 } });
      setTasks(data.data || []);
    } catch {}
    finally { setLoading(false); }
  }, [leadId]);

  useEffect(() => { load(); }, [load]);

  const onComplete = async (taskId) => {
    try {
      await api.post(`/tasks/${taskId}/complete`, { outcome: completionOutcome });
      setCompleting(null); setCompletionOutcome('');
      load();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  return (
    <div style={{ borderTop: '1px solid rgba(0,0,0,0.05)', paddingTop: 8 }} data-testid="lead-tasks-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 4 }}>
          <CheckSquare size={12} color="#2563eb" /> Tasks ({tasks.filter(t => ['open', 'in_progress', 'snoozed'].includes(t.status)).length} aktif)
        </div>
        <button className="btn-pill btn-pill-secondary" style={{ fontSize: 9, padding: '2px 8px' }} onClick={() => setShowAdd(true)} data-testid="lead-add-task">
          <Plus size={10} style={{ display: 'inline', marginRight: 2 }} />Tambah
        </button>
      </div>
      {loading ? (
        <div style={{ fontSize: 10, color: '#8896ab', padding: 6 }}>Memuat...</div>
      ) : tasks.length === 0 ? (
        <div style={{ fontSize: 10, color: '#8896ab', textAlign: 'center', padding: 10 }} data-testid="lead-tasks-empty">Belum ada task untuk lead ini.</div>
      ) : (
        <div style={{ maxHeight: 180, overflowY: 'auto' }}>
          {tasks.map(t => (
            <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0', borderBottom: '1px solid rgba(0,0,0,0.03)', opacity: t.status === 'completed' || t.status === 'canceled' ? 0.55 : 1 }} data-testid={`lead-task-${t.id}`}>
              <PriorityDot priority={t.priority} />
              <TaskTypeBadge type={t.type} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 10, fontWeight: 600, textDecoration: t.status === 'completed' ? 'line-through' : 'none' }}>{t.title}</div>
                <div style={{ fontSize: 8, color: isOverdue(t) ? '#ef4444' : '#8896ab' }}>{formatDue(t.due_date)} • {t.assigned_to?.split('@')[0] || 'unassigned'}</div>
              </div>
              <StatusPill status={t.status} />
              {['open', 'in_progress', 'snoozed'].includes(t.status) && (
                <button onClick={() => setCompleting(t)} title="Selesaikan" data-testid={`lead-complete-${t.id}`}
                  style={{ background: 'rgba(16,185,129,0.12)', color: '#10b981', border: 'none', borderRadius: 4, padding: '2px 5px', cursor: 'pointer' }}>
                  <CheckCircle2 size={10} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      {completing && (
        <div className="modal-overlay" onClick={() => setCompleting(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="lead-complete-modal">
            <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Selesaikan: {completing.title}</h2>
            <textarea value={completionOutcome} onChange={e => setCompletionOutcome(e.target.value)} placeholder="Outcome..." data-testid="lead-complete-outcome"
              style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, minHeight: 60 }} />
            <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
              <button className="btn-pill btn-pill-primary" onClick={() => onComplete(completing.id)} data-testid="lead-confirm-complete" style={{ fontSize: 11 }}>Selesai</button>
              <button className="btn-pill btn-pill-secondary" onClick={() => setCompleting(null)} style={{ fontSize: 11 }}>Batal</button>
            </div>
          </div>
        </div>
      )}
      {showAdd && (
        <CreateTaskModal
          users={[]}
          defaults={{ related_entity_type: 'lead', related_entity_id: leadId, title: `Follow-up: ${leadName || 'Lead'}` }}
          onClose={() => setShowAdd(false)}
          onSaved={() => { setShowAdd(false); load(); }}
        />
      )}
    </div>
  );
}
