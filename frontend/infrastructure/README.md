# Infrastructure Code for User Interface

This is an infrastructure CDK template for User Interface CloudFormation stack.

## Deploying the stack

1. Install dependencies.
   If you use NPM:
   ```
   npm install
   ```

   Yarn:
   ```
   yarn install
   ```

1. Bootstrap CDK into your account and region (assuming that the region is `us-east-1`):
   ```
   cdk bootstrap aws://12345678900/us-east-1
   ```

2. Deploy `../prerequisites/vew-deployment-account-prerequisites.yml` to the target AWS account. 

   If you modify CDK template to use Cognito User Pool authentication instead, make sure that you configure a strong password policy and enable multi factor authentication.

3. Update configuration in the `cdk.json` file. Set the following parameters:
  * `"app-name"`: `"my-test-app"` - name of your application without whitespaces. This must be the same application name from step 2 and it must be globally unique, as it will be used in the Cognito domain prefix.

4. Run the following command to deploy the CloudFormation stack:
   ```
   cdk deploy -c account=<ACCOUNT> -c environment=dev -c region=us-east-1
   ```

   This will deploy an S3 bucket, CloudFront distribution and a User Pool client for the frontend app to use in us-east-1 region.

   Note, that an additional S3 bucket will be created to store S3 and CloudFront access logs, which will incur a small charge. You can opt to disable S3 and CloudFront access logs in CDK template at your own risk.

## Deleting the stack

Lambda@Edge functions can only be deleted after all of the replicas have been deleted by CloudFront. For this reason, Lambda@Edge function in this CDK template is configured with `RETAIN` removal policy, which means, that it has to be deleted manually after destroying the CloudFormation stack (see [Deleting Lambda@Edge Functions and Replicas](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-edge-delete-replicas.html)).

1. Note the physical ID of the Lambda@Edge function in the Resources tab of the CloudFormation stack details.
2. Note the name of the stack. It will be in the following format: `aws-sample-my-test-app-us-east-1-001234567890`.
3. Run the following command to destroy the CloudFormation stack:
   ```
   cdk destroy --profile aws-profile-name
   ```
4. Manually delete an S3 bucket with the following name: `{stack_name}-logs`.
5. Manually delete a Cognito user pool with the following name: `{stack_name}-user-pool`.
6. After a few hours, all the Lambda@Edge replicas will be automatically deleted. In the AWS Console, find the Lambda with the ID from step 1, and delete it manually.
7. Remove the following secret from the Secrets Manager, containing the corporate OIDC configuration: `{app_name}-{environment}/oidc`, replacing the `{app_name}` with a chosen `app-name` configuration value in the `cdk.json` file.
