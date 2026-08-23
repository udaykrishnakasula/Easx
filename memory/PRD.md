# Halo — Landing Page (Hero from reference video)

## Problem statement
Recreate a premium cinematic hero section exactly from an uploaded screen recording
(Halo — "Your Wealth Works"): hero at absolute top, full viewport, navbar overlay,
floating/rotating 3D silver coins, lavender cinematic background, same composition on
desktop & mobile, no horizontal overflow, mobile-viewport-stable (svh/dvh).

## Architecture
- Frontend: React 19 (CRA/craco), framer-motion, Tailwind + custom CSS. No new libs added.
- 3D coins: pure CSS 3D transforms (front/back engraved faces + stacked-disc rim), GPU-only
  transform/opacity animations (spin + float + shadow). No WebGL.
- Assets in /app/frontend/public/assets/ (coin.png, flowers.png, hero_bg.jpg) generated + processed.
- Backend: unchanged default FastAPI scaffold.

## Implemented (2026-06)
- Full-screen hero (min-height:100svh, fallback 100vh) starting at 0px; navbar overlay.
- Heading "Your Wealth Works", subtext, "Join us" CTA (left-anchored); "Open Wallet" nav btn.
- Two 3D coins (lead + sub) with continuous rotation, float, soft shadow, engraved silver faces.
- Lavender atmospheric bg + blurred flowers + partner strip (Aave/Compound/MakerDAO/Chainlink/Curve).
- Same composition scaled via clamp()/vw across desktop & mobile.
- Below-fold: features (dark), stats (light), CTA band, footer.
- Fonts: Bricolage Grotesque (display) + Manrope (body).
- Verified: 1920, 1440, 1280, 1024, 768, 390, 393, 360 + landspace — no horizontal overflow,
  hero starts at top, no layout jump, consistent composition.

## Notes
- Buttons are visual-only placeholders (per user choice).
- prefers-reduced-motion disables coin animation.

## Backlog / Next
- P1: Wire "Open Wallet"/"Join us" to real routes/actions.
- P2: Add nav links + mobile menu; "How it works" section; scroll-linked coin parallax.

## Update (2026-06) — Coin animation fixes (UI/UX otherwise unchanged)
- Rotation sped up: lead 18s→3.2s, sub 22s→3.8s (still linear/continuous, no stutter/reset).
- Fixed paper-thin/disappearing flip: increased rim thickness (--t) + disc count (lead 46, sub 34),
  discs now double-sided (backface-visibility:visible) so the reeded metallic edge stays visible
  through 90deg. Verified frozen at rotateY(88deg) — solid edge, never vanishes.
- Added moving metallic sheen (coinSheen sweep synced to spin) + static specular hotspot; engraving
  and edge catch light. Subtle, screen-blended, no flashing.
- Unchanged: coin positions/sizes (--d), layout, typography, background, sections, responsiveness.

## Update (2026-06) — Reeded (milled) coin edge
- Replaced the conic-gradient rim (caused moiré) with a real reeded cylinder wall:
  thin radial strips (lead 104, sub 68) alternating light/dark = fine milled grooves
  that run across the thickness and stay uniform all the way around the rim.
- Discs kept as a smooth silver core (opacity fill); faces unchanged.
- Verified edge-on (rotateY ~78deg) + running, desktop 1440 & mobile 390 — crisp grooves,
  no moiré, no horizontal overflow. Coin positions/sizes and all other UI unchanged.

## Update (2026-08) — Autoplay carousel under "What Halo does"
- Added shadcn/ui Carousel with embla-carousel-autoplay plugin (Autoplay delay:2000, loop),
  placed exactly below the "A digital dollar that earns on its own." heading in Sections.jsx.
- Installed dep: embla-carousel-autoplay (embla-carousel-react already present).
- 5 placeholder slides (basis 1/2 md, 1/3 lg) styled via .halo-carousel* in App.css.
  User will replace placeholders with Card components next.
- Also installed the UI UX Pro Max design-intelligence skill at /app/.claude/skills/ui-ux-pro-max.

## Update (2026-08) — Diamond Investment Cards in carousel
- Imported InvestmentCard (3D luxury card, 4 variants: silver/gold/diamond/platinum) from
  github.com/udaykrishnakasula/diamond-investment-card. Converted TS -> JS:
  /components/landing/DiamondInvestmentCard.jsx + investment-card-themes.js (deps: framer-motion, tailwind — already present).
