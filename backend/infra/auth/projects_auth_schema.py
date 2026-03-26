import enum

from infra import constants


class UserEntityAttributes(enum.StrEnum):
    TotalAdminAssignments = "totalAdminAssignments"


class ProjectsBCEntities(enum.StrEnum):
    Enrolment = "Enrolment"
    Project = "Project"
    ProjectAccount = "ProjectAccount"
    ProjectAssignment = "ProjectAssignment"
    Technology = "Technology"
    User = "User"


class ProjectsBCActions(enum.StrEnum):
    AddProjectAccount = "AddProjectAccount"
    AddProjectUser = "AddProjectUser"
    AddTechnology = "AddTechnology"
    CreateProject = "CreateProject"
    DeleteTechnology = "DeleteTechnology"
    EnrolUser = "EnrolUser"
    GetProject = "GetProject"
    GetProjectAccountHealthEndpoints = "GetProjectAccountHealthEndpoints"
    GetProjectAccounts = "GetProjectAccounts"
    GetProjectEnrolments = "GetProjectEnrolments"
    GetProjects = "GetProjects"
    GetProjectUsers = "GetProjectUsers"
    GetSwaggerSpec = "GetSwaggerSpec"
    GetTechnologies = "GetTechnologies"
    GetUserRoles = "GetUserRoles"
    ReAssignProjectUsers = "ReAssignProjectUsers"
    ReAssignUserAssignments = "ReAssignUserAssignments"
    RemoveProjectUser = "RemoveProjectUser"
    RemoveProjectUsers = "RemoveProjectUsers"
    ReonboardProjectAccount = "ReonboardProjectAccount"
    RetriggerUserADGroup = "RetriggerUserADGroup"
    UpdateEnrolments = "UpdateEnrolments"
    UpdateProject = "UpdateProject"
    UpdateProjectAccount = "UpdateProjectAccount"
    UpdateTechnology = "UpdateTechnology"


cross_cutting_auth_entities = {
    ProjectsBCEntities.Project: {
        "shape": {
            "type": "Record",
            "attributes": {
                "platformUsers": {"type": "Entity", "required": True, "name": ProjectsBCEntities.ProjectAssignment},
                "betaUsers": {"type": "Entity", "required": True, "name": ProjectsBCEntities.ProjectAssignment},
                "productContributors": {
                    "type": "Entity",
                    "required": True,
                    "name": ProjectsBCEntities.ProjectAssignment,
                },
                "powerUsers": {"type": "Entity", "required": True, "name": ProjectsBCEntities.ProjectAssignment},
                "programOwners": {"type": "Entity", "required": True, "name": ProjectsBCEntities.ProjectAssignment},
                "admins": {"type": "Entity", "required": True, "name": ProjectsBCEntities.ProjectAssignment},
                "vewUsers": {"type": "Entity", "required": True, "name": ProjectsBCEntities.ProjectAssignment},
                "hilUsers": {"type": "Entity", "required": True, "name": ProjectsBCEntities.ProjectAssignment},
                "vvplUsers": {"type": "Entity", "required": True, "name": ProjectsBCEntities.ProjectAssignment},
            },
        }
    },
    ProjectsBCEntities.ProjectAssignment: {
        "shape": {"type": "Record", "attributes": {}},
        "memberOfTypes": [ProjectsBCEntities.ProjectAssignment],
    },
    ProjectsBCEntities.User: {
        "shape": {
            "type": "Record",
            "attributes": {
                UserEntityAttributes.TotalAdminAssignments: {
                    "type": "Long",
                    "required": False,
                }
            },
        },
        "memberOfTypes": [ProjectsBCEntities.ProjectAssignment],
    },
}

projects_bc_entities = {
    **cross_cutting_auth_entities,
    ProjectsBCEntities.Enrolment: {
        "shape": {
            "type": "Record",
            "attributes": {"owner": {"type": "Entity", "required": True, "name": ProjectsBCEntities.User}},
        },
        "memberOfTypes": [ProjectsBCEntities.Project],
    },
    ProjectsBCEntities.ProjectAccount: {
        "shape": {"type": "Record", "attributes": {}},
        "memberOfTypes": [ProjectsBCEntities.Project],
    },
    ProjectsBCEntities.Technology: {
        "shape": {"type": "Record", "attributes": {}},
        "memberOfTypes": [ProjectsBCEntities.Project],
    },
}

projects_bc_actions = {
    action.value: {
        "appliesTo": {
            "resourceTypes": [
                ProjectsBCEntities.Project,
            ],
            "principalTypes": [ProjectsBCEntities.User],
        }
    }
    for action in ProjectsBCActions
}

projects_schema = {
    constants.CEDAR_POLICY_NAMESPACE: {
        "entityTypes": {
            **projects_bc_entities,
        },
        "actions": {**projects_bc_actions},
    }
}


def get_full_action_names(names: list[str]) -> str:
    return "[" + ", ".join([f'{constants.CEDAR_POLICY_NAMESPACE}::Action::"{name}"' for name in names]) + "]"
