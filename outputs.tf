output "app_service_default_hostname" {
    value = azurerm_app_service.app.default_site_hostname
}

output "sql_server_fqdn" {
    value = azurerm_mssql_server.server.fully_qualified_domain_name
}

output "admin_password" {
  sensitive = true
  value     = local.admin_password
}
