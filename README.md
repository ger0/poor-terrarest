# Poor man's terraform MSSQL + Rest API deployment

Sets up a single table `journal` consisting of:
```
    title VARCHAR(100) PRIMARY KEY,
    content VARCHAR(512)
```

and then creates Rest API endpoints for insertion and listing of it's content.

```
terraform init
terraform apply -target=azurerm_linux_function_app.function_app
terraform apply
cd app
func azure functionapp publish restingdev001app --python
```

## Endpoints

journal-add requires an input json with 'title' and 'content'
journal-get requires a parameter 'title', displays content for the specified entry
journal-list lists all journal entries
journal-delete requires a parameter 'title', removes the specified entry
