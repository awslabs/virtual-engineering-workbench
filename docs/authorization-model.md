# Authorization model

VEW has three ways to authorize an API call. Each API uses exactly one of them. This page is the reference; other documents link here.

| Caller | Authentication | Authorization | Where it lives |
| --- | --- | --- | --- |
| A person using the portal, the vew CLI or the MCP gateway | Cognito JWT | Amazon Verified Permissions (Cedar policies) | User APIs, `/projects/...`, `/packaging/...` and so on |
| Another application (service to service, S2S) | Cognito OAuth access token, client credentials grant | OAuth scopes per operation; the packaging routes also require a project assignment for the client | S2S APIs, `/clients/<context>/v1/...` |
| A bounded context calling another one | AWS IAM (SigV4) | IAM policy on the calling role | `/internal/*` operations |

## User APIs: Cognito JWT and Cedar

An API Gateway Lambda request authorizer (`AVP-Request-Authorizer` in each user API schema) validates the Cognito JWT and asks Amazon Verified Permissions to evaluate the Cedar policies for the user, the path and the HTTP method. API Gateway caches the result for 1800 seconds. Code: `backend/app/authorization/entrypoints/api_gateway_authorizer_request_event_handler/`.

## S2S APIs: OAuth scopes

An S2S API declares one security scheme, `ClientCredentials`, a Cognito user pool authorizer. Every operation lists the OAuth scopes it needs, and API Gateway rejects a token without them. Example: `backend/app/packaging/entrypoints/s2s_api/schema/proserve-workbench-s2s-packaging-api-schema.yaml`.

The handler then checks two more things before it acts (`backend/app/packaging/entrypoints/s2s_api/routers/components.py`):

1. The token carries the scope for the operation (`common.require_scope`).
2. The client is assigned to the project in the path. The packaging service asks the Projects API at `/internal/projects/{projectId}/clients/{clientId}`.

A scope grants an action. **An S2S client is scoped to the deployment, not to a project**: the provisioning and projects routes check the scope only — `require_access` appears nowhere outside packaging (`backend/app/provisioning/entrypoints/s2s_api/handler.py`, `backend/app/projects/entrypoints/s2s_api/routers/assignments.py`) — so a client holding one of those scopes may act on any project in the deployment, and provisioning's lifecycle routes act under a service identity rather than as a user. The packaging routes are stricter: each of their routers calls `require_access` alongside `require_scope`, so a packaging request also needs the client to be assigned to the project in the path.

Treat S2S credentials as deployment-wide. Where separate teams must not reach each other's projects, the boundary is a separate deployment. `SECURITY.md` records this under accepted design decisions, and under production recommendations for adopters who need per-project isolation.

There is no Cedar evaluation on the S2S path. See [Packaging service-to-service API](packaging-s2s-api.md) and [Provisioning service-to-service API](provisioning-s2s-api.md) for the scopes and how to obtain a token.

## Internal calls: IAM

Operations under `/internal/*` use `sigv4` (API Gateway IAM authorization). They serve calls between bounded contexts, for example the projects `GET /internal/projects/{projectId}/clients/{clientId}` used above. They are not for end users.

## Not covered

The CloudFront viewer check (Lambda@Edge JWT validation) protects the web application, not the APIs. The APIs authorize on their own, as described above.
