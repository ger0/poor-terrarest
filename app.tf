resource "azurerm_service_plan" "asp" {
  name                = "${var.name}${var.environment}serviceplan"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_log_analytics_workspace" "la" {
  name                = "${var.name}${var.environment}workspace"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "insights" {
  name                = "${var.name}${var.environment}appinsights"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "other"
  workspace_id        = azurerm_log_analytics_workspace.la.id
}

resource "azurerm_storage_account" "appcode" {
  name                     = "${var.name}${var.environment}storage"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_linux_function_app" "function_app" {
  name                       = "${var.name}${var.environment}app"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location

  service_plan_id        = azurerm_service_plan.asp.id

  storage_account_name       = azurerm_storage_account.appcode.name
  storage_account_access_key = azurerm_storage_account.appcode.primary_access_key

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE" = "",
    "AzureWebJobsStorage"      = azurerm_storage_account.appcode.primary_connection_string
    "FUNCTIONS_WORKER_RUNTIME" = "python",
    "SQL_CONNECTION_STRING"    = "DRIVER={ODBC Driver 17 for SQL Server};Server=tcp:${azurerm_mssql_server.server.fully_qualified_domain_name},1433;Database=${azurerm_mssql_database.db.name};UID=${var.admin_username};PWD=${local.admin_password}"
  }

  site_config {
    always_on = false
    application_stack {
        python_version = "3.9"
    }
  }

  lifecycle {
    ignore_changes = [
      app_settings["WEBSITE_RUN_FROM_PACKAGE"],
    ]
  }
}
