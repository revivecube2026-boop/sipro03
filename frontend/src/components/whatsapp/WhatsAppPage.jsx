import React, { useState, useEffect } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { MessageCircle, Send, Clock, CheckCircle, FileText } from 'lucide-react';

export default function WhatsAppPage() {
  const [messages, setMessages] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [showSend, setShowSend] = useState(false);
  const [form, setForm] = useState({ recipient_phone: '', recipient_name: '', message: '', message_type: 'notification' });
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const { t } = useLang();

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [msgRes, tplRes] = await Promise.all([
        api.get('/whatsapp/messages'),
        api.get('/whatsapp/templates')
      ]);
      setMessages(msgRes.data.data);
      setTotal(msgRes.data.total);
      setTemplates(tplRes.data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    try {
      await api.post('/whatsapp/send', form);
      setShowSend(false);
      setForm({ recipient_phone: '', recipient_name: '', message: '', message_type: 'notification' });
      loadData();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const applyTemplate = (tplId) => {
    const tpl = templates.find(t => t.id === tplId);
    if (tpl) {
      setForm({ ...form, message: tpl.message, message_type: tpl.type || 'notification' });
      setSelectedTemplate(tplId);
    }
  };

  const msgTypes = { notification: '#3b82f6', follow_up: '#f59e0b', reminder: '#7c3aed', payment_reminder: '#ef4444' };

  return (
    <div className="animate-fade-in" data-testid="whatsapp-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>
            <MessageCircle size={24} style={{ display: 'inline', marginRight: 8, color: '#25D366' }} />{t('whatsapp')}
          </h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Kirim pesan dan lihat log komunikasi</p>
        </div>
        <button className="btn-pill btn-pill-primary" onClick={() => setShowSend(true)} data-testid="send-wa-btn">
          <Send size={16} style={{ display: 'inline', marginRight: 6 }} />{t('send_message')}
        </button>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{total}</div>
          <div className="kpi-label">Total Pesan</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ color: '#22c55e' }}>{messages.filter(m => m.status === 'sent').length}</div>
          <div className="kpi-label">Terkirim</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ color: '#f59e0b' }}>{messages.filter(m => m.status === 'queued').length}</div>
          <div className="kpi-label">Antrian</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{templates.length}</div>
          <div className="kpi-label">Template</div>
        </div>
      </div>

      {/* Messages Log */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9' }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{t('messages_log')}</span>
        </div>
        <table className="sipro-table" data-testid="wa-messages-table">
          <thead>
            <tr>
              <th>{t('recipient')}</th>
              <th>{t('message')}</th>
              <th>{t('type')}</th>
              <th>{t('status')}</th>
              <th>Waktu</th>
            </tr>
          </thead>
          <tbody>
            {messages.map(msg => (
              <tr key={msg.id}>
                <td>
                  <div style={{ fontWeight: 600 }}>{msg.recipient_name || '-'}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>{msg.recipient_phone}</div>
                </td>
                <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{msg.message}</td>
                <td>
                  <span style={{ fontSize: 11, fontWeight: 600, color: msgTypes[msg.message_type] || '#64748b', textTransform: 'capitalize' }}>
                    {msg.message_type?.replace('_', ' ')}
                  </span>
                </td>
                <td>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    {msg.status === 'sent' ? <CheckCircle size={14} color="#22c55e" /> : <Clock size={14} color="#f59e0b" />}
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{msg.status}</span>
                  </span>
                </td>
                <td style={{ fontSize: 12, color: '#94a3b8' }}>{new Date(msg.created_at).toLocaleString('id-ID')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {messages.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>{t('no_data')}</div>
        )}
      </div>

      {/* Send Modal */}
      {showSend && (
        <div className="modal-overlay" onClick={() => setShowSend(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>
              <MessageCircle size={20} style={{ display: 'inline', marginRight: 8, color: '#25D366' }} />{t('send_message')}
            </h2>

            {/* Templates */}
            {templates.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 6 }}>{t('template')}</label>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {templates.map(tpl => (
                    <button key={tpl.id} className={`filter-chip ${selectedTemplate === tpl.id ? 'active' : ''}`}
                      onClick={() => applyTemplate(tpl.id)} style={{ fontSize: 11 }}>
                      <FileText size={12} /> {tpl.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <form onSubmit={handleSend}>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>No. WhatsApp *</label>
                <input value={form.recipient_phone} onChange={e => setForm({ ...form, recipient_phone: e.target.value })}
                  required placeholder="+628xxxxxxxxxx"
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }}
                  data-testid="wa-phone-input" />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('name')}</label>
                <input value={form.recipient_name} onChange={e => setForm({ ...form, recipient_name: e.target.value })}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }}
                  data-testid="wa-name-input" />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('message')} *</label>
                <textarea value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} required
                  rows={4}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit', resize: 'vertical' }}
                  data-testid="wa-message-input" />
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button type="submit" className="btn-pill btn-pill-primary" data-testid="wa-send-submit">
                  <Send size={14} style={{ display: 'inline', marginRight: 6 }} />Kirim
                </button>
                <button type="button" className="btn-pill btn-pill-secondary" onClick={() => setShowSend(false)}>{t('cancel')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
