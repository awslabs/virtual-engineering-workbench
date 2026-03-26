from infra import config
from infra.auth import projects_auth_schema
from infra.constructs import backend_app_api_auth

projects_bc_auth_policies: list[backend_app_api_auth.CedarPolicy] = [
    backend_app_api_auth.CedarPolicy(
        description="Allows admins to onboard accounts, manage users, and change project configuration",
        statement=f"""
            permit (
                principal,
                action in {projects_auth_schema.get_full_action_names([
                    projects_auth_schema.ProjectsBCActions.AddProjectAccount,
                    projects_auth_schema.ProjectsBCActions.AddProjectUser,
                    projects_auth_schema.ProjectsBCActions.AddTechnology,
                    projects_auth_schema.ProjectsBCActions.DeleteTechnology,
                    projects_auth_schema.ProjectsBCActions.RemoveProjectUser,
                    projects_auth_schema.ProjectsBCActions.RemoveProjectUsers,
                    projects_auth_schema.ProjectsBCActions.ReonboardProjectAccount,
                    projects_auth_schema.ProjectsBCActions.UpdateProject,
                    projects_auth_schema.ProjectsBCActions.UpdateProjectAccount,
                    projects_auth_schema.ProjectsBCActions.UpdateTechnology,
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.ADMINS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows program owners to approve enrolment requests and change user roles.",
        statement=f"""
            permit (
                principal,
                action in {projects_auth_schema.get_full_action_names([
                    projects_auth_schema.ProjectsBCActions.GetProjectEnrolments,
                    projects_auth_schema.ProjectsBCActions.GetProjectUsers,
                    projects_auth_schema.ProjectsBCActions.GetUserRoles,
                    projects_auth_schema.ProjectsBCActions.ReAssignProjectUsers,
                    projects_auth_schema.ProjectsBCActions.ReAssignUserAssignments,
                    projects_auth_schema.ProjectsBCActions.RetriggerUserADGroup,
                    projects_auth_schema.ProjectsBCActions.UpdateEnrolments,
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.PROGRAM_OWNERS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows contributors to get technologies.",
        statement=f"""
            permit (
                principal,
                action in {projects_auth_schema.get_full_action_names([
                    projects_auth_schema.ProjectsBCActions.GetTechnologies,
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.PRODUCT_CONTRIBUTORS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows users to get project health check endpoints and accounts.",
        statement=f"""
            permit (
                principal,
                action in {projects_auth_schema.get_full_action_names([
                    projects_auth_schema.ProjectsBCActions.GetProject,
                    projects_auth_schema.ProjectsBCActions.GetProjectAccountHealthEndpoints,
                    projects_auth_schema.ProjectsBCActions.GetProjectAccounts,
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.PLATFORM_USERS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows all authenticated principals to enrol, get available projects and get Swagger API spec.",
        statement=f"""
            permit (
                principal,
                action in {projects_auth_schema.get_full_action_names([
                    projects_auth_schema.ProjectsBCActions.GetProjects,
                    projects_auth_schema.ProjectsBCActions.GetSwaggerSpec,
                    projects_auth_schema.ProjectsBCActions.EnrolUser,
                ])},
                resource
            );
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows users that are admins in at least one project to create a new project.",
        statement=f"""
            permit (
                principal,
                action in {projects_auth_schema.get_full_action_names([
                    projects_auth_schema.ProjectsBCActions.CreateProject,
                ])},
                resource
            )
            when {{ principal has {projects_auth_schema.UserEntityAttributes.TotalAdminAssignments} && principal.{projects_auth_schema.UserEntityAttributes.TotalAdminAssignments} > 0 }};
    """,
    ),
]
