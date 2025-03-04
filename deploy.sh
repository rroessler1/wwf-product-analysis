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
      --image $1/$DOCKER_REPO_NAME:$DOCKER_TAG \
      --ingress external \
      --target-port 80 \
      --secrets "openai-api-key=${OPENAI_API_KEY}" \
      --env-vars OPENAI_API_KEY=secretref:openai-api-key \
      --environment $ENVIRONMENT

    app_url=$(az containerapp show \
      --name $CONTAINER_APP_NAME  \
      --resource-group $RESOURCE_GROUP \
      --query properties.configuration.ingress.fqdn \
      --output tsv)

    echo "Deployment to Azure completed!"
    echo "Now test logging in with:"
    echo az containerapp exec  --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --command "/bin/bash"
    echo "URL is $app_url"
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

check_api_key_available() {
    if [[ -z "$OPENAI_API_KEY" ]]; then
        echo "Error: OPENAI_API_KEY must be set as an environment variable so we can push it to Azure." >&2
        exit 1
fi
}

run_azure_prereqs() {
    check_azure_cli_installed
    check_api_key_available
}

read -p "Enter your Docker Hub username: " DOCKER_USERNAME

# Display menu options
echo "Choose an option:"
echo "1) Push to Docker Hub"
echo "2) Deploy to Azure Container Apps"
echo "3) Do both"

read -p "Enter your choice (1/2/3): " choice

case $choice in
    1)
        push_to_docker $DOCKER_USERNAME
        ;;
    2)
        run_azure_prereqs
        push_to_azure $DOCKER_USERNAME
        ;;
    3)
        run_azure_prereqs
        push_to_docker $DOCKER_USERNAME
        push_to_azure $DOCKER_USERNAME
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac


