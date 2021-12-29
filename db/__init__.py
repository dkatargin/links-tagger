from sqlalchemy import create_engine

from common.config import config

engine = create_engine(
    f'postgresql://{config.get("Database", "user")}:{config.get("Database", "pass")}@{config.get("Database", "host")}:{config.get("Database", "port")}/{config.get("Database", "db_name")}')
