# GONTOBBO Email OTP Sign-In

The website now uses real email OTP verification through the included Node.js backend.

## Setup
1. Install Node.js.
2. In this folder run `npm install`.
3. Copy `.env.example` to `.env`.
4. Set `EMAIL_USER` to the Gmail address that will send OTPs.
5. Set `EMAIL_PASS` to a Gmail **App Password** (not the normal Gmail password). Enable 2-Step Verification on that Google account first.
6. Optionally change `EMAIL_FROM` and `PORT`.
7. Run `npm start`.
8. Open `http://localhost:3000/gontobbo-home-search.html`.

## Flow
Email → Send OTP → OTP arrives in that exact email inbox → Verify OTP → Sign in.

OTP is 6 digits, expires after 5 minutes, resend has a 60-second cooldown, and there are at most 5 verification attempts per OTP.
