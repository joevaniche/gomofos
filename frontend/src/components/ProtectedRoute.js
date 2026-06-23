import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import AdRail from './AdRail';
import Footer from './Footer';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A]">
        <div className="text-white text-lg">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // `relative` wrapper anchors the absolutely-positioned AdRail on xl+ so it
  // scrolls WITH the page (instead of staying fixed) and never sits on top of
  // text — page content gets `xl:pr-[200px]` to leave a clear right column.
  return (
    <div className="relative min-h-screen">
      <div className="xl:pr-[200px]">
        {children}
        <AdRail />
      </div>
      <Footer />
    </div>
  );
}

export default ProtectedRoute;
