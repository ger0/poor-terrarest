import logging
import json
import os
import azure.functions as func
import pyodbc

import uuid

from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.storage.queue import (
    QueueServiceClient,
    BinaryBase64DecodePolicy,
    BinaryBase64EncodePolicy,
)
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials


app = func.FunctionApp()

try:
    PHOTOS_QUEUE_URL = os.environ["ENV_PHOTOS_QUEUE_URL"]
    PHOTOS_TABLE_URL = os.environ["ENV_PHOTOS_TABLE_URL"]
    PHOTOS_CONTAINER_URL = os.environ["ENV_PHOTOS_CONTAINER_URL"]
    PHOTOS_TABLE_NAME = os.environ["ENV_PHOTOS_TABLE_NAME"]
    PHOTOS_QUEUE_NAME = os.environ["ENV_PHOTOS_QUEUE_NAME"]
    PHOTOS_CONTAINER_NAME = os.environ["ENV_PHOTOS_CONTAINER_NAME"]
    PHOTOS_PRIMARY_KEY = os.environ["ENV_PHOTOS_PRIMARY_KEY"]
    SQL_CONNECTION_STR = os.environ["SQL_CONNECTION_STRING"]
    CREDENTIALS = {
        "account_name": os.environ["ENV_PHOTOS_ACCOUNT_NAME"],
        "account_key": PHOTOS_PRIMARY_KEY,
    }
    PHOTOS_CONNSTRING = os.environ["ENV_PHOTOS_CONNSTR"]
    CV_ENDPOINT = os.environ["ENV_COGNITIVE_URL"]
    CV_KEY = os.environ["ENV_COGNITIVE_KEY"]
except KeyError as e:
    logging.error(f"Error: {e}")
    raise e


def generate_sas_token(image_name):
    blob_service_client = BlobServiceClient.from_connection_string(PHOTOS_CONNSTRING)
    blob_client = blob_service_client.get_blob_client(
        container=PHOTOS_CONTAINER_NAME, blob=image_name
    )
    token = generate_blob_sas(
        account_name=blob_client.account_name,
        container_name=blob_client.container_name,
        blob_name=blob_client.blob_name,
        account_key=PHOTOS_PRIMARY_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.datetime.now() + datetime.timedelta(hours=1),
    )
    return f"{blob_client.url}?{token}"


@app.function_name(name="post")
@app.route(route="post", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def post(req: func.HttpRequest) -> func.HttpResponse:
    """Post image from body to Azure Blob Storage and create an entry in Azure Table Storage"""
    try:
        table_service_client = TableServiceClient.from_connection_string(
            PHOTOS_CONNSTRING
        )
        table_client = table_service_client.get_table_client(PHOTOS_TABLE_NAME)
        blob_service_client = BlobServiceClient.from_connection_string(
            PHOTOS_CONNSTRING
        )
        queue_service_client = QueueServiceClient.from_connection_string(
            PHOTOS_CONNSTRING
        )
        queue_client = queue_service_client.get_queue_client(
            PHOTOS_QUEUE_NAME,
            message_encode_policy=BinaryBase64EncodePolicy(),
            message_decode_policy=BinaryBase64DecodePolicy(),
        )
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            "Error: Unable to connect to Azure Storage", status_code=500
        )

    logging.info(
        "Uploading a photo to Azure Blob Storage and creating an entry in Azure Table Storage"
    )
    if not req.get_body():
        return func.HttpResponse(
            "Please pass an image in the request body", status_code=400
        )

    try:
        body = req.get_body()
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            "Error: Unable to read the image from the request body", status_code=400
        )

    idx = str(uuid.uuid4())
    image_name = idx + ".png"

    try:
        blob_client = blob_service_client.get_blob_client(
            container=PHOTOS_CONTAINER_NAME, blob=image_name
        )
        blob_client.upload_blob(body, overwrite=True)
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            "Error: Unable to upload image to Azure Blob Storage", status_code=500
        )

    entity = {
        "PartitionKey": idx,
        "RowKey": idx,
        "Timestamp": datetime.datetime.now().isoformat(),
        "Url": generate_sas_token(image_name),
        "State": "uploaded",
        "Result": "Nothing",
    }
    try:
        logging.info("upserting entity")
        table_client.upsert_entity(entity=entity)
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            "Error: Unable to create an entry in Azure Table Storage", status_code=500
        )

    # add message to the queue
    try:
        queue_client.send_message(idx.encode("utf-8"))
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            "Error: Unable to add a message to the Azure Queue", status_code=500
        )

    return func.HttpResponse(
        json.dumps(entity),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )


