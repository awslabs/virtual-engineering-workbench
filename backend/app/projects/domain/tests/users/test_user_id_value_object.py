import assertpy

from app.projects.domain.value_objects import user_id_value_object


def test_user_id_value_object_should_unquote_user_id():
    # ACT
    user_id = user_id_value_object.from_str("test.user%40example.com")

    # ASSERT
    assertpy.assert_that(user_id.value).is_equal_to("test.user@example.com")
