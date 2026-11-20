# kics-scan ignore-block - Build-time CDK deployment container; pinning apk versions is impractical for ephemeral build containers
FROM public.ecr.aws/docker/library/python:3.12-alpine@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89
COPY --from=ghcr.io/astral-sh/uv:0.11.3@sha256:90bbb3c16635e9627f49eec6539f956d70746c409209041800a0280b93152823 /uv /uvx /bin/

COPY .cdk.staging /.cdk.staging
COPY requirements.txt /.cdk.staging/requirements.txt
WORKDIR /.cdk.staging

RUN apk add --update bash nodejs~=24 npm rsync
RUN mv -f cdk-usecase.json cdk.json
RUN npm install --location=global aws-cdk@2.1133.0
RUN uv pip install --system --requirement requirements.txt

# Run as non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && \
    chown -R appuser:appgroup /.cdk.staging
USER appuser
