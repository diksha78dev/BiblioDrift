# Bruno API Collection Security Guide

## 🔐 Security Best Practices for API Testing

This guide explains how to securely use Bruno API collection with BiliBili and other services without exposing sensitive credentials.

---

## ⚠️ Critical Security Issues Addressed

### Previous Vulnerabilities (FIXED)
- ❌ Hardcoded API keys in `default.bru` files
- ❌ Real JWT tokens committed to version control
- ❌ Session cookies visible in git history
- ❌ Credentials exposed in public repository

### Current Secure Implementation
- ✅ All credentials stored in environment variables only
- ✅ Sensitive files properly gitignored
- ✅ Template files with placeholder values
- ✅ Clear separation between version-controlled and local files

---

## 📁 File Structure

```
bruno/
├── bruno.json                          # Collection configuration (safe to commit)
├── environments/
│   ├── default.bru                     # Variable NAMES only (safe to commit)
│   └── local.bru.template             # Template for local credentials (DO NOT COMMIT .bru)
└── app.bilibili.com/
    └── x/
        └── report/
            └── heartbeat/
                └── mobile_start.bru   # Request file using {{variables}}
```

---

## 🔒 Security Rules

### Rule 1: NEVER Hardcode Credentials

**❌ WRONG - Exposes secrets in git:**
```bru
vars {
  appKey: 1d8b6e7d45233436  # ← NEVER DO THIS!
  access_key: abc123secret # ← NEVER DO THIS!
}
```

**✅ CORRECT - Use environment variables:**
```bru
vars {
  appKey: process.env.appKey      # ← Always reference env vars
  access_key: process.env.access_key
}
```

### Rule 2: NEVER Commit Actual Tokens

**❌ WRONG - Real JWT in version control:**
```bru
headers {
  x-bili-ticket: eyJhbGciOiJIUzI1NiIs... # ← NEVER DO THIS!
}
```

**✅ CORRECT - Use variable references:**
```bru
headers {
  x-bili-ticket: {{bili_ticket}}  # ← Reference from environment
}
```

### Rule 3: ALWAYS Gitignore Sensitive Files

The following files are automatically ignored by `.gitignore`:
- `bruno/environments/local.bru` - Contains actual credentials
- `*.token` - Token files
- `*.secret` - Secret key files

---

## 🚀 Setup Instructions

### Step 1: Copy the Template
```bash
cp bruno/environments/local.bru.template bruno/environments/local.bru
```

### Step 2: Add Your Credentials
Edit `bruno/environments/local.bru` with your actual values:
```bru
vars {
  phone: "8612345678901"
  pwd: "your_actual_password"
  mid: "your_mid_value"
  buvid: "your_buvid_value"
  csrf: "your_csrf_token"
  appKey: "your_app_key_from_bilibili"
  access_key: "your_access_key"
  cookieStr: "your_cookie_string_from_browser"
  bili_ticket: "your_jwt_token"
}
```

### Step 3: Verify Gitignore
Make sure `local.bru` is not tracked:
```bash
git status
```
You should NOT see `bruno/environments/local.bru` in the list.

---

## 🛡️ Security Checklist

Before committing any changes, verify:

- [ ] No hardcoded API keys in `.bru` files
- [ ] No real tokens or session data in version control
- [ ] All credentials reference `process.env.*`
- [ ] `local.bru` file exists and is gitignored
- [ ] No `.token` or `.secret` files staged for commit

---

## 🔄 Getting Credentials

### BiliBili API Keys
1. Visit [BiliBili Open Platform](https://open.bilibili.com/)
2. Create a developer application
3. Get your `appKey` and `access_key` from the dashboard

### Session Cookies
1. Open browser developer tools (F12)
2. Go to Network tab
3. Log in to BiliBili
4. Find any API request
5. Copy the `Cookie` header value → `cookieStr`
6. Extract `buvid`, `mid`, `csrf` from cookies

### JWT Ticket (bili_ticket)
1. Look for `x-bili-ticket` header in network requests
2. Or generate using BiliBili's authentication flow
3. Update regularly as tokens expire

---

## 🚨 If You Accidentally Committed Secrets

### Immediate Actions:

1. **Rotate ALL exposed credentials immediately:**
   - Change BiliBili API keys
   - Invalidate session tokens
   - Generate new JWT tickets

2. **Remove from git history:**
   ```bash
   # Install BFG Repo-Cleaner
   bfg --delete-files '*.bru' --no-blob-protection
   
   # Or use git filter-branch
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch bruno/environments/local.bru' \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **Force push cleaned history:**
   ```bash
   git push origin --force --all
   ```

4. **Contact GitHub support** to remove cached data if it's a public repo

---

## 📝 Example Request File

Here's how to properly structure a request:

```bru
url: https://app.bilibili.com/x/report/heartbeat/mobile/start
method: POST
headers {
  Content-Type: application/json
  User-Agent: {{user_agent}}
  x-bili-ticket: {{bili_ticket}}  # ← Variable reference, NOT hardcoded
}
body {
  mode: raw
  json: {
    "mid": "{{mid}}",
    "buvid": "{{buvid}}",
    "csrf": "{{csrf}}"
  }
}
```

---

## 🎯 Why This Matters

### Risks of Exposed Credentials:

1. **Account Compromise**: Attackers can access your BiliBili account
2. **API Abuse**: Use your quota, get you rate-limited or banned
3. **Data Theft**: Access private user data
4. **Financial Loss**: If linked to payment methods
5. **Reputation Damage**: Attacks made from your account

### Benefits of Proper Security:

1. ✅ Safe to share code publicly
2. ✅ Team members can use their own credentials
3. ✅ No secrets in git history
4. ✅ Easy credential rotation
5. ✅ Compliance with security best practices

---

## 📚 Additional Resources

- [Bruno Documentation - Environments](https://www.usebruno.com/documentation)
- [OWASP Credential Management](https://cheatsheetseries.owasp.org/cheatsheets/Credentials_Management_Cheat_Sheet.html)
- [BiliBili Open Platform](https://open.bilibili.com/)

---

## ❓ Troubleshooting

### "Variable not found" error
- Make sure `local.bru` exists in `bruno/environments/`
- Check that variable names match exactly (case-sensitive)
- Restart Bruno after editing environment files

### "Invalid credentials" error
- Verify your API keys are correct
- Check if tokens have expired
- Ensure you're using the right environment (local vs default)

### Git still tracking local.bru
```bash
# Remove from tracking (keeps file locally)
git rm --cached bruno/environments/local.bru

# Add to .gitignore (already done)
echo "bruno/environments/local.bru" >> .gitignore
```

---

**Remember: Security is everyone's responsibility. Never commit what you wouldn't want exposed!** 🔒
