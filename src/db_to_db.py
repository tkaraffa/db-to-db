"""
Load data from one database into a landing table,
where that data can be upserted/merged into the target table.
"""
from typing import Union, Literal, Iterable, Any
import argparse
import logging
import sys

import polars as pl
from pydantic import validate_call
from sqlalchemy import MetaData, Table, Column, select, delete, Selectable, Delete

from db_connector import DBConnection, DBConnector

DEFAULT_BATCH_SIZE = 10000
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)

logger.addHandler(stdout_handler)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source_connection",
        type=lambda val: DBConnector.__getitem__(val.upper()).value,
        help="Source database URI",
        required=True,
        metavar="SOURCE_CONN",
    )
    parser.add_argument(
        "--target_connection",
        type=lambda val: DBConnector.__getitem__(val.upper()).value,
        help="Target database URI",
        required=True,
        metavar="TARGET_CONN",
    )
    parser.add_argument(
        "--source_table",
        type=str,
        help="Table to load data from.",
        required=True,
        metavar="TABLE",
    )
    parser.add_argument(
        "--target_table",
        type=str,
        help="Table to load data into; default: landing__<source_table>",
        metavar="TABLE",
    )
    parser.add_argument(
        "--source_schema",
        type=str,
        help="Schema of source table",
        required=True,
        metavar="SCHEMA",
    )
    parser.add_argument(
        "--target_schema",
        type=str,
        help="Schema of target table; default: <source_schema>",
        metavar="SCHEMA",
    )

    parser.add_argument(
        "--batch_size",
        type=int,
        help=f"Batch size; default: {DEFAULT_BATCH_SIZE}",
        default=DEFAULT_BATCH_SIZE,
        metavar="N",
    )

    gte_group = parser.add_argument_group(
        "gte",
        "Filter table with values greater than or equal to this value.",
    )
    gte_group.add_argument(
        "--gte_column",
        type=str,
        help="Column to use to filter table.",
        metavar="COLUMN",
    )
    gte_group.add_argument(
        "--gte_value",
        type=str,
        help="Value to use to filter table.",
        metavar="VALUE",
    )

    lt_group = parser.add_argument_group(
        "lt",
        "Filter table with values less than this value.",
    )
    lt_group.add_argument(
        "--lt_column",
        type=str,
        help="Column to use to filter table.",
        metavar="COLUMN",
    )
    lt_group.add_argument(
        "--lt_value",
        type=str,
        help="Value to use to filter table.",
        metavar="VALUE",
    )

    parser.add_argument(
        "--initial_write_behavior",
        type=str,
        choices=["fail", "replace", "append"],
        default="append",
        help="Behavior for initial write to target table.",
        metavar="BEHAVIOR",
    )
    parser.add_argument(
        "--delete_from_target_table",
        action="store_true",
        help="""Flag to indicate whether or not to delete data from target table before writing data. 
        Usually not needed, because `delete` should be handled by upstream tasks, 
        but might be needed if job fails; 
        the behavior of using this flag should be included in whatever orchestrates this script, 
        e.g., `if retry: --delete_from_target_table`""",
    )

    args = parser.parse_args()
    return args


@validate_call(config=dict(arbitrary_types_allowed=True))
def add_where_clause(
    query: Union[Selectable, Delete],
    gte_column: str = None,
    gte_value=None,
    lt_column: str = None,
    lt_value=None,
):
    if gte_column:
        query = query.where(Column(gte_column) >= gte_value)
    if lt_column:
        query = query.where(Column(lt_column) < lt_value)
    return query


@validate_call(config=dict(arbitrary_types_allowed=True))
def delete_from_table(
    connection: DBConnection,
    schema: str,
    table: str,
    metadata: MetaData,
    gte_column: str = None,
    gte_value: Any = None,
    lt_column: str = None,
    lt_value: Any = None,
):
    table_object = Table(
        table, metadata, schema=schema, autoload_with=connection.engine
    )
    query = delete(table_object)
    query = add_where_clause(query, gte_column, gte_value, lt_column, lt_value)
    logger.info(f"Deleting data with {query}")
    with connection.engine.connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as conn:
        conn.execute(query)


@validate_call(config=dict(arbitrary_types_allowed=True))
def get_select_query(
    connection: DBConnection,
    table: str,
    schema: str,
    metadata: MetaData,
    gte_column: str = None,
    gte_value: Any = None,
    lt_column: str = None,
    lt_value: Any = None,
) -> select:
    table_object = Table(
        table, metadata, schema=schema, autoload_with=connection.engine
    )
    query = select("*").select_from(table_object)
    query = add_where_clause(query, gte_column, gte_value, lt_column, lt_value)
    return query


@validate_call(config=dict(arbitrary_types_allowed=True))
def db_to_db(
    query: Selectable,
    source_connection: DBConnection,
    target_connection: DBConnection,
    target_schema: str,
    target_table: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    initial_behavior: Union[
        Literal["fail"], Literal["replace"], Literal["append"]
    ] = "append",
) -> None:
    with source_connection.engine.connect() as conn:
        dfs: Iterable[pl.DataFrame] = pl.read_database(
            query,
            conn,
            iter_batches=True,
            batch_size=batch_size,
        )
    rows = 0
    for i, chunk in enumerate(dfs):
        if i == 0:
            table_exists_behavior = initial_behavior
        else:
            table_exists_behavior = "append"
        logger.info(
            f"Writing chunk {i+1} of size {batch_size} to database with if-exists behavior: {table_exists_behavior}"
        )

        chunk.write_database(
            table_name=".".join([target_schema, target_table]),
            connection=target_connection.uri,
            if_table_exists=table_exists_behavior,
        )
        rows += len(chunk)
        logger.info(f"Chunk {i+1} written to database")
    logger.info(f"Total rows written: {rows}")


def main():
    args = get_args()

    source_connection = args.source_connection()
    target_connection = args.target_connection()
    source_table = args.source_table
    target_table = args.target_table
    source_schema = args.source_schema
    target_schema = args.target_schema
    gte_column = args.gte_column
    gte_value = args.gte_value
    lt_column = args.lt_column
    lt_value = args.lt_value
    batch_size = args.batch_size
    initial_behavior = args.initial_write_behavior
    delete_from_target_table = args.delete_from_target_table

    if bool(lt_column) is not bool(lt_value):
        raise ValueError("lt_column and lt_value must be both set or both unset")
    if bool(gte_column) is not bool(gte_value):
        raise ValueError("gte_column and gte_value must be both set or both unset")

    if target_schema is None:
        target_schema = source_schema

    if target_table is None:
        target_table = f"landing__{source_table}"

    metadata = MetaData()

    if delete_from_target_table:
        delete_from_table(
            target_connection,
            target_schema,
            target_table,
            metadata,
            gte_column=gte_column,
            gte_value=gte_value,
            lt_column=lt_column,
            lt_value=lt_value,
        )
    query = get_select_query(
        source_connection,
        source_table,
        source_schema,
        metadata,
        gte_column,
        gte_value,
        lt_column,
        lt_value,
    )

    db_to_db(
        query,
        source_connection,
        target_connection,
        target_schema,
        target_table,
        batch_size=batch_size,
        initial_behavior=initial_behavior,
    )


if __name__ == "__main__":
    main()
