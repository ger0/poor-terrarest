output "sql_server_fqdn" {
    value = azurerm_mssql_server.server.fully_qualified_domain_name
}

output "admin_password" {
  sensitive = true
  value     = local.admin_password
}