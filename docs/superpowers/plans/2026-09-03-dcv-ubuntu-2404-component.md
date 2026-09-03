# Ubuntu 24 Amazon DCV Component Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a secure Amazon DCV desktop component for Ubuntu 24.04 x86_64 and make the code-server POC directly reachable with unique per-instance credentials.

**Architecture:** A release-specific EC2 Image Builder component installs the non-GPU Ubuntu desktop and pinned DCV server/web-viewer packages, then configures a PAM-authenticated automatic `console` session owned by `ubuntu`. The product template owns runtime concerns: a generated Secrets Manager credential, first-boot password application, an explicitly public primary network interface, and the outputs VEW consumes.

**Tech Stack:** EC2 Image Builder AWSTOE YAML, Ubuntu 24.04, Amazon DCV 2025.0-20103, CloudFormation/Jinja YAML, AWS Secrets Manager, pytest, PyYAML

**Spec:** `docs/superpowers/specs/2026-09-03-dcv-components-design.md`

## Global Constraints

- Support only official Ubuntu Server 24.04 x86_64 images.
- Pin DCV to `2025.0-20103` and the archive SHA-256 to `a39374d39f2d849bd13ee101970bb9eea15a8c5ec743799b7cbb7f562ece9e17`.
- Use DCV `system` authentication and never enable `none` authentication.
- Use the automatic console session ID `console`, owned by `ubuntu`.
- Install the DCV web viewer because the existing VEW frontend opens the instance's DCV URL.
- Keep code-server on `127.0.0.1:8080`; do not add an ingress rule for port 8080.
- Add no public ingress CIDR. VEW's attached user security group remains responsible for `/32` authorization.
- Generate the workstation password per provisioned instance; never store it in an AMI or embed it in user data.
- Tag the secret `vew:provisionedProduct:ownerId` with `OwnerTID` so VEW's provisioning role can reveal it to the owner.
- Preserve unrelated worktree changes.

---

### Task 1: Add the Ubuntu 24 DCV component contract

**Files:**
- Create: `examples/code-server/test_dcv_component.py`
- Create: `examples/code-server/dcv-ubuntu-2404-component.yaml`

**Interfaces:**
- Consumes: Ubuntu user `ubuntu`; official DCV archive `https://d1uj6qtbmh3dt5.cloudfront.net/2025.0/Servers/nice-dcv-2025.0-20103-ubuntu2404-x86_64.tgz`
- Produces: enabled `gdm3.service` and `dcvserver.service`, `/etc/dcv/dcv.conf`, `/etc/X11/xorg.conf`, automatic DCV session `console`, TCP listener on 8443

- [x] **Step 1: Write the component structure and security tests**

Create `examples/code-server/test_dcv_component.py` with these helpers and assertions:

```python
from pathlib import Path

import yaml


COMPONENT_PATH = Path(__file__).with_name("dcv-ubuntu-2404-component.yaml")


def load_component() -> dict:
    return yaml.safe_load(COMPONENT_PATH.read_text(encoding="utf-8"))


def commands_for(phase_name: str) -> str:
    phase = next(phase for phase in load_component()["phases"] if phase["name"] == phase_name)
    return "\n".join(
        command
        for step in phase["steps"]
        for command in step["inputs"]["commands"]
    )


def test_component_uses_awstoe_schema() -> None:
    component = load_component()
    assert component["schemaVersion"] == 1.0
    assert [phase["name"] for phase in component["phases"]] == ["build", "validate"]


def test_component_rejects_unsupported_images() -> None:
    build = commands_for("build")
    assert 'test "$ID" = "ubuntu"' in build
    assert 'test "$VERSION_ID" = "24.04"' in build
    assert 'test "$(uname -m)" = "x86_64"' in build


def test_component_verifies_pinned_dcv_archive() -> None:
    build = commands_for("build")
    assert "2025.0/Servers/nice-dcv-2025.0-20103-ubuntu2404-x86_64.tgz" in build
    assert "a39374d39f2d849bd13ee101970bb9eea15a8c5ec743799b7cbb7f562ece9e17" in build
    assert "sha256sum -c -" in build


def test_component_installs_desktop_and_web_viewer() -> None:
    build = commands_for("build")
    assert "ubuntu-desktop-minimal" in build
    assert "gdm3" in build
    assert "xserver-xorg-video-dummy" in build
    assert "nice-dcv-server_2025.0.20103-1_amd64.ubuntu2404.deb" in build
    assert "nice-dcv-web-viewer_2025.0.20103-1_amd64.ubuntu2404.deb" in build
    assert "WaylandEnable=false" in build
    assert 'Driver "dummy"' in build


def test_component_requires_pam_and_owner_only_console_session() -> None:
    build = commands_for("build")
    assert 'authentication="system"' in build
    assert 'authentication="none"' not in build
    assert "create-session=true" in build
    assert 'owner="ubuntu"' in build
    assert "systemctl enable gdm3.service dcvserver.service" in build


def test_component_validates_listener_and_console_session() -> None:
    validate = commands_for("validate")
    assert "dpkg-query" in validate
    assert "systemctl is-enabled" in validate
    assert "ss -lnt" in validate
    assert "8443" in validate
    assert "dcv list-sessions" in validate
    assert "journalctl -u dcvserver.service" in validate
```

