FROM python:3.11-slim

RUN pip install dbt-trino

WORKDIR /usr/app/
COPY . .
RUN dbt deps

ENV DBT_PROFILES_DIR=/dbt
ENV DBT_PROJECT_DIR=/dbt
ENTRYPOINT ["dbt"]
