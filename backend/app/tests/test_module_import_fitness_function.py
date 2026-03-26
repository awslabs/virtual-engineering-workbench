import assertpy
import pytest

from app.tests import hexagonal_architecture_helpers


@pytest.mark.parametrize(
    "bounded_context,app_file_context",
    hexagonal_architecture_helpers.AppDirectory.from_root_dir("app").bounded_contexts,
)
def test_bounded_context_modules_should_not_have_cross_imports(
    bounded_context: str, app_file_context: list[hexagonal_architecture_helpers.AppFileContext]
):
    # ARRANGE
    hexagonal_app_imports = {ctx.filename: ctx.module_imports for ctx in app_file_context}
    allowed_imports = ["app.shared", f"app.{bounded_context}"]
    prohibited_imports_result = {}

    # ACT
    for filename, imports in hexagonal_app_imports.items():
        prohibited_imports = [
            i
            for i in imports
            if i.startswith("app.") and not next((ai for ai in allowed_imports if i.startswith(ai)), None)
        ]
        if prohibited_imports:
            prohibited_imports_result[filename] = prohibited_imports

    # ASSERT
    assertpy.assert_that(prohibited_imports_result).described_as("prohibited cross bounded context import").is_empty()


@pytest.mark.parametrize(
    "bounded_context,app_file_context",
    hexagonal_architecture_helpers.AppDirectory.from_root_dir("app").bounded_contexts,
)
def test_domain_should_not_import_adapters_and_entrypoints(
    bounded_context: str, app_file_context: list[hexagonal_architecture_helpers.AppFileContext]
):
    # ARRANGE
    domain_files = [d for d in app_file_context if d.hexagonal_arch_context == "domain"]
    allowed_imports = ["app.shared", f"app.{bounded_context}.domain"]
    prohibited_imports_result = {}

    # ACT
    for app_file in domain_files:
        app_imports = [i for i in app_file.module_imports if i.startswith(f"{app_file.root}.")]
        prohibited_imports = [
            i for i in app_imports if not next((ai for ai in allowed_imports if i.startswith(ai)), None)
        ]
        if prohibited_imports:
            prohibited_imports_result[app_file.filename] = prohibited_imports

    # ASSERT
    assertpy.assert_that(prohibited_imports_result).described_as(
        f"prohibited imports in {bounded_context} domain detected"
    ).is_empty()


@pytest.mark.parametrize(
    "bounded_context,app_file_context",
    hexagonal_architecture_helpers.AppDirectory.from_root_dir("app").bounded_contexts,
)
def test_adapters_should_not_import_entrypoints(
    bounded_context: str, app_file_context: list[hexagonal_architecture_helpers.AppFileContext]
):
    # ARRANGE
    domain_files = [d for d in app_file_context if d.hexagonal_arch_context == "adapters"]
    allowed_imports = ["app.shared", f"app.{bounded_context}.adapters", f"app.{bounded_context}.domain"]
    prohibited_imports_result = {}

    # ACT
    for app_file in domain_files:
        app_imports = [i for i in app_file.module_imports if i.startswith(f"{app_file.root}.")]
        prohibited_imports = [
            i for i in app_imports if not next((ai for ai in allowed_imports if i.startswith(ai)), None)
        ]
        if prohibited_imports:
            prohibited_imports_result[app_file.filename] = prohibited_imports

    # ASSERT
    assertpy.assert_that(prohibited_imports_result).described_as(
        f"prohibited imports in {bounded_context} adapters detected"
    ).is_empty()


@pytest.mark.parametrize(
    "bounded_context,app_file_context",
    hexagonal_architecture_helpers.AppDirectory.from_root_dir("app").bounded_contexts,
)
def test_entrypoints_should_not_import_other_entrypoints(
    bounded_context: str, app_file_context: list[hexagonal_architecture_helpers.AppFileContext]
):
    # ARRANGE
    domain_files = [
        d for d in app_file_context if d.hexagonal_arch_context and d.hexagonal_arch_context.startswith("entrypoints.")
    ]
    prohibited_imports_result = {}

    # ACT
    for app_file in domain_files:
        entrypoint_imports = [
            i
            for i in app_file.module_imports
            if i.startswith(f"{app_file.root}.{app_file.bounded_context}.entrypoints.")
        ]
        prohibited_imports = [
            i
            for i in entrypoint_imports
            if not i.startswith(f"{app_file.root}.{app_file.bounded_context}.{app_file.hexagonal_arch_context}")
        ]
        if prohibited_imports:
            prohibited_imports_result[app_file.filename] = prohibited_imports

    # ASSERT
    assertpy.assert_that(prohibited_imports_result).described_as(
        f"prohibited imports in {bounded_context} entrypoints detected"
    ).is_empty()