- [x] **Step 2: Run the component tests and confirm the missing file failure**

Run:

```bash
uv run --project backend pytest examples/code-server/test_dcv_component.py -q
```

Expected: FAIL with `FileNotFoundError` for `dcv-ubuntu-2404-component.yaml`.

- [x] **Step 3: Implement the AWSTOE build phase**

Create `examples/code-server/dcv-ubuntu-2404-component.yaml` with `schemaVersion: 1.0`, `build` and `validate` phases. The build phase must use separate `ExecuteBash` steps named `ValidatePlatform`, `InstallDesktop`, `ConfigureDisplay`, `InstallDcv`, and `ConfigureDcv`.

Use this platform guard:

```bash
set -euo pipefail
. /etc/os-release
test "$ID" = "ubuntu"
test "$VERSION_ID" = "24.04"
test "$(uname -m)" = "x86_64"
getent passwd ubuntu >/dev/null
```

Use noninteractive package installation:

```bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
echo "gdm3 shared/default-x-display-manager select gdm3" | debconf-set-selections
apt-get update
apt-get install -y ubuntu-desktop-minimal gdm3 xserver-xorg-video-dummy ca-certificates curl jq iproute2
```

Create a separate `examples/aws-cli/component.yaml` that supports Ubuntu 22.04 and 24.04 x86_64. It installs the pinned AWS CLI v2 bundle system-wide under `/usr/local`, verifies its SHA-256 digest before running the installer, and validates the exact installed version. Do not depend on an `awscli` APT candidate, because it is not available from every Ubuntu image's enabled package sources.

Set `WaylandEnable=false` under the existing `[daemon]` section in `/etc/gdm3/custom.conf`, replacing a commented or active `WaylandEnable` entry when present and inserting it when absent. Write `/etc/X11/xorg.conf` with the AWS-recommended dummy device, monitor, and screen:

```text
Section "Device"
    Identifier "DummyDevice"
    Driver "dummy"
    Option "UseEDID" "false"
    VideoRam 512000
EndSection

Section "Monitor"
    Identifier "DummyMonitor"
    HorizSync 5.0 - 1000.0
    VertRefresh 5.0 - 200.0
    Option "ReducedBlanking"
EndSection

Section "Screen"
    Identifier "DummyScreen"
    Device "DummyDevice"
    Monitor "DummyMonitor"
    DefaultDepth 24
    SubSection "Display"
        Viewport 0 0
        Depth 24
        Virtual 4096 2160
    EndSubSection
EndSection
```

Download and install DCV using exact paths, not broad package globs:

```bash
set -euo pipefail
archive=/tmp/nice-dcv-ubuntu2404-x86_64.tgz
install_dir=/tmp/nice-dcv-2025.0-20103-ubuntu2404-x86_64
curl -fsSL https://d1uj6qtbmh3dt5.cloudfront.net/2025.0/Servers/nice-dcv-2025.0-20103-ubuntu2404-x86_64.tgz -o "$archive"
echo "a39374d39f2d849bd13ee101970bb9eea15a8c5ec743799b7cbb7f562ece9e17  $archive" | sha256sum -c -
tar -xzf "$archive" -C /tmp
apt-get install -y \
  "$install_dir/nice-dcv-server_2025.0.20103-1_amd64.ubuntu2404.deb" \
  "$install_dir/nice-dcv-web-viewer_2025.0.20103-1_amd64.ubuntu2404.deb"
rm -f "$archive"
rm -rf "$install_dir"
apt-get clean
```

Write this minimal `/etc/dcv/dcv.conf`, then enable the services without starting them in the build step:

```ini
[security]
authentication="system"

[session-management]
create-session=true

[session-management/automatic-console-session]
owner="ubuntu"
```

Finish with:

```bash
usermod -aG video dcv
systemctl set-default graphical.target
systemctl enable gdm3.service dcvserver.service
```

