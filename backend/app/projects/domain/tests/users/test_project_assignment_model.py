import assertpy

from app.projects.domain.model import project_assignment


def test_can_parse_upper_case_role_name():
    # Arrange
    test_assignment = {"userId": "testUser", "projectId": "testProject", "roles": ["PLATFORM_USER", "ADMIN"]}
    # Act
    result = project_assignment.Assignment.model_validate(test_assignment)
    # Assert
    assertpy.assert_that(result).is_type_of(project_assignment.Assignment)


def test_can_parse_lower_case_role_name():
    # Arrange
    test_assignment = {"userId": "testUser", "projectId": "testProject", "roles": ["platform_user", "admin"]}
    # Act
    result = project_assignment.Assignment.model_validate(test_assignment)
    # Assert
    assertpy.assert_that(result).is_type_of(project_assignment.Assignment)
