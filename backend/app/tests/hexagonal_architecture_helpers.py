import ast
import os
import typing

import pydantic


class AppFileContext(pydantic.BaseModel):
    root: str
    bounded_context: str
    hexagonal_arch_context: str | None
    filename: str
    module_imports: list[str]


app_directory_instances: dict[str, typing.Any] = {}


class AppDirectory:
    def __init__(
        self,
        root_dir: str,
        non_bcs: set[str] = {"authorizer", "shared", "tests", "monitoring"},
        hexagonal_contexts: set[str] = {"adapters", "domain", "entrypoints"},
    ) -> None:
        self._root_dir = root_dir
        self._non_bcs = non_bcs
        self._bounded_contexts = {}
        self._hexagonal_contexts = hexagonal_contexts

    def analyze_files(self) -> typing.Self:
        for root, _, files in os.walk(self._root_dir):
            for name in [f for f in files if f.endswith(".py")]:
                self._analyze_file(root, name)
        return self

    def _analyze_file(self, root: str, file: str):
        path_parts = root.split(os.sep)
        if len(path_parts) >= 2:  # Inside BC
            self._store_bc_file(bounded_context=path_parts[1], path_parts=path_parts, root=root, file=file)

    def _store_bc_file(self, bounded_context: str, path_parts: list[str], root: str, file: str):
        if bounded_context in self._non_bcs:
            return

        hexagonal_arch_context = self._get_hexagonal_arch_context(path_parts=path_parts)
        full_file_name = os.path.join(root, file)
        module_imports = self._get_module_imports(full_file_name)

        ctx = AppFileContext(
            root=self._root_dir,
            bounded_context=bounded_context,
            hexagonal_arch_context=hexagonal_arch_context,
            filename=full_file_name,
            module_imports=module_imports,
        )
        if bounded_context in self._bounded_contexts:
            self._bounded_contexts[bounded_context].append(ctx)
        else:
            self._bounded_contexts[bounded_context] = [ctx]

    def _get_hexagonal_arch_context(self, path_parts: list[str]):
        if len(path_parts) < 3:
            return None

        if path_parts[2] not in self._hexagonal_contexts:
            return None

        if path_parts[2] == "entrypoints" and len(path_parts) >= 4:
            return f"{path_parts[2]}.{path_parts[3]}"

        return path_parts[2]

    def _get_module_imports(self, full_file_name: str):
        module_imports = []
        with open(full_file_name) as fh:
            root = ast.parse(fh.read(), full_file_name)
            for node in ast.iter_child_nodes(root):
                module = []
                if isinstance(node, ast.ImportFrom):
                    module = node.module.split(".")
                elif not isinstance(node, ast.Import):
                    continue

                for n in node.names:
                    module_imports.append(".".join([*module, n.name]))

        return module_imports

    @property
    def bounded_contexts(self):
        return [(key, value) for key, value in self._bounded_contexts.items()]

    @staticmethod
    def from_root_dir(root_dir: str) -> typing.Self:
        if root_dir not in app_directory_instances:
            app_directory_instances[root_dir] = AppDirectory(root_dir=root_dir).analyze_files()

        return app_directory_instances.get(root_dir)
