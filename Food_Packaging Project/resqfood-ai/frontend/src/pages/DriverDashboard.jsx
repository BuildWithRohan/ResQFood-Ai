import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../services/api';

export default function DriverDashboard({ user, onLogout }) {
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [otpInputs, setOtpInputs] = useState({});
  const [verifying, setVerifying] = useState({});

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const d = await api.deliveries.list();
      setDeliveries(d);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const updateDeliveryStatus = async (deliveryId, status) => {
    try {
      await api.deliveries.update(deliveryId, { status });
      await loadData();
    } catch (e) { setError(e.message); }
  };

  const updateStopStatus = async (deliveryId, stopId, status) => {
    try {
      await api.deliveries.updateStop(deliveryId, stopId, { status });
      await loadData();
    } catch (e) { setError(e.message); }
  };

  const verifyOtp = async (deliveryId, stopId) => {
    const otp = otpInputs[stopId];
    if (!otp || otp.length !== 6) { setError('Please enter a 6-digit OTP'); return; }
    setVerifying(v => ({ ...v, [stopId]: true }));
    try {
      await api.deliveries.verifyOtp(deliveryId, stopId, otp);
      setOtpInputs(o => ({ ...o, [stopId]: '' }));
      await loadData();
    } catch (e) { setError(e.message); }
    finally { setVerifying(v => ({ ...v, [stopId]: false })); }
  };

  return (
    <div className="app-layout">
      <Sidebar user={user} onLogout={onLogout} />
      <div className="main-content">
        <div className="page-header">
          <h1>Driver Dashboard</h1>
          <p>Manage pickups, deliveries, and OTP verifications</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {loading ? <div className="loading"><div className="spinner" />Loading...</div> : (
          <>
            {deliveries.length === 0 ? (
              <div className="empty-state">
                <div className="icon">🚗</div>
                <p>No deliveries assigned yet</p>
              </div>
            ) : deliveries.map(delivery => (
              <div key={delivery.id} className="card mb-2">
                {/* Delivery Header */}
                <div className="flex-between mb-1">
                  <div>
                    <h2 style={{ fontSize: '1.1rem' }}>Delivery #{delivery.id}</h2>
                    <p className="text-sm text-muted">
                      {delivery.total_meals} meals · {delivery.total_weight_kg} kg · {delivery.total_stops} stops
                    </p>
                  </div>
                  <StatusBadge status={delivery.status} />
                </div>

                {/* Delivery Actions */}
                <div className="flex gap-1 mb-2">
                  {delivery.status === 'planned' && (
                    <button className="btn btn-primary btn-sm"
                            onClick={() => updateDeliveryStatus(delivery.id, 'pickup_in_progress')}>
                      🚗 Start Pickup
                    </button>
                  )}
                  {delivery.status === 'pickup_in_progress' && (
                    <button className="btn btn-success btn-sm"
                            onClick={() => updateDeliveryStatus(delivery.id, 'in_transit')}>
                      📦 Pickup Complete — Start Delivery
                    </button>
                  )}
                </div>

                {/* Pickup Location */}
                <div className="card" style={{ background: 'var(--bg-secondary)', marginBottom: '1rem' }}>
                  <div className="flex gap-1" style={{ alignItems: 'center' }}>
                    <span style={{ fontSize: '1.5rem' }}>🍳</span>
                    <div>
                      <div className="text-xs text-muted">PICKUP LOCATION</div>
                      <div style={{ fontWeight: 600 }}>{delivery.pickup_location || 'Kitchen'}</div>
                    </div>
                  </div>
                </div>

                {/* Delivery Timeline */}
                <div className="section-title">📍 Delivery Route</div>
                <div className="timeline">
                  {delivery.stops?.map((stop, idx) => (
                    <div key={stop.id} className={`timeline-item ${stop.status === 'delivered' ? 'completed' : stop.status === 'arrived' ? 'active' : ''}`}>
                      <div className="card" style={{ background: 'var(--bg-secondary)' }}>
                        <div className="flex-between mb-1">
                          <div>
                            <span className="text-xs text-muted">STOP {stop.sequence_order}</span>
                            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>{stop.ngo_name}</h3>
                          </div>
                          <StatusBadge status={stop.status} />
                        </div>

                        <div className="grid-2" style={{ gap: '0.5rem', marginBottom: '0.75rem' }}>
                          <div>
                            <span className="text-xs text-muted">Quantity</span><br/>
                            <strong>{stop.quantity} meals</strong>
                          </div>
                          <div>
                            <span className="text-xs text-muted">Priority</span><br/>
                            <UrgencyBadge urgency={stop.priority} />
                          </div>
                          <div>
                            <span className="text-xs text-muted">Address</span><br/>
                            <span className="text-sm">{stop.address || '—'}</span>
                          </div>
                          <div>
                            <span className="text-xs text-muted">ETA</span><br/>
                            <span className="text-sm">
                              {stop.estimated_arrival ? new Date(stop.estimated_arrival).toLocaleTimeString() : '—'}
                            </span>
                          </div>
                        </div>

                        {/* Stop Actions */}
                        {stop.status === 'pending' && delivery.status === 'in_transit' && (
                          <button className="btn btn-warning btn-sm"
                                  onClick={() => updateStopStatus(delivery.id, stop.id, 'arrived')}>
                            📍 Mark Arrived
                          </button>
                        )}

                        {stop.status === 'arrived' && (
                          <div style={{
                            background: 'var(--bg-input)', border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-sm)', padding: '1rem', marginTop: '0.5rem',
                          }}>
                            <div className="text-xs text-muted mb-1">ENTER OTP FROM RECIPIENT</div>
                            <div className="flex gap-1">
                              <input
                                type="text" maxLength={6} placeholder="000000"
                                value={otpInputs[stop.id] || ''}
                                onChange={e => setOtpInputs(o => ({ ...o, [stop.id]: e.target.value }))}
                                style={{
                                  width: '120px', textAlign: 'center', fontSize: '1.2rem',
                                  fontWeight: 700, letterSpacing: '4px',
                                  background: 'var(--bg-card)', border: '1px solid var(--border)',
                                  borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
                                  padding: '0.5rem',
                                }}
                              />
                              <button className="btn btn-success btn-sm"
                                      onClick={() => verifyOtp(delivery.id, stop.id)}
                                      disabled={verifying[stop.id]}>
                                {verifying[stop.id] ? '⏳' : '✅ Verify OTP'}
                              </button>
                            </div>
                          </div>
                        )}

                        {stop.status === 'delivered' && (
                          <div style={{
                            background: 'var(--accent-green-dim)', borderRadius: 'var(--radius-sm)',
                            padding: '0.75rem', marginTop: '0.5rem', textAlign: 'center',
                          }}>
                            <span style={{ color: 'var(--accent-green)', fontWeight: 700 }}>
                              ✅ Delivered Successfully
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Duration info */}
                {delivery.estimated_duration_min && (
                  <p className="text-sm text-muted mt-1">
                    Estimated total duration: {delivery.estimated_duration_min} minutes
                  </p>
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    planned: 'purple', assigned: 'blue', pickup_in_progress: 'orange',
    in_transit: 'cyan', arrived: 'blue', delivered: 'green', failed: 'red',
    pending: 'gray',
  };
  return <span className={`badge ${map[status] || 'gray'}`}>{status?.replace(/_/g, ' ')}</span>;
}

function UrgencyBadge({ urgency }) {
  const map = { low: 'gray', medium: 'blue', high: 'orange', very_high: 'red', critical: 'red' };
  return <span className={`badge ${map[urgency] || 'gray'}`}>{urgency?.replace(/_/g, ' ')}</span>;
}
