# db-to-db

Local and cluster implementation of moving data from one database to another.

Three major tables are involved:
* source table
  * The table that accumulates data to be copied to the target table
* landing table
  * A copy of the target table to load data into
  * Staging area to use the database-agnostic approach of loading data, then using database-specific merge/update statements to actually load it into the target table
* target table
  * The "user-access"-level table


This approach assumes several things:
* the source table exists with data to copy to the new database
* the target _landing_ table already exists in the relevant schema
* the target _landing_ table is permanent, but can have data added and deleted arbitrarily

## Setup

Start relevant services: two databases and the Trino coordinator.

```sh
docker compose up target source cluster
```

```sh
docker compose exec cluster trino --execute "create table "source".public.test_table as (select 1 as id, '2024-01-01' as date union all select 2 as id, '2024-01-02' as date);"
docker compose exec cluster trino --execute "create schema "target".raw;"
```

## Local

Using polars as an intermediate, write chunked dataframes from the source database into the target database.

### (Delete and) Insert

```sh
docker compose run local src/db_to_db.py --target_connection target --source_connection source --source_table test_table --source_schema public --gte_column date --gte_value "2024-01-01" --lt_column date --lt_value "2024-01-02" --batch_size=2 --target_table test_table --target_schema raw --initial_write_behavior append --truncate_target_table
```

If this script fails, and data was inserted into the target table without being copied into the target table 
(and subsequently deleted),
the `--delete_from_target_table` flag can be used to delete data from the target table before reinserting data. 
This functionality should be handled by the orchestrating body of this script.

## Cluster

Using Trino as a query engine, directly connect to each database 
and create/replace or trucnate/insert the landing table
in the target database
using data from the source database.


### (Delete and) Insert

```sh
docker compose exec cluster trino --execute "insert into target.raw.test_table (select * from source.public.test_table where date>='2024-01-01' and date<'2024-01-02');"       
```

If this script fails, and data was inserted into the target table without being copied into the target table 
(and subsequently deleted), 
the above `--execute` option can be prepended with 
"delete from target.raw.test_table where date>='2024-01-01' and date<'2024-01-02'" 
to delete data from the target table before reinserting data. 
This functionality should be handled by the orchestrating body of this script.


## dbt

```sh
docker compose run dbt build -s test_table --vars '{"start_date":"2024-01-01", "end_date":"2024-01-02"}'
```

This includes a post-hook that deletes data in the same date range
from the landing table, effectively "moving" the data from the landing table into the target table.