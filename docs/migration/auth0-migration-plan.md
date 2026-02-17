# Firebase to Auth0 Migration Plan

**Goal:** Replace Firebase Authentication with Auth0 to support broader social identity providers for family/friends audience.

**Status:** Planning phase - implementation deferred pending other concurrent work

## Prerequisites

- [ ] Create Auth0 account (free tier)
- [ ] Review Auth0 pricing to confirm free tier adequate (7,500 MAU)
- [ ] Document current Firebase configuration (enabled providers, user count)

## Phase 1: Auth0 Setup

### 1.1 Create Auth0 Tenant
- [ ] Sign up at https://auth0.com
- [ ] Create tenant (recommend: `photosharing` or similar)
- [ ] Choose region closest to users (Europe for Sweden deployment)

### 1.2 Configure Application
- [ ] Create "Single Page Application" in Auth0 dashboard
- [ ] Note: Client ID, Domain
- [ ] Configure allowed callback URLs (local + production)
- [ ] Configure allowed logout URLs
- [ ] Configure allowed web origins (CORS)

### 1.3 Configure Social Connections
**Priority providers (non-technical users):**
- [ ] Google (easiest, most common)
- [ ] Microsoft/Outlook
- [ ] Apple (requires Apple Developer account)
- [ ] Facebook (requires Meta Developer account + app review)

**Optional providers:**
- [ ] GitHub
- [ ] LinkedIn
- [ ] Twitter/X

**Passwordless option (recommended):**
- [ ] Email magic link (no password needed)

### 1.4 Configure API
- [ ] Create API in Auth0 (represents your Photo Sharing backend)
- [ ] Note: API Identifier (audience)
- [ ] Configure token expiration (default: 24h access, 30d refresh)
- [ ] Enable RBAC if needed (probably not for MVP)

## Phase 2: Backend Changes

### 2.1 Update Authentication Configuration
**File:** [src/api/PhotoSharing.Api/Program.cs](../../src/api/PhotoSharing.Api/Program.cs)

**Changes:**
```csharp
// Replace Firebase configuration
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = $"https://{auth0Domain}/";
        options.Audience = auth0Audience;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = $"https://{auth0Domain}/",
            ValidateAudience = true,
            ValidAudience = auth0Audience,
            ValidateLifetime = true
        };
    });
```

**Configuration values needed:**
- `Auth0:Domain` (e.g., `photosharing.us.auth0.com`)
- `Auth0:Audience` (API identifier)

### 2.2 Update Configuration Files
- [ ] Add Auth0 settings to `appsettings.json`
- [ ] Add Auth0 settings to `appsettings.Development.json`
- [ ] Update Azure Container Apps environment variables (deployment)

### 2.3 User ID Mapping
**Current:** Firebase user IDs (format: 28-character string)
**New:** Auth0 user IDs (format: `provider|id`, e.g., `google-oauth2|123456789`)

**Decision needed:**
- Option A: Keep user ID as-is (Auth0 format), migrate existing data
- Option B: Hash/normalize user IDs to stable format
- Option C: Create user mapping table

**Recommendation:** Option A (simplest, Auth0 IDs are stable)

### 2.4 Claims Mapping
**Review code for JWT claims usage:**
- [ ] Search for `User.Claims` usage in controllers
- [ ] Verify `sub` claim extraction (user ID)
- [ ] Check if email, name, or other claims are used
- [ ] Update claim extraction if Auth0 claim names differ

### 2.5 Testing
- [ ] Test JWT validation with Auth0 tokens
- [ ] Test unauthorized access (401 responses)
- [ ] Test with multiple providers (Google, Microsoft, etc.)

## Phase 3: Frontend Changes

**Note:** Frontend implementation not yet in codebase - document expected changes

### 3.1 Authentication Library
**Replace:** Firebase SDK
**With:** Auth0 SPA SDK (`@auth0/auth0-spa-js`)

**Key differences:**
- Different initialization
- Different login/logout methods
- Token acquisition handled by SDK
- Refresh tokens handled automatically

### 3.2 Authentication Flow
```javascript
// Initialize Auth0 client
const auth0Client = await createAuth0Client({
  domain: 'photosharing.us.auth0.com',
  client_id: 'YOUR_CLIENT_ID',
  audience: 'YOUR_API_IDENTIFIER',
  redirect_uri: window.location.origin
});

// Login
await auth0Client.loginWithRedirect();

// Get token for API calls
const token = await auth0Client.getTokenSilently();

// Logout
await auth0Client.logout({ returnTo: window.location.origin });
```

