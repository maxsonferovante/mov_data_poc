## Visão geral do projeto

Este repositório contém uma **PoC de movimentação de dados entre buckets S3** usando:
- **Infraestrutura como código** com Terraform (VPC isolada, S3, ECS Fargate, Step Functions, ECR, IAM, CloudWatch Logs).
- **Aplicação em Python assíncrona** para copiar objetos entre buckets S3, com streaming e multipart upload.
- **Docker + ECR** para empacotar e distribuir a aplicação, consumida por tarefas ECS Fargate orquestradas pelo Step Functions.

## Arquitetura em alto nível

- **Buckets S3**
  - `mov-poc-source`: bucket de origem dos dados.
  - `mov-poc-target`: bucket de destino dos dados.
  - Versionamento e criptografia SSE-KMS gerenciados pela AWS.

- **Rede**
  - VPC dedicada, subnets privadas, sem saída direta para internet.
  - VPC Endpoints para S3, ECS, ECR, Logs, Step Functions, STS.

- **ECS Fargate + ECR**
  - Cluster ECS Fargate para executar a tarefa de movimentação (`mov-poc-data-mover`).
  - Task Definition aponta para imagem Docker da aplicação no ECR (`mov-poc-app`).
  - Roles IAM específicas para:
    - Execução da task (pull da imagem, logs).
    - Acesso de leitura no bucket de origem e escrita no bucket de destino.

- **Step Functions**
  - State Machine `mov-poc-data-mover-sm` que executa `ecs:runTask.sync`.
  - Passa via **overrides** as variáveis de ambiente:
    - `SOURCE_BUCKET`, `SOURCE_PREFIX`
    - `TARGET_BUCKET`, `TARGET_PREFIX`

## Aplicação Python (movimentação S3)

- Código principal em `main.py` e pacote `app/`.
- Organização em camadas (estilo Clean Architecture):
  - `app/core/domain`: modelos e interfaces de domínio.
  - `app/core/use_cases`: casos de uso (`list_objects`, `copy_object`, `copy_batch`).
  - `app/infra`: integrações (S3 assíncrono, logging).
  - `app/config.py`: leitura e validação de variáveis de ambiente.
- Tecnologias-chave:
  - `asyncio` + `aiobotocore` para chamadas S3 assíncronas.
  - Streaming em chunks e **multipart upload** para arquivos grandes.
  - Comportamento padrão: **copiar** (não apaga origem).

### Variáveis de ambiente principais

- Obrigatórias:
  - `SOURCE_BUCKET`: nome do bucket de origem.
  - `SOURCE_PREFIX`: prefixo dentro do bucket de origem (pode ser vazio).
  - `TARGET_BUCKET`: nome do bucket de destino.
  - `TARGET_PREFIX`: prefixo dentro do bucket de destino (pode ser vazio).

- Opcionais (com defaults):
  - `MAX_CONCURRENCY`: número máximo de objetos processados em paralelo.
  - `CHUNK_SIZE_MB`: tamanho do chunk em MB para streaming/multipart.

## Como provisionar a infraestrutura (Terraform)

Pré-requisitos:
- Terraform instalado.
- Credenciais AWS configuradas para a conta da PoC.

Passos:

```bash
cd infra
terraform init
terraform apply
```

Isso criará:
- VPC, subnets privadas, endpoints.
- Buckets S3 de origem/destino.
- Cluster ECS Fargate, task definition, roles IAM.
- State Machine do Step Functions.
- Repositório ECR da aplicação.

> Observação: o módulo S3/ECR está configurado com `force_destroy`/`force_delete` para facilitar destruir tudo em ambiente de PoC.

## Como buildar e publicar a imagem no ECR

Pré-requisitos:
- Docker instalado e em execução.
- AWS CLI configurada.

Passos:

```bash
cd scripts
chmod +x build_and_push_ecr.sh
./build_and_push_ecr.sh
```

O script:
- Descobre a conta e região AWS.
- Faz login no ECR.
- Faz build da imagem Docker a partir do `Dockerfile` na raiz.
- Marca com a tag configurada (por padrão `latest`).
- Faz push para o repositório ECR `mov-poc-app`.

Após o push, a próxima execução da task ECS usará a imagem atualizada (de acordo com `image_tag` no módulo ECS).

## Como testar localmente (sem ECS/Step Functions)

1. Criar e ativar um ambiente virtual (opcional, mas recomendado):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r requirements.txt
```

2. Configurar variáveis de ambiente (exemplo usando `.env` ou export direto):

```bash
export SOURCE_BUCKET=mov-poc-source
export SOURCE_PREFIX=meus-arquivos/
export TARGET_BUCKET=mov-poc-target
export TARGET_PREFIX=backup/
export MAX_CONCURRENCY=1
export CHUNK_SIZE_MB=4
```

3. Executar a aplicação:

```bash
python3 main.py
```

Você verá logs indicando:
- Arquivos listados no bucket de origem.
- Início e fim da cópia de cada objeto.
- Estatísticas finais (quantos arquivos copiados com sucesso/falha).

## Como testar via Step Functions + ECS

1. Com a infraestrutura já provisionada e a imagem publicada no ECR:
   - Vá até o console do **Step Functions**.
   - Abra a state machine `mov-poc-data-mover-sm`.

2. Inicie uma nova execução usando um input JSON como:

```json
{
  "source_bucket": "mov-poc-source",
  "source_prefix": "meus-arquivos/",
  "target_bucket": "mov-poc-target",
  "target_prefix": "backup/"
}
```

3. Acompanhe:
   - O progresso da execução da state machine.
   - Os logs da task ECS no CloudWatch Logs (`/ecs/mov-poc-data-mover`).

## Como destruir a infraestrutura

> Atenção: isso irá remover VPC, ECS, Step Functions, ECR e os buckets S3 (incluindo objetos/versões).

```bash
cd infra
terraform destroy
```

Devido a `force_destroy` nos buckets S3 e `force_delete` no ECR, o Terraform consegue apagar todos os recursos da PoC, mesmo que ainda existam dados/imagens.+
