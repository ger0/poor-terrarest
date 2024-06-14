resource "random_password" "admin_password" {
  count       = var.admin_password == null ? 1 : 0
  length      = 20
  special     = false
  min_numeric = 1
  min_upper   = 1
  min_lower   = 1
  min_special = 0
}

locals {
  admin_password = try(random_password.admin_password[0].result, var.admin_password)
}

resource "azurerm_sql_server" "server" {
  name                         = "sqlserver-restowo"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  version                      = "12.0"
  administrator_login          = var.admin_username
  administrator_login_password = local.admin_password
}

resource "azurerm_sql_database" "db" {
  name        = var.sql_db_name
  location    = var.location
  server_name = azurerm_sql_server.server.name
  resource_group_name          = azurerm_resource_group.rg.name
}

resource "azurerm_sql_firewall_rule" "allow_azure_services" {
  name                = "AllowAzureServices"
  server_name         = azurerm_sql_server.server.name
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "0.0.0.0"
  resource_group_name          = azurerm_resource_group.rg.name
}

resource "azurerm_sql_firewall_rule" "allow_function_app" {
  depends_on          = [azurerm_linux_function_app.function_app]
  server_name         = azurerm_sql_server.server.name
  resource_group_name = azurerm_resource_group.rg.name
  for_each            = toset(split(",", azurerm_linux_function_app.function_app.outbound_ip_addresses))
  name                = "AllowFunctionApp${each.key}"
  start_ip_address    = each.value
  end_ip_address      = each.value
}

resource "null_resource" "create_tables" {
  depends_on = [azurerm_sql_database.db]

  provisioner "local-exec" {
    command = <<EOT
      sqlcmd -S ${azurerm_sql_server.server.fully_qualified_domain_name} \
             -U ${var.admin_username} \
             -P ${local.admin_password} \
             -d ${azurerm_sql_database.db.name} \
             -i CREATE TABLE users (\
                  username VARCHAR(100) PRIMARY KEY,);\
                CREATE TABLE journal (\
                    title VARCHAR(100) PRIMARY KEY,\
                    content VARCHAR(512));
    EOT
  }
}
