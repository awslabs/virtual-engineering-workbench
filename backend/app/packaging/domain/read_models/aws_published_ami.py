import os
from typing import Optional

from pydantic import BaseModel, Field


class AwsPublishedAmiCandidate(BaseModel):
    """One AMI that could satisfy an AWS-published Marketplace listing.

    AWS is Seller of Record for these products, so no buyer-side agreement
    exists (``CreateAgreementRequest`` returns "This action is not supported.")
    and therefore no License Manager grant is ever issued. The regular
    discovery path keys off that grant, so it can never surface them. Nothing
    needs subscribing either: the image is already public and launchable, and
    the licence is priced through the instance-hour billing code
    (``UsageOperation`` ``RunInstances:0010`` for RHEL, ``:0002`` for
    Windows).

    ``amiName`` is carried deliberately. When a product publishes more than
    one architecture the resolution is ambiguous and the user has to choose,
    and the AMI name is the only description specific enough to choose on:
    the listing's own metadata is identical for every candidate. It is also
    what ``AwsPublishedAmiResolution.displayName`` renders.
    """

    amiId: str = Field(..., title="AmiId")
    amiName: str = Field(..., title="AmiName")
    ownerId: str = Field(..., title="OwnerId")
    architecture: Optional[str] = Field(None, title="Architecture")
    platformDetails: Optional[str] = Field(None, title="PlatformDetails")
    usageOperation: Optional[str] = Field(None, title="UsageOperation")
    creationDate: Optional[str] = Field(None, title="CreationDate")
    region: str = Field(..., title="Region")


class AwsPublishedAmiResolution(BaseModel):
    """Outcome of resolving an AWS-published product to AMI candidates.

    The resolver keeps only the newest build per architecture, so
    ``unambiguous`` is True exactly when a single architecture remains. When
    it is False the caller MUST present ``candidates`` for selection rather
    than silently taking the first: the remaining candidates are different
    architectures, and picking blind would import an image that cannot run
    the user's workload.
    """

    productId: str = Field(..., title="ProductId")
    unambiguous: bool = Field(..., title="Unambiguous")
    candidates: list[AwsPublishedAmiCandidate] = Field(default_factory=list, title="Candidates")

    @property
    def displayName(self) -> str:
        """A label a user would recognise.

        Built from the candidates rather than from ``osFamily``/``osVersion``,
        which carry EC2 tokens: "WIN2022" + "10", or "SUSE" + "Enterprise
        Server 12". For an unambiguous product the AMI name is the product
        name; for an ambiguous one the shared prefix of the candidate names is
        the most specific honest description available.
        """
        if not self.candidates:
            return self.productId
        if self.unambiguous:
            return self.candidates[0].amiName
        prefix = os.path.commonprefix([c.amiName for c in self.candidates]).rstrip("-_ ")
        return prefix or self.candidates[0].amiName

    @property
    def resolved(self) -> Optional[AwsPublishedAmiCandidate]:
        """The single AMI to use, or None when the user must choose."""
        if self.unambiguous and self.candidates:
            return self.candidates[0]
        return None
