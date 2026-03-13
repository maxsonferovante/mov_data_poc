# mov_data_poc

PoC de infraestrutura em **AWS + Terraform** para orquestrar movimentação de dados entre **dois buckets S3** usando **AWS Step Functions** e **ECS Fargate**.

> Nesta fase não há implementação do “mover de dados”. A task do ECS usa uma imagem *placeholder* e apenas imprime uma mensagem e aguarda alguns segundos. Em seguida, vamos publicar o código real no **ECR** e trocar a imagem da task definition.

## Objetivo

- Executar movimentações **sob demanda** (uma por execução) de:
  - `source_bucket` + `source_prefix`
  - para `target_bucket` + `target_prefix`
- O fluxo é controlado via **Step Functions**, que dispara uma **ECS Fargate Task** passando esses parâmetros como variáveis de ambiente.

## Requisitos e decisões

- **Uma única conta AWS**, um único ambiente (PoC).
- **VPC dedicada**, somente **subnets privadas**.
- **Sem internet**:
  - sem subnets públicas
  - sem Internet Gateway
  - sem NAT Gateway
  - acesso a serviços AWS via **VPC Endpoints** (PrivateLink / Gateway)
- **S3**:
  - **versionamento habilitado**
  - **SSE-KMS** com chave **gerenciada pela AWS**
  - bloqueio de acesso público

## Arquitetura (alto nível)

1. Você inicia uma execução do **Step Functions** com os parâmetros (buckets/prefixos).
2. A state machine executa `ecs:runTask.sync` no **ECS Fargate** (awsvpc).
3. A task (futura) lê do bucket/prefixo de origem e escreve no bucket/prefixo de destino.

## Estrutura do repositório

- `infra/`
  - `main.tf`, `providers.tf`, `variables.tf`, `outputs.tf`: composição dos módulos.
  - `terraform.tfvars`: valores do ambiente (ex.: região).
- `infra/modules/`
  - `network/`: VPC privada + subnets privadas + VPC endpoints (S3, ECS, Logs, States, STS, ECR).
  - `s3/`: buckets de origem/destino com versionamento e SSE-KMS.
  - `ecs/`: cluster ECS Fargate, roles IAM, log group e task definition placeholder.
  - `step_functions/`: state machine e role IAM para disparar tasks ECS.
  - `observability/`: ponto de extensão para alarms/observabilidade (mantido simples na PoC).

## Como aplicar a infraestrutura

### Pré-requisitos

- Terraform `>= 1.5`
- Credenciais AWS configuradas localmente (ex.: `aws configure` / SSO / env vars)

### Configuração

Edite `infra/terraform.tfvars` (já criado) e garanta a região:

```hcl
aws_region = "us-west-2"
```

### Deploy

Dentro da pasta `infra/`:

```bash
cd infra
terraform init
terraform plan
terraform apply
```

Ao final, veja `infra/outputs.tf` para outputs como:

- `source_bucket_name` (ex.: `mov-poc-source`)
- `target_bucket_name` (ex.: `mov-poc-target`)
- `step_functions_state_machine_arn`

## Como testar (execução do Step Functions)

No Console da AWS:

1. Vá em **Step Functions**.
2. Abra a state machine `mov-poc-data-mover-sm`.
3. Clique em **Start execution** e use um input como:

```json
{
  "source_bucket": "mov-poc-source",
  "source_prefix": "teste/origem/",
  "target_bucket": "mov-poc-target",
  "target_prefix": "teste/destino/"
}
```

### Onde ver logs

- **ECS Task logs**: CloudWatch Logs group `/ecs/mov-poc-data-mover`
- **Step Functions logs**: CloudWatch Logs group `/aws/states/mov-poc-data-mover`

## IAM (visão objetiva)

- **ECS Execution Role**: policy gerenciada `AmazonECSTaskExecutionRolePolicy` (logs e ECR).
- **ECS Task Role**:
  - ler/listar no bucket de origem
  - escrever/listar no bucket de destino
  - usar KMS (Encrypt/Decrypt/DataKey) para SSE-KMS do S3
- **Step Functions Role**:
  - `ecs:RunTask` / `ecs:DescribeTasks`
  - `iam:PassRole` para as roles do ECS

## Próximos passos (quando formos colocar o código real)

1. Criar repositório no **ECR**.
2. Buildar e publicar a imagem do container.
3. Trocar a `image` em `modules/ecs/main.tf` na task definition.
4. Ajustar (se necessário) `command`/`env` para o seu binário de movimentação.

## Remover recursos

```bash
terraform destroy
```

