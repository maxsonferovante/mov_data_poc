# mov_data_poc

PoC para movimentar objetos entre buckets S3 com AWS ECS Fargate e Step Functions, usando Terraform para infraestrutura e Python assíncrono para execução da cópia.

## O que o projeto faz

- Provisiona infraestrutura AWS da PoC:
  - VPC privada com endpoints
  - Buckets S3 de origem e destino
  - ECS Fargate + ECR
  - Step Functions para orquestração
- Executa cópia de objetos S3 por prefixo de origem/destino.
- Processa itens com fila assíncrona + workers.
- Escolhe estratégia de cópia por tamanho do arquivo (Strategy + Factory):
  - **Small (< 5MB):** `put_object`
  - **Large (>= 5MB):** multipart upload sequencial
- Gera relatório final detalhado e serializável para integração com notificação.

## Arquitetura da aplicação

- `app/core/domain`: modelos e contratos.
- `app/core/use_cases`:
  - `copy_batch.py`: producer/queue/workers.
  - `copy_object.py`: plano de cópia por objeto.
  - `copy_strategies.py`: estratégias Small/Large.
  - `copy_strategy_factory.py`: seleção da estratégia por `size_bytes`.
- `app/infra/aws/async_s3_client.py`: implementação S3 assíncrona.
- `main.py`: bootstrap da execução.

## Variáveis de ambiente

### Obrigatórias

- `SOURCE_BUCKET`
- `SOURCE_PREFIX`
- `TARGET_BUCKET`
- `TARGET_PREFIX`

### Opcionais

- `MAX_CONCURRENCY` (default: `4`)  
  Quantidade de workers.
- `QUEUE_MAX_SIZE` (default: `worker_count * 2`)  
  Tamanho da fila assíncrona.
- `PROGRESS_LOG_EVERY` (default: `50`)  
  Frequência do log agregado de progresso.
- `CHUNK_SIZE_MB` (default: `8`)  
  Tamanho do chunk para streaming.
- `LOG_LEVEL` (default: `INFO`)  
  Nível de log.

## Relatório final da execução

Ao final, a aplicação gera e loga um payload serializável com:

- `total_files_processed`
- `total_success`
- `total_failed`
- `total_bytes_moved`
- `success_items[]` com:
  - `source_key`
  - `target_key`
  - `size_bytes`
- `failed_items[]` com:
  - `source_key`
  - `target_key`
  - `size_bytes`
  - `error_message`

Esse payload pode ser serializado com `json.dumps(...)` e enviado depois para SNS/SQS/webhook.

## Como rodar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r requirements.txt
python3 main.py
```

## Infraestrutura (Terraform)

```bash
cd infra
terraform init
terraform apply
```

## Build e push da imagem (ECR)

```bash
cd scripts
chmod +x build_and_push_ecr.sh
./build_and_push_ecr.sh
```

## Destroy da PoC

```bash
cd infra
terraform destroy
```

Os módulos já estão preparados para facilitar a remoção completa da PoC, inclusive recursos com dados/imagens.
