from abc import ABC, abstractmethod

from app.packaging.domain.read_models.aws_published_ami import AwsPublishedAmiResolution


class AwsPublishedAmiResolverService(ABC):
    """Resolves an AWS-published Marketplace product to usable AMI ids.

    Exists because AWS publishes no listing-to-AMI mapping for its own
    products. ``GetListing``, ``GetProduct`` and ``GetOffer`` carry no AMI id,
    and the ``/aws/service/marketplace/`` SSM tree indexes partner vendors
    only, never amazon, microsoft, redhat or suse. The mapping therefore has
    to be derived from runtime data.

    Implementations combine two sources: the Marketplace offer, whose product
    code is the value AWS stamps onto the AMIs published for that product, and
    ``ec2:DescribeImages``, which lists the vendor's live published images.

    An implementation never guesses. It reports ``unambiguous=False`` with its
    candidates when it cannot narrow the answer to one AMI, and a resolution
    with no candidates when nothing identifies an AMI at all.
    """

    @abstractmethod
    def resolve(self, product_id: str, region: str) -> AwsPublishedAmiResolution: ...
