import React from 'react';
import TopNav from '../components/TopNav';
import Footer from '../components/Footer';
import { useAuth } from '../contexts/AuthContext';

// Generic placeholder for the 6 footer pages. Each child page just supplies a
// tag, title, and short copy — we'll flesh them out one by one later.
//
// Renders TopNav only when the user is signed in (these pages are public).
export default function StaticPage({ tag, title, children, testId }) {
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-[#0A0A0A]/60 text-white flex flex-col">
      {user && <TopNav />}
      <main className="flex-1 max-w-3xl mx-auto px-6 py-16" data-testid={testId}>
        <p className="text-xs font-bold tracking-[0.3em] text-[#FF3B30] mb-2">{tag}</p>
        <h1 className="text-5xl font-black mb-6 leading-tight">{title}</h1>
        <div className="prose prose-invert text-[#D4D4D4] text-base leading-relaxed space-y-4">
          {children}
        </div>
        <p className="mt-12 text-xs text-[#525252]">
          This page is a placeholder while we draft the final copy. Want to help shape it?
          Reach out via <a href="/contact" className="text-[#FF3B30] hover:underline">CONTACT</a>.
        </p>
      </main>
      <Footer />
    </div>
  );
}
