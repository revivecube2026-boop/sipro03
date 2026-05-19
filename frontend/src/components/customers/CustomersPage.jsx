import React, { useState, useEffect, useCallback } from 'react';
import api from '../../lib/api';
import { Users, Plus, Search, RefreshCw, X, Mail, Phone, MapPin, Briefcase, IdCard, Heart } from 'lucide-react';

const FIELDS = [
  { key: 'name', label: 'Nama Lengkap', required: true, icon: Users },
  { key: 'nik', label: 'NIK (16 digit)', placeholder: '3201234567890001' },
  { key: 'npwp', label: 'NPWP' },
  { key: 'phone', label: 'Telepon', icon: Phone, placeholder: '081xxx atau +62xxx' },
  { key: 'email', label: 'Email', icon: Mail, type: 'email' },
  { key: 'birthplace', label: 'Tempat Lahir' },
  { key: 'birthdate', label: 'Tgl Lahir', type: 'date' },
  { key: 'gender', label: 'Jenis Kelamin', select: [['male', 'Laki-laki'], ['female', 'Perempuan']] },
  { key: 'marital_status', label: 'Status', select: [['single', 'Lajang'], ['married', 'Menikah'], ['divorced', 'Cerai'], ['widowed', 'Janda/Duda']] },
  { key: 'address', label: 'Alamat', icon: MapPin, full: true },
  { key: 'city', label: 'Kota' },
  { key: 'province', label: 'Provinsi' },
  { key: 'postal_code', label: 'Kode Pos' },
  { key: 'occupation', label: 'Pekerjaan', icon: Briefcase },
  { key: 'company', label: 'Perusahaan' },
  { key: 'monthly_income', label: 'Penghasilan/Bulan (IDR)', type: 'number' },
  { key: 'spouse_name', label: 'Nama Pasangan', icon: Heart },
  { key: 'spouse_nik', label: 'NIK Pasangan' },
  { key: 'spouse_phone', label: 'Telepon Pasangan' },
  { key: 'heir_name', label: 'Nama Ahli Waris' },
  { key: 'heir_relation', label: 'Hubungan Ahli Waris' },
  { key: 'heir_phone', label: 'Telepon Ahli Waris' },
];

const fmtIDR = (n) => n ? 'Rp ' + Number(n).toLocaleString('id-ID') : '-';

