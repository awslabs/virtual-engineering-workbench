class AdapterException(Exception):
    pass


class LicenseGrantRejectedException(AdapterException):
    """AWS refused to create, deliver or activate a License Manager grant.

    The AMI-sharing state machine catches this error by its class name and falls back to
    checking whether the spoke already has its own grant or subscription, so a refused
    grant ends no worse than a hub that never tried. Throttling and service errors are
    plain AdapterExceptions, because retrying them later can succeed.
    """
