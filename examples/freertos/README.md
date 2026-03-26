# Build your first product: FreeRTOS virtual target

This tutorial takes you from an empty VEW platform to a running FreeRTOS virtual target you can SSH into. You'll create a component, bundle it into a recipe, build a machine image, publish it as a product, and provision an instance — the full VEW workflow.

Expect about 30 minutes of hands-on time, plus waiting for builds and provisioning.

## What you'll need

- A deployed VEW platform with product contributor permissions
- The two files in this folder: [`component.yaml`](component.yaml) (the EC2 Image Builder component definition) and [`product.yaml`](product.yaml) (the CloudFormation product template)

## Step 1: Create the component

A component is a single piece of software — in this case, the ARM GCC toolchain, QEMU ARM emulator, and FreeRTOS kernel. VEW maps components to [EC2 Image Builder components](https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-components.html).

1. Go to **Components** in the side navigation.
2. Choose **Create component**.
3. Fill in the form:

   | Field | Value |
   | ------- | ------- |
   | Name | `FreeRTOS` |
   | Description | `FreeRTOS is a market-leading embedded system RTOS.` |
   | Platform | **Linux** |
   | Supported architectures | **amd64** |
   | Supported OS version | **Ubuntu 2024** |

4. Choose **Create version**.
5. Fill in the version details:

   | Field | Value |
   | ------- | ------- |
   | Description | `Initial component` |
   | Software vendor | `FreeRTOS` |
   | Software version | `202411.00` |
   | Release type | **Major** |

6. Choose **Next**.
7. Open [`component.yaml`](component.yaml) from this folder and copy its contents into the **YAML Definition** form.
8. Choose **Next**.
9. Skip the dependencies page (this component has none) — choose **Next**.
10. Review everything, then choose **Next** to kick off validation.

The status shows **Validating** while VEW checks the YAML. Wait for it to change to **Released** before moving on.

## Step 2: Create the recipe

A recipe bundles one or more components into a buildable image spec. VEW maps recipes to [EC2 Image Builder recipes](https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-recipes.html).

1. Go to **Recipes** in the side navigation.
2. Choose **Create recipe**.
3. Fill in the form:

   | Field | Value |
   | ------- | ------- |
   | Name | `FreeRTOS virtual target` |
   | Description | `Virtual target for FreeRTOS` |
   | Platform | **Linux** |
   | Supported architectures | **amd64** |
   | Supported OS version | **Ubuntu 2024** |

4. From the recipes list, choose **FreeRTOS virtual target**, then choose **Create version**.
5. For **Description**, enter `Initial FreeRTOS virtual target recipe`.
6. On the components page, add:

   | Field | Value |
   | ------- | ------- |
   | Component | **FreeRTOS** |
   | Version | **1.0.0** |
   | Type | **Main** |

7. Review and choose **Create version**.
8. Wait for the status to reach **Validated**.
9. Select version **1.0.0-rc.1**, open the **Actions** dropdown, and choose **Release**.

## Step 3: Build the image

A pipeline automates image builds from a recipe. VEW maps pipelines to [EC2 Image Builder pipelines](https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-pipelines.html).

1. Go to **Pipelines** in the side navigation.
2. Choose **Create pipeline**.
3. Fill in the form:

   | Field | Value |
   | ------- | ------- |
   | Name | `FreeRTOS image build pipeline` |
   | Description | `Pipeline to build FreeRTOS image for virtual target` |
   | Schedule | `0 13 1 4 ? *` |

4. Configure the build:

   | Field | Value |
   | ------- | ------- |
   | Recipe | **FreeRTOS virtual target** |
   | Recipe version | **1.0.0** |
   | Build instance type | **m8i.2xlarge** |
   | Product | Leave empty |

5. Choose **Create Pipeline**.
6. Select **FreeRTOS image build pipeline** from the list and choose **Create image**.
7. Wait for the image status to change from **Creating** to **Created**. This takes several minutes — VEW provisions a build instance, installs the components, runs the validation phase, and captures the AMI.

## Step 4: Publish the product

A product is what end users see in the catalog. It ties a CloudFormation template to the AMI you just built.

1. Go to **Products** in the side navigation.
2. Choose **Create product**.
3. Fill in the form:

   | Field | Value |
   | ------- | ------- |
   | Name | `FreeRTOS` |
   | Description | `Virtual target running FreeRTOS` |

4. Pick the first technology item from the list.
5. For **Type**, choose **Virtual target**.
6. From the products list, choose **FreeRTOS**, then choose **Create version**.
7. For **Description**, enter `Initial FreeRTOS virtual target`.
8. In the **AMI ID** field, search for `freertos` and select the AMI you built in Step 3.
9. Choose **Next**.
10. Open [`product.yaml`](product.yaml) from this folder and copy its contents into the YAML definition form.
11. Choose **Next** to start the product version build.
12. Wait for the status to reach **Created**.

## Step 5: Launch the virtual target

1. Go to **All virtual targets** in the side navigation.
2. Find **FreeRTOS** and choose **Create**.
3. Select version **1.0.0-rc.1**, then choose **Next**.
4. Keep the default parameters — they're fine for a first run. Choose **Next**.
5. Review and choose **Launch instance**.

Provisioning takes a few minutes. Once the status shows **Running**, you're ready to connect.

## Step 6: Connect

For a full walkthrough of all connection methods (DCV browser, DCV client, SSH), see [Connect to a product](../../docs/connect-to-a-product.md).

Here's the quick SSH path:

1. Go to **My virtual targets** in the side navigation.
2. Select your FreeRTOS instance and choose **Log in**.
3. Confirm — VEW downloads an SSH key file named `connect_vew-pp-<UUID>.key`.
4. Lock down the key permissions:

   ```bash
   chmod 0600 connect_vew-pp-<UUID>.key
   ```

5. Get the public IP from **View details** → **General configuration** → **Public IP**.
6. Connect:

   ```bash
   ssh -i connect_vew-pp-<UUID>.key ubuntu@<public-ip>
   ```

7. Check that FreeRTOS is running:

   ```bash
   less /var/log/freertos-userdata.log
   ```

You should see output from the FreeRTOS CORTEX_MPS2_QEMU demo. That's it — you've gone from zero to a running virtual target.

## What's next

- [Launch a product](../../docs/launch-a-product.md) — the short version, for when you already have products in the catalog
- [Connect to a product](../../docs/connect-to-a-product.md) — DCV browser, DCV client, and SSH options
- [android-cuttlefish/](../android-cuttlefish/) — a more advanced example with nested virtualization