- [x] **Step 4: Implement the AWSTOE validation phase**

Add `VerifyDcvConfiguration` and `VerifyDcvRuntime` `ExecuteBash` steps. The configuration step must use `dpkg-query -W` for `nice-dcv-server`, `nice-dcv-web-viewer`, `gdm3`, and `xserver-xorg-video-dummy`; fixed-string `grep` checks for the secure settings; `systemctl is-enabled` for both services; and `systemd-analyze verify` for their units.

The runtime step must start GDM3 and DCV, wait up to 60 seconds for both TCP 8443 and the `console` session, verify `ubuntu` appears in `dcv list-sessions`, and stop the services on exit. On failure, print:

```bash
systemctl status gdm3.service dcvserver.service --no-pager || true
journalctl -u gdm3.service -u dcvserver.service --no-pager -n 100 || true
dcv list-sessions || true
```

- [x] **Step 5: Run the component tests**

Run:

```bash
uv run --project backend pytest examples/code-server/test_dcv_component.py -q
```

Expected: 6 tests PASS.

- [ ] **Step 6: Validate the component with AWSTOE**

Run:

```bash
validation_dir=$(mktemp -d)
curl -fsSL https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/linux/amd64/awstoe -o "$validation_dir/awstoe"
chmod +x "$validation_dir/awstoe"
"$validation_dir/awstoe" validate --documents examples/code-server/dcv-ubuntu-2404-component.yaml --trace
```

Expected: AWSTOE reports a successful document validation.

- [x] **Step 7: Commit the component**

```bash
git add examples/code-server/test_dcv_component.py examples/code-server/dcv-ubuntu-2404-component.yaml
git commit -m "feat: add Ubuntu 24 DCV component"
```

---

### Task 2: Add per-instance credentials and direct public connectivity

**Files:**
- Modify: `examples/code-server/test_product.py`
- Modify: `examples/code-server/product.yaml`

**Interfaces:**
- Consumes: component-created `ubuntu` user, `gdm3.service`, `dcvserver.service`, and `code-server.service`; VEW parameter `UserSecurityGroupId`
- Produces: CloudFormation outputs `PublicIP` and `UserCredentialsSecret`; one generated secret containing `username` and `password`; a public primary ENI protected by both VEW security groups

- [x] **Step 1: Write failing product tests for credentials**

Append these tests to `examples/code-server/test_product.py`:

```python
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
```

Update the existing VEW-output assertion to require `PublicIP` and `UserCredentialsSecret`.

- [x] **Step 2: Write failing product tests for networking and bootstrap**

Append:

```python
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

    assert "aws secretsmanager get-secret-value" in rendered
    assert "jq -er '.username'" in rendered
    assert "jq -er '.password'" in rendered
    assert 'printf \'%s:%s\\n\' "$username" "$password" | chpasswd' in rendered
    assert "systemctl enable --now gdm3.service dcvserver.service code-server.service" in rendered
    assert "authentication=none" not in rendered


def test_product_has_no_public_ingress_cidr() -> None:
    product = load_product()
    ingress = product["Resources"]["SecurityGroup"]["Properties"]["SecurityGroupIngress"]

    assert all(rule.get("CidrIp") != "0.0.0.0/0" for rule in ingress)
    assert all(rule.get("CidrIpv6") != "::/0" for rule in ingress)
```

- [x] **Step 3: Run the new product tests and confirm they fail**

Run:

```bash
uv run --project backend pytest examples/code-server/test_product.py -q
```

Expected: FAIL because `WorkbenchUserCredentials`, `PublicIP`, `UserCredentialsSecret`, `NetworkInterfaces`, and `MetadataOptions` do not exist.

- [x] **Step 4: Add the secret, output, and least-privilege role policy**

Add:

```yaml
Outputs:
  PublicIP:
    Description: Public IP address of the newly created EC2 instance
    Value: !GetAtt Workbench.PublicIp
  UserCredentialsSecret:
    Description: Secret containing the workstation login credentials
    Value: !Ref WorkbenchUserCredentials

Resources:
  WorkbenchUserCredentials:
    Type: AWS::SecretsManager::Secret
    Properties:
      Description: Per-instance login credentials for the code-server workbench
      GenerateSecretString:
        SecretStringTemplate: '{"username":"ubuntu"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludePunctuation: true
        RequireEachIncludedType: true
      Tags:
        - Key: vew:provisionedProduct:ownerId
          Value: !Ref OwnerTID
```

Append this inline policy to `InstanceRole.Properties.Policies`:

