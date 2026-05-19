import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../lib/api';
import {
  DollarSign, Plus, RefreshCw, CheckCircle2, CreditCard,
  Clock, AlertCircle, Filter, Settings
} from 'lucide-react';

const fmtIDR = (n) => 'Rp ' + Number(n || 0).toLocaleString('id-ID');

const STATUS_CONFIG = {
  pending: { label: 'Pending', color: '#f59e0b' },
  approved: { label: 'Approved', color: '#2563eb' },
  paid: { label: 'Paid', color: '#10b981' },
};

export default function CommissionsPage() {
  const { user } = useAuth();
  const [list, setList] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [showRules, setShowRules] = useState(false);
  const [paying, setPaying] = useState(null);
  const [payForm, setPayForm] = useState({ payout_date: new Date().toISOString().slice(0, 10), reference: '', notes: '' });

  const canApprove = ['super_admin', 'marketing_admin', 'management', 'finance'].includes(user?.role);
  const canPay = ['super_admin', 'finance', 'management'].includes(user?.role);
  const canManageRules = ['super_admin', 'marketing_admin', 'management'].includes(user?.role);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filter) params.status = filter;
      const [{ data: items }, { data: s }] = await Promise.all([
        api.get('/commissions', { params }),
        api.get('/commissions/stats'),
      ]);
      setList(items.data || []); setStats(s.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const approve = async (id) => {
    try { await api.post(`/commissions/${id}/approve`); load(); }
    catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const pay = async () => {
    if (!paying) return;
    try {
      await api.post(`/commissions/${paying.id}/pay`, payForm);
      setPaying(null); setPayForm({ payout_date: new Date().toISOString().slice(0, 10), reference: '', notes: '' });
      load();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="animate-fade-in" data-testid="commissions-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>Komisi</h1>
          <p style={{ color: '#8896ab', fontSize: 10, marginTop: 1 }}>Tracking komisi sales otomatis dari deal booked</p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn-pill btn-pill-secondary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={load} data-testid="commissions-refresh">
            <RefreshCw size={12} style={{ display: 'inline', marginRight: 3 }} />Refresh
          </button>
          {canManageRules && (
            <button className="btn-pill btn-pill-secondary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={() => setShowRules(true)} data-testid="commission-rules-btn">
              <Settings size={12} style={{ display: 'inline', marginRight: 3 }} />Aturan Komisi
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 8 }}>
          {['pending', 'approved', 'paid'].map(k => {
            const s = stats[k]; const c = STATUS_CONFIG[k];
            const Icon = k === 'pending' ? Clock : k === 'approved' ? AlertCircle : CheckCircle2;
            return (
              <div key={k} className="mini-dashboard-card" style={{ padding: '8px 12px' }} data-testid={`stats-${k}`}>
                <Icon size={11} color={c.color} />
                <div className="kpi-number" style={{ fontSize: 16, color: c.color }}>{fmtIDR(s.amount)}</div>
                <div className="kpi-label" style={{ fontSize: 8 }}>{c.label} • {s.count} item</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Filter */}
      <div className="glass-card" style={{ padding: 8, marginBottom: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
        <Filter size={12} color="#8896ab" />
        <select value={filter} onChange={e => setFilter(e.target.value)} data-testid="commission-filter"
          style={{ fontSize: 10, padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(0,0,0,0.08)' }}>
          <option value="">Semua Status</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="paid">Paid</option>
        </select>
      </div>

      {/* Table */}
      <div className="glass-card" style={{ padding: 0, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }} data-testid="commissions-table">
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.02)', textAlign: 'left' }}>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Customer</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Sales</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Aturan</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Harga Deal</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Komisi</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Status</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab', textAlign: 'right' }}>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {list.map(c => {
              const sc = STATUS_CONFIG[c.status] || STATUS_CONFIG.pending;
              return (
                <tr key={c.id} style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }} data-testid={`commission-row-${c.id}`}>
                  <td style={{ padding: '5px 10px', fontWeight: 700 }}>{c.customer_name}</td>
                  <td style={{ padding: '5px 10px', fontSize: 10, color: '#556680' }}>{c.assignee_email?.split('@')[0] || '-'}</td>
                  <td style={{ padding: '5px 10px', fontSize: 9, color: '#8896ab' }}>{c.rule_name}</td>
                  <td style={{ padding: '5px 10px', fontSize: 10 }}>{fmtIDR(c.deal_price)}</td>
                  <td style={{ padding: '5px 10px', fontWeight: 700, color: '#10b981' }}>{fmtIDR(c.amount)}</td>
                  <td style={{ padding: '5px 10px' }}>
                    <span style={{ fontSize: 8, fontWeight: 800, color: sc.color, background: `${sc.color}15`, padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase' }}>{sc.label}</span>
                  </td>
                  <td style={{ padding: '5px 10px', textAlign: 'right' }}>
                    {c.status === 'pending' && canApprove && (
                      <button onClick={() => approve(c.id)} data-testid={`approve-${c.id}`} style={{ background: 'rgba(37,99,235,0.12)', color: '#2563eb', border: 'none', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontSize: 9, marginRight: 4 }}>Approve</button>
                    )}
                    {c.status === 'approved' && canPay && (
                      <button onClick={() => setPaying(c)} data-testid={`pay-${c.id}`} style={{ background: 'rgba(16,185,129,0.12)', color: '#10b981', border: 'none', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontSize: 9 }}>
                        <CreditCard size={10} style={{ display: 'inline', marginRight: 2 }} />Bayar
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!loading && list.length === 0 && <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }} data-testid="commissions-empty">Belum ada komisi.</div>}
        {loading && <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }}>Memuat...</div>}
      </div>

      {/* Pay modal */}
      {paying && (
        <div className="modal-overlay" onClick={() => setPaying(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="pay-modal">
            <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Bayar Komisi: {fmtIDR(paying.amount)}</h2>
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Tanggal Payout</label>
              <input type="date" value={payForm.payout_date} onChange={e => setPayForm({ ...payForm, payout_date: e.target.value })} data-testid="pay-date"
                style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Referensi (No. Transfer)</label>
              <input value={payForm.reference} onChange={e => setPayForm({ ...payForm, reference: e.target.value })} data-testid="pay-ref"
                style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Catatan</label>
              <textarea value={payForm.notes} onChange={e => setPayForm({ ...payForm, notes: e.target.value })} data-testid="pay-notes"
                style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11, minHeight: 50 }} />
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn-pill btn-pill-primary" onClick={pay} data-testid="confirm-pay" style={{ fontSize: 11 }}>Konfirmasi Bayar</button>
              <button className="btn-pill btn-pill-secondary" onClick={() => setPaying(null)} style={{ fontSize: 11 }}>Batal</button>
            </div>
          </div>
        </div>
      )}

      {/* Rules modal */}
      {showRules && <CommissionRulesModal onClose={() => setShowRules(false)} />}
    </div>
  );
}

function CommissionRulesModal({ onClose }) {
  const [rules, setRules] = useState([]);
  const [form, setForm] = useState({ name: '', rate_type: 'percent', rate_value: 2.5, is_active: true, priority: 0, role: '', project_id: '' });

  const load = async () => {
    try { const { data } = await api.get('/commissions/rules'); setRules(data.data || []); }
    catch {}
  };
  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...form };
      payload.rate_value = Number(payload.rate_value);
      payload.priority = Number(payload.priority);
      if (!payload.project_id) delete payload.project_id;
      if (!payload.role) delete payload.role;
      await api.post('/commissions/rules', payload);
      setForm({ name: '', rate_type: 'percent', rate_value: 2.5, is_active: true, priority: 0, role: '', project_id: '' });
      load();
    } catch (e2) { alert(e2.response?.data?.detail || e2.message); }
  };

  const del = async (id) => {
    if (!confirm('Hapus aturan ini?')) return;
    try { await api.delete(`/commissions/rules/${id}`); load(); }
    catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="rules-modal" style={{ maxWidth: 700 }}>
        <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Aturan Komisi</h2>
        <form onSubmit={save} style={{ borderBottom: '1px solid rgba(0,0,0,0.06)', paddingBottom: 8, marginBottom: 8 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr', gap: 6, alignItems: 'end' }}>
            <div>
              <label style={{ fontSize: 9, color: '#8896ab', fontWeight: 700 }}>Nama</label>
              <input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="rule-name"
                style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }} />
            </div>
            <div>
              <label style={{ fontSize: 9, color: '#8896ab', fontWeight: 700 }}>Tipe</label>
              <select value={form.rate_type} onChange={e => setForm({ ...form, rate_type: e.target.value })} data-testid="rule-type"
                style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }}>
                <option value="percent">Persen</option>
                <option value="flat">Flat (Rp)</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: 9, color: '#8896ab', fontWeight: 700 }}>Nilai</label>
              <input type="number" step="0.1" value={form.rate_value} onChange={e => setForm({ ...form, rate_value: e.target.value })} data-testid="rule-value"
                style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }} />
            </div>
            <div>
              <label style={{ fontSize: 9, color: '#8896ab', fontWeight: 700 }}>Role</label>
              <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} data-testid="rule-role"
                style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }}>
                <option value="">Semua</option>
                <option value="sales">sales</option>
                <option value="marketing_inhouse">marketing_inhouse</option>
                <option value="marketing_admin">marketing_admin</option>
              </select>
            </div>
            <div>
              <button type="submit" className="btn-pill btn-pill-primary" data-testid="add-rule" style={{ fontSize: 11, padding: '6px 12px' }}>
                <Plus size={11} style={{ display: 'inline', marginRight: 2 }} />Tambah
              </button>
            </div>
          </div>
        </form>
        <div style={{ maxHeight: 300, overflowY: 'auto' }}>
          {rules.map(r => (
            <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: '1px solid rgba(0,0,0,0.03)', fontSize: 11 }} data-testid={`rule-${r.id}`}>
              <span style={{ fontWeight: 700, flex: 1 }}>{r.name}</span>
              <span style={{ fontSize: 10, color: '#8896ab' }}>{r.role || 'all roles'}</span>
              <span style={{ fontSize: 10, fontWeight: 700, color: '#10b981' }}>{r.rate_type === 'percent' ? `${r.rate_value}%` : fmtIDR(r.rate_value)}</span>
              <span style={{ fontSize: 8, fontWeight: 700, color: r.is_active ? '#10b981' : '#8896ab' }}>{r.is_active ? 'AKTIF' : 'NON-AKTIF'}</span>
              <button onClick={() => del(r.id)} data-testid={`del-rule-${r.id}`} style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', fontSize: 9 }}>Hapus</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
