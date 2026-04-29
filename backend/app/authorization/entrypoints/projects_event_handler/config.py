import os

from app.shared import config


class AppConfig(config.VEWBaseConfig):
    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_gsi_name_inverted_pk(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK", "")
