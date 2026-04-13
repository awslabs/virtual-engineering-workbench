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

## Connect to the device

Once your virtual target is running, get its public IP and SSH key by following the same steps as [Step 6 of the FreeRTOS tutorial](../freertos/README.md#step-6-connect):

1. Go to **My virtual targets** in the side navigation.
2. Select your Android Cuttlefish instance and choose **Log in**.
3. Confirm — VEW downloads an SSH key file named `connect_vew-pp-<UUID>.key`.
4. Lock down the key permissions:

   ```bash
   chmod 0600 connect_vew-pp-<UUID>.key
   ```

5. Get the public IP from **View details** → **General configuration** → **Public IP**.

### Cuttlefish operator (browser)

Open the device's public IP in your browser:

```
https://<public-ip>:8443
```

This opens the Cuttlefish operator web UI, which gives you a virtual screen, controls, and logs for the Android device directly in the browser.

### ADB over SSH tunnel

To use ADB from your local machine, establish an SSH tunnel that forwards the Cuttlefish ADB port:

1. Open the tunnel:

   ```bash
   ssh -i connect_vew-pp-<UUID>.key -L 6520:localhost:6520 ubuntu@<public-ip>
   ```

2. In a separate terminal, connect ADB through the tunnel:

   ```bash
   adb connect localhost:6520
   ```

3. Verify the device is visible:

   ```bash
   adb devices
   ```

   You should see `localhost:6520` listed as an attached device.
