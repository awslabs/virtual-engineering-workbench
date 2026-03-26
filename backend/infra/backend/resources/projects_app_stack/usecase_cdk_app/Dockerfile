# kics-scan ignore-block - Build-time CDK deployment container; pinning apk/npm/pip versions is impractical for ephemeral build containers
FROM public.ecr.aws/docker/library/python:3.12-alpine

COPY .cdk.staging /.cdk.staging
COPY requirements.txt /.cdk.staging/requirements.txt
WORKDIR /.cdk.staging

RUN apk add --update bash nodejs~=24 npm rsync
RUN mv -f cdk-usecase.json cdk.json
RUN npm install --location=global aws-cdk
RUN pip install --requirement requirements.txt

# Run as non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && \
    chown -R appuser:appgroup /.cdk.staging
USER appuser
