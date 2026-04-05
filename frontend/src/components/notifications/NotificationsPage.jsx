import React, { useState, useEffect } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { Bell, Check, CheckCheck, Zap, Plus, Trash2, ToggleLeft, ToggleRight, MessageCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [rules, setRules] = useState([]);
  const [unread, setUnread] = useState(0);
  const [total, setTotal] = useState(0);
  const [activeTab, setActiveTab] = useState('inbox');
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [ruleForm, setRuleForm] = useState({ name: '', trigger_event: 'lead.created', delay_minutes: 5, message_template: '', channel: 'whatsapp', is_active: true });
  const [loading, setLoading] = useState(true);
  const { t } = useLang();

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [notifRes, rulesRes] = await Promise.all([
        api.get('/notifications'),
        api.get('/notifications/auto-rules')
      ]);
      setNotifications(notifRes.data.data);
      setUnread(notifRes.data.unread);
      setTotal(notifRes.data.total);
      setRules(rulesRes.data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const markRead = async (id) => {
    try {
      await api.put(`/notifications/${id}/read`);
      loadData();
    } catch {}
  };

  const markAllRead = async () => {
    try {
      await api.put('/notifications/read-all');
      loadData();
    } catch {}
  };

  const createRule = async (e) => {
    e.preventDefault();
    try {
      await api.post('/notifications/auto-rules', ruleForm);
      setShowRuleForm(false);
      setRuleForm({ name: '', trigger_event: 'lead.created', delay_minutes: 5, message_template: '', channel: 'whatsapp', is_active: true });
      loadData();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const toggleRule = async (ruleId, isActive) => {
    try {
      await api.put(`/notifications/auto-rules/${ruleId}`, { is_active: !isActive });
      loadData();
    } catch {}
  };

  const deleteRule = async (ruleId) => {
    if (!window.confirm('Hapus rule ini?')) return;
    try {
      await api.delete(`/notifications/auto-rules/${ruleId}`);
      loadData();
    } catch {}
  };

  const typeIcon = (type) => {
    if (type === 'follow_up') return <Zap size={16} color="#f59e0b" />;
    if (type === 'success') return <CheckCircle size={16} color="#22c55e" />;
    if (type === 'danger') return <AlertTriangle size={16} color="#ef4444" />;
    return <Info size={16} color="#3b82f6" />;
  };

  const triggerEvents = [
    { value: 'lead.created', label: 'Lead Baru Masuk' },
    { value: 'appointment.no_show', label: 'Appointment No-Show' },
    { value: 'payment.overdue', label: 'Pembayaran Overdue' },
    { value: 'deal.reserved', label: 'Deal Reserved' },
    { value: 'deal.booked', label: 'Deal Booked' },
  ];

  return (
    <div className="animate-fade-in" data-testid="notifications-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>
            <Bell size={24} style={{ display: 'inline', marginRight: 8, color: '#7c3aed' }} />Notification Center
          </h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Notifikasi real-time dan auto follow-up engine</p>
        </div>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{total}</div>
          <div className="kpi-label">Total Notifikasi</div>
        </div>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #ef4444' }}>
          <div className="kpi-number" style={{ color: '#ef4444' }}>{unread}</div>
          <div className="kpi-label">Belum Dibaca</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ color: '#7c3aed' }}>{rules.length}</div>
          <div className="kpi-label">Auto Rules</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ color: '#22c55e' }}>{rules.filter(r => r.is_active).length}</div>
          <div className="kpi-label">Rules Aktif</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button className={`filter-chip ${activeTab === 'inbox' ? 'active' : ''}`} onClick={() => setActiveTab('inbox')} data-testid="notif-tab-inbox">
          <Bell size={14} /> Inbox ({unread} baru)
        </button>
        <button className={`filter-chip ${activeTab === 'rules' ? 'active' : ''}`} onClick={() => setActiveTab('rules')} data-testid="notif-tab-rules">
          <Zap size={14} /> Auto Follow-Up Rules ({rules.length})
        </button>
      </div>

      {/* Inbox */}
      {activeTab === 'inbox' && (
        <div>
          {unread > 0 && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
              <button className="btn-pill btn-pill-secondary" style={{ fontSize: 12 }} onClick={markAllRead} data-testid="mark-all-read">
                <CheckCheck size={14} style={{ display: 'inline', marginRight: 4 }} /> Tandai semua dibaca
              </button>
            </div>
          )}
          <div className="glass-card" style={{ overflow: 'hidden' }}>
            {notifications.map(notif => (
              <div
                key={notif.id}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 14, padding: '14px 20px',
                  borderBottom: '1px solid #f1f5f9', cursor: 'pointer',
                  background: notif.read ? 'transparent' : 'rgba(37,99,235,0.03)',
                  transition: 'background 0.15s ease'
                }}
                onClick={() => !notif.read && markRead(notif.id)}
                data-testid={`notification-${notif.id}`}
              >
                <div style={{ marginTop: 2 }}>{typeIcon(notif.type)}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ fontWeight: notif.read ? 500 : 700, fontSize: 14, color: notif.read ? '#64748b' : '#1e293b' }}>
                      {notif.title}
                    </div>
                    <div style={{ fontSize: 11, color: '#94a3b8', whiteSpace: 'nowrap', marginLeft: 12 }}>
                      {new Date(notif.created_at).toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                  <div style={{ fontSize: 13, color: '#64748b', marginTop: 2, lineHeight: 1.4 }}>{notif.message}</div>
                  {!notif.read && (
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#2563eb', position: 'absolute', right: 20, top: '50%', transform: 'translateY(-50%)' }} />
                  )}
                </div>
              </div>
            ))}
            {notifications.length === 0 && <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>Tidak ada notifikasi</div>}
          </div>
        </div>
      )}

      {/* Auto Follow-Up Rules */}
      {activeTab === 'rules' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <p style={{ fontSize: 13, color: '#64748b' }}>
              Atur auto follow-up untuk lead baru dari ads — kirim WhatsApp otomatis dalam hitungan menit!
            </p>
            <button className="btn-pill btn-pill-primary" onClick={() => setShowRuleForm(true)} data-testid="add-rule-btn">
              <Plus size={14} style={{ display: 'inline', marginRight: 4 }} /> Tambah Rule
            </button>
          </div>

          <div className="stagger-children">
            {rules.map(rule => (
              <div key={rule.id} className="glass-card" style={{ padding: 20, marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <span style={{ fontWeight: 700, fontSize: 15 }}>{rule.name}</span>
                    <span className={`status-badge ${rule.is_active ? 'status-active' : 'status-not_started'}`}>
                      {rule.is_active ? 'Aktif' : 'Nonaktif'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, color: '#64748b' }}>
                      <Zap size={12} style={{ display: 'inline', marginRight: 4 }} />
                      Trigger: <strong>{triggerEvents.find(t => t.value === rule.trigger_event)?.label || rule.trigger_event}</strong>
                    </span>
                    <span style={{ fontSize: 12, color: '#64748b' }}>
                      Delay: <strong>{rule.delay_minutes} menit</strong>
                    </span>
                    <span style={{ fontSize: 12, color: '#64748b' }}>
                      Channel: <strong style={{ textTransform: 'capitalize' }}>{rule.channel}</strong>
                    </span>
                    <span style={{ fontSize: 12, color: '#64748b' }}>
                      Eksekusi: <strong>{rule.executions || 0}x</strong>
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 6, fontStyle: 'italic', maxWidth: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    "{rule.message_template}"
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <button onClick={() => toggleRule(rule.id, rule.is_active)} style={{ background: 'none', border: 'none', cursor: 'pointer' }} data-testid={`toggle-rule-${rule.id}`}>
                    {rule.is_active ? <ToggleRight size={28} color="#22c55e" /> : <ToggleLeft size={28} color="#94a3b8" />}
                  </button>
                  <button onClick={() => deleteRule(rule.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}>
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {rules.length === 0 && <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>Belum ada auto follow-up rules</div>}
        </div>
      )}

      {/* Rule Form Modal */}
      {showRuleForm && (
        <div className="modal-overlay" onClick={() => setShowRuleForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>
              <Zap size={20} style={{ display: 'inline', marginRight: 8, color: '#f59e0b' }} /> Auto Follow-Up Rule Baru
            </h2>
            <form onSubmit={createRule}>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>Nama Rule *</label>
                <input value={ruleForm.name} onChange={e => setRuleForm({ ...ruleForm, name: e.target.value })} required placeholder="e.g. Auto WA Lead Baru"
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="rule-form-name" />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>Trigger Event</label>
                  <select value={ruleForm.trigger_event} onChange={e => setRuleForm({ ...ruleForm, trigger_event: e.target.value })}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="rule-form-trigger">
                    {triggerEvents.map(te => <option key={te.value} value={te.value}>{te.label}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>Delay (menit)</label>
                  <input type="number" value={ruleForm.delay_minutes} onChange={e => setRuleForm({ ...ruleForm, delay_minutes: parseInt(e.target.value) || 0 })}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="rule-form-delay" />
                </div>
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>Channel</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['whatsapp', 'in_app'].map(ch => (
                    <button key={ch} type="button" className={`filter-chip ${ruleForm.channel === ch ? 'active' : ''}`}
                      onClick={() => setRuleForm({ ...ruleForm, channel: ch })}>
                      {ch === 'whatsapp' ? <MessageCircle size={12} /> : <Bell size={12} />} {ch === 'whatsapp' ? 'WhatsApp' : 'In-App'}
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>Template Pesan * <span style={{ fontWeight: 400 }}>(gunakan {'{name}'}, {'{source}'}, {'{project}'})</span></label>
                <textarea value={ruleForm.message_template} onChange={e => setRuleForm({ ...ruleForm, message_template: e.target.value })} required rows={3}
                  placeholder="Halo {name}! Terima kasih telah tertarik..."
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit', resize: 'vertical' }} data-testid="rule-form-template" />
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button type="submit" className="btn-pill btn-pill-primary" data-testid="rule-form-submit">{t('save')}</button>
                <button type="button" className="btn-pill btn-pill-secondary" onClick={() => setShowRuleForm(false)}>{t('cancel')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
