import React, { useState, useEffect } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { Calendar, Plus, Clock, MapPin, User, Phone, ChevronLeft, ChevronRight, CheckCircle, X, AlertTriangle } from 'lucide-react';

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [currentMonth, setCurrentMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ lead_id: '', project_id: '', scheduled_at: '', location: '', notes: '' });
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const { t } = useLang();

  useEffect(() => { loadProjects(); loadLeads(); }, []);
  useEffect(() => { loadAppointments(); }, [currentMonth, selectedProject]);

  const loadProjects = async () => {
    try { const { data } = await api.get('/projects'); setProjects(data.data); } catch {}
  };

  const loadLeads = async () => {
    try { const { data } = await api.get('/leads', { params: { limit: 200 } }); setLeads(data.data); } catch {}
  };

  const loadAppointments = async () => {
    setLoading(true);
    try {
      const params = { month: currentMonth };
      if (selectedProject) params.project_id = selectedProject;
      const { data } = await api.get('/appointments/calendar', { params });
      setAppointments(data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/appointments', form);
      setShowForm(false);
      setForm({ lead_id: '', project_id: '', scheduled_at: '', location: '', notes: '' });
      loadAppointments();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const updateStatus = async (id, status) => {
    try {
      await api.put(`/appointments/${id}`, { status });
      loadAppointments();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  // Calendar helpers
  const monthDate = new Date(currentMonth + '-01');
  const monthName = monthDate.toLocaleString('id-ID', { month: 'long', year: 'numeric' });
  const daysInMonth = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0).getDate();
  const firstDay = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1).getDay();
  const dayNames = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];

  const getApptsForDay = (day) => {
    const dateStr = `${currentMonth}-${String(day).padStart(2, '0')}`;
    return appointments.filter(a => a.scheduled_at?.startsWith(dateStr));
  };

  const prevMonth = () => {
    const d = new Date(monthDate);
    d.setMonth(d.getMonth() - 1);
    setCurrentMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  };

  const nextMonth = () => {
    const d = new Date(monthDate);
    d.setMonth(d.getMonth() + 1);
    setCurrentMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  };

  const statusColors = {
    pending: '#f59e0b', confirmed: '#22c55e', rescheduled: '#3b82f6',
    no_show: '#ef4444', completed: '#6b7280', canceled: '#ef4444'
  };

  const summary = {
    total: appointments.length,
    pending: appointments.filter(a => a.status === 'pending').length,
    confirmed: appointments.filter(a => a.status === 'confirmed').length,
    completed: appointments.filter(a => a.status === 'completed').length,
    no_show: appointments.filter(a => a.status === 'no_show').length,
  };

  return (
    <div className="animate-fade-in" data-testid="appointments-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>
            <Calendar size={24} style={{ display: 'inline', marginRight: 8, color: '#2563eb' }} />Jadwal & Appointment
          </h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Kelola jadwal survey dan meeting</p>
        </div>
        <button className="btn-pill btn-pill-primary" onClick={() => setShowForm(true)} data-testid="add-appointment-btn">
          <Plus size={16} style={{ display: 'inline', marginRight: 6 }} />Jadwal Baru
        </button>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{summary.total}</div>
          <div className="kpi-label">Bulan Ini</div>
        </div>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #f59e0b' }}>
          <div className="kpi-number" style={{ color: '#f59e0b' }}>{summary.pending}</div>
          <div className="kpi-label">Pending</div>
        </div>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #22c55e' }}>
          <div className="kpi-number" style={{ color: '#22c55e' }}>{summary.confirmed}</div>
          <div className="kpi-label">Confirmed</div>
        </div>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #6b7280' }}>
          <div className="kpi-number" style={{ color: '#6b7280' }}>{summary.completed}</div>
          <div className="kpi-label">{t('completed')}</div>
        </div>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #ef4444' }}>
          <div className="kpi-number" style={{ color: '#ef4444' }}>{summary.no_show}</div>
          <div className="kpi-label">No-Show</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        {/* Calendar Grid */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <button onClick={prevMonth} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: 8 }}>
              <ChevronLeft size={20} />
            </button>
            <span style={{ fontWeight: 700, fontSize: 16 }}>{monthName}</span>
            <button onClick={nextMonth} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: 8 }}>
              <ChevronRight size={20} />
            </button>
          </div>

          {/* Day headers */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2, marginBottom: 4 }}>
            {dayNames.map(d => (
              <div key={d} style={{ textAlign: 'center', fontSize: 11, fontWeight: 700, color: '#94a3b8', padding: 6 }}>{d}</div>
            ))}
          </div>

          {/* Calendar days */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2 }}>
            {/* Empty cells for first week offset */}
            {Array.from({ length: firstDay }, (_, i) => (
              <div key={`empty-${i}`} style={{ padding: 8 }} />
            ))}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const dayAppts = getApptsForDay(day);
              const isToday = new Date().getDate() === day && new Date().getMonth() === monthDate.getMonth() && new Date().getFullYear() === monthDate.getFullYear();
              return (
                <div key={day} style={{
                  padding: 6, borderRadius: 8, minHeight: 55,
                  background: isToday ? 'rgba(37,99,235,0.06)' : dayAppts.length > 0 ? 'rgba(241,245,249,0.6)' : 'transparent',
                  border: isToday ? '2px solid #2563eb' : '1px solid transparent',
                  cursor: dayAppts.length > 0 ? 'pointer' : 'default'
                }}>
                  <div style={{ fontSize: 12, fontWeight: isToday ? 800 : 500, color: isToday ? '#2563eb' : '#334155', marginBottom: 2 }}>
                    {day}
                  </div>
                  {dayAppts.slice(0, 2).map(a => (
                    <div key={a.id} style={{
                      fontSize: 9, padding: '2px 4px', borderRadius: 4, marginBottom: 2,
                      background: statusColors[a.status] || '#94a3b8', color: 'white', fontWeight: 600,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                    }}>
                      {a.scheduled_at?.substring(11, 16)} {a.lead_name || ''}
                    </div>
                  ))}
                  {dayAppts.length > 2 && (
                    <div style={{ fontSize: 9, color: '#94a3b8', fontWeight: 600 }}>+{dayAppts.length - 2} lagi</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Upcoming List */}
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontWeight: 700, fontSize: 15, marginBottom: 16 }}>Jadwal Mendatang</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {appointments.filter(a => ['pending', 'confirmed'].includes(a.status)).slice(0, 8).map(appt => (
              <div key={appt.id} style={{ padding: 12, borderRadius: 10, background: '#f8fafc', border: '1px solid #f1f5f9' }} data-testid={`appt-${appt.id}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{appt.lead_name || 'Lead'}</div>
                  <span className={`status-badge status-${appt.status === 'confirmed' ? 'active' : 'reserved'}`} style={{ fontSize: 10 }}>
                    {appt.status}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 11, color: '#64748b' }}>
                  <span><Clock size={10} style={{ display: 'inline', marginRight: 4 }} />{new Date(appt.scheduled_at).toLocaleString('id-ID', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
                  {appt.location && <span><MapPin size={10} style={{ display: 'inline', marginRight: 4 }} />{appt.location}</span>}
                  {appt.lead_phone && <span><Phone size={10} style={{ display: 'inline', marginRight: 4 }} />{appt.lead_phone}</span>}
                </div>
                <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                  {appt.status === 'pending' && (
                    <button className="btn-pill btn-pill-primary" style={{ padding: '3px 10px', fontSize: 10 }} onClick={() => updateStatus(appt.id, 'confirmed')}>
                      <CheckCircle size={10} style={{ display: 'inline', marginRight: 3 }} />Konfirmasi
                    </button>
                  )}
                  {appt.status === 'confirmed' && (
                    <button className="btn-pill btn-pill-secondary" style={{ padding: '3px 10px', fontSize: 10 }} onClick={() => updateStatus(appt.id, 'completed')}>
                      Selesai
                    </button>
                  )}
                  <button className="btn-pill btn-pill-secondary" style={{ padding: '3px 10px', fontSize: 10, color: '#ef4444' }} onClick={() => updateStatus(appt.id, 'no_show')}>
                    No-Show
                  </button>
                </div>
              </div>
            ))}
            {appointments.filter(a => ['pending', 'confirmed'].includes(a.status)).length === 0 && (
              <div style={{ textAlign: 'center', padding: 20, color: '#94a3b8', fontSize: 13 }}>Tidak ada jadwal mendatang</div>
            )}
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Jadwal Appointment Baru</h2>
            <form onSubmit={handleCreate}>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>Lead *</label>
                <select value={form.lead_id} onChange={e => setForm({ ...form, lead_id: e.target.value })} required
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="appt-form-lead">
                  <option value="">Pilih Lead</option>
                  {leads.map(l => <option key={l.id} value={l.id}>{l.name} ({l.phone})</option>)}
                </select>
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('projects')}</label>
                <select value={form.project_id} onChange={e => setForm({ ...form, project_id: e.target.value })}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="appt-form-project">
                  <option value="">Pilih Proyek</option>
                  {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>Tanggal & Waktu *</label>
                <input type="datetime-local" value={form.scheduled_at} onChange={e => setForm({ ...form, scheduled_at: e.target.value })} required
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="appt-form-datetime" />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('location')}</label>
                <input value={form.location} onChange={e => setForm({ ...form, location: e.target.value })}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="appt-form-location" />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('notes')}</label>
                <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit', resize: 'vertical' }} data-testid="appt-form-notes" />
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button type="submit" className="btn-pill btn-pill-primary" data-testid="appt-form-submit">{t('save')}</button>
                <button type="button" className="btn-pill btn-pill-secondary" onClick={() => setShowForm(false)}>{t('cancel')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
