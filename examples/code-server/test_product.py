from pathlib import Path

import yaml
from jinja2 import Template


PRODUCT_PATH = Path(__file__).with_name("product.yaml")


class CloudFormationLoader(yaml.SafeLoader):
    pass


def construct_cloudformation_tag(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    else:
        value = loader.construct_mapping(node)
    return {f"!{tag_suffix}": value}


CloudFormationLoader.add_multi_constructor("!", construct_cloudformation_tag)


def render_product() -> str:
    template = Template(PRODUCT_PATH.read_text(encoding="utf-8"))
    return template.render(
        product_name="Code Server",
        product_version="1.0.0",
        ami_ids={"us-east-1": "ami-0123456789abcdef0"},
    )


def load_product() -> dict:
    return yaml.load(render_product(), Loader=CloudFormationLoader)


def test_product_exposes_the_parameters_and_outputs_required_by_vew() -> None:
    product = load_product()

    assert {"InstanceType", "OwnerTID", "SubnetId", "UserSecurityGroupId", "VolumeSize", "VpcIdSSM"} <= set(
        product["Parameters"]
    )
    assert {"FeatureToggles", "InstanceId", "PrivateIP", "PublicIP", "UserCredentialsSecret"} <= set(
        product["Outputs"]
    )


def test_product_launches_the_rendered_ami_with_encrypted_storage() -> None:
    product = load_product()
    workbench = product["Resources"]["Workbench"]["Properties"]
    volume = workbench["BlockDeviceMappings"][0]["Ebs"]

    assert workbench["ImageId"] == {"!FindInMap": ["RegionMap", {"!Ref": "AWS::Region"}, "AMIId"]}
    assert volume["Encrypted"] is True
    assert volume["VolumeType"] == "gp3"


def test_product_does_not_shrink_the_ami_root_snapshot() -> None:
    product = load_product()
    volume_size = product["Parameters"]["VolumeSize"]

    assert volume_size["Default"] == 100
    assert min(volume_size["AllowedValues"]) >= 100


def test_product_starts_code_server_without_exposing_port_8080() -> None:
    product = load_product()
    rendered = render_product()
    ingress = product["Resources"]["SecurityGroup"]["Properties"]["SecurityGroupIngress"]

    assert "code-server.service" in rendered
    assert all(rule.get("FromPort") != 8080 and rule.get("ToPort") != 8080 for rule in ingress)


def test_product_generates_revealable_per_instance_credentials() -> None:
    product = load_product()
    secret = product["Resources"]["WorkbenchUserCredentials"]
    generated = secret["Properties"]["GenerateSecretString"]

    assert secret["Type"] == "AWS::SecretsManager::Secret"
    assert generated["SecretStringTemplate"] == '{"username":"ubuntu"}'
    assert generated["GenerateStringKey"] == "password"
    assert generated["PasswordLength"] == 32
    assert generated["ExcludePunctuation"] is True
    assert {
        "Key": "vew:provisionedProduct:ownerId",
        "Value": {"!Ref": "OwnerTID"},
    } in secret["Properties"]["Tags"]
    assert product["Outputs"]["UserCredentialsSecret"]["Value"] == {
        "!Ref": "WorkbenchUserCredentials"
    }


def test_instance_can_read_only_its_generated_credential() -> None:
    product = load_product()
    policies = product["Resources"]["InstanceRole"]["Properties"]["Policies"]
    policy = next(policy for policy in policies if policy["PolicyName"] == "ReadWorkbenchUserCredential")
    statement = policy["PolicyDocument"]["Statement"][0]

    assert statement["Action"] == "secretsmanager:GetSecretValue"
    assert statement["Resource"] == {"!Ref": "WorkbenchUserCredentials"}


def test_product_explicitly_assigns_a_public_ip_with_both_security_groups() -> None:
    product = load_product()
    workbench = product["Resources"]["Workbench"]["Properties"]
    interface = workbench["NetworkInterfaces"][0]

    assert interface["AssociatePublicIpAddress"] is True
    assert interface["DeleteOnTermination"] is True
    assert interface["DeviceIndex"] == "0"
    assert interface["SubnetId"] == {"!Ref": "SubnetId"}
    assert interface["GroupSet"] == [
        {"!GetAtt": "SecurityGroup.GroupId"},
        {"!Ref": "UserSecurityGroupId"},
    ]
    assert "SubnetId" not in workbench
    assert "SecurityGroupIds" not in workbench
    assert workbench["MetadataOptions"]["HttpTokens"] == "required"
    assert product["Outputs"]["PublicIP"]["Value"] == {"!GetAtt": "Workbench.PublicIp"}


def test_product_applies_secret_without_embedding_a_password() -> None:
    rendered = render_product()

    assert "/usr/local/bin/aws secretsmanager get-secret-value" in rendered
    assert "jq -er '.username'" in rendered
    assert "jq -er '.password'" in rendered
    assert "printf '%s:%s\\n' \"$username\" \"$password\" | chpasswd" in rendered
    assert "systemctl enable --now gdm3.service dcvserver.service code-server.service" in rendered
    assert "authentication=none" not in rendered


def test_product_has_no_public_ingress_cidr() -> None:
    product = load_product()
    ingress = product["Resources"]["SecurityGroup"]["Properties"]["SecurityGroupIngress"]

    assert all(rule.get("CidrIp") != "0.0.0.0/0" for rule in ingress)
    assert all(rule.get("CidrIpv6") != "::/0" for rule in ingress)
