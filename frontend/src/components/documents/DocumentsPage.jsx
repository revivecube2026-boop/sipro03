import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../lib/api';
import {
  FileText, Plus, Download, CheckCircle2, FileSignature,
  Search, Filter, X, Settings, Trash2, Edit3
} from 'lucide-react';

const STATUS_CONFIG = {
  draft: { label: 'Draft', color: '#8896ab' },
  finalized: { label: 'Finalized', color: '#2563eb' },
  signed: { label: 'Signed', color: '#10b981' },
  canceled: { label: 'Canceled', color: '#ef4444' },
};

const CODE_COLOR = {
  SPK: '#f59e0b',
  PPJB: '#2563eb',
  AJB: '#7c3aed',
  BAST: '#10b981',
};

export default function DocumentsPage() {
  const { user } = useAuth();
  const [list, setList] = useState([]);
  const [total, setTotal] = useState(0);
  const [templates, setTemplates] = useState([]);
  const [filter, setFilter] = useState({ status: '', template_code: '' });
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showEditor, setShowEditor] = useState(null);
  const [showSign, setShowSign] = useState(null);
  const [showTemplates, setShowTemplates] = useState(false);

  const canManageTemplates = ['super_admin', 'marketing_admin', 'management'].includes(user?.role);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filter.status) params.status = filter.status;
      if (filter.template_code) params.template_code = filter.template_code;
      const [{ data }, { data: tpls }] = await Promise.all([
        api.get('/documents', { params }),
        api.get('/document-templates'),
      ]);
      setList(data.data || []); setTotal(data.total || 0);
      setTemplates(tpls.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const downloadPdf = async (docId, docNumber) => {
    try {
      const res = await api.get(`/documents/${docId}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url; a.download = `${docNumber.replace(/\//g, '_')}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { alert('Gagal mengunduh PDF: ' + (e.response?.data?.detail || e.message)); }
  };

  const previewPdf = async (docId) => {
    try {
      const res = await api.get(`/documents/${docId}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    } catch (e) { alert('Gagal preview PDF: ' + (e.response?.data?.detail || e.message)); }
  };

  const finalize = async (docId) => {
    if (!confirm('Finalisasi dokumen ini? Setelah final tidak dapat diedit.')) return;
    try { await api.post(`/documents/${docId}/finalize`); load(); }
    catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const remove = async (docId) => {
    if (!confirm('Hapus dokumen ini?')) return;
    try { await api.delete(`/documents/${docId}`); load(); }
    catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="animate-fade-in" data-testid="documents-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>Dokumen Legal</h1>
          <p style={{ color: '#8896ab', fontSize: 10, marginTop: 1 }}>SPK / PPJB / AJB / BAST — generate, finalisasi, e-sign, unduh PDF</p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {canManageTemplates && (
            <button className="btn-pill btn-pill-secondary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={() => setShowTemplates(true)} data-testid="manage-templates-btn">
              <Settings size={12} style={{ display: 'inline', marginRight: 3 }} />Template
            </button>
          )}
          <button className="btn-pill btn-pill-primary" style={{ fontSize: 10, padding: '5px 10px' }} onClick={() => setShowCreate(true)} data-testid="create-doc-btn">
            <Plus size={12} style={{ display: 'inline', marginRight: 3 }} />Buat Dokumen
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card" style={{ padding: 8, marginBottom: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
        <Filter size={12} color="#8896ab" />
        <select value={filter.template_code} onChange={e => setFilter({ ...filter, template_code: e.target.value })} data-testid="filter-code"
          style={{ fontSize: 10, padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(0,0,0,0.08)' }}>
          <option value="">Semua Tipe</option>
          {['SPK', 'PPJB', 'AJB', 'BAST'].map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filter.status} onChange={e => setFilter({ ...filter, status: e.target.value })} data-testid="filter-doc-status"
          style={{ fontSize: 10, padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(0,0,0,0.08)' }}>
          <option value="">Semua Status</option>
          {Object.entries(STATUS_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: '#8896ab' }}>{total} dokumen</span>
      </div>

      {/* Table */}
      <div className="glass-card" style={{ padding: 0, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }} data-testid="documents-table">
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.02)', textAlign: 'left' }}>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Tipe</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Nomor</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Judul</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Status</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Signatures</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab' }}>Tgl Buat</th>
              <th style={{ padding: '6px 10px', fontSize: 9, fontWeight: 800, color: '#8896ab', textAlign: 'right' }}>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {list.map(d => {
              const sc = STATUS_CONFIG[d.status] || STATUS_CONFIG.draft;
              const color = CODE_COLOR[d.template_code] || '#8896ab';
              return (
                <tr key={d.id} style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }} data-testid={`doc-row-${d.id}`}>
                  <td style={{ padding: '5px 10px' }}>
                    <span style={{ fontSize: 9, fontWeight: 800, color, background: `${color}15`, padding: '2px 6px', borderRadius: 4 }}>{d.template_code}</span>
                  </td>
                  <td style={{ padding: '5px 10px', fontSize: 10, fontFamily: 'monospace', color: '#556680' }}>{d.doc_number}</td>
                  <td style={{ padding: '5px 10px', fontWeight: 600 }}>{d.title}</td>
                  <td style={{ padding: '5px 10px' }}>
                    <span style={{ fontSize: 8, fontWeight: 800, color: sc.color, background: `${sc.color}15`, padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase' }}>{sc.label}</span>
                  </td>
                  <td style={{ padding: '5px 10px', fontSize: 10 }}>{(d.signatures || []).length}/3</td>
                  <td style={{ padding: '5px 10px', fontSize: 9, color: '#8896ab' }}>{(d.created_at || '').slice(0, 10)}</td>
                  <td style={{ padding: '5px 10px', textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: 4 }}>
                      <button onClick={() => previewPdf(d.id)} title="Preview PDF" data-testid={`preview-${d.id}`}
                        style={{ background: 'rgba(37,99,235,0.12)', color: '#2563eb', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer' }}>
                        <FileText size={11} />
                      </button>
                      <button onClick={() => downloadPdf(d.id, d.doc_number)} title="Unduh PDF" data-testid={`download-${d.id}`}
                        style={{ background: 'rgba(16,185,129,0.12)', color: '#10b981', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer' }}>
                        <Download size={11} />
                      </button>
                      {d.status === 'draft' && (
                        <>
                          <button onClick={() => setShowEditor(d.id)} title="Edit konten" data-testid={`edit-${d.id}`}
                            style={{ background: 'rgba(245,158,11,0.12)', color: '#f59e0b', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer' }}>
                            <Edit3 size={11} />
                          </button>
                          <button onClick={() => finalize(d.id)} title="Finalisasi" data-testid={`finalize-${d.id}`}
                            style={{ background: 'rgba(37,99,235,0.12)', color: '#2563eb', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer' }}>
                            <CheckCircle2 size={11} />
                          </button>
                        </>
                      )}
                      {(d.status === 'finalized' || d.status === 'signed') && (
                        <button onClick={() => setShowSign(d)} title="Tanda tangan" data-testid={`sign-${d.id}`}
                          style={{ background: 'rgba(124,58,237,0.12)', color: '#7c3aed', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer' }}>
                          <FileSignature size={11} />
                        </button>
                      )}
                      <button onClick={() => remove(d.id)} title="Hapus" data-testid={`delete-${d.id}`}
                        style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444', border: 'none', borderRadius: 4, padding: '2px 6px', cursor: 'pointer' }}>
                        <Trash2 size={11} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!loading && list.length === 0 && <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }} data-testid="docs-empty">Belum ada dokumen. Buat dokumen pertama dari deal.</div>}
        {loading && <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }}>Memuat...</div>}
      </div>

      {showCreate && <CreateDocModal templates={templates} onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load(); }} />}
      {showEditor && <ContentEditorModal docId={showEditor} onClose={() => setShowEditor(null)} onSaved={() => { setShowEditor(null); load(); }} />}
      {showSign && <SignModal doc={showSign} onClose={() => setShowSign(null)} onSigned={() => { setShowSign(null); load(); }} />}
      {showTemplates && <TemplatesModal templates={templates} onClose={() => setShowTemplates(false)} onChanged={() => load()} />}
    </div>
  );
}

function CreateDocModal({ templates, onClose, onCreated }) {
  const [deals, setDeals] = useState([]);
  const [form, setForm] = useState({ template_id: '', deal_id: '' });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.get('/deals', { params: { limit: 200 } }).then(({ data }) => setDeals(data.data || [])).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr('');
    try { await api.post('/documents', form); onCreated && onCreated(); }
    catch (e2) { setErr(e2.response?.data?.detail || e2.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="create-doc-modal" style={{ maxWidth: 540 }}>
        <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Buat Dokumen Baru</h2>
        <form onSubmit={submit}>
          <div style={{ marginBottom: 8 }}>
            <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Template *</label>
            <select required value={form.template_id} onChange={e => setForm({ ...form, template_id: e.target.value })} data-testid="select-template"
              style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }}>
              <option value="">-- Pilih template --</option>
              {templates.map(t => <option key={t.id} value={t.id}>{t.code} - {t.name}</option>)}
            </select>
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Deal *</label>
            <select required value={form.deal_id} onChange={e => setForm({ ...form, deal_id: e.target.value })} data-testid="select-deal"
              style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }}>
              <option value="">-- Pilih deal --</option>
              {deals.map(d => <option key={d.id} value={d.id}>{d.customer_name} — Unit {d.unit_label || d.unit_id} — Rp {Number(d.price).toLocaleString('id-ID')}</option>)}
            </select>
          </div>
          {err && <div style={{ color: '#ef4444', fontSize: 10, marginBottom: 6 }}>{err}</div>}
          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            <button type="submit" className="btn-pill btn-pill-primary" disabled={busy} data-testid="submit-doc" style={{ fontSize: 11 }}>{busy ? 'Membuat...' : 'Buat & Resolve Variabel'}</button>
            <button type="button" className="btn-pill btn-pill-secondary" onClick={onClose} style={{ fontSize: 11 }}>Batal</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ContentEditorModal({ docId, onClose, onSaved }) {
  const [doc, setDoc] = useState(null);
  const [content, setContent] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/documents/${docId}`).then(({ data }) => { setDoc(data.data); setContent(data.data.content || ''); });
  }, [docId]);

  const save = async () => {
    setBusy(true);
    try { await api.put(`/documents/${docId}`, { content }); onSaved && onSaved(); }
    catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  if (!doc) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="editor-modal" style={{ maxWidth: 800, maxHeight: '90vh', overflowY: 'auto' }}>
        <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Edit Konten: {doc.title}</h2>
        <p style={{ fontSize: 10, color: '#8896ab', marginBottom: 8 }}>Markdown ringan: `# Heading`, `## Sub`, `- bullet`, `**bold**`. Variabel sudah ter-resolve.</p>
        <textarea value={content} onChange={e => setContent(e.target.value)} data-testid="content-editor"
          style={{ width: '100%', minHeight: 400, padding: 10, borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11, fontFamily: 'monospace' }} />
        <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
          <button className="btn-pill btn-pill-primary" onClick={save} disabled={busy} data-testid="save-content" style={{ fontSize: 11 }}>{busy ? 'Menyimpan...' : 'Simpan'}</button>
          <button className="btn-pill btn-pill-secondary" onClick={onClose} style={{ fontSize: 11 }}>Batal</button>
        </div>
      </div>
    </div>
  );
}

function SignModal({ doc, onClose, onSigned }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const [form, setForm] = useState({ role: 'buyer', name: '' });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current; if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = '#0b1d3a';
  }, []);

  const pos = (e) => {
    const c = canvasRef.current; const r = c.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - r.top;
    return [x * (c.width / r.width), y * (c.height / r.height)];
  };
  const start = (e) => { drawing.current = true; const [x, y] = pos(e); const ctx = canvasRef.current.getContext('2d'); ctx.beginPath(); ctx.moveTo(x, y); };
  const move = (e) => { if (!drawing.current) return; e.preventDefault(); const [x, y] = pos(e); const ctx = canvasRef.current.getContext('2d'); ctx.lineTo(x, y); ctx.stroke(); };
  const end = () => { drawing.current = false; };
  const clear = () => {
    const c = canvasRef.current; const ctx = c.getContext('2d');
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, c.width, c.height);
  };

  const submit = async () => {
    if (!form.name) { alert('Nama wajib diisi'); return; }
    setBusy(true);
    try {
      const signature_image = canvasRef.current.toDataURL('image/png');
      await api.post(`/documents/${doc.id}/sign`, { ...form, signature_image });
      onSigned && onSigned();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="sign-modal" style={{ maxWidth: 600 }}>
        <h2 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Tanda Tangan: {doc.title}</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
          <div>
            <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Peran</label>
            <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} data-testid="sig-role"
              style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }}>
              <option value="buyer">Pembeli</option>
              <option value="seller">Penjual</option>
              <option value="witness">Saksi</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Nama</label>
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="sig-name"
              style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11 }} />
          </div>
        </div>
        <div style={{ marginBottom: 8 }}>
          <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Goreskan Tanda Tangan</label>
          <canvas ref={canvasRef} width={520} height={180} data-testid="sig-canvas"
            onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
            onTouchStart={start} onTouchMove={move} onTouchEnd={end}
            style={{ border: '1px dashed rgba(0,0,0,0.2)', borderRadius: 8, width: '100%', maxWidth: 520, height: 180, background: '#fff', touchAction: 'none' }} />
          <button onClick={clear} type="button" data-testid="sig-clear" style={{ fontSize: 9, padding: '3px 8px', marginTop: 4, background: 'rgba(0,0,0,0.05)', border: 'none', borderRadius: 4, cursor: 'pointer' }}>Bersihkan</button>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn-pill btn-pill-primary" onClick={submit} disabled={busy} data-testid="submit-sig" style={{ fontSize: 11 }}>{busy ? 'Menandatangani...' : 'Tanda Tangan'}</button>
          <button className="btn-pill btn-pill-secondary" onClick={onClose} style={{ fontSize: 11 }}>Batal</button>
        </div>
      </div>
    </div>
  );
}

