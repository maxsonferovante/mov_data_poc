#!/usr/bin/env bash
set -euo pipefail

# Script de build e push da imagem da aplicação para o ECR

AWS_REGION="${AWS_REGION:-us-west-2}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ECR_REPOSITORY_NAME="${ECR_REPOSITORY_NAME:-mov-poc-app}"

echo "Região: ${AWS_REGION}"
echo "Repositório ECR: ${ECR_REPOSITORY_NAME}"
echo "Tag da imagem: ${IMAGE_TAG}"

AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
if [[ -z "${AWS_ACCOUNT_ID}" ]]; then
  echo "Não foi possível obter AWS_ACCOUNT_ID via aws sts get-caller-identity." >&2
  exit 1
fi

ECR_HOST="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
REPO_URL="${ECR_HOST}/${ECR_REPOSITORY_NAME}"

echo "Account ID: ${AWS_ACCOUNT_ID}"
echo "ECR Host: ${ECR_HOST}"
echo "ECR Repo URL: ${REPO_URL}"

echo "Fazendo login no ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_HOST}"

echo "Build da imagem local para linux/amd64"
docker build --platform linux/amd64 -t "${ECR_REPOSITORY_NAME}:${IMAGE_TAG}" .

echo "Tagueando imagem para o ECR"
docker tag "${ECR_REPOSITORY_NAME}:${IMAGE_TAG}" "${REPO_URL}:${IMAGE_TAG}"

echo "Fazendo push da imagem para o ECR"
docker push "${REPO_URL}:${IMAGE_TAG}"

echo "Imagem publicada com sucesso em ${REPO_URL}:${IMAGE_TAG}"

