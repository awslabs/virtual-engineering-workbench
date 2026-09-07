# Auth0 Integration Changes

This document records the Auth0-specific configuration added to VEW. It sits beside `FINDINGS.md` so deployment findings and the resulting changes remain separate.

## Stable VEW user ID

VEW requires an immutable internal user ID in Cognito's `custom:user_tid` attribute. Auth0 supplies that value from `app_metadata.vew_user_id`; email is not used as the identifier.

Create an Auth0 **Post Login** Action with this code:

```javascript
const crypto = require('crypto');

const VEW_USER_ID_CLAIM = 'https://d3t9uqm0nnoy9y.cloudfront.net/vew/user_id';
const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

const generateVewUserId = () => {
  let value = 'U';
  for (let index = 0; index < 7; index += 1) {
    value += ALPHABET[crypto.randomInt(0, ALPHABET.length)];
  }
  return value;
};

exports.onExecutePostLogin = async (event, api) => {
  let vewUserId = event.user.app_metadata?.vew_user_id;

  if (!vewUserId) {
    vewUserId = generateVewUserId();
    api.user.setAppMetadata('vew_user_id', vewUserId);
  }

  api.idToken.setCustomClaim(VEW_USER_ID_CLAIM, vewUserId);
};
```

Deploy the Action and add it to the Auth0 Login flow. A user without `app_metadata.vew_user_id` receives an ID such as `U7F3K29D` on their next login. Later logins reuse the stored value.

Configure the deployment with the same claim name:

```bash
OIDC_USER_ID_CLAIM="https://d3t9uqm0nnoy9y.cloudfront.net/vew/user_id"
```

`deploy.sh` stores that value in the OIDC Secrets Manager secret as `UserIDClaim`. The frontend infrastructure reads the field and maps the corresponding Auth0 ID-token claim to Cognito `custom:user_tid`. It also maps Auth0's `email_verified` claim to Cognito.

The claim URI is a namespace identifier; it does not need to serve a web page.

## Complete Auth0 logout

The public CloudFront deployment now configures this browser flow:

```text
VEW/Amplify sign-out
  -> Cognito /logout
  -> https://elva-dev.eu.auth0.com/v2/logout
  -> https://d3t9uqm0nnoy9y.cloudfront.net/login
  -> fresh Cognito/Auth0 login flow
```

The Auth0 logout request includes the Auth0 application client ID and uses the VEW `/login` URL as `returnTo`. It intentionally omits `federated`, so it clears the VEW, Cognito, and Auth0 sessions without signing the user out of an upstream enterprise or social identity provider.

### Required Auth0 dashboard setting

In the Auth0 application configured for VEW, add this exact value to **Allowed Logout URLs**:

```text
https://d3t9uqm0nnoy9y.cloudfront.net/login
```

Auth0 validates `returnTo` against this list. A missing or mismatched value results in an Auth0 logout error page.

If AWS replaces the CloudFront distribution and assigns a new domain, update the allowed logout URL before using the new deployment. The existing claim namespace can remain stable because it is an identifier and does not need to resolve to the current application domain.

## Verification

1. Log in as an invited Auth0 user who has no `app_metadata.vew_user_id`.
2. Confirm Auth0 adds an eight-character ID beginning with `U` to `app_metadata.vew_user_id`.
3. Confirm the Cognito ID token contains the same value as `custom:user_tid` and VEW uses it for the logged-in user.
4. Select **Sign out** and confirm the browser passes through Cognito and Auth0 logout.
5. Confirm the browser returns to the VEW `/login` entry point without an Auth0 error or redirect loop.
6. Start login again and confirm Auth0 does not silently reuse its previous session.
7. If Auth0 uses an upstream enterprise provider, confirm that provider's session remains available; this is the intended non-federated behavior.
