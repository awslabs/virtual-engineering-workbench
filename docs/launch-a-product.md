# Launch a product

This covers provisioning any product from the VEW catalog — workbenches and virtual targets alike. If you haven't created a product yet, start with the [FreeRTOS tutorial](../examples/freertos/).

## Steps

1. Go to **All workbenches** or **All virtual targets** in the side navigation (depending on the product type).
2. Find the product you want and choose **Create**.
3. Pick a **Region**. Choose the one closest to your location for the best latency.
4. Pick a **Stage**. For released products, choose **PROD**.
5. Pick a **Version**. The version details panel shows what's included in each one. Go with the latest unless you have a reason not to.
6. Choose **Next**.
7. Set the **parameters**. These control the instance type and storage size. Start with the smallest configuration — you can always reprovision with a larger one later.
8. Choose **Next**.
9. Review the summary and choose **Launch instance**.

The product appears in **My workbenches** or **My virtual targets**. Provisioning takes a few minutes (check the "Estimated provisioning time" on the product card). Once the status shows **Running**, you can connect to it.

## Stop and start

You don't have to terminate a product when you're done for the day. Stopping it keeps the configuration and storage intact, and it's much faster to start again (under 2 minutes) than provisioning from scratch.

- To stop: select the product and choose **Stop**. The underlying EC2 instance stops — no compute charges while stopped, though EBS storage charges still apply.
- To start: select the stopped product and choose **Start**. It goes back to **Running** within a couple of minutes.

## Terminate

When you no longer need the product, select it and choose **Terminate**. This deletes the underlying resources. The action is irreversible — any data on the instance that isn't backed up elsewhere is lost.
