# db-to-db

Local and cluster implementation of moving data from one database to another


## Local

Using polars as an intermediate, write chunked dataframes from the source database into the target database.

### Replace Table

```sh
dcor local src/db_to_db.py --target_connection TARGET --source_connection source --source_table test_table --source_schema public --gte_column date --gte_value "2024-01-01" --lt_column date --lt_value "2024-01-02" --batch_size=2 --target_table test_table --target_schema raw
````

### Truncate and Insert

```sh
dcor local src/db_to_db.py --target_connection TARGET --source_connection source --source_table test_table --source_schema public --gte_column date --gte_value "2024-01-01" --lt_column date --lt_value "2024-01-02" --batch_size=2 --target_table test_table --target_schema raw --initial_write_behavior append --truncate_target_table
```

## Cluster

Using Trino as a query engine, directly connect to each database 
and create/replace or trucnate/insert the landing table
in the target database
using data from the source database.

### Replace Table

```sh
docker compose exec cluster trino --execute "drop table if exists \"postgres-target\".raw.test_table; create table \"postgres-target\".raw.test_table as  (select * from \"postgres-source\".public.test_table where date>='2024-01-01' and date<'2024-01-02');"  
````

### Truncate and Insert

```sh
docker compose exec cluster trino --execute "delete from \"postgres-target\".raw.test_table;  insert into \"postgres-target\".raw.test_table (select * from \"postgres-source\".public.test_table where date>='2024-01-01' and date<'2024-01-02');"       
````

## dbt

```sh
dcob dbt && dcor dbt build -s test_table --vars '{"start_date":"2024-01-01", "end_date":"2024-01-02"}'
```