resource "azurerm_network_interface" "utility" {
  name                = "${local.identifier}-utility-nic"
  location            = azurerm_resource_group.shared_rg.location
  resource_group_name = azurerm_resource_group.shared_rg.name
  tags                = local.tags

  ip_configuration {
    name                          = "ipconfig1"
    subnet_id                     = azurerm_subnet.utility.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_windows_virtual_machine" "utility" {
  name                = "${local.identifier}-utility-vm"
  computer_name       = "${local.identifier}-utility"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  size                = "Standard_B2s"
  admin_username      = "azureuser"
  admin_password      = var.utility_vm_admin_password
  network_interface_ids = [
    azurerm_network_interface.utility.id
  ]
  tags = local.tags

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "MicrosoftWindowsDesktop"
    offer     = "windows-11"
    sku       = "win11-25h2-pro"
    version   = "latest"
  }
}
