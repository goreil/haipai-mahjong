# Landing Page

Build a public-facing page for unauthenticated visitors. Currently they hit a login wall with no context.

---

## L-01: Public landing route (HIGH) ✅

**Current state**: All routes require login. Someone clicking the Discord link sees a login/register form with no idea what the app does.

**Build**:
- If user is not logged in and hits `/`, show the landing page instead of the app
- If user IS logged in, show the app as normal
- Single page, no framework — consistent with the vanilla JS approach

**Content**:
- Headline: "Haipai — Study Your Mahjong Mistakes"
- 3 value props (with icons or tile SVGs):
  1. "Upload your Mortal analysis and see your mistakes categorized"
  2. "Practice your weak spots with quizzes from your own games"
  3. "Track your improvement over time"
- Screenshot of the review UI (can be a static PNG in /static/)
- "Register with invite code" → links to register form
- "Already have an account?" → links to login form

**Files**: `app.py` (modify `/` route), `static/landing.html` or inline in `index.html`, `static/style.css`.

---

## L-02: Screenshot/demo image (MEDIUM)

Take a screenshot of the review view with a real game loaded. Crop to show:
- SVG hand tiles with dora highlighting
- EV comparison table
- Category badge
- Board context (discards, melds)

Save as `static/screenshot.png`. Reference from landing page.

**Alternative**: Animated GIF showing a quick walkthrough (upload → review → practice). More compelling but more work.

---

## L-03: Demo mode (LOW — post-launch)

Let visitors try the app without registering:
- Pre-loaded sample game with interesting mistakes
- Read-only: can browse review, see practice, see trends
- "Register to upload your own games" CTA throughout
- Requires a demo user/session mechanism

This is the best conversion tool but significant work. Save for after beta feedback confirms demand.
