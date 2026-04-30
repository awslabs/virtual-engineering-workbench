from __future__ import annotations

import abc

import aws_cdk
import constructs
import jsii
from aws_cdk import aws_dynamodb, aws_iam

from infra import config
from infra.constructs import backend_app_entrypoints, backend_app_openapi


@jsii.implements(aws_cdk.IAspect)
class _PinExportsAspect:
    """Aspect that calls ``pin_exports`` once when it visits the owning stack."""

    def __init__(self, stack: VEWBoundedContextStack) -> None:
        self._stack = stack
        self._done = False

    def visit(self, node: constructs.IConstruct) -> None:
        if not self._done and node is self._stack:
            self._done = True
            self._stack.pin_exports()


class VEWBoundedContextStack(aws_cdk.Stack):
    """Abstract base for bounded context stacks that expose internal APIs.

    Subclasses must implement:
    - backend_app: property returning the BackendAppEntrypoints instance
    - internal_api: property returning the BackendAppOpenApi construct (or None)
    - table: property returning the DynamoDB table (or None)

    ``pin_exports()`` is called automatically via an Aspect after all
    constructs are defined — subclasses do not need to call it.
    """

    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        **kwargs,
    ) -> None:
        if "stack_name" not in kwargs:
            kwargs["stack_name"] = app_config.format_base_resource_name(app_config.component_name)
        self._app_config = app_config
        super().__init__(scope, id, **kwargs)
        aws_cdk.Aspects.of(self).add(_PinExportsAspect(self))

    @property
    def bounded_context(self) -> str:
        return self._app_config.component_name

    @property
    @abc.abstractmethod
    def backend_app(self) -> backend_app_entrypoints.BackendAppEntrypoints: ...

    @property
    @abc.abstractmethod
    def internal_api(self) -> backend_app_openapi.BackendAppOpenApi | None: ...

    @property
    @abc.abstractmethod
    def table(self) -> aws_dynamodb.ITable | None: ...

    def entrypoint_role(self, short_name: str) -> aws_iam.IRole:
        """Return the Lambda execution role for a named entrypoint."""
        full_name = self._app_config.format_resource_name(short_name)
        return self.backend_app.entrypoint(full_name).function.role

    def entrypoints_with_api_access(self) -> list[backend_app_entrypoints.AppEntryFunctionsAttributes]:
        """Return all entrypoints that declare cross-BC API access."""
        return [entry for entry in self.backend_app.app_entries.values() if entry.cross_bc_api_access]

    def pin_exports(self) -> None:
        """Pin all cross-stack-referenced resources as explicit CloudFormation exports.

        Called automatically by ``_PinExportsAspect`` during the prepare phase.

        ``Stack.export_value()`` (without a *name*) produces the **same**
        logical-ID and export name as CDK's automatic cross-stack machinery.
        It is idempotent: while the auto-export exists the two collapse into
        one Output; when the auto-export disappears the explicit one keeps the
        value available.
        """
        for entry in self.backend_app.app_entries.values():
            if entry.function.role:
                self.export_value(entry.function.role.role_name)

        open_api = self.internal_api
        if open_api is not None:
            self.export_value(open_api.api.rest_api_id)
            if open_api.api.deployment_stage:
                self.export_value(open_api.api.deployment_stage.stage_name)

        tbl = self.table
        if tbl is not None:
            self.export_value(tbl.table_name)
            self.export_value(tbl.table_arn)
            if tbl.table_stream_arn:
                self.export_value(tbl.table_stream_arn)
