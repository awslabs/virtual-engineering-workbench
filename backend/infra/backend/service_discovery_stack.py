from __future__ import annotations

import hashlib

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_iam

from infra import config
from infra.backend import vew_bounded_context_stack
from infra.constructs import backend_app_entrypoints


class ServiceDiscoveryStack(aws_cdk.Stack):
    def __init__(self, scope: constructs.Construct, id: str, app_config: config.AppConfig, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self._app_config = app_config
        self._registered: dict[str, vew_bounded_context_stack.VEWBoundedContextStack] = {}

    def register(self, *stacks: vew_bounded_context_stack.VEWBoundedContextStack) -> ServiceDiscoveryStack:
        """Register BC stacks. Returns self for fluent chaining."""
        for stack in stacks:
            bc = stack.bounded_context
            if bc in self._registered and self._registered[bc] is not stack:
                raise ValueError(f"BoundedContext '{bc}' already registered")
            if bc not in self._registered:
                self._registered[bc] = stack
                self.add_dependency(stack)
        return self

    def apply_permissions(self) -> None:
        """Create IAM policies for all entrypoints with cross-BC API access."""
        for consumer_stack in self._registered.values():
            for entry in consumer_stack.entrypoints_with_api_access():
                self._create_policy(consumer_stack, entry)

    def _create_policy(
        self,
        consumer: vew_bounded_context_stack.VEWBoundedContextStack,
        entry: backend_app_entrypoints.AppEntryFunctionsAttributes,
    ) -> None:
        consumer_bc = consumer.bounded_context
        bc_pascal = consumer_bc.replace("-", " ").title().replace(" ", "")
        name_hash = hashlib.sha256(entry.app_name.encode()).hexdigest()[:8]

        api_arns: list[str] = []
        wildcard_arns: list[str] = []
        ssm_param_arns: set[str] = set()

        for target_bc, routes in entry.cross_bc_api_access.items():
            target_stack = self._registered.get(target_bc)
            if target_stack is None:
                raise ValueError(
                    f"BoundedContext '{target_bc}' referenced by " f"{consumer_bc}/{entry.app_name} is not registered"
                )
            self._collect_arns(target_stack, target_bc, routes, api_arns, wildcard_arns, ssm_param_arns)

        if not api_arns:
            return

        statements = self._build_statements(api_arns, ssm_param_arns)

        policy = aws_iam.ManagedPolicy(
            self,
            f"{bc_pascal}{name_hash}CrossServicePolicy",
            managed_policy_name=f"VEW{bc_pascal}{name_hash}APIAccess",
            path="/VirtualWorkbench/",
            roles=[entry.function.role],
            statements=statements,
            description=f"Cross-BC API access for {consumer_bc}/{entry.app_name}",
        )

        if wildcard_arns:
            cdk_nag.NagSuppressions.add_resource_suppressions(
                policy,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM5",
                        reason="Wildcards represent dynamic API path parameters.",
                    ),
                ],
            )

    def _collect_arns(self, target_stack, target_bc, routes, api_arns, wildcard_arns, ssm_param_arns):
        open_api = target_stack.internal_api
        if open_api is None:
            raise ValueError(
                f"BoundedContext '{target_bc}' is referenced as a cross-BC API target "
                f"but does not expose an internal API"
            )
        api = open_api.api
        for method, path in routes:
            arn = api.arn_for_execute_api(method=method, path=path, stage=api.deployment_stage.stage_name)
            api_arns.append(arn)
            if "*" in path:
                wildcard_arns.append(arn)

        ssm_param_name = open_api.api_url_ssm_parameter_name
        ssm_param_arns.add(
            self.format_arn(service="ssm", resource="parameter", resource_name=ssm_param_name.lstrip("/"))
        )

    @staticmethod
    def _build_statements(api_arns, ssm_param_arns):
        statements = [
            aws_iam.PolicyStatement(actions=["execute-api:Invoke"], effect=aws_iam.Effect.ALLOW, resources=api_arns),
        ]
        if ssm_param_arns:
            statements.append(
                aws_iam.PolicyStatement(
                    actions=["ssm:GetParameter"], effect=aws_iam.Effect.ALLOW, resources=sorted(ssm_param_arns)
                ),
            )
        return statements
