# One image for all Python stages (ingest, Spark silver job, tests).
# Java is needed only because Spark runs on the JVM; we never write Java.
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# JDBC driver so Spark can write to Postgres
ADD https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar /opt/jars/postgresql.jar

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

