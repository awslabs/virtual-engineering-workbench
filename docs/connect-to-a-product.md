# Connect to a product

Once your product is in **Running** state, there are three ways to connect: DCV in the browser, the DCV desktop client, or SSH. DCV gives you a full graphical desktop; SSH gives you a terminal. If your administrator has turned it on, [Session Manager](#session-manager) also gives you a terminal, without an SSH key.

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

## Session Manager

A terminal through AWS Systems Manager. It needs no SSH key and no open port, and you don't need an AWS account.

1. Install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and its [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html).
2. Go to **My workbenches** or **My virtual targets**.
3. Select your product and choose **Log in**.
4. Choose **Session Manager**, choose **Continue**, then choose **Copy command**.
5. Paste the command into a terminal on macOS, Linux, or WSL. Its credentials expire after an hour; get a new command after that.

The shell starts as `ssm-user`. Run `sudo -iu ubuntu`, or the product's own user, to switch.

Administrators turn the option on in the provisioning API's feature toggles parameter, `/<prefix>-provisioning-api-<environment>/feature-toggles`, with an entry for `SessionManagerConnectionOption`. Set `enabled` to `true` for everyone, or list upper-case user IDs in `userOverrides` to try it with a few users first.
