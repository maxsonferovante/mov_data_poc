## Aplicação de movimentação S3 (ECS Fargate)

Aplicação em **Python assíncrono** para copiar objetos de um bucket S3 de origem para um bucket S3 de destino, usando **streaming** e **multipart upload**, preparada para rodar em uma **task ECS Fargate** (orquestrada pelo Step Functions já criado na infra).

### Visão geral

- **Entrada** (variáveis de ambiente):
  - `SOURCE_BUCKET`: bucket de origem.
  - `SOURCE_PREFIX`: prefixo de origem (será normalizado para terminar com `/`).
  - `TARGET_BUCKET`: bucket de destino.
  - `TARGET_PREFIX`: prefixo de destino (será normalizado para terminar com `/`).
  - `MAX_CONCURRENCY` (opcional, default `4`): quantas cópias de arquivos em paralelo.
  - `CHUNK_SIZE_MB` (opcional, default `8`): tamanho do chunk de streaming/multipart em MB.
  - `LOG_LEVEL` (opcional, default `INFO`).

- **Comportamento**:
  - Lista objetos em `SOURCE_BUCKET` com `SOURCE_PREFIX`.
  - Para cada objeto encontrado, cria um plano de cópia preservando o path relativo.
  - Faz leitura do objeto origem em **chunks** e envia para o destino via **multipart upload**.
  - Processa vários objetos em paralelo com `asyncio` (concorrência configurável).

### Arquitetura (Clean Architecture)

- `app/config.py`: leitura e validação da configuração (variáveis de ambiente).
- `app/core/domain/`:
  - `models.py`: modelos de domínio (`BucketRef`, `ObjectLocation`, `CopyPlan`, `CopyStats`).
  - `interfaces.py`: porta `AsyncS3Port` (interface assíncrona de S3).
- `app/core/use_cases/`:
  - `list_objects.py`: lista objetos a partir do prefixo.
  - `copy_object.py`: copia um único objeto via streaming + multipart.
  - `copy_batch.py`: orquestra cópia em lote com `asyncio` + retries.
- `app/infra/`:
  - `logging.py`: configuração de logging.
  - `aws/async_s3_client.py`: implementação de `AsyncS3Port` usando `aiobotocore` (S3 assíncrono).
- `app/main.py`: ponto de entrada (`asyncio.run`) que liga tudo.

### Dependências (aplicação)

Listadas em `requirements.txt` na raiz do projeto:

- `aiobotocore`
- `boto3`

> As versões podem ser ajustadas conforme necessidade; por enquanto usamos os nomes simples para a PoC.

### Como executar localmente

Na raiz do projeto:

```bash
pip install -r requirements.txt

export AWS_REGION=us-west-2
export SOURCE_BUCKET=mov-poc-source
export SOURCE_PREFIX=teste/origem/
export TARGET_BUCKET=mov-poc-target
export TARGET_PREFIX=teste/destino/

python -m app.main
```

### Fluxo resumido

1. `app/main.py` lê a configuração e monta `BucketRef` de origem e destino.
2. Cria um cliente S3 assíncrono (`AiobotocoreS3Client`).
3. Instancia `CopyBatchUseCase` com:
   - porta S3 assíncrona
   - source/target
   - concorrência e chunk size.
4. Executa `run()`:
   - lista objetos com `ListObjectsToCopyUseCase`.
   - dispara workers assíncronos para cada objeto (`CopyObjectUseCase`).
5. Ao final, loga estatísticas (total, sucesso, erro) e retorna código de saída 0/1.

### Integração com ECS / Step Functions

- A task definition do ECS deve:
  - usar uma imagem Docker que execute `python -m app.main` como comando/entrypoint.
  - injetar as variáveis de ambiente (`SOURCE_*`, `TARGET_*`) – já preparado no Step Functions da infra.

