import uuid


def generate_provisioned_product_id(type_prefix: str) -> str:
    return "-".join([type_prefix, str(uuid.uuid4())])
