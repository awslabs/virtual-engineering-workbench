import enum

ATTRIBUTE_NAME_ENTITY = "entity"


class DBPrefix(str, enum.Enum):
    PROJECT = "PROJECT"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    AWS_ACCOUNT = "AWS_ACCOUNT"
    PORTFOLIO = "PORTFOLIO"
    VERSION = "VERSION"
    AMI = "AMI"
    SHARED_AMI = "SHARED_AMI"

    def __str__(self):
        return str(self.value)