export default function CustomersPage() {
  const [list, setList] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [detail, setDetail] = useState(null);
  const [form, setForm] = useState({});
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/customers', { params: { search: search || undefined, limit: 100 } });
      setList(data.data || []); setTotal(data.total || 0);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [search]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditing(null); setForm({}); setErr(''); setShowForm(true); };
  const openEdit = (c) => { setEditing(c.id); setForm({ ...c }); setErr(''); setShowForm(true); };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr('');
    try {
      const payload = { ...form };
      if (payload.monthly_income) payload.monthly_income = Number(payload.monthly_income);
      Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = null; });
      if (editing) await api.put(`/customers/${editing}`, payload);
      else await api.post('/customers', payload);
      setShowForm(false); load();
    } catch (e2) { setErr(e2.response?.data?.detail || e2.message); }
    finally { setBusy(false); }
  };

  const backfill = async () => {
    if (!confirm('Jalankan backfill customer dari deal lama?')) return;
    try {
      const { data } = await api.post('/customers/backfill');
      alert(`Backfill selesai: ${data.data.deals_processed} deal diproses, ${data.data.linked} customer ter-link.`);
      load();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const openDetail = async (id) => {
    try { const { data } = await api.get(`/customers/${id}`); setDetail(data.data); }
    catch (e) { console.error(e); }
  };

  return (
    <div className="animate-fade-in" data-testid="customers-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>Customers</h1>
          <p style={{ color: '#8896ab', fontSize: 10, marginTop: 1 }}>Master pelanggan & data KYC untuk PPJB/AJB</p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn-pill btn-pill-secondary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={backfill} data-testid="customers-backfill-btn">
            <RefreshCw size={12} style={{ display: 'inline', marginRight: 3 }} />Backfill dari Deal
          </button>
          <button className="btn-pill btn-pill-primary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={openCreate} data-testid="customers-add-btn">
            <Plus size={12} style={{ display: 'inline', marginRight: 3 }} />Tambah Customer
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="glass-card" style={{ padding: 8, marginBottom: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
        <Search size={14} color="#8896ab" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Cari nama, telepon, NIK, email..." data-testid="customers-search"
          style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: 12, fontFamily: 'inherit' }} />
        <span style={{ fontSize: 10, color: '#8896ab' }}>{total} customers</span>
      </div>

      {/* Table */}
      <div className="glass-card" style={{ padding: 0, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }} data-testid="customers-table">
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.02)', textAlign: 'left' }}>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Nama</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>NIK</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Telepon</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Email</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Pekerjaan</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Penghasilan</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Deals</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {list.map(c => (
              <tr key={c.id} style={{ borderTop: '1px solid rgba(0,0,0,0.04)', cursor: 'pointer' }} data-testid={`customer-row-${c.id}`} onClick={() => openDetail(c.id)}>
                <td style={{ padding: '5px 10px', fontWeight: 700 }}>{c.name}</td>
                <td style={{ padding: '5px 10px', fontSize: 10, color: '#556680' }}>{c.nik || '-'}</td>
                <td style={{ padding: '5px 10px', fontSize: 10, color: '#556680' }}>{c.phone || '-'}</td>
                <td style={{ padding: '5px 10px', fontSize: 10, color: '#556680' }}>{c.email || '-'}</td>
                <td style={{ padding: '5px 10px', fontSize: 10 }}>{c.occupation || '-'}</td>
                <td style={{ padding: '5px 10px', fontSize: 10 }}>{fmtIDR(c.monthly_income)}</td>
                <td style={{ padding: '5px 10px' }}><span style={{ fontSize: 9, fontWeight: 700, color: '#10b981', background: 'rgba(16,185,129,0.12)', padding: '1px 6px', borderRadius: 4 }}>{c.deal_count || 0}</span></td>
                <td style={{ padding: '5px 10px' }} onClick={e => e.stopPropagation()}>
                  <button onClick={() => openEdit(c)} data-testid={`edit-customer-${c.id}`} style={{ background: 'rgba(37,99,235,0.12)', color: '#2563eb', border: 'none', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontSize: 9 }}>Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && list.length === 0 && <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }} data-testid="customers-empty">Belum ada customer.</div>}
        {loading && <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }}>Memuat...</div>}
      </div>

      {/* Form modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="customer-form-modal" style={{ maxWidth: 700, maxHeight: '88vh', overflowY: 'auto' }}>
            <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>{editing ? 'Edit Customer' : 'Customer Baru'}</h2>
            <form onSubmit={submit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {FIELDS.map(f => (
                  <div key={f.key} style={{ gridColumn: f.full ? '1 / -1' : 'auto' }}>
                    <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>{f.label}{f.required && ' *'}</label>
                    {f.select ? (
                      <select value={form[f.key] || ''} onChange={e => setForm({ ...form, [f.key]: e.target.value })} data-testid={`field-${f.key}`}
                        style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11, fontFamily: 'inherit' }}>
                        <option value="">-</option>
                        {f.select.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    ) : (
                      <input type={f.type || 'text'} value={form[f.key] || ''} onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                        required={f.required} placeholder={f.placeholder} data-testid={`field-${f.key}`}
                        style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11, fontFamily: 'inherit' }} />
                    )}
                  </div>
                ))}
              </div>
              {err && <div style={{ color: '#ef4444', fontSize: 10, marginTop: 8 }}>{err}</div>}
              <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
                <button type="submit" className="btn-pill btn-pill-primary" disabled={busy} data-testid="customer-submit" style={{ fontSize: 11 }}>{busy ? 'Menyimpan...' : 'Simpan'}</button>
                <button type="button" className="btn-pill btn-pill-secondary" onClick={() => setShowForm(false)} style={{ fontSize: 11 }}>Batal</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Detail modal */}
      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="customer-detail-modal" style={{ maxWidth: 700 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h2 style={{ fontSize: 14, fontWeight: 800 }}>{detail.name}</h2>
              <button onClick={() => setDetail(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8896ab' }}><X size={16} /></button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11 }}>
              <div><b style={{ fontSize: 9, color: '#8896ab' }}>NIK:</b> {detail.nik || '-'}</div>
              <div><b style={{ fontSize: 9, color: '#8896ab' }}>NPWP:</b> {detail.npwp || '-'}</div>
              <div><b style={{ fontSize: 9, color: '#8896ab' }}>Telepon:</b> {detail.phone || '-'}</div>
              <div><b style={{ fontSize: 9, color: '#8896ab' }}>Email:</b> {detail.email || '-'}</div>
              <div><b style={{ fontSize: 9, color: '#8896ab' }}>Alamat:</b> {detail.address || '-'}, {detail.city}</div>
              <div><b style={{ fontSize: 9, color: '#8896ab' }}>Pekerjaan:</b> {detail.occupation || '-'} @ {detail.company || '-'}</div>
              <div><b style={{ fontSize: 9, color: '#8896ab' }}>Penghasilan:</b> {fmtIDR(detail.monthly_income)}</div>
              <div><b style={{ fontSize: 9, color: '#8896ab' }}>Pasangan:</b> {detail.spouse_name || '-'}</div>
              <div style={{ gridColumn: '1 / -1', borderTop: '1px solid rgba(0,0,0,0.06)', marginTop: 6, paddingTop: 6 }}>
                <b style={{ fontSize: 10 }}>Deals ({(detail.deals || []).length})</b>
                {(detail.deals || []).map(d => (
                  <div key={d.id} style={{ fontSize: 10, color: '#556680', padding: '3px 0' }}>
                    • {d.unit_label || d.unit_id} — {fmtIDR(d.price)} — <span style={{ fontWeight: 700 }}>{d.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
