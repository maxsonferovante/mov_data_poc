import asyncio
import logging
from typing import AsyncIterator, Callable, Awaitable

from app.core.domain.interfaces import AsyncS3Port
from app.core.domain.models import BucketRef, CopyStats, ObjectLocation
from app.core.use_cases.copy_object import CopyObjectUseCase
from app.core.use_cases.list_objects import ListObjectsToCopyUseCase


logger = logging.getLogger(__name__)


class CopyBatchUseCase:
    # Caso de uso que coordena a cópia em lote com concorrência controlada

    def __init__(
        self,
        s3: AsyncS3Port,
        source: BucketRef,
        target: BucketRef,
        max_concurrency: int,
        chunk_size_bytes: int,
        retry_attempts: int = 3,
        retry_backoff_base: float = 0.5,
    ) -> None:
        self._s3 = s3
        self._source = source
        self._target = target
        self._max_concurrency = max_concurrency
        self._chunk_size_bytes = chunk_size_bytes
        self._retry_attempts = retry_attempts
        self._retry_backoff_base = retry_backoff_base

    async def _retry(
        self,
        func: Callable[[], Awaitable[None]],
        description: str,
    ) -> None:
        # Implementa retries simples com backoff exponencial
        attempt = 0
        while True:
            try:
                await func()
                return
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                if attempt >= self._retry_attempts:
                    logger.error(
                        "Falha definitiva ao %s depois de %d tentativas: %s",
                        description,
                        attempt,
                        exc,
                    )
                    raise
                delay = self._retry_backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "Erro ao %s, tentativa %d/%d, aguardando %.2fs: %s",
                    description,
                    attempt,
                    self._retry_attempts,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

    async def _worker(
        self,
        semaphore: asyncio.Semaphore,
        obj: ObjectLocation,
        stats: CopyStats,
    ) -> None:
        # Worker responsável por copiar um único objeto com retry e logs de início/fim
        copy_uc = CopyObjectUseCase(
            s3=self._s3,
            source=self._source,
            target=self._target,
            chunk_size_bytes=self._chunk_size_bytes,
        )

        async with semaphore:
            logger.info("Iniciando cópia do objeto %s/%s", obj.bucket, obj.key)
            try:
                await self._retry(
                    func=lambda: copy_uc.copy_one(obj),
                    description=f"copiar objeto {obj.bucket}/{obj.key}",
                )
            except Exception:
                stats.error_count += 1
                logger.error("Falha ao copiar objeto %s/%s", obj.bucket, obj.key)
            else:
                stats.success_count += 1
                logger.info("Cópia concluída do objeto %s/%s", obj.bucket, obj.key)

    async def run(self) -> CopyStats:
        # Orquestra a listagem e a cópia concorrente dos objetos
        list_uc = ListObjectsToCopyUseCase(self._s3, self._source)
        stats = CopyStats()
        semaphore = asyncio.Semaphore(self._max_concurrency)
        tasks: list[asyncio.Task[None]] = []

        async for obj in list_uc.execute():
            stats.total_objects += 1
            task = asyncio.create_task(self._worker(semaphore, obj, stats))
            tasks.append(task)

        if not tasks:
            logger.info("Nenhum objeto encontrado para o prefixo informado.")
            return stats

        await asyncio.gather(*tasks, return_exceptions=False)
        return stats

