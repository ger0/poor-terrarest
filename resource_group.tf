resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.name}${var.environment}"
  location = var.location

  tags = {
    contact = "gero"
  }
}
