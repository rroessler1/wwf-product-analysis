#!/bin/bash

# Set your Docker Hub username and Azure details
DOCKER_REPO_NAME="parse"
DOCKER_TAG="latest"
LOCAL_REPO_NAME="wwf-product-analysis-docker"

RESOURCE_GROUP="WWF"
CONTAINER_APP_NAME="wwf-product-analysis"
ENVIRONMENT="managedEnvironment-WWF-9ad0"

# Function to push the image to Docker Hub
push_to_docker() {
    echo "Building Docker image..."
    docker build -t $LOCAL_REPO_NAME .
    docker tag $LOCAL_REPO_NAME $1/$DOCKER_REPO_NAME:$DOCKER_TAG

    echo "Logging into Docker Hub..."
    docker login

    echo "Pushing image to Docker Hub..."
    docker push $1/$DOCKER_REPO_NAME:$DOCKER_TAG

    echo "Docker image pushed successfully!"
}

# Function to deploy to Azure Container Apps
push_to_azure() {
    echo "Deploying to Azure Container Apps..."
    az containerapp create \
      --name $CONTAINER_APP_NAME \
      --resource-group $RESOURCE_GROUP \
      --image $DOCKER_USERNAME/$DOCKER_REPO_NAME:$DOCKER_TAG \
      --ingress external \
      --environment $ENVIRONMENT

    echo "Deployment to Azure completed!"
    echo "Now test logging in with:"
    echo az containerapp exec  --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --command "/bin/bash"
}

# Validate that Azure CLI is installed
check_azure_cli_installed() {
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
}

get_docker_username() {
    read -p "Enter your Docker Hub username: " DOCKER_USERNAME
    echo "$DOCKER_USERNAME"
}

# Display menu options
echo "Choose an option:"
echo "1) Push to Docker Hub"
echo "2) Deploy to Azure Container Apps"
echo "3) Do both"

read -p "Enter your choice (1/2/3): " choice

case $choice in
    1)
	username=$(get_docker_username)
	push_to_docker $username
        ;;
    2)
	check_azure_cli_installed
        push_to_azure
        ;;
    3)
	check_azure_cli_installed
	username=$(get_docker_username)
	push_to_docker $username
        push_to_azure
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac


