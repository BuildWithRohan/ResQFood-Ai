import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import KitchenDashboard from './pages/KitchenDashboard';
import NGODashboard from './pages/NGODashboard';
import DriverDashboard from './pages/DriverDashboard';
import AllocationPage from './pages/AllocationPage';
import './index.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('resqfood_user');
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch { localStorage.clear(); }
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData, token) => {
    localStorage.setItem('resqfood_token', token);
    localStorage.setItem('resqfood_user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.clear();
    setUser(null);
  };

  if (loading) return <div className="loading"><div className="spinner" />Loading...</div>;

  if (!user) return <Login onLogin={handleLogin} />;

  const roleHome = `/${user.role}`;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin" element={
          user.role === 'admin' ? <AdminDashboard user={user} onLogout={handleLogout} /> : <Navigate to={roleHome} />
        } />
        <Route path="/kitchen" element={
          user.role === 'kitchen' ? <KitchenDashboard user={user} onLogout={handleLogout} /> : <Navigate to={roleHome} />
        } />
        <Route path="/ngo" element={
          user.role === 'ngo' ? <NGODashboard user={user} onLogout={handleLogout} /> : <Navigate to={roleHome} />
        } />
        <Route path="/driver" element={
          user.role === 'driver' ? <DriverDashboard user={user} onLogout={handleLogout} /> : <Navigate to={roleHome} />
        } />
        <Route path="/allocation/:surplusId" element={
          <AllocationPage user={user} onLogout={handleLogout} />
        } />
        <Route path="*" element={<Navigate to={roleHome} />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
