#!/bin/bash

# Check if 'az' command exists
if ! command -v az &> /dev/null; then
    echo "Azure CLI (az) is not installed!"
    echo "Run the following commands to install it and set it up:"
    echo ""
    echo "  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    echo "  az login  # May take multiple tries"
    echo "  az extension add --name containerapp --upgrade"
    echo ""
    echo "After installing, restart your terminal and rerun this script."
    exit 1
fi

az containerapp up   --name wwf-product-analysis   --resource-group WWF --location switzerlandnorth   --source .
echo "Be sure to delete the auto-created container registry after so it doesn't charge you money."
echo "https://portal.azure.com/#browse/Microsoft.ContainerRegistry%2Fregistries"

