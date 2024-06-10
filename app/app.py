import logging

import azure.functions as func

import os
import pyodbc

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    query="SELECT * FROM dbo.users"
    connection_string = os.getenv('SQL_CONNECTION_STRING')

    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            # Create table if it doesn't exist
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' and xtype='U')
                CREATE TABLE users (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    name NVARCHAR(50)
                )
            """)
            conn.commit()
            return func.HttpResponse("Table 'users' created or already exists.", status_code=200)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