- Rendered dynamically in the autoplay carousel by mapping over variants. Cards kept at full
  natural size (w-[420px], aspect 42/26); carousel slides sized to the card (basis-auto, center align).
- Carousel drag disabled (watchDrag:false) so each card's own drag-to-rotate 3D interaction works;
  autoplay 2s + prev/next arrows.

## Update (2026-08) — Database Foundation (Phase 2)
- NOTE: EasyX uses **MongoDB (Motor)**, not SQL. The requested "relational schema" is
  implemented as the MongoDB-native equivalent: collections + $jsonSchema validators +
  unique/compound/TTL/sparse indexes + Decimal128 money + versioned migration runner.
- Versioned migrations in `backend/migrations/` (runner + schema m0001 + seed m0002),
  tracked in `schema_migrations`. Runs on startup (idempotent) and via `python migrate.py --verify`.
- 20 domain collections created: users, user_profiles, email_verifications, password_resets,
  investment_plans, investments, wallets, wallet_transactions, deposits, withdrawals,
  withdrawal_addresses, referrals, referral_commissions, kyc_records, kyc_documents,
  notifications, admin, audit_logs, platform_settings, maintenance_settings.
- All money fields = **Decimal128** (validator rejects float). Status fields = enum-constrained.
- Plans seeded EXACTLY (idempotent, $setOnInsert so admin edits are preserved):
  Silver 300/60d/60%/160% #1; Gold 1000/60d/60%/160% #2; Platinum 5000/60d/100%/200% #3;
  Diamond 10000/60d/100%/200% #4.
- investments store plan-term SNAPSHOT fields (profit_/maturity_percentage_snapshot,
  lock_days_snapshot) so future admin plan changes never mutate existing investments.
- Verified: 21 collections present, validators enforce enums + decimal, admin login regression OK.
- Landing page untouched.

## Update (2026-08) — Direct (1-level) Referral Commission System
- Implemented ONE-LEVEL direct referral commission per spec. Only the DIRECT
  referrer earns; no multi-level.
- Commission = referral_percentage (default 10%, platform_settings) of EACH
  successful investment's principal. In EasyX investments activate immediately
  on purchase from wallet, so commission is paid at purchase time.
- ONE commission record PER investment: buying 3 Gold => 3 records of $100 = $300.
- Paid IMMEDIATELY to referrer's wallet (REFERRAL_COMMISSION ledger, ref_type
  'referral', inc total_earned) => available + withdrawable.
- IDEMPOTENT: unique sparse index on referral_commissions.investment_id +
  wallet idempotency_key 'referral:{inv_id}' => never double-pays.
- Self-referral impossible (referred_by set once at signup); duplicate
  relationship impossible (unique referee_id in referrals collection).
- NO reversal if admin later cancels an investment (no reversal logic exists).
- Reinvestment = a new investment => a new 10% commission automatically.
- Migration m0006 DROPPED the wrong unique index on referral_commissions.referee_id
  (it blocked multiple commissions per referee) and kept the unique investment_id guard.
- Files: backend/referral_service.py (new), invest_service.py (hook in buy_plan),
  auth_service.py (referrals relationship record), user_router.py
  (GET /api/referrals/summary), migrations/referral_commissions_fix.py.
- Frontend: new ReferralPage (/app/referral) — referral code + share link
  (?ref=CODE prefills register), total commission earned, total referrals,
  commission rate, referred-users list, commission history. Sidebar "Referrals"
  link now routes to the real page (was ComingSoon).
- Verified: backend 58/58 tests pass (basic $100, 3x=$300, no-referrer, idempotency,
  withdrawable, decimals, self-referral). Demo data: referrer earned $330 (3 Gold + 1 Silver).

## Update (2026-08) — KYC Identity Verification
- KYC NOT required to invest; REQUIRED for withdrawal (enforced in withdrawal task).
- Docs: government ID photo (Aadhaar/National ID/Passport) + Selfie. Optional ID
  number stored ENCRYPTED (Fernet, KYC_ENC_KEY) and never returned in plaintext
  (only id_number_present boolean). Document bytes stored in MongoDB (BSON Binary)
  => NO public URL; served only via authenticated owner-or-admin endpoints.
