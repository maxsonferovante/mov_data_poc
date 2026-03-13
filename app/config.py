import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass
class AppConfig:
    # Configuração central da aplicação de cópia S3
    source_bucket: str
    source_prefix: str
    target_bucket: str
    target_prefix: str
    max_concurrency: int
    chunk_size_bytes: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        # Lê e valida as variáveis de ambiente obrigatórias
        source_bucket = os.getenv("SOURCE_BUCKET", "").strip()
        source_prefix = os.getenv("SOURCE_PREFIX", "").strip()
        target_bucket = os.getenv("TARGET_BUCKET", "").strip()
        target_prefix = os.getenv("TARGET_PREFIX", "").strip()

        if not source_bucket or not target_bucket:
            raise ValueError("SOURCE_BUCKET e TARGET_BUCKET são obrigatórios.")

        if not source_prefix:
            raise ValueError("SOURCE_PREFIX é obrigatório.")

        if not target_prefix:
            raise ValueError("TARGET_PREFIX é obrigatório.")

        # Normaliza prefixos para sempre terminar com '/'
        if not source_prefix.endswith("/"):
            source_prefix += "/"

        if not target_prefix.endswith("/"):
            target_prefix += "/"

        # Define concorrência padrão e garante valor mínimo aceitável
        max_concurrency = int(os.getenv("MAX_CONCURRENCY", "4"))
        if max_concurrency < 1:
            max_concurrency = 1

        # Define tamanho do chunk em MB e converte para bytes
        chunk_mb = int(os.getenv("CHUNK_SIZE_MB", "8"))
        if chunk_mb < 1:
            chunk_mb = 1
        chunk_size_bytes = chunk_mb * 1024 * 1024

        return cls(
            source_bucket=source_bucket,
            source_prefix=source_prefix,
            target_bucket=target_bucket,
            target_prefix=target_prefix,
            max_concurrency=max_concurrency,
            chunk_size_bytes=chunk_size_bytes,
        )

