# Android Cuttlefish virtual target

This example provisions an Android 15 virtual device using [Cuttlefish](https://source.android.com/docs/devices/cuttlefish), Google's reference virtual Android device. It runs on Intel instances with nested virtualization enabled (c8i or m8i families).

## Files

- `component.yaml` — EC2 Image Builder component that registers the Cuttlefish apt repository, installs host packages, and downloads the Android 15 x86_64 phone image from ci.android.com.
- `product.yaml` — CloudFormation template that launches a c8i.2xlarge instance with `CpuOptions.NestedVirtualization` enabled. Because CloudFormation's `AWS::EC2::Instance` doesn't support that parameter, the template uses a Lambda-backed Custom Resource that calls the EC2 RunInstances API directly.

## Dependencies

The recipe for this example needs two components:

1. The [qemu-kvm](../qemu-kvm/) component — installs QEMU, KVM kernel modules, and libvirt
2. This component — installs Cuttlefish and the Android image on top

Add them in that order when creating the recipe.

## How to use

The workflow is the same as the [FreeRTOS tutorial](../freertos/) — create a component, create a recipe, build an image through a pipeline, publish the product, and provision it. The key differences:

- You'll create two components instead of one (qemu-kvm first, then this one)
- The recipe includes both components, with qemu-kvm listed before android-cuttlefish
- Use `c8i.2xlarge` or `m8i.2xlarge` as the build instance type (nested virtualization requires Intel)
- The product template uses a 500 GB volume (Android images are large)
