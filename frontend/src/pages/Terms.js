import React from 'react';
import StaticPage from '../components/StaticPage';

// Source: /artifacts/Terms of Use Clean.docx (Last Updated 24 June 2026)
// Long-form copy supplied by the platform owner — kept in plain JSX
// so we can style sections later without re-fetching anything.
export default function Terms() {
  return (
    <StaticPage tag="LEGAL · LAST UPDATED 24 JUNE 2026" title="Terms and Conditions of Use" testId="terms-page">
      <p className="italic text-[#A3A3A3]">For a non-monetary, play-credit gaming challenge platform.</p>
      <p>Welcome to the website operated by Gomofos Pty Ltd (“we”, “us”, or “our”).</p>

      <Section n="1" title="Accepting These Terms">
        <Item k="Legally Binding Agreement">By creating an account or using our platform, you agree to be bound by these Terms and Conditions.</Item>
        <Item k="Immediate Termination">If you do not agree to every clause in this document, you must stop using our website and services immediately.</Item>
        <Item k="Jurisdiction">These terms are governed by the laws of New South Wales (NSW), Australia.</Item>
      </Section>

      <Section n="2" title="Eligibility and Account Management">
        <Item k="Age Requirement">You must be at least 13 years old to register an account.</Item>
        <Item k="Location Restrictions">You must not access this website from any jurisdiction where online competitive gaming platforms are prohibited by law.</Item>
        <Item k="Account Security">You are solely responsible for maintaining the confidentiality of your login credentials and for all activities under your account.</Item>
        <Item k="Identity Verification">We may request identity verification to prevent fraud, duplicate accounts, or abuse of referral systems.</Item>
      </Section>

      <Section n="3" title="Earning and Using Play Credits">
        <Item k="No Monetary Value">Play credits on our platform have no real-world monetary value. They cannot be purchased, sold, traded, withdrawn, or exchanged for fiat currency or cryptocurrency.</Item>
        <Item k="Earning Credits">Credits are earned exclusively through:
          <ul className="list-disc pl-5 mt-1 text-[#A3A3A3]">
            <li>Referring new users who successfully register</li>
            <li>Achieving gameplay milestones (e.g., number of wins, streaks, participation)</li>
            <li>Completing platform challenges or seasonal objectives</li>
          </ul>
        </Item>
        <Item k="Non Transferable">Credits cannot be transferred between users or moved outside the platform.</Item>
        <Item k="No Refunds or Compensation">Because credits cannot be purchased, no refunds or compensation apply under any circumstances.</Item>
        <Item k="No Interest">Credit balances do not earn interest and are not protected by any financial guarantee.</Item>
      </Section>

      <Section n="4" title="Matchmaking and Challenge Rules">
        <Item k="Supported Platforms">We facilitate matchmaking for video games played across major consoles and PC.</Item>
        <Item k="Skill Based Only">All matches are skill-based. The platform does not offer gambling, games of chance, or wagering of real-world value.</Item>
        <Item k="Challenge Participation">Players may allocate play credits to challenges or matches as part of the platform’s progression and ranking system.</Item>
        <Item k="Locked Credits">Once a match begins, any credits allocated to that match are locked until a winner is determined.</Item>
      </Section>

      <Section n="5" title="Match Integrity and Fair Play">
        <Item k="Cheating Prohibition">Using hacks, aimbots, exploits, modified game files, or third-party tools to gain an unfair advantage is strictly banned.</Item>
        <Item k="Smurfing and Boosting">Creating alternate accounts or manipulating match outcomes to gain credits or milestones is forbidden.</Item>
        <Item k="Honest Reporting">Players must submit accurate match results and valid, unaltered evidence (screenshots or video captures) when required.</Item>
        <Item k="Collusion">Match-fixing, intentional losing, or coordinating outcomes with opponents is strictly prohibited and may result in permanent account termination.</Item>
      </Section>

      <Section n="6" title="Dispute Resolution">
        <Item k="Final Authority">In the event of conflicting match reports, our moderation team will review all submitted evidence.</Item>
        <Item k="Binding Decisions">Our ruling regarding match outcomes, credit adjustments, or voided matches is final and non-appealable.</Item>
        <Item k="Technical Disconnections">We are not responsible for lost progress or credits resulting from internet dropouts, hardware failures, console updates, or external game server issues.</Item>
      </Section>

      <Section n="7" title="Indemnity and Limitation of Liability">
        <Item k="As-Is Basis">The platform is provided “as is” without guarantees of uninterrupted service, uptime, or error-free performance.</Item>
        <Item k="Australian Consumer Law">To the maximum extent permitted by the Competition and Consumer Act 2010 (Cth), we exclude all implied warranties.</Item>
        <Item k="Liability Cap">Because no monetary transactions occur on the platform, our total liability for any claim is limited to the maximum extent permitted by law and will not exceed AUD $1.</Item>
      </Section>
    </StaticPage>
  );
}

function Section({ n, title, children }) {
  return (
    <section className="mt-8">
      <h2 className="text-xl font-black tracking-tight mb-3 text-white">{n}. {title}</h2>
      <div className="space-y-2 text-[#D4D4D4]">{children}</div>
    </section>
  );
}
function Item({ k, children }) {
  return (
    <p><strong className="text-white">{k}:</strong> <span className="text-[#D4D4D4]">{children}</span></p>
  );
}
