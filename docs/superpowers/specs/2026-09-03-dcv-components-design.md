# Amazon DCV Component for the Code-Server POC

## Goal

Provide direct, browser-based Amazon DCV access to the code-server workstation POC on official Ubuntu Server 24.04 x86_64 AMIs. Keep the image component small and explicit so failures can be diagnosed without cross-release branching.

This is a public proof of concept, not the final production access architecture. The instance receives a public IPv4 address, while VEW restricts supported connection ports to the current user's observed public IP using `/32` security-group rules. DCV still requires PAM credentials and TLS.

## Scope

The change adds one EC2 Image Builder component:

- `dcv-ubuntu-2404-component.yaml`

The component supports only Ubuntu 24.04 on x86_64, which matches VEW's current Linux/amd64 packaging test matrix. It must fail before installing packages when used with a different OS release or CPU architecture. Ubuntu 22.04 support can be added later as a separate component after VEW supports that OS in its packaging and recipe models.

The existing `product.yaml` is extended to provide a public network interface and per-instance credentials. The existing code-server component remains separate and continues binding code-server to `127.0.0.1:8080` with no direct network exposure.

## Image Component Design

The component performs this sequence:

1. Verify `/etc/os-release` identifies Ubuntu and the expected release, and verify `uname -m` is `x86_64`.
2. Install the Ubuntu graphical environment, GDM3, Xorg, the XDummy video driver, and supporting utilities non-interactively.
3. Disable Wayland because Amazon DCV console sessions use Xorg.
4. Configure an XDummy display suitable for a non-GPU `m8i` instance, with a maximum virtual resolution of 4096 by 2160.
5. Download the Ubuntu 24.04 Amazon DCV 2025.0-20103 archive from its versioned AWS CloudFront URL.
6. Verify the downloaded archive with the pinned SHA-256 digest `a39374d39f2d849bd13ee101970bb9eea15a8c5ec743799b7cbb7f562ece9e17`.
7. Install `nice-dcv-server` and `nice-dcv-web-viewer` from the archive. Virtual-session and GPU packages are excluded.
8. Add the `dcv` service account to the `video` group.
9. Configure `/etc/dcv/dcv.conf` with `authentication="system"`, automatic console-session creation, and `ubuntu` as the session owner.
10. Set the system's default boot target to `graphical.target` and enable GDM3 and `dcvserver`.
11. Remove downloaded installation artifacts and package-manager caches.

The DCV default permissions remain in effect. They grant the session owner access and do not create a shared session. DCV's generated self-signed TLS certificate is acceptable for this POC, although users will receive a certificate warning. A trusted hostname and certificate are explicitly outside this change.

## Component Validation

The Image Builder validation phase checks:

- the OS release and architecture;
- the DCV server and web-viewer packages;
- GDM3, Xorg, and XDummy installation;
- Wayland being disabled;
- `authentication="system"` and the automatic `console` session configuration;
- the absence of DCV `authentication="none"`;
- enabled GDM3 and DCV services;
- a valid DCV configuration and systemd units;
- after starting the graphical target and DCV, a listener on TCP 8443 and a `console` session owned by `ubuntu`.

A validation failure must emit service status and recent journal output before returning a non-zero exit code.

## Per-Instance Credentials

`product.yaml` creates an `AWS::SecretsManager::Secret` for every provisioned workstation. Its JSON value contains:

```json
{"username":"ubuntu","password":"generated-by-secrets-manager"}
```

The generated password is 32 characters and excludes characters that make shell or JSON handling ambiguous. The instance role receives `secretsmanager:GetSecretValue` only for this secret.

The secret is tagged `vew:provisionedProduct:ownerId` with `OwnerTID`. VEW's cross-account provisioning role requires this ownership tag before it can reveal the credential to the provisioned-product owner.

At first boot, user data retrieves the secret in the instance's region, extracts the username and password without printing them, and passes them to `chpasswd` through standard input. It then enables and starts GDM3, DCV, and code-server. Failure causes user data to exit non-zero and leaves diagnostic output that does not include the password.

The CloudFormation output `UserCredentialsSecret` contains the secret ARN returned by `Ref`. VEW already recognizes that output and allows only the provisioned-product owner to reveal the credentials through the existing **Show login credentials** action.

The password is not stored in either AMI and is not embedded in CloudFormation user data.

## Public Networking

DCV itself does not require a public IP. This POC does because the public VEW frontend opens the workstation address directly and no VPN, private proxy, or DCV gateway is in scope.

The EC2 resource uses one primary network interface with:

- `AssociatePublicIpAddress: true`;
- the selected `SubnetId`;
- the product security group and `UserSecurityGroupId`;
- `DeleteOnTermination: true`.

The template adds a `PublicIP` output. It requires IMDSv2 through `MetadataOptions.HttpTokens: required`.

No public CIDR ingress rule is added by the product. The attached VEW user security group remains responsible for adding the current API Gateway source IP as `/32`. The product's existing security-group-reference rules permit traffic from the user's other VEW resources but do not permit arbitrary internet clients.

## Failure Handling

- Unsupported images fail during the first component step with the detected OS version and architecture.
- Package downloads use HTTPS, fixed versioned URLs, and fixed SHA-256 digests.
- Missing expected packages in an archive fail rather than using a broad or guessed package match.
- Credential bootstrap fails closed: DCV keeps PAM authentication, and no fallback password or unauthenticated mode is enabled.
- If the instance has no usable internet route despite receiving a public IP, VEW will show the address but connection will fail. Route-table and internet-gateway configuration remain deployment prerequisites.

## Tests and Verification

Repository tests will parse the component document and assert:

- valid EC2 Image Builder phase structure;
- the Ubuntu 24.04 guard, versioned URL, package names, and SHA-256 value;
- secure authentication and console-owner configuration;
- installation of the web viewer and non-GPU desktop prerequisites;
- no unauthenticated DCV configuration.

Product-template tests will assert:

- a generated per-instance credential secret and least-privilege read policy;
- the VEW provisioned-product owner tag on the secret;
- a `UserCredentialsSecret` output;
- explicit public-IP association and a `PublicIP` output;
- IMDSv2 enforcement;
- both required security groups on the primary interface;
- no `0.0.0.0/0` or `::/0` ingress rule;
- secure password application through standard input rather than command arguments.

The component will be checked with `awstoe validate`, and all focused Python tests will run locally. Final integration acceptance requires building and launching an image from an official Ubuntu 24.04 x86_64 AMI, then confirming browser DCV login to the `console` session and access to code-server at `http://127.0.0.1:8080` inside the desktop.

## Out of Scope

- Ubuntu 22.04, ARM64, and non-Ubuntu distributions
- GPU acceleration and `nice-dcv-gl`
- DCV virtual sessions and `nice-xdcv`
- Active Directory and external token authentication
- A DCV gateway or reverse proxy
- Public DNS and a CA-issued TLS certificate
- Changes to VEW's existing dynamic IP-authorization behavior
