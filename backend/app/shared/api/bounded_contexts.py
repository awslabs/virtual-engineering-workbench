import enum


class BoundedContext(enum.StrEnum):
    AUTHORIZATION = "authorization"
    PACKAGING = "packaging"
    PROJECTS = "projects"
    PROVISIONING = "provisioning"
    PUBLISHING = "publishing"
