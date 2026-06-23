import React from 'react';
import StaticPage from '../components/StaticPage';

export default function Contact() {
  return (
    <StaticPage tag="GET IN TOUCH" title="Contact" testId="contact-page">
      <p>General questions, partnerships, sponsorship enquiries — drop us a line.</p>
      <p><strong>Email:</strong> <a className="text-[#FF3B30] hover:underline" href="mailto:helpdesk@gomofos.com">helpdesk@gomofos.com</a></p>
      <p><strong>Disputes:</strong> Use the in-app dispute flow on the match page. An admin reviews every dispute within 24 hours.</p>
    </StaticPage>
  );
}
