from app.shared.adapters.boto.boto_provider import SupportsContextManager


class DictCtxProvider(SupportsContextManager):
    def __init__(self):
        self._dict = {}

    def append_context(self, **additional_context):
        self._dict.update(**additional_context)

    @property
    def context(self) -> dict:
        return self._dict
