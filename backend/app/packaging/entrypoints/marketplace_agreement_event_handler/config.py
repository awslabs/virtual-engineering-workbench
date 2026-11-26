import os

from pydantic import BaseModel

# AWS emits `aws.agreement-marketplace` events only to the default
# EventBridge bus in us-east-1 (buyer guide, "Overview" section). A
# Lambda deployed elsewhere subscribes to a bus that never receives
# these events, and its outbound domain-event publish would target the
# wrong regional bus. We hard-fail at cold start rather than silently
# no-op for months.
REQUIRED_REGION = "us-east-1"


class AppConfig(BaseModel):
    def get_default_region(self) -> str:
        region = os.environ.get("AWS_DEFAULT_REGION")
        if region != REQUIRED_REGION:
            raise RuntimeError(
                f"marketplace_agreement_event_handler must run in "
                f"{REQUIRED_REGION}; got {region!r}. AWS Marketplace emits "
                f"aws.agreement-marketplace events only in us-east-1 — a "
                f"Lambda deployed elsewhere would silently do nothing. See "
                f"https://docs.aws.amazon.com/marketplace/latest/buyerguide/"
                f"agreement-eventbridge.html"
            )
        return region

    def get_domain_event_bus_name(self) -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")
