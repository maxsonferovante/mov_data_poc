import asyncio
import logging
from typing import Callable, Optional

from app.core.domain.models import BucketRef, CopyStats, ObjectLocation
from app.core.use_cases.copy_object import CopyObjectUseCase
from app.core.use_cases.list_objects import ListObjectsToCopyUseCase
from app.infra.aws.async_s3_client import AiobotocoreS3Client


logger = logging.getLogger(__name__)


class CopyBatchUseCase:
    # Caso de uso que coordena a cópia em lote com concorrência controlada

    def __init__(
        self,
        s3_client_factory: Callable[[], AiobotocoreS3Client],
        source: BucketRef,
        target: BucketRef,
        max_concurrency: int,
        chunk_size_bytes: int,
        queue_max_size: int = 100,
        progress_log_every: int = 100,
    ) -> None:
        self._s3_client_factory = s3_client_factory
        self._source = source
        self._target = target
        self._max_concurrency = max_concurrency
        self._chunk_size_bytes = chunk_size_bytes
        self._queue_max_size = max(1, queue_max_size)
        self._progress_log_every = max(1, progress_log_every)

    async def _copy_one(
        self,
        copy_uc: CopyObjectUseCase,
        obj: ObjectLocation,
        stats: CopyStats,
    ) -> None:
        # Copia um único item sem retry manual, com logs e coleta de resultado detalhado.
        plan = copy_uc.build_plan(obj)
        logger.debug("Iniciando cópia do objeto %s/%s", obj.bucket, obj.key)
        try:
            await copy_uc.copy_one(obj)
        except Exception as exc:  # noqa: BLE001
            stats.error_count += 1
            logger.error("Falha ao copiar objeto %s/%s: %s", obj.bucket, obj.key, exc)
            stats.failed_items.append(
                {
                    "source_key": plan.source.key,
                    "target_key": plan.target.key,
                    "size_bytes": obj.size_bytes,
                    "error_message": str(exc),
                }
            )
        else:
            stats.success_count += 1
            stats.total_bytes_moved += obj.size_bytes
            stats.success_items.append(
                {
                    "source_key": plan.source.key,
                    "target_key": plan.target.key,
                    "size_bytes": obj.size_bytes,
                }
            )
            logger.debug("Cópia concluída do objeto %s/%s", obj.bucket, obj.key)

        processed = stats.success_count + stats.error_count
        if processed > 0 and processed % self._progress_log_every == 0:
            logger.info(
                "Progresso da cópia: processados=%d total=%d sucesso=%d erro=%d",
                processed,
                stats.total_objects,
                stats.success_count,
                stats.error_count,
            )

    async def _producer(
        self,
        queue: asyncio.Queue[Optional[ObjectLocation]],
        stats: CopyStats,
    ) -> None:
        # Produz itens de cópia e publica sentinelas para encerrar workers
        async with self._s3_client_factory() as producer_s3:
            list_uc = ListObjectsToCopyUseCase(producer_s3, self._source)
            async for obj in list_uc.execute():
                stats.total_objects += 1
                await queue.put(obj)

        for _ in range(self._max_concurrency):
            await queue.put(None)

    async def _worker_loop(
        self,
        worker_id: int,
        queue: asyncio.Queue[Optional[ObjectLocation]],
        stats: CopyStats,
    ) -> None:
        # Worker consome fila até receber sentinela
        async with self._s3_client_factory() as worker_s3:
            copy_uc = CopyObjectUseCase(
                s3=worker_s3,
                source=self._source,
                target=self._target,
                chunk_size_bytes=self._chunk_size_bytes,
            )

            while True:
                item = await queue.get()
                if item is None:
                    queue.task_done()
                    logger.debug("Worker %d encerrado.", worker_id)
                    return

                try:
                    await self._copy_one(copy_uc, item, stats)
                finally:
                    queue.task_done()

    async def run(self) -> CopyStats:
        # Orquestra listagem e cópia em modelo produtor-consumidor com fila assíncrona
        stats = CopyStats()
        queue: asyncio.Queue[Optional[ObjectLocation]] = asyncio.Queue(
            maxsize=self._queue_max_size
        )

        producer_task = asyncio.create_task(self._producer(queue, stats))
        worker_tasks = [
            asyncio.create_task(self._worker_loop(idx + 1, queue, stats))
            for idx in range(self._max_concurrency)
        ]

        await producer_task
        if stats.total_objects == 0:
            logger.info("Nenhum objeto encontrado para o prefixo informado.")
            await asyncio.gather(*worker_tasks, return_exceptions=False)
            return stats

        await queue.join()
        await asyncio.gather(*worker_tasks, return_exceptions=False)
        return stats

