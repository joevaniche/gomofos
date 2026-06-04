import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

function Register() {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const result = await register(email, password, username);
    setLoading(false);
    
    if (result.success) {
      toast.success('Registration successful');
      navigate('/dashboard');
    } else {
      toast.error(result.error);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        <div className="mb-8">
          <h1 className="text-4xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>REGISTER</h1>
          <p className="text-sm text-[#A3A3A3]">Create your account and get <span className="text-[#22C55E] font-bold">1,000 free credits</span> to start</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6" data-testid="register-form">
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">USERNAME</label>
            <input
              data-testid="register-username-input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
              placeholder="gamer123"
            />
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">EMAIL</label>
            <input
              data-testid="register-email-input"
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
              data-testid="register-password-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
              placeholder="••••••••"
            />
          </div>

          <button
            data-testid="register-submit-btn"
            type="submit"
            disabled={loading}
            className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50"
          >
            {loading ? 'CREATING ACCOUNT...' : 'CREATE ACCOUNT'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[#A3A3A3]">
          Already have an account?{' '}
          <Link to="/login" className="text-[#FF3B30] hover:text-[#D62F26] font-bold" data-testid="register-login-link">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}

export default Register;
