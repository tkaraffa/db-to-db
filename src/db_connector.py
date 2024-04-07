from abc import ABC, abstractmethod
import os
from sqlalchemy.dialects import postgresql
from pydantic.dataclasses import dataclass
from enum import Enum
from sqlalchemy import create_engine, URL


@dataclass
class DBConnection(ABC):
    username: str
    password: str
    host: str
    port: int
    database: str
    drivername: str
    dialect: str

    @abstractmethod
    def uri(self):
        """Create URI to use in `write_database` calls."""

    @property
    def engine(self):
        return create_engine(self.uri)


@dataclass
class PGDBConnection(DBConnection, ABC):
    username: str
    password: str
    host: str
    database: str
    port: int
    drivername: str = "postgresql"
    dialect: str = postgresql.dialect()

    @property
    def uri(self):
        return URL.create(
            self.drivername,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )


@dataclass
class SourcePostgres(PGDBConnection):
    username: str = os.getenv("SOURCE_USER")
    password: str = os.getenv("SOURCE_PASSWORD")
    host: str = os.getenv("SOURCE_HOST")
    database: str = os.getenv("SOURCE_DATABASE")
    port: int = os.getenv("SOURCE_PORT")

    @property
    def uri(self):
        return URL.create(
            self.drivername,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )


@dataclass
class TargetPostgres(PGDBConnection):
    username: str = os.getenv("TARGET_USER")
    password: str = os.getenv("TARGET_PASSWORD")
    host: str = os.getenv("TARGET_HOST")
    database: str = os.getenv("TARGET_DATABASE")
    port: int = os.getenv("TARGET_PORT")

    @property
    def uri(self):
        return URL.create(
            self.drivername,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )


class DBConnector(Enum):
    SOURCE = SourcePostgres
    TARGET = TargetPostgres
