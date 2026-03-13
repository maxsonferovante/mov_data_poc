import asyncio
import logging
import os
import sys

from app.config import AppConfig
from app.core.domain.models import BucketRef
from app.core.use_cases.copy_batch import CopyBatchUseCase
from app.infra.aws.async_s3_client import AiobotocoreS3Client
from app.infra.logging import setup_logging


async def main_async() -> int:
    # Configura logging global antes de qualquer operação
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        config = AppConfig.from_env()
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao carregar configuração: %s", exc)
        return 1

    logger.info(
        "Iniciando cópia: %s/%s -> %s/%s (concorrência=%d, chunk=%d bytes)",
        config.source_bucket,
        config.source_prefix,
        config.target_bucket,
        config.target_prefix,
        config.max_concurrency,
        config.chunk_size_bytes,
    )

    # Cria referências de buckets normalizadas
    source = BucketRef(bucket=config.source_bucket, prefix=config.source_prefix)
    target = BucketRef(bucket=config.target_bucket, prefix=config.target_prefix)

    # Descobre a região para o cliente S3 a partir do ambiente
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or None
    s3_client = AiobotocoreS3Client(region_name=region)

    use_case = CopyBatchUseCase(
        s3=s3_client,
        source=source,
        target=target,
        max_concurrency=config.max_concurrency,
        chunk_size_bytes=config.chunk_size_bytes,
    )

    # Chamada principal do caso de uso de cópia em lote
    stats = await use_case.run()

    logger.info(
        "Cópia concluída. Total=%d, sucesso=%d, erro=%d",
        stats.total_objects,
        stats.success_count,
        stats.error_count,
    )

    # Define código de saída com base no resultado
    return 0 if stats.error_count == 0 else 1


def main() -> None:
    # Ponto de entrada síncrono para facilitar execução pela task ECS
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

