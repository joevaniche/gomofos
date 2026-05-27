import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const result = await login(email, password);
    setLoading(false);
    
    if (result.success) {
      toast.success('Login successful');
      navigate('/dashboard');
    } else {
      toast.error(result.error);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        <div className="mb-8">
          <h1 className="text-4xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>LOGIN</h1>
          <p className="text-sm text-[#A3A3A3]">Enter your credentials to access your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
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

        <p className="mt-6 text-center text-sm text-[#A3A3A3]">
          Don't have an account?{' '}
          <Link to="/register" className="text-[#FF3B30] hover:text-[#D62F26] font-bold" data-testid="login-register-link">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}

export default Login;