resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.name}${var.environment}-001"
  location = var.location

  tags = {
    contact = "gero"
  }
}

resource "azurerm_app_service" "app" {
  name                = "rest-app"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  app_service_plan_id = azurerm_service_plan.asp.id

  site_config {
    python_version = "3.4"
  }

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
  }
}