- Statuses none->pending->(approved|rejected); resubmit after rejection.
- File validation: JPG/PNG/WebP/PDF, max 5MB, non-empty.
- User endpoints: GET /api/kyc, POST /api/kyc/submit (multipart), GET /api/kyc/documents/{id}.
- Admin: GET /api/admin/kyc[?status], approve, reject {reason}, GET /api/admin/kyc/documents/{id}.
- Notifications on approve/reject. Files: kyc_service.py, kyc_router.py, admin_router.py.
- Frontend: /app/kyc user page (submit/resubmit + status), /admin/kyc admin review page
  (thumbnails via authenticated blob fetch, approve/reject with reason).
- Verified: backend 43/44 tests pass (security: cross-user 403, no plaintext ID, file validation).

## Referral Notifications — ALREADY LIVE
- referral_service.pay_for_investment creates an in-app 'referral_commission' notification
  ("You earned X USDT ...") the moment a referral's investment pays commission. Surfaces on
  the existing Notifications page + sidebar unread badge. No extra work needed.

## Backlog (requested)
- Withdrawal system with Email OTP (Resend) — BLOCKED on RESEND_API_KEY from user.
- Admin Referral View (read-only list of relationships + commissions paid).

---

## Admin: Account Suspension + Maintenance Mode (added)

### Account Suspension
- Admin can suspend/reactivate any non-admin user from `/admin/users` (list, status filters, search).
- Suspended user: cannot log in and cannot use ANY account function (all Bearer-protected routes return 403). Suspend requires a reason.
- Existing ACTIVE investments keep running toward normal maturity — suspension never cancels them. Wallet/maturity engine unaffected.
- Admins cannot be suspended.
- Endpoints: `GET /api/admin/users`, `GET /api/admin/users/{id}`, `POST /api/admin/users/{id}/suspend` {reason}, `POST /api/admin/users/{id}/unsuspend`.

### Maintenance Mode
- Global maintenance toggle + per-feature switches (registration, deposits, investments, withdrawals) at `/admin/maintenance`, with an admin-editable message.
- Global ON blocks all four user-facing writes (503 + message); individual switches disable a single feature. Existing investments, maturity engine and wallet balances are never affected. Admin login always works.
- Public status: `GET /api/maintenance` (no auth) → drives amber banner on login/register screens.
- Endpoints: `GET/PUT /api/admin/maintenance`.

### Audit Logs
- All admin mutations (suspend/unsuspend, wallet adjust, maintenance changes) append immutable records to `audit_logs`. Read via `GET /api/admin/audit-logs`.

---

## Admin: Overview, Plan Editor, Investment Cancel, Withdrawals (added)

### Admin Overview (/admin/overview)
- KPI dashboard (GET /api/admin/overview): users(total/active/suspended), platform liabilities (available + locked), investments(active/matured/cancelled + active principal), pending deposits + approved total, withdrawals(pending/approved/paid total), pending KYC, referral commissions paid.

### Investment Plan Editor (/admin/plans)
- Edit price, profit %, maturity %, lock days, active state per plan. Each save bumps a version and appends a before/after record to plan_history (viewable). Existing investments retain their original snapshotted terms (unaffected).
- Endpoints: GET /api/admin/plans, PUT /api/admin/plans/{key}, GET /api/admin/plans/{key}/history.

### Investment Cancel + Refund (/admin/investments)
- Admin cancels an ACTIVE investment with a chosen refund amount (0..principal) and a required reason. Profit is NEVER paid; already-paid referral commission is NOT reversed. Atomic active->cancelled flip (safe vs maturity engine). Refund credited to wallet as REFUND. Audit logged.
- Endpoints: GET /api/admin/investments, POST /api/admin/investments/{id}/cancel {refund_amount, reason}.

### Withdrawals (user + admin)
- User (/app/withdraw): KYC-approved only. Requests debit/hold funds from available balance immediately (min 10 USDT, TRC20/BEP20). Maintenance-gated. GET /api/withdrawals/config, GET/POST /api/withdrawals.
- Admin (/admin/withdrawals): Approve, Reject (refunds held amount via WITHDRAWAL_REVERSAL), Process (records blockchain TX hash -> paid). Audit logged.
- Endpoints: GET /api/admin/withdrawals, POST /api/admin/withdrawals/{id}/{approve|reject|process}.