@app.function_name(name="list")
@app.route(route="list", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def list(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    try:
        table_service_client = TableServiceClient.from_connection_string(
            PHOTOS_CONNSTRING
        )
        table_client = table_service_client.get_table_client(PHOTOS_TABLE_NAME)
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            "Error: Unable to connect to Azure Storage", status_code=500
        )

    logging.info(f"Connected to Azure Table Storage: {PHOTOS_TABLE_NAME}")

    # read all entities from the table
    entities = []
    try:
        for entity in table_client.list_entities():
            entities.append(entity)
        logging.warn(f"Entities: {entities}")
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            "Error: Unable to read entities from Azure Table Storage", status_code=500
        )
    return func.HttpResponse(
        json.dumps({"list": entities}),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )


# Process an id from queue with Azure Cognitive Services image recognition
@app.function_name(name="process")
@app.queue_trigger(
    queue_name=PHOTOS_QUEUE_NAME, connection="ENV_PHOTOS_CONNSTR", arg_name="msg"
)
def process(msg: func.QueueMessage) -> None:
    idx = msg.get_body().decode("utf-8")
    logging.info("Python HTTP trigger function processed a request.")

    try:
        table_service_client = TableServiceClient.from_connection_string(
            PHOTOS_CONNSTRING
        )
        table_client = table_service_client.get_table_client(PHOTOS_TABLE_NAME)
        credentials = CognitiveServicesCredentials(CV_KEY)
        cv_service_client = ComputerVisionClient(CV_ENDPOINT, credentials)
    except Exception as e:
        logging.error(f"Error: {e}")
        raise e

    logging.info(f"Connected to Azure Table Storage: {PHOTOS_TABLE_NAME}")

    # read the entity from the table
    entity = None
    try:
        entity = table_client.get_entity(partition_key=idx, row_key=idx)
    except Exception as e:
        logging.error(f"Error: {e}")
        raise e

    if entity is None:
        return

    # get sas token
    try:
        sas_token = generate_sas_token(idx + ".png")
    except Exception as e:
        logging.error(f"Error: {e}")
        raise e

    # Label image with Azure Congitive Services
    try:
        tags = []
        analysis = cv_service_client.analyze_image(sas_token, [VisualFeatureTypes.tags])
        for tag in analysis.tags:
            if tag.confidence > 0.8:
                tags.append(tag.name)
    except Exception as e:
        logging.error(f"Error: {e}")
        raise e

    entity["Result"] = tags
    entity["State"] = "processed"

    try:
        table_client.upsert_entity(entity=entity)
    except Exception as e:
        logging.error(f"Error: {e}")
        raise e

    return None

@app.function_name(name="create")
@app.route(route='create', auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def create(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    query="SELECT * FROM dbo.users"

    try:
        with pyodbc.connect(SQL_CONNECTION_STR) as conn:
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

    try:
        title = req.params.get('title')
        with pyodbc.connect(SQL_CONNECTION_STR) as conn:
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


@app.function_name(name="journal-delete")
@app.route(route='journal-delete', auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def journal_delete(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a journal request.')
    query = "DELETE FROM journal WHERE title = ?"

    try:
        title = req.params.get('title')
        with pyodbc.connect(SQL_CONNECTION_STR) as conn:
            cursor = conn.cursor()
            cursor.execute(query, title)
            return func.HttpResponse(
                "Successfully deleted the entry...",
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

    try:
        with pyodbc.connect(SQL_CONNECTION_STR) as conn:
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
    try:
        with pyodbc.connect(SQL_CONNECTION_STR) as conn:
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
