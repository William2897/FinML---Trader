#!/bin/bash
set -e

# The 'psql' command allows us to execute SQL commands.
# We connect as the default postgres superuser to create our new user and database.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create a new user named 'user' with the password 'password'
    -- Note: "user" is a reserved keyword in SQL, so we quote it.
    CREATE USER "user" WITH PASSWORD 'password';

    -- Create the database for our financial data
    CREATE DATABASE finml_data;

    -- Grant all privileges on the new database to our new user
    GRANT ALL PRIVILEGES ON DATABASE finml_data TO "user";
EOSQL