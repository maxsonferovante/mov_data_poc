## Scripts de build e deploy da imagem

Este diretório contém scripts auxiliares para buildar e publicar a imagem Docker da aplicação de movimentação S3 no Amazon ECR.

### `build_and_push_ecr.sh`

- **Função**: faz o build da imagem Docker local, faz login no ECR e publica a imagem com uma tag (default `latest`).
- **Pré-requisitos**:
  - Docker instalado e rodando.
  - AWS CLI configurado (`aws configure` ou SSO) com permissões para `sts:GetCallerIdentity` e operações de ECR.
  - Infra aplicada (`terraform apply` em `infra/`) para garantir que o repositório ECR exista.

#### Variáveis de ambiente suportadas

- `AWS_REGION`:
  - Região AWS usada (default: `us-west-2`).
- `ECR_REPOSITORY_NAME`:
  - Nome do repositório ECR (default: `mov-poc-app`, compatível com o módulo `ecs`).
- `IMAGE_TAG`:
  - Tag da imagem (default: `latest`).

#### Passo a passo

Na raiz do projeto:

```bash
cd /Users/mferovante/Documents/workspace/mov_data_poc

# Opcional: ajustar região, repositório ou tag
export AWS_REGION=us-west-2
export ECR_REPOSITORY_NAME=mov-poc-app
export IMAGE_TAG=latest

chmod +x scripts/build_and_push_ecr.sh
bash scripts/build_and_push_ecr.sh
```

O script irá:

1. Descobrir o `AWS_ACCOUNT_ID` via `aws sts get-caller-identity`.
2. Fazer login no ECR da conta/região.
3. Executar `docker build` usando o `Dockerfile` da raiz.
4. Taguear a imagem como `<account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>`.
5. Fazer `docker push` para o repositório ECR.

