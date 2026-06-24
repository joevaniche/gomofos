import React from 'react';
import StaticPage from '../components/StaticPage';

// Source: /artifacts/Privacy Policy.docx (Last Updated 24 June 2026)
export default function Privacy() {
  return (
    <StaticPage tag="LEGAL · LAST UPDATED 24 JUNE 2026" title="Privacy Policy" testId="privacy-page">
      <p>Gomofos Pty Ltd (“we”, “us”, or “our”) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, store, and disclose your personal information when you use our website, platform, and related services. By accessing or using our platform, you agree to the practices described in this Privacy Policy.</p>

      <Section n="1" title="Information We Collect">
        <p>We collect the following categories of information:</p>
        <SubSection n="1.1" title="Information You Provide Directly">
          <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
            <li>Account registration details (username, email address, password)</li>
            <li>Profile information (display name, avatar, gaming IDs)</li>
            <li>Match results, uploaded screenshots, and gameplay evidence</li>
            <li>Referral information (e.g., usernames of people you refer)</li>
            <li>Communications sent to our support team</li>
          </ul>
        </SubSection>
        <SubSection n="1.2" title="Information Collected Automatically">
          <p>When you use our platform, we automatically collect:</p>
          <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
            <li>IP address and device identifiers</li>
            <li>Browser type, operating system, and device information</li>
            <li>Usage data (pages visited, time spent, interactions)</li>
            <li>Log data related to matches, challenges, and platform activity</li>
          </ul>
        </SubSection>
        <SubSection n="1.3" title="Optional Identity Verification">
          <p>If required to prevent fraud or duplicate accounts, we may request:</p>
          <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
            <li>Government-issued ID</li>
            <li>Proof of age</li>
            <li>Proof of residency</li>
          </ul>
          <p>Identity verification is only requested when necessary for platform integrity.</p>
        </SubSection>
      </Section>

      <Section n="2" title="How We Use Your Information">
        <p>We use your information to:</p>
        <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
          <li>Create and manage your account</li>
          <li>Facilitate matchmaking, challenges, and gameplay features</li>
          <li>Track milestones, wins, and referral-based credit rewards</li>
          <li>Detect fraud, duplicate accounts, cheating, or abuse</li>
          <li>Improve platform performance and user experience</li>
          <li>Communicate updates, announcements, and support responses</li>
          <li>Enforce our Terms and Conditions</li>
        </ul>
        <p className="mt-3"><strong className="text-white">We do not sell your personal information.</strong></p>
      </Section>

      <Section n="3" title="Play Credits and Non-Monetary Data">
        <p>Our platform uses <strong className="text-white">non-monetary play credits</strong> earned through referrals and gameplay achievements. We <strong className="text-white">do not</strong> collect or store:</p>
        <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
          <li>Payment card details</li>
          <li>Bank account information</li>
          <li>Cryptocurrency wallet addresses</li>
        </ul>
        <p>Because no financial transactions occur, no financial data is ever processed.</p>
      </Section>

      <Section n="4" title="Cookies and Tracking Technologies">
        <p>We use cookies and similar technologies to:</p>
        <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
          <li>Maintain login sessions</li>
          <li>Personalise your experience</li>
          <li>Analyse platform usage</li>
          <li>Improve website performance</li>
        </ul>
        <p>You may disable cookies in your browser settings, but some features may not function correctly.</p>
      </Section>

      <Section n="5" title="Sharing Your Information">
        <p>We may share your information with:</p>
        <SubSection n="5.1" title="Service Providers">
          <p>Trusted third-party providers who assist with:</p>
          <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
            <li>Hosting and infrastructure</li>
            <li>Analytics</li>
            <li>Security and fraud prevention</li>
            <li>Email delivery</li>
          </ul>
          <p>These providers are bound by confidentiality obligations.</p>
        </SubSection>
        <SubSection n="5.2" title="Legal and Safety Requirements">
          <p>We may disclose information if required by:</p>
          <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
            <li>Law enforcement</li>
            <li>Court orders</li>
            <li>Regulatory authorities</li>
          </ul>
          <p>Or when necessary to:</p>
          <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
            <li>Protect platform integrity</li>
            <li>Prevent fraud or cyber abuse</li>
            <li>Enforce our Terms and Conditions</li>
          </ul>
        </SubSection>
        <SubSection n="5.3" title="No Sale of Personal Data">
          <p>We <strong className="text-white">do not</strong> sell, rent, or trade your personal information to third parties.</p>
        </SubSection>
      </Section>

      <Section n="6" title="Data Storage and Security">
        <p>We implement reasonable technical and organisational measures to protect your data, including:</p>
        <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
          <li>Encrypted data transmission (HTTPS)</li>
          <li>Secure password hashing</li>
          <li>Access controls and audit logs</li>
          <li>Regular security reviews</li>
        </ul>
        <p>However, no online service can guarantee absolute security.</p>
      </Section>

      <Section n="7" title="International Data Transfers">
        <p>Our servers or service providers may be located outside Australia. Where data is transferred internationally, we ensure appropriate safeguards are in place consistent with the Australian Privacy Act 1988 (Cth).</p>
      </Section>

      <Section n="8" title="Children’s Privacy">
        <p>Our platform is intended for users <strong className="text-white">13 years and older</strong>. We do not knowingly collect personal information from children under 13. If you believe a child has created an account, contact us immediately.</p>
      </Section>

      <Section n="9" title="Accessing and Updating Your Information">
        <p>You may request to:</p>
        <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
          <li>Access the personal information we hold about you</li>
          <li>Correct inaccurate or outdated information</li>
          <li>Delete your account</li>
        </ul>
        <p>Requests can be made via our support contact below.</p>
      </Section>

      <Section n="10" title="Data Retention">
        <p>We retain personal information only as long as necessary for:</p>
        <ul className="list-disc pl-5 space-y-1 text-[#D4D4D4]">
          <li>Account operation</li>
          <li>Legal compliance</li>
          <li>Fraud prevention</li>
          <li>Platform integrity</li>
        </ul>
        <p>When no longer required, data is securely deleted.</p>
      </Section>

      <Section n="11" title="Links to Third Party Sites">
        <p>Our platform may contain links to external websites. We are not responsible for the privacy practices of third-party sites.</p>
      </Section>

      <Section n="12" title="Changes to This Privacy Policy">
        <p>We may update this Privacy Policy from time to time. The “Last Updated” date at the top of this page reflects the most recent version. Continued use of the platform constitutes acceptance of any changes.</p>
      </Section>

      <Section n="13" title="Contact Us">
        <p>For privacy inquiries, data access requests, or complaints, contact:</p>
        <p className="text-[#D4D4D4]"><strong className="text-white">Gomofos Pty Ltd</strong></p>
        <p>Email: <a href="mailto:helpdesk@gomofos.com" className="text-[#FF3B30] hover:underline">helpdesk@gomofos.com</a></p>
        <p>We will respond to all privacy related requests within a reasonable timeframe.</p>
      </Section>
    </StaticPage>
  );
}

function Section({ n, title, children }) {
  return (
    <section className="mt-8">
      <h2 className="text-2xl font-black tracking-tight mb-3 text-white">{n}. {title}</h2>
      <div className="space-y-2">{children}</div>
    </section>
  );
}
function SubSection({ n, title, children }) {
  return (
    <div className="mt-4 ml-2 border-l border-[#262626] pl-4">
      <h3 className="text-base font-bold mb-2 text-white">{n} · {title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}