```yaml
- PolicyName: ReadWorkbenchUserCredential
  PolicyDocument:
    Version: 2012-10-17
    Statement:
      - Effect: Allow
        Action: secretsmanager:GetSecretValue
        Resource: !Ref WorkbenchUserCredentials
```

- [x] **Step 5: Make the primary interface explicitly public and require IMDSv2**

Remove the top-level `SubnetId` and `SecurityGroupIds` properties from `Workbench.Properties`. Add:

```yaml
MetadataOptions:
  HttpEndpoint: enabled
  HttpTokens: required
NetworkInterfaces:
  - AssociatePublicIpAddress: true
    DeleteOnTermination: true
    DeviceIndex: "0"
    GroupSet:
      - !GetAtt SecurityGroup.GroupId
      - !Ref UserSecurityGroupId
    SubnetId: !Ref SubnetId
```

- [x] **Step 6: Apply the secret and start workstation services at first boot**

Replace the current user data body with:

```bash
#!/bin/bash
set -euo pipefail

AWS_REGION="${AWS::Region}"
secret_json=$(aws secretsmanager get-secret-value \
  --secret-id '${WorkbenchUserCredentials}' \
  --region "$AWS_REGION" \
  --query SecretString \
  --output text)
username=$(printf '%s' "$secret_json" | jq -er '.username')
password=$(printf '%s' "$secret_json" | jq -er '.password')
printf '%s:%s\n' "$username" "$password" | chpasswd
unset password secret_json

systemctl daemon-reload
systemctl enable --now gdm3.service dcvserver.service code-server.service
```

Do not add `set -x`, print the secret, or put the password in a process argument.

- [x] **Step 7: Run all focused tests**

Run:

```bash
uv run --project backend pytest \
  examples/code-server/test_component.py \
  examples/code-server/test_dcv_component.py \
  examples/code-server/test_product.py \
  -q
```

Expected: all focused tests PASS.

- [ ] **Step 8: Validate formatting and both component documents**

Run:

```bash
git diff --check
validation_dir=$(mktemp -d)
curl -fsSL https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/linux/amd64/awstoe -o "$validation_dir/awstoe"
chmod +x "$validation_dir/awstoe"
"$validation_dir/awstoe" validate \
  --documents examples/code-server/component.yaml,examples/code-server/dcv-ubuntu-2404-component.yaml \
  --trace
```

Expected: `git diff --check` produces no output and AWSTOE validates both documents successfully.

- [x] **Step 9: Commit the product integration**

```bash
git add examples/code-server/product.yaml examples/code-server/test_product.py
git commit -m "feat: integrate DCV workstation access"
```

---

### Task 3: Perform the EC2 integration acceptance checks

**Files:**
- No repository changes required

**Interfaces:**
- Consumes: published Ubuntu 24 DCV component, code-server component, rendered product template, a public subnet with an internet-gateway route, and VEW `AuthorizeUserIp` enabled
- Produces: evidence that image build, first boot, credential reveal, `/32` authorization, and DCV browser login work together

- [ ] **Step 1: Build the image through VEW**

Create and validate the Ubuntu 24 DCV component version, include it after the code-server component in the recipe, and build an image using VEW's `Ubuntu 24`, `amd64` configuration.

Expected: component validation observes TCP 8443 and session `console`; the image reaches a successful build state.

- [ ] **Step 2: Launch the product into a public subnet**

Launch the rendered product with a subnet whose route table sends `0.0.0.0/0` to an internet gateway.

Expected: the provisioned product records non-empty private and public IPv4 addresses.

- [ ] **Step 3: Verify first-boot state without exposing credentials**

Using SSM Session Manager, run:

```bash
sudo cloud-init status --wait
sudo systemctl status gdm3.service dcvserver.service code-server.service --no-pager
sudo dcv list-sessions
sudo ss -lntp | grep ':8443'
curl -fsS http://127.0.0.1:8080/healthz
```

Expected: cloud-init is complete, all three services are active, `console` is owned by `ubuntu`, TCP 8443 is listening, and code-server reports healthy.

- [ ] **Step 4: Verify VEW authentication and connection**

Use **Show login credentials** and confirm it returns username `ubuntu` with the generated password. Choose **DCV Browser**, accept the POC self-signed-certificate warning after verifying the fingerprint, and authenticate to `console`.

Expected: the Ubuntu desktop opens and `http://127.0.0.1:8080` loads code-server inside its browser. The user security group contains TCP 8443 ingress from the browser request's public IP as `/32`, with no public-wide ingress rule.
