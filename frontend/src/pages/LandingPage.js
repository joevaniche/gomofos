import React, { useEffect, useRef } from 'react';
import Logo from '../components/Logo';
import { useNavigate } from 'react-router-dom';
import { Trophy, Users, Shield, Lightning } from '@phosphor-icons/react';
import { useAuth } from '../contexts/AuthContext';

function LandingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const taglineRef = useRef(null);
  const stakeRef = useRef(null);
  const competeRef = useRef(null);
  const dominateRef = useRef(null);
  const descRef = useRef(null);
  const ctaRef = useRef(null);

  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  useEffect(() => {
    const reveal = (el) => {
      if (!el) return;
      el.style.opacity = '1';
      el.style.transform = 'translateY(0) scale(1)';
    };
    const schedule = [
      [100, taglineRef],
      [600, stakeRef],
      [1600, competeRef],
      [2600, dominateRef],
      [3400, descRef],
      [3400, ctaRef],
    ];
    const timers = schedule.map(([delay, ref]) => setTimeout(() => reveal(ref.current), delay));
    return () => timers.forEach(clearTimeout);
  }, []);

  const hidden = {
    opacity: 0,
    transform: 'translateY(20px) scale(0.95)',
    transition: 'opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1), transform 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
  };

  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="absolute top-0 left-0 right-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-start justify-between">
          <Logo size="xlarge" />
          <div className="flex gap-4 pt-4">
            <button data-testid="nav-login-btn" onClick={() => navigate('/login')} className="px-6 py-2 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">
              LOGIN
            </button>
            <button data-testid="nav-register-btn" onClick={() => navigate('/register')} className="px-6 py-2 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors">
              GET STARTED
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="relative z-10 max-w-7xl mx-auto px-6 pt-56 pb-32">
          <div className="max-w-3xl">
            <p ref={taglineRef} data-testid="hero-tagline" className="text-xs font-bold uppercase tracking-[0.2em] text-[#FF3B30] mb-4" style={hidden}>GAME ON MOFOS!</p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl tracking-tighter leading-none font-black text-white mb-6 flex flex-wrap gap-x-4" style={{fontFamily: 'Chivo'}}>
              <span ref={stakeRef} data-testid="hero-word-stake" className="inline-block" style={hidden}>STAKE.</span>
              <span ref={competeRef} data-testid="hero-word-compete" className="inline-block" style={hidden}>COMPETE.</span>
              <span ref={dominateRef} data-testid="hero-word-dominate" className="inline-block" style={hidden}>DOMINATE.</span>
            </h1>
            <p ref={descRef} className="text-sm sm:text-base leading-relaxed tracking-wide text-[#A3A3A3] mb-8 max-w-2xl" style={hidden}>
              Join the ultimate esports competition platform. Organize tournaments, stake credits, and prove your skills across FIFA, NBA, Call of Duty, and more. Winner takes the pot.
            </p>
            <div ref={ctaRef} style={hidden}>
              <button data-testid="hero-get-started-btn" onClick={() => navigate('/register')} className="px-8 py-4 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors text-lg">
                START COMPETING
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-[#141414]/70 backdrop-blur-sm border-y border-[#262626]">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <div className="border border-[#262626] p-6 bg-[#0A0A0A]/80 backdrop-blur-sm" data-testid="feature-secure-escrow">
              <Shield size={40} weight="duotone" className="text-[#FF3B30] mb-4" />
              <h3 className="text-xl font-bold mb-2 tracking-tight" style={{fontFamily: 'Chivo'}}>SECURE ESCROW</h3>
              <p className="text-sm text-[#A3A3A3] leading-relaxed">Platform holds stakes in escrow. Winner gets the pot automatically.</p>
            </div>

            <div className="border border-[#262626] p-6 bg-[#0A0A0A]/80 backdrop-blur-sm" data-testid="feature-all-games">
              <Lightning size={40} weight="duotone" className="text-[#007AFF] mb-4" />
              <h3 className="text-xl font-bold mb-2 tracking-tight" style={{fontFamily: 'Chivo'}}>ALL GAMES</h3>
              <p className="text-sm text-[#A3A3A3] leading-relaxed">FIFA, NBA, COD, and more. Any game, any platform.</p>
            </div>

            <div className="border border-[#262626] p-6 bg-[#0A0A0A]/80 backdrop-blur-sm" data-testid="feature-live-chat">
              <Users size={40} weight="duotone" className="text-[#22C55E] mb-4" />
              <h3 className="text-xl font-bold mb-2 tracking-tight" style={{fontFamily: 'Chivo'}}>LIVE CHAT</h3>
              <p className="text-sm text-[#A3A3A3] leading-relaxed">Communicate with opponents in real-time during matches.</p>
            </div>

            <div className="border border-[#262626] p-6 bg-[#0A0A0A]/80 backdrop-blur-sm" data-testid="feature-leaderboard">
              <Trophy size={40} weight="duotone" className="text-[#F59E0B] mb-4" />
              <h3 className="text-xl font-bold mb-2 tracking-tight" style={{fontFamily: 'Chivo'}}>LEADERBOARDS</h3>
              <p className="text-sm text-[#A3A3A3] leading-relaxed">Climb the ranks. Prove you're the best.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 border-t border-[#262626]">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl lg:text-4xl tracking-tight leading-tight font-bold mb-6" style={{fontFamily: 'Chivo'}}>
            READY TO COMPETE?
          </h2>
          <p className="text-sm sm:text-base leading-relaxed tracking-wide text-[#A3A3A3] mb-8">
            Join thousands of gamers staking and winning on the platform.
          </p>
          <button data-testid="cta-join-now-btn" onClick={() => navigate('/register')} className="px-8 py-4 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors text-lg">
            JOIN NOW
          </button>
        </div>
      </section>
    </div>
  );
}

export default LandingPage;
