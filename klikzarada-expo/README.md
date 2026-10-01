# KlikZarada mobile preview

Expo Go opens the separate mobile interface at `https://klikzarada.onrender.com/mobilna`. The interface uses the same `/api/ui` backend, session, accounts, tasks, campaigns, messages and balances as the website. It does not create a second database. Admin stays in the browser.

This is a preview, not a store release. Actions made after login are real and affect the same production account as the website. Use a test account for review, and do not approve proofs, activate testers or request payouts just to test the layout.

Run `npm install`, then `npx expo start --clear`. Scan the QR code in Expo Go on a phone on the same network as the development computer. The phone needs internet access to Render. `.env.local` can override the defaults but is not committed.

The standalone mobile UI source is in the backend's `mobile` directory and is built into the Render Docker image. The website keeps its own design and routes. Some high-risk flows, including standard-task anti-fraud proof submission and full campaign creation, deliberately open the existing website workflow until equivalent native screens can preserve all checks.
