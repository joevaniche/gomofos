import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import axios from 'axios';
import Logo from '../components/Logo';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [twofa, setTwofa] = useState(null);   // { challenge_id, expires_in }
  const [code, setCode] = useState('');
  const { login, checkAuth } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const result = await login(email, password);
    setLoading(false);
    if (result.success) {
      // Could be a normal login OR a 2FA challenge
      if (result.data?.requires_2fa) {
        setTwofa({ challenge_id: result.data.challenge_id, expires_in: result.data.expires_in });
        toast.message('Check WhatsApp for your 6-digit admin code');
      } else {
        toast.success('Login successful');
        navigate('/dashboard');
      }
    } else {
      toast.error(result.error);
    }
  };

  const handleVerify2FA = async (e) => {
    e.preventDefault();
    if (code.replace(/\D/g, '').length !== 6) { toast.error('Enter the 6-digit code'); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/auth/2fa/verify`, { challenge_id: twofa.challenge_id, code: code.replace(/\D/g, '') }, { withCredentials: true });
      await checkAuth();
      toast.success('Admin signed in');
      navigate('/dashboard');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Verification failed');
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <div className="px-6 py-6 flex justify-center">
        <Logo size="large" />
      </div>
      <div className="flex-1 flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        <div className="mb-8">
          <h1 className="text-4xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>LOGIN</h1>
          <p className="text-sm text-[#A3A3A3]">Enter your credentials to access your account</p>
        </div>

        <form onSubmit={handleSubmit} className={`space-y-6 ${twofa ? 'hidden' : ''}`} data-testid="login-form">
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">EMAIL</label>
            <input
              data-testid="login-email-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
              placeholder="your@email.com"
            />
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">PASSWORD</label>
            <input
              data-testid="login-password-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
              placeholder="••••••••"
            />
          </div>

          <button
            data-testid="login-submit-btn"
            type="submit"
            disabled={loading}
            className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50"
          >
            {loading ? 'LOGGING IN...' : 'LOGIN'}
          </button>
        </form>

        {twofa && (
          <form onSubmit={handleVerify2FA} className="space-y-6" data-testid="twofa-form">
            <div className="border border-[#FF3B30]/40 bg-[#FF3B30]/10 p-4 mb-2">
              <p className="text-sm font-bold text-[#FF3B30] mb-1">🔐 ADMIN VERIFICATION REQUIRED</p>
              <p className="text-xs text-[#A3A3A3]">We've sent a 6-digit code to the WhatsApp number on this admin account. Enter it below within 5 minutes.</p>
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">6-DIGIT CODE</label>
              <input data-testid="twofa-code-input" type="text" inputMode="numeric" maxLength={6} autoFocus
                value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white text-2xl tracking-[0.4em] text-center focus:outline-none focus:border-[#FF3B30]"
                placeholder="------" />
            </div>
            <button data-testid="twofa-verify-btn" type="submit" disabled={loading || code.length !== 6}
              className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50">
              {loading ? 'VERIFYING...' : 'VERIFY & SIGN IN'}
            </button>
            <button type="button" onClick={() => { setTwofa(null); setCode(''); }}
              data-testid="twofa-cancel-btn"
              className="w-full text-xs text-[#A3A3A3] hover:text-white">← Cancel and use a different account</button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-[#A3A3A3]">
          Don't have an account?{' '}
          <Link to="/register" className="text-[#FF3B30] hover:text-[#D62F26] font-bold" data-testid="login-register-link">
            Register
          </Link>
        </p>
      </div>
      </div>
    </div>
  );
}

export default Login;
