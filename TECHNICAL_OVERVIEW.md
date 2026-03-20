# Visão Técnica da Movimentação S3

## Objetivo técnico

A aplicação executa movimentação (cópia) de objetos entre prefixos S3 com processamento assíncrono, concorrência controlada e seleção de estratégia de upload baseada no tamanho do arquivo.

O foco é:
- throughput previsível;
- baixo acoplamento entre regras de negócio e infraestrutura;
- extensibilidade para novas estratégias;
- geração de relatório final serializável para integração externa.

## Stack e ferramentas

- **Python 3**
- **asyncio** para concorrência cooperativa
- **aiobotocore** para chamadas assíncronas ao S3
- **dataclasses** para modelos de domínio
- **logging** para telemetria de execução

## Arquitetura por camadas

- `app/core/domain`
  - modelos (`BucketRef`, `ObjectLocation`, `CopyPlan`, `CopyStats`)
  - contratos (`AsyncS3Port`)
- `app/core/use_cases`
  - orquestração em lote (`CopyBatchUseCase`)
  - cópia por objeto (`CopyObjectUseCase`)
  - estratégias de cópia (`SmallObjectCopyStrategy`, `LargeObjectCopyStrategy`)
  - fábrica de estratégia (`CopyStrategyFactory`)
- `app/infra/aws`
  - implementação concreta do contrato S3 (`AiobotocoreS3Client`)
- `main.py`
  - bootstrap e composição de dependências

## Fluxo operacional

1. A aplicação carrega variáveis de ambiente (`AppConfig`).
2. `CopyBatchUseCase` cria:
   - **producer** para listar objetos por prefixo;
   - **N workers** (`MAX_CONCURRENCY`) para consumir a fila.
3. Cada worker usa seu próprio cliente S3 (`s3_client_factory`).
4. Para cada objeto:
   - monta `CopyPlan` (source -> target);
   - seleciona strategy via `CopyStrategyFactory`:
     - `< 5MB`: `put_object`;
     - `>= 5MB`: multipart sequencial.
5. Atualiza `CopyStats` (contadores + detalhes por item).
6. Emite relatório final serializável.

## Padrões de projeto aplicados

## 1) Strategy

Encapsula algoritmos de cópia por tipo de arquivo:
- `SmallObjectCopyStrategy`
- `LargeObjectCopyStrategy`

Benefício: troca de comportamento sem alterar orquestração.

## 2) Factory

`CopyStrategyFactory` decide a strategy em runtime com base em `size_bytes`.

Benefício: centraliza decisão e evita condicionais espalhadas.

## 3) Ports and Adapters

`AsyncS3Port` define a interface de infraestrutura.  
`AiobotocoreS3Client` implementa essa interface.

Benefício: desacoplamento entre domínio e SDK AWS.

## Estruturas de dados principais

## `ObjectLocation`

Representa objeto S3 com metadados mínimos para roteamento:

```python
@dataclass(frozen=True)
class ObjectLocation:
    bucket: str
    key: str
    size_bytes: int = 0
```

`size_bytes` é preenchido a partir de `list_objects_v2` (`Size`), evitando chamadas extras para decisão de strategy.

## `CopyStats`

Acumula:
- totais (`total_objects`, `success_count`, `error_count`);
- bytes movimentados (`total_bytes_moved`);
- itens detalhados de sucesso e falha.

Estrutura pronta para serialização:

```python
def to_serializable(self) -> dict[str, object]:
    return {
        "total_files_processed": self.total_objects,
        "total_success": self.success_count,
        "total_failed": self.error_count,
        "total_bytes_moved": self.total_bytes_moved,
        "success_items": self.success_items,
        "failed_items": self.failed_items,
    }
```

## Exemplo real: seleção de strategy por tamanho

```python
@dataclass(frozen=True)
class CopyStrategyFactory:
    s3: AsyncS3Port
    small_threshold_bytes: int = 5 * 1024 * 1024

    def for_size(self, size_bytes: int):
        if size_bytes < self.small_threshold_bytes:
            return SmallObjectCopyStrategy(s3=self.s3)
        return LargeObjectCopyStrategy(s3=self.s3)
```

## Exemplo real: roteamento no use case de cópia

```python
async def copy_one(self, obj: ObjectLocation) -> None:
    plan = self.build_plan(obj)
    strategy = self._strategy_factory.for_size(obj.size_bytes)
    await strategy.copy(plan=plan, chunk_size_bytes=self._chunk_size_bytes)
```

## Exemplo real: producer + workers assíncronos

```python
producer_task = asyncio.create_task(self._producer(queue, stats))
worker_tasks = [
    asyncio.create_task(self._worker_loop(idx + 1, queue, stats))
    for idx in range(self._max_concurrency)
]
```

Esse modelo fornece:
- backpressure (`QUEUE_MAX_SIZE`);
- paralelismo previsível por worker;
- encerramento limpo por sentinela (`None`).

## Producer e Workers no pipeline de movimentação

### Producer (listagem)

O **producer** é responsável exclusivamente por:
- listar objetos do prefixo de origem (`list_objects_v2`);
- converter cada entrada em `ObjectLocation` (incluindo `size_bytes`);
- enfileirar os itens para processamento;
- publicar sentinelas (`None`) ao final para encerrar os workers.

Trecho representativo:

```python
async with self._s3_client_factory() as producer_s3:
    list_uc = ListObjectsToCopyUseCase(producer_s3, self._source)
    async for obj in list_uc.execute():
        stats.total_objects += 1
        await queue.put(obj)
```

### Workers (download/upload)

Cada **worker** possui cliente S3 próprio e executa o ciclo completo por item:
1. recebe `ObjectLocation` da fila;
2. cria/usa `CopyObjectUseCase`;
3. faz download em streaming (`stream_object`);
4. faz upload por strategy selecionada:
   - small: `put_object_stream`;
   - large: `multipart_upload_stream`;
5. atualiza métricas e relatório detalhado.

Trecho representativo:

```python
async with self._s3_client_factory() as worker_s3:
    copy_uc = CopyObjectUseCase(...)
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            return
        try:
            await self._copy_one(copy_uc, item, stats)
        finally:
            queue.task_done()
```

Essa separação Producer/Workers evita acoplamento entre listagem e cópia, melhora throughput e mantém controle de memória.

## Exemplo real: leitura de tamanho na listagem S3

```python
for item in response.get("Contents", []):
    key = item["Key"]
    size_bytes = int(item.get("Size", 0))
    yield ObjectLocation(bucket=bucket, key=key, size_bytes=size_bytes)
```

## Considerações de performance

- `MAX_CONCURRENCY` controla workers ativos.
- `QUEUE_MAX_SIZE` limita memória da fila.
- `CHUNK_SIZE_MB` impacta latência/memória por stream.
- `PROGRESS_LOG_EVERY` reduz overhead de log por item.

Recomendação inicial:
- `MAX_CONCURRENCY=8`
- `QUEUE_MAX_SIZE=32`
- `CHUNK_SIZE_MB=8`
- `PROGRESS_LOG_EVERY=50`

## Observações operacionais

- O código atual gera relatório rico no final, apto para envio a serviços de notificação.
- O `main.py` está preparado para execução local e containerizada.
- O design permite adicionar novas strategies sem alterar o fluxo de lote.