### 3.3 API Request Changes
- [ ] Update token acquisition in HTTP client
- [ ] Add `Authorization: Bearer <token>` header
- [ ] Handle token refresh (automatic with SDK)
- [ ] Handle unauthorized responses (redirect to login)

## Phase 4: Data Migration

### 4.1 User Data Assessment
- [ ] Export Firebase users (if any exist in production)
- [ ] Count affected records in database
- [ ] Identify user-specific data (photo uploads, edits, etc.)

### 4.2 Migration Strategy

**If no production users yet:**
- [ ] Simply switch - no migration needed
- [ ] Test with new Auth0 accounts

**If production users exist:**
- [ ] Option A: Manual re-registration (announce to users)
- [ ] Option B: Bulk import to Auth0 (requires password reset)
- [ ] Option C: Dual authentication (support both during transition)

**Recommendation:** If <50 users, manual re-registration is simplest

### 4.3 Database Updates
- [ ] Review database for Firebase-specific user ID references
- [ ] Update user ID format if needed (see Phase 2.3)
- [ ] Test with Auth0 user ID format

## Phase 5: Infrastructure Updates

### 5.1 Configuration Management
- [ ] Add Auth0 secrets to Azure Key Vault (if using)
- [ ] Update Container Apps environment variables
- [ ] Remove Firebase configuration

### 5.2 Documentation Updates
- [ ] Update [docs/architecture/overview.md](../architecture/overview.md)
- [ ] Update [CLAUDE.md](../../CLAUDE.md) quick reference
- [ ] Update deployment scripts if needed
- [ ] Update README with Auth0 setup instructions

## Phase 6: Testing & Validation

### 6.1 Local Testing
- [ ] Test API authentication with Auth0 tokens
- [ ] Test all social providers configured
- [ ] Test token expiration/refresh
- [ ] Test logout flow

### 6.2 Production Testing
- [ ] Deploy to staging environment (if available)
- [ ] Test with real Auth0 tenant (not dev)
- [ ] Test each social provider end-to-end
- [ ] Verify user experience on mobile browsers

### 6.3 Rollback Plan
- [ ] Document rollback steps
- [ ] Keep Firebase configuration in version control
- [ ] Test rollback procedure in staging

## Phase 7: Deployment

### 7.1 Communication
- [ ] Notify users of upcoming change (if applicable)
- [ ] Prepare support documentation
- [ ] Set migration date

### 7.2 Deployment Steps
- [ ] Deploy backend changes (API authentication)
- [ ] Update Container Apps configuration
- [ ] Deploy frontend changes
- [ ] Monitor error logs

### 7.3 Post-Deployment
- [ ] Monitor authentication success rates
- [ ] Monitor error logs for auth failures
- [ ] Gather user feedback
- [ ] Address issues promptly

## Phase 8: Cleanup

### 8.1 Remove Firebase
- [ ] Remove Firebase SDK from frontend
- [ ] Remove Firebase configuration from backend
- [ ] Remove Firebase npm packages
- [ ] Remove Firebase NuGet packages (if any)
- [ ] Disable Firebase project (after confirmation)

### 8.2 Documentation
- [ ] Archive Firebase configuration documentation
- [ ] Update all relevant docs to reflect Auth0
- [ ] Remove this migration plan (or mark as completed)

## Cost Comparison

**Firebase (Blaze plan):**
- Free: 50,000 MAU
- Beyond: $0.0055/MAU

**Auth0 (Free tier):**
- Free: 7,500 MAU
- Essential: $35/month for 500 MAU + $0.07 per additional user
- Professional: $240/month for 500 MAU + $0.48 per additional user

**For family/friends audience (<500 users):** Auth0 free tier is sufficient

## Security Considerations

- [ ] Review Auth0 security checklist
- [ ] Enable MFA option for users (optional)
- [ ] Configure token lifetime appropriately
- [ ] Enable anomaly detection (Auth0 feature)
- [ ] Review Auth0 security logs regularly

## Notes

- Auth0 free tier includes: Basic SSO, Social connections, Email/password, Passwordless
- No credit card required for free tier
- Can upgrade if user base grows beyond 7,500 MAU
- Auth0 Universal Login handles all provider UX consistently
- Better mobile support than Firebase for social providers

## Resources

- Auth0 Quickstart (SPA): https://auth0.com/docs/quickstart/spa
- Auth0 ASP.NET Core: https://auth0.com/docs/quickstart/backend/aspnet-core-webapi
- Social Connections: https://auth0.com/docs/connections/social
- Migration Guide: https://auth0.com/docs/users/user-migration
