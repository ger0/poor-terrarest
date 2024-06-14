import logging
import json
import os
import azure.functions as func
import pyodbc


app = func.FunctionApp()

@app.function_name(name="create")
@app.route(route='create', auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def create(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    query="SELECT * FROM dbo.users"
    connection_string = os.getenv('SQL_CONNECTION_STRING')

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            # Create table if it doesn't exist
            cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='journal' and xtype='U')
            CREATE TABLE journal (
                    title VARCHAR(100) PRIMARY KEY,
                    content VARCHAR(512)
                )
            """)
            conn.commit()
            return func.HttpResponse("Table 'journal' created or already exists.", status_code=200)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


@app.function_name(name="journal-get")
@app.route(route='journal-get', auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def journal_get(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a journal request.')
    query = "SELECT * FROM journal WHERE title = ?"
    connection_string = os.getenv('SQL_CONNECTION_STRING')

    try:
        title = req.params.get('title')
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, title)

            result = {"content": "Journal Entry with the specified title doesn't exist!"}
            for row in cursor.fetchall():
                result = {"content": row.content}

            json_data = json.dumps(result)
            return func.HttpResponse(
                json_data,
                status_code=200,
                headers={"Content-Type": "application/json"},
            )
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


@app.function_name(name="journal-list")
@app.route(route='journal-list', auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def journal_list(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a journal request.')
    query = "SELECT * FROM journal;"
    connection_string = os.getenv('SQL_CONNECTION_STRING')

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query)

            results = []
            for row in cursor.fetchall():
                results.append({
                    'title': row.title,
                    'content': row.content,
                    # Add more columns as needed
                })
            # Convert results to JSON string
            json_data = json.dumps(results)
            return func.HttpResponse(
                json_data,
                status_code=200,
                headers={"Content-Type": "application/json"},
            )
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


def insert_data_to_sql(data):
    connection_string = os.getenv('SQL_CONNECTION_STRING')
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO journal (title, content) VALUES (?, ?);", data['title'], data['content'])
            conn.commit()
            return True
    except Exception as e:
        logging.error(f"Error inserting data: {str(e)}")
        return False


@app.function_name(name="journal-add")
@app.route(route='journal-add', auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def journal_add(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a journal push request.')
    try:
        req_body = req.get_json()
        title = req_body.get('title')
        content = req_body.get('content')

        if title and content:
            if insert_data_to_sql({'title': title, 'content': content}):
                return func.HttpResponse("Data pushed successfully", status_code=200)
            else:
                return func.HttpResponse("Failed to push data", status_code=500)
        else:
            return func.HttpResponse("Please provide 'title' and 'content' in the request body", status_code=400)
    except ValueError:
        return func.HttpResponse("Invalid JSON format", status_code=400)
