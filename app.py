import logging
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    method = req.method

    if method == "GET":
        name = req.params.get('name')
        if not name:
            try:
                req_body = req.get_json()
            except ValueError:
                pass
            else:
                name = req_body.get('name')

        if name:
            return func.HttpResponse(f"Hello, {name}!")
        else:
            return func.HttpResponse(
                "Please pass a name on the query string or in the request body",
                status_code=400
            )

    elif method == "POST":
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse("Invalid JSON", status_code=400)

        data = req_body.get('data')
        if data:
            response = {
                "message": "Data received",
                "data": data
            }
            return func.HttpResponse(json.dumps(response), mimetype="application/json", status_code=200)
        else:
            return func.HttpResponse("Missing 'data' in request body", status_code=400)

    else:
        return func.HttpResponse(f"Method {method} not allowed", status_code=405)
