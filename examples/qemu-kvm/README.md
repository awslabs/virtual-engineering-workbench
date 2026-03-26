# QEMU/KVM nested virtualization

This is a component-only example — there's no product template. It's a building block used by other examples (like [android-cuttlefish](../android-cuttlefish/)) that need nested virtualization.

## What it installs

- QEMU and KVM packages (`qemu-kvm`, `qemu-system-x86`, `libvirt-daemon-system`)
- KVM kernel module configuration for Intel processors (`kvm_intel nested=1`)
- libvirt management tools (`virsh`, `virt-install`, `bridge-utils`)

## Target instances

This component targets Intel instances that support nested virtualization — specifically the c8i family (e.g., `c8i.2xlarge`). The instance must be launched with `CpuOptions.NestedVirtualization` set to `enabled`.

During image build, `/dev/kvm` won't be available (the build instance may not have nested virtualization enabled). The validation phase checks that packages are installed and module config files exist, but skips runtime KVM checks.

## How to use

Create this as a component in VEW, then reference it as a dependency in recipes that need KVM support. See the [FreeRTOS tutorial](../freertos/) for the step-by-step component creation process.
