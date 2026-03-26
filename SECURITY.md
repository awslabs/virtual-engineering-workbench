# Security

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it by emailing <aws-security@amazon.com>. Please do not report security vulnerabilities through public GitHub issues.

## Security Best Practices

### Deployment Security

- Use separate AWS accounts for dev, qa, and prod environments
- Deploy with the provided `deploy.sh` script which automatically configures environment-specific CORS origins
- Review and customize `backend/infra/config.py` environment configurations before production deployment
- Ensure `retain_resources` and `backup-resources` are `True` for production (default for qa/prod configs)

### Encryption

- All data stores use AWS-managed encryption by default (S3 SSE-S3, DynamoDB AWS-managed, SQS KMS)
- For enhanced key management control, pass KMS customer-managed keys to construct parameters:
  - `encryption_key` on `BackendAppStorage`, `Bucket`, `BackendAppWaf`, and log group constructs
  - `server_access_logs_bucket` on `Bucket` for S3 access logging

### Operational Security

- CloudWatch Logs retain data for 2 months by default
- WAF anomaly detection alarms are configured for blocked request monitoring
- API Gateway throttling is set to 1000 req/s with 500 burst
- `data_trace_enabled` is automatically disabled for non-dev environments

### Network Security

- VPC endpoints are used for AWS service communication in private deployment mode
- Security groups follow least-privilege principles
- Private API endpoints restrict access to configured CIDR ranges

### Authentication & Authorization

- Cognito User Pool with OIDC/SAML federation (self-signup disabled)
- Amazon Verified Permissions with Cedar policies for fine-grained authorization
- Lambda@Edge JWT validation on CloudFront viewer requests
- API Gateway IAM authentication

## Known Security Considerations

### Accepted Design Decisions

- Lambda@Edge allows unauthenticated access to landing and documentation pages; backend API has independent auth
- `/webhooks/github` endpoint is unauthenticated by design; implement HMAC-SHA256 signature validation in handler
- cdk_nag suppressions are documented in source code for EC2 workbench launch template configurations
- Client IP header is included in CloudFront error responses for debugging

### Production Recommendations

- Enable KMS customer-managed keys for CloudWatch log groups containing sensitive data
- Configure S3 server access logging for audit requirements
- Add GitHub webhook signature validation
- Review cdk_nag suppressions periodically

## Compliance Considerations

Users should evaluate this solution against their specific compliance requirements including:

- Data residency and sovereignty
- Encryption key management policies
- Audit logging requirements
- Network isolation requirements