function TemplatesModal({ templates, onClose, onChanged }) {
  const [editing, setEditing] = useState(null);
  const [content, setContent] = useState('');
  const [busy, setBusy] = useState(false);

  const open = (t) => { setEditing(t); setContent(t.content); };

  const save = async () => {
    if (!editing) return;
    setBusy(true);
    try {
      await api.put(`/document-templates/${editing.id}`, { content });
      setEditing(null); onChanged && onChanged();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="templates-modal" style={{ maxWidth: 900, maxHeight: '92vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h2 style={{ fontSize: 14, fontWeight: 800 }}>Template Dokumen</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={16} /></button>
        </div>
        {!editing ? (
          <div>
            {templates.map(t => (
              <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', borderBottom: '1px solid rgba(0,0,0,0.04)' }} data-testid={`tpl-${t.code}`}>
                <span style={{ fontSize: 10, fontWeight: 800, color: CODE_COLOR[t.code] || '#8896ab', background: `${CODE_COLOR[t.code] || '#8896ab'}15`, padding: '2px 6px', borderRadius: 4 }}>{t.code}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, fontWeight: 700 }}>{t.name}</div>
                  <div style={{ fontSize: 9, color: '#8896ab' }}>{t.description}</div>
                </div>
                <button onClick={() => open(t)} className="btn-pill btn-pill-secondary" data-testid={`edit-tpl-${t.code}`} style={{ fontSize: 10, padding: '4px 10px' }}>
                  <Edit3 size={10} style={{ display: 'inline', marginRight: 2 }} />Edit
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 4 }}>{editing.code} — {editing.name}</div>
            <p style={{ fontSize: 9, color: '#8896ab', marginBottom: 6 }}>Gunakan variabel `{'{{customer.name}}'}, `{'{{unit.label}}'}, `{'{{deal.price_idr}}'}, `{'{{deal.price_words}}'}, `{'{{today}}'}`, dll.</p>
            <textarea value={content} onChange={e => setContent(e.target.value)} data-testid="tpl-content"
              style={{ width: '100%', minHeight: 400, padding: 10, borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11, fontFamily: 'monospace' }} />
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <button className="btn-pill btn-pill-primary" onClick={save} disabled={busy} data-testid="save-tpl" style={{ fontSize: 11 }}>{busy ? 'Menyimpan...' : 'Simpan Template'}</button>
              <button className="btn-pill btn-pill-secondary" onClick={() => setEditing(null)} style={{ fontSize: 11 }}>Kembali</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
