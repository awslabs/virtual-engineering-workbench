import tempfile
from abc import ABC, abstractmethod


class TemplateService(ABC):
    @abstractmethod
    def get_template(self, template_path: str, download_directory: str = tempfile.gettempdir()) -> str: ...

    @abstractmethod
    def put_template(self, template_path: str, content: bytes) -> None: ...

    @abstractmethod
    def does_template_exist(self, template_path: str) -> bool: ...

    @abstractmethod
    def get_object(self, object_path: str) -> str: ...
