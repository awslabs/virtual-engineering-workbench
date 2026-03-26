import enum


class SharedAttributes(enum.StrEnum):
    TotalAdminAssignments = "totalAdminAssignments"


class SharedEntities:
    Project = "Project"
    ProjectAssignment = "ProjectAssignment"
    User = "User"


cross_cutting_auth_entities = {
    SharedEntities.Project: {
        "shape": {
            "type": "Record",
            "attributes": {
                "platformUsers": {"type": "Entity", "required": True, "name": SharedEntities.ProjectAssignment},
                "betaUsers": {"type": "Entity", "required": True, "name": SharedEntities.ProjectAssignment},
                "productContributors": {
                    "type": "Entity",
                    "required": True,
                    "name": SharedEntities.ProjectAssignment,
                },
                "powerUsers": {"type": "Entity", "required": True, "name": SharedEntities.ProjectAssignment},
                "programOwners": {"type": "Entity", "required": True, "name": SharedEntities.ProjectAssignment},
                "admins": {"type": "Entity", "required": True, "name": SharedEntities.ProjectAssignment},
                "vewUsers": {"type": "Entity", "required": True, "name": SharedEntities.ProjectAssignment},
                "hilUsers": {"type": "Entity", "required": True, "name": SharedEntities.ProjectAssignment},
                "vvplUsers": {"type": "Entity", "required": True, "name": SharedEntities.ProjectAssignment},
            },
        }
    },
    SharedEntities.ProjectAssignment: {
        "shape": {"type": "Record", "attributes": {}},
        "memberOfTypes": [SharedEntities.ProjectAssignment],
    },
    SharedEntities.User: {
        "shape": {
            "type": "Record",
            "attributes": {
                SharedAttributes.TotalAdminAssignments: {
                    "type": "Long",
                    "required": False,
                }
            },
        },
        "memberOfTypes": [SharedEntities.ProjectAssignment],
    },
}
