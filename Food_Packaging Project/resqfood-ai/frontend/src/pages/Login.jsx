import { useState } from 'react';
import { api } from '../services/api';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.auth.login(email, password);
      onLogin(res.user, res.access_token);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = (em, pw) => { setEmail(em); setPassword(pw); };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>ResQFood AI</h1>
        <p className="tagline">Predict · Prevent · Allocate · Rescue</p>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                   placeholder="Enter your email" required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                   placeholder="Enter password" required />
          </div>
          <button className="btn btn-primary btn-lg" style={{ width: '100%', marginTop: '0.5rem' }}
                  disabled={loading} type="submit">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
          <p className="text-xs text-muted" style={{ marginBottom: '0.5rem', textAlign: 'center' }}>
            DEMO ACCOUNTS
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
            {[
              { label: 'Admin', email: 'admin@resqfood.ai', pw: 'admin123', color: 'var(--accent-purple)' },
              { label: 'Kitchen', email: 'kitchen@abccollege.edu', pw: 'kitchen123', color: 'var(--accent-green)' },
              { label: 'NGO A', email: 'ngo_a@feedindia.org', pw: 'ngoa123', color: 'var(--accent-blue)' },
              { label: 'NGO B', email: 'ngo_b@mealshare.org', pw: 'ngob123', color: 'var(--accent-cyan)' },
              { label: 'NGO C', email: 'ngo_c@foodrescue.in', pw: 'ngoc123', color: 'var(--accent-orange)' },
              { label: 'Driver', email: 'driver@resqfood.ai', pw: 'driver123', color: 'var(--accent-red)' },
            ].map((a) => (
              <button key={a.email} className="btn btn-outline btn-sm"
                      onClick={() => quickLogin(a.email, a.pw)}
                      style={{ borderColor: a.color, color: a.color, fontSize: '0.68rem' }}>
                {a.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
