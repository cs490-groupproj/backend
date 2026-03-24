#!/bin/bash

# Install Microsoft ODBC driver if not already installed
if ! command -v /opt/mssql-tools18/bin/sqlcmd &> /dev/null
then
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
    curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
    apt-get update
    ACCEPT_EULA=Y apt-get install -y msodbcsql18
fi

# Start Gunicorn
gunicorn app:app
