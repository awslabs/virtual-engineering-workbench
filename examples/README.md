# Examples

Ready-made component definitions and product templates you can use to get started with VEW.

| Example | What it does | Includes product template? |
|---------|-------------|---------------------------|
| [freertos/](freertos/) | ARM GCC cross-compiler, FreeRTOS kernel, QEMU ARM emulator | Yes |
| [android-cuttlefish/](android-cuttlefish/) | Android 15 Cuttlefish virtual device with nested virtualization | Yes |
| [qemu-kvm/](qemu-kvm/) | QEMU/KVM with libvirt for nested virtualization on Intel instances | No (component only) |

If you're new to VEW, start with the [FreeRTOS tutorial](freertos/) — it walks through the full workflow from component creation to a running virtual target.

## Logging in

Both product templates give each virtual target an SSH key the same way the default workbench template does: an ed25519 `AWS::EC2::KeyPair`, `KeyName` on the instance, and an output named `SSHKeyPair` whose value is the `/ec2/keypair/<id>` parameter path. VEW reads that output to offer SSH in the **Log in** dialog; remove all three to turn SSH off. [Step 6 of the FreeRTOS tutorial](freertos/README.md#step-6-connect) walks through the login, and [Connect to a product](../docs/connect-to-a-product.md) covers every connection method.
