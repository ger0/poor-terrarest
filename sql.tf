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

resource "azurerm_mssql_server" "server" {
  name                         = var.sql_sv_name
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  version                      = "12.0"
  administrator_login          = var.admin_username
  administrator_login_password = local.admin_password
}

resource "azurerm_mssql_database" "db" {
  name      = var.sql_db_name
  server_id = azurerm_mssql_server.server.id
  sku_name            = "S1"
}

resource "azurerm_mssql_firewall_rule" "allow_azure_services" {
  name                = "AllowAzureServices"
  server_id           = azurerm_mssql_server.server.id
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "0.0.0.0"
}

resource "azurerm_mssql_firewall_rule" "allow_function_app" {
  depends_on          = [azurerm_linux_function_app.function_app]
  server_id           = azurerm_mssql_server.server.id
  for_each            = toset(split(",", azurerm_linux_function_app.function_app.outbound_ip_addresses))
  name                = "AllowFunctionApp${each.key}"
  start_ip_address    = each.value
  end_ip_address      = each.value
}

data "http" "my_public_ip" {
  url = "https://ifconfig.co/json"
  request_headers = {
    Accept = "application/json"
  }
}

locals {
  ifconfig_co_json = jsondecode(data.http.my_public_ip.body)
  my_ip_addr = local.ifconfig_co_json.ip
}

resource "azurerm_mssql_firewall_rule" "allow_this_pc" {
  depends_on          = [azurerm_linux_function_app.function_app]
  server_id           = azurerm_mssql_server.server.id
  name                = "AllowFunctionApp_PC"
  start_ip_address    = local.my_ip_addr
  end_ip_address      = local.my_ip_addr
}

resource "null_resource" "create_tables" {
  depends_on = [azurerm_mssql_firewall_rule.allow_this_pc]
  provisioner "local-exec" {
    command = <<EOT
      export DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1; \
      mssql-cli -S ${azurerm_mssql_server.server.fully_qualified_domain_name} \
             -U ${var.admin_username} \
             -P ${local.admin_password} \
             -d ${azurerm_mssql_database.db.name} \
             -Q "CREATE TABLE journal (\
                    title VARCHAR(100) PRIMARY KEY,\
                    content VARCHAR(512));"
    EOT
  }
}
