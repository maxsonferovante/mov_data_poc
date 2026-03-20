import asyncio
import json
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
        os.environ["SOURCE_BUCKET"] = "tech-floripa-certificates-dev-bucket"
        os.environ["SOURCE_PREFIX"] = "certificates/"
        os.environ["TARGET_BUCKET"] = "tech-floripa-certificates-dev-bucket"
        os.environ["TARGET_PREFIX"] = "copy/certificates/"
        config = AppConfig.from_env()
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao carregar configuração: %s", exc)
        return 1

    logger.info(
        "Iniciando cópia: %s/%s -> %s/%s (workers=%d, fila=%d, chunk=%d bytes)",
        config.source_bucket,
        config.source_prefix,
        config.target_bucket,
        config.target_prefix,
        config.worker_count,
        config.queue_max_size,
        config.chunk_size_bytes,
    )

    # Cria referências de buckets normalizadas
    source = BucketRef(bucket=config.source_bucket, prefix=config.source_prefix)
    target = BucketRef(bucket=config.target_bucket, prefix=config.target_prefix)

    # Descobre a região para o cliente S3 a partir do ambiente
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or None
    use_case = CopyBatchUseCase(
        s3_client_factory=lambda: AiobotocoreS3Client(region_name=region),
        source=source,
        target=target,
        max_concurrency=config.worker_count,
        queue_max_size=config.queue_max_size,
        progress_log_every=config.progress_log_every,
        chunk_size_bytes=config.chunk_size_bytes,
    )

    # Chamada principal do caso de uso de cópia em lote
    stats = await use_case.run()

    logger.info(
        "Cópia concluída. Total=%d, sucesso=%d, erro=%d, bytes_movimentados=%d",
        stats.total_objects,
        stats.success_count,
        stats.error_count,
        stats.total_bytes_moved,
    )
    # logger.info("Relatório detalhado: %s", json.dumps(stats.to_serializable()))

    # Define código de saída com base no resultado
    return 0 if stats.error_count == 0 else 1


def main() -> None:
    # Ponto de entrada síncrono para facilitar execução pela task ECS
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

