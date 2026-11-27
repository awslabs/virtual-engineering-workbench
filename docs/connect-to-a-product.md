# Connect to a product

Once your product is in **Running** state, there are up to four ways to connect: DCV in the browser, the DCV desktop client, RDP, or SSH. DCV and RDP give you a full graphical desktop; SSH gives you a terminal. The portal shows only the options that are enabled:

- **DCV** appears only when the product's `DCVConnectionOptions` feature toggle is on (set in the product template's `FeatureToggles` output, or globally). The product also needs the Amazon DCV component in its image. Example products such as [`examples/freertos`](../examples/freertos/product.yaml) do not enable it.
- **RDP** appears only when the `RDPConnectionOption` feature toggle is on, in the product template or globally.
- **SSH** appears only when the deployment allows it. The `SSH_CONNECTION_OPTION` setting in `config.env` controls this and defaults to `"true"`.

If you see no connection option, ask your administrator which of these is set.

## DCV browser

The fastest option — no software to install.

1. Go to **My workbenches** or **My virtual targets**.
2. Select your product and choose **Log in**.
3. Choose **NICE DCV Browser** and choose **Continue**.
4. Your browser opens the DCV session directly. Log in with your credentials if prompted.

## DCV client

Better performance than the browser, especially for graphics-heavy workloads.

1. Go to **My workbenches** or **My virtual targets**.
2. Select your product and choose **Log in**.
3. Choose **NICE DCV File** and choose **Continue**.
4. If you don't have the DCV client yet, download it from the link on the page and install it.
5. Download the connection file and open it with the DCV client.
6. Log in with your credentials if prompted.

## RDP

For a Windows product, where you would rather use the Remote Desktop client you already have.

1. Go to **My workbenches** or **My virtual targets**.
2. Select your product and choose **Log in**.
3. Choose **RDP** and choose **Continue**. Tick **Extend to all monitors** first if you want the session to span them.
4. Download the connection file and open it with your Remote Desktop client. It carries the instance's address and your user name in the form `DOMAIN\USERID`, and asks for a 1920×1080 session.
5. If the product allows a password login, the page has a **Reveal password** control; use that password when the client prompts.

## SSH

For terminal-only access — useful for virtual targets and headless workloads.

1. Go to **My workbenches** or **My virtual targets**.
2. Select your product and choose **Log in**.
3. Confirm by choosing **Log in** again. VEW downloads an SSH key file named `connect_vew-pp-<UUID>.key`.
4. Lock down the key permissions so only you can read it:

   ```bash
   chmod 0600 connect_vew-pp-<UUID>.key
   ```

5. Get the public IP: go back to the product list, select your product, and choose **View details**. Copy the **Public IP** from the General configuration section.
6. Connect:

   ```bash
   ssh -i path/to/connect_vew-pp-<UUID>.key ubuntu@<public-ip>
   ```

   Replace `ubuntu` with the appropriate user if your product runs a different OS (e.g., `ec2-user` for Amazon Linux, `Administrator` for Windows via SSH).
