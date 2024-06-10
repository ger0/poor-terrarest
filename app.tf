resource "azurerm_service_plan" "asp" {
  name                = "${var.name}${var.environment}serviceplan"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1"
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
    "FUNCTIONS_WORKER_RUNTIME" = "python",
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
