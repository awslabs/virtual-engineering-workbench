class InstanceStartException(Exception):
    """EC2 refused to start a workbench's instance for a reason other than capacity: the message
    carries the EC2 error code and text, for statusReason."""
