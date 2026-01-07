# Playground Authentication Test Example

## Quick Start

```bash
# 1. Set up environment
cd packages/runtime/examples/test_examples
cp .env.example .env

# 2. Run the example
cd ../../../..  # Back to project root
uv run --active python -m packages.runtime.examples.test_examples.auth_example
```

## What This Tests

✅ JWT secret from environment variable  
✅ Login page shown on first visit  
✅ Signup flow (create team account)  
✅ Login flow (authenticate)  
✅ Session persistence via cookies  
✅ CSRF protection

## Flow

1. **First Visit** → Signup page

   - Enter team email + password
   - Creates account + auto-login

2. **Subsequent Visits** → Auto-authenticated

   - Cookie contains valid JWT
   - No login required

3. **Settings Page** → View logged in user
   - See team email
   - Sign out option

## Endpoints

- `http://localhost:8000` - Playground UI (requires auth)
- `http://localhost:8000/docs` - API documentation
- `http://localhost:8000/auth/session` - Check session status
- `http://localhost:8000/auth/needs-signup` - Check if first-time setup

## Environment Variables

Required:

- `ASTRA_JWT_SECRET` - Secret for signing JWTs (auto-generated in .env.example)

## Database

Creates `test_auth.db` in the current directory with:

- `astra_team_auth` table for credentials
- `astra_threads` table for conversations
- `astra_messages` table for messages

Clean up after testing:

```bash
rm test_auth.db
```
