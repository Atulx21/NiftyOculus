# Airflow image. Pipeline tasks run in a SEPARATE virtualenv so Airflow's pinned
# dependencies never clash with dbt / PySpark / pandas.
FROM apache/airflow:2.11.2-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*
ADD https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar /opt/jars/postgresql.jar
RUN chmod 644 /opt/jars/postgresql.jar

USER airflow
# pre-create the bronze output dir with airflow user ownership
RUN mkdir -p /opt/airflow/bronze_data
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/airflow/pipeline-venv \
    && /opt/airflow/pipeline-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

