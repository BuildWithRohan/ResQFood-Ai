import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { api } from '../services/api';

export default function NGODashboard({ user, onLogout }) {
  const [surplus, setSurplus] = useState([]);
  const [requests, setRequests] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('available');
  const navigate = useNavigate();

  // Request form
  const [requestForm, setRequestForm] = useState(null);
  const [reqQty, setReqQty] = useState('');
  const [reqUrgency, setReqUrgency] = useState('high');
  const [reqNotes, setReqNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [s, r, d] = await Promise.all([
        api.surplus.list(),
        api.requests.list(),
        api.deliveries.list(),
      ]);
      setSurplus(s.filter(i => ['eligible', 'urgent', 'allocated'].includes(i.status)));
      setRequests(r);
      setDeliveries(d);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const submitRequest = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await api.requests.create({
        surplus_id: requestForm.id,
        requested_quantity: parseInt(reqQty),
        urgency: reqUrgency,
        notes: reqNotes,
      });
      setRequestForm(null);
      await loadData();
    } catch (e) { setError(e.message); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="app-layout">
      <Sidebar user={user} onLogout={onLogout} />
      <div className="main-content">
        <div className="page-header">
          <h1>NGO Dashboard</h1>
          <p>Browse available food, submit requests, and track deliveries</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="flex gap-1 mb-2">
          {['available', 'requests', 'deliveries'].map(t => (
            <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-outline'} btn-sm`}
                    onClick={() => setTab(t)}>
              {t === 'available' ? '🍽 Available Food' : t === 'requests' ? '📋 My Requests' : '🚚 Deliveries'}
            </button>
          ))}
        </div>

        {loading ? <div className="loading"><div className="spinner" />Loading...</div> : (
          <>
            {/* ── Available Food ─────────────────────────────── */}
            {tab === 'available' && (
              <div className="section">
                {surplus.length === 0 ? (
                  <div className="empty-state">
                    <div className="icon">🍽</div>
                    <p>No surplus food available right now</p>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
                    {surplus.map(s => (
                      <div key={s.id} className="card">
                        <div className="flex-between mb-1">
                          <h3 style={{ fontWeight: 700, fontSize: '1rem' }}>{s.food_name}</h3>
                          <StatusBadge status={s.status} />
                        </div>
                        <div className="grid-2" style={{ gap: '0.5rem', marginBottom: '0.75rem' }}>
                          <div><span className="text-xs text-muted">Quantity</span><br/>
                            <strong>{s.remaining_quantity || s.quantity} {s.unit}</strong></div>
                          <div><span className="text-xs text-muted">Weight</span><br/>
                            <strong>{s.estimated_weight_kg ? `${s.estimated_weight_kg} kg` : '–'}</strong></div>
                          <div><span className="text-xs text-muted">Remaining Time</span><br/>
                            <Countdown minutes={s.remaining_minutes} /></div>
                          <div><span className="text-xs text-muted">Kitchen</span><br/>
                            <span className="text-sm">{s.kitchen_name || 'Unknown'}</span></div>
                        </div>
                        {s.description && <p className="text-xs text-muted mb-1">{s.description}</p>}
                        <div className="flex gap-1">
                          <button className="btn btn-success btn-sm" onClick={() => { setRequestForm(s); setReqQty(''); }}>
                            📋 Request Food
                          </button>
                          {s.status === 'allocated' && (
                            <button className="btn btn-outline btn-sm" onClick={() => navigate(`/allocation/${s.id}`)}>
                              🔍 View Allocation
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── Request Form Modal ────────────────────────── */}
            {requestForm && (
              <div style={{
                position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
              }} onClick={() => setRequestForm(null)}>
                <div className="card" style={{ width: 400, maxWidth: '90vw' }} onClick={e => e.stopPropagation()}>
                  <h2 style={{ marginBottom: '1rem' }}>Request: {requestForm.food_name}</h2>
                  <p className="text-sm text-muted mb-2">
                    Available: {requestForm.remaining_quantity || requestForm.quantity} {requestForm.unit} ·
                    Remaining: <Countdown minutes={requestForm.remaining_minutes} />
                  </p>
                  <form onSubmit={submitRequest}>
                    <div className="form-group">
                      <label>Quantity Needed *</label>
                      <input type="number" value={reqQty} onChange={e => setReqQty(e.target.value)}
                             placeholder="e.g. 15" required min="1" />
                    </div>
                    <div className="form-group">
                      <label>Urgency *</label>
                      <select value={reqUrgency} onChange={e => setReqUrgency(e.target.value)}>
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="very_high">Very High</option>
                        <option value="critical">Critical</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Notes</label>
                      <textarea value={reqNotes} onChange={e => setReqNotes(e.target.value)}
                                placeholder="Reason for request" rows={2} />
                    </div>
                    <div className="flex gap-1">
                      <button className="btn btn-success" type="submit" disabled={submitting}>
                        {submitting ? 'Submitting...' : 'Submit Request'}
                      </button>
                      <button className="btn btn-outline" type="button" onClick={() => setRequestForm(null)}>Cancel</button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* ── My Requests ───────────────────────────────── */}
            {tab === 'requests' && (
              <div className="section">
                {requests.length === 0 ? (
                  <div className="empty-state"><div className="icon">📋</div><p>No requests submitted</p></div>
                ) : (
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Food</th><th>Requested</th><th>Allocated</th>
                          <th>Urgency</th><th>Status</th><th>Remaining</th>
                        </tr>
                      </thead>
                      <tbody>
                        {requests.map(r => (
                          <tr key={r.id}>
                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.food_name || 'Food'}</td>
                            <td>{r.requested_quantity}</td>
                            <td style={{ fontWeight: 700, color: r.allocated_quantity > 0 ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                              {r.allocated_quantity}
                            </td>
                            <td><UrgencyBadge urgency={r.urgency} /></td>
                            <td><StatusBadge status={r.status} /></td>
                            <td><Countdown minutes={r.remaining_minutes} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* ── Deliveries ────────────────────────────────── */}
            {tab === 'deliveries' && (
              <div className="section">
                {deliveries.length === 0 ? (
                  <div className="empty-state"><div className="icon">🚚</div><p>No deliveries yet</p></div>
                ) : deliveries.map(d => (
                  <div key={d.id} className="card mb-2">
                    <div className="flex-between mb-1">
                      <h3>Delivery #{d.id}</h3>
                      <StatusBadge status={d.status} />
                    </div>
                    <p className="text-sm text-muted mb-1">
                      {d.total_meals} meals · {d.total_stops} stops · Est. {d.estimated_duration_min} min
                    </p>
                    {d.stops?.map(stop => (
                      <div key={stop.id} className="card" style={{ marginTop: '0.5rem', background: 'var(--bg-secondary)' }}>
                        <div className="flex-between">
                          <div>
                            <strong>{stop.ngo_name}</strong>
                            <span className="text-xs text-muted"> · {stop.quantity} meals</span>
                          </div>
                          <StatusBadge status={stop.status} />
                        </div>
                        {stop.otp_code && (
                          <div style={{
                            marginTop: '0.5rem', padding: '0.5rem', background: 'var(--accent-green-dim)',
                            borderRadius: 'var(--radius-sm)', textAlign: 'center',
                          }}>
                            <span className="text-xs text-muted">Your OTP:</span>
                            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-green)', letterSpacing: '4px' }}>
                              {stop.otp_code}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    eligible: 'green', urgent: 'orange', allocated: 'blue', expired: 'red',
    pending: 'orange', fulfilled: 'green', partially_fulfilled: 'cyan',
    rejected: 'red', planned: 'purple', assigned: 'blue',
    pickup_in_progress: 'orange', in_transit: 'cyan', delivered: 'green',
    arrived: 'blue', failed: 'red',
  };
  return <span className={`badge ${map[status] || 'gray'}`}>{status?.replace(/_/g, ' ')}</span>;
}

function UrgencyBadge({ urgency }) {
  const map = { low: 'gray', medium: 'blue', high: 'orange', very_high: 'red', critical: 'red' };
  return <span className={`badge ${map[urgency] || 'gray'}`}>{urgency?.replace(/_/g, ' ')}</span>;
}

function Countdown({ minutes }) {
  if (minutes === null || minutes === undefined) return <span className="text-muted">—</span>;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  const cls = minutes < 30 ? 'urgent' : minutes < 60 ? 'warning' : 'ok';
  return <span className={`countdown ${cls}`}>{h}h {m}m</span>;
}
