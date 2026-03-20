from __future__ import annotations

from typing import AsyncIterator, Protocol

from app.core.domain.models import ObjectLocation


class AsyncS3Port(Protocol):
    # Porta assíncrona para operações de leitura/escrita no S3

    async def list_objects(
        self,
        bucket: str,
        prefix: str,
    ) -> AsyncIterator[ObjectLocation]:
        # Lista objetos de forma paginada a partir de um prefixo
        ...

    async def stream_object(
        self,
        bucket: str,
        key: str,
        chunk_size: int,
    ) -> AsyncIterator[bytes]:
        # Faz streaming de um objeto em chunks de tamanho fixo
        ...

    async def multipart_upload_stream(
        self,
        bucket: str,
        key: str,
        data_stream: AsyncIterator[bytes],
        content_type: str | None = None,
    ) -> None:
        # Envia um stream de bytes para o S3 usando multipart upload
        ...

    async def put_object_stream(
        self,
        bucket: str,
        key: str,
        data_stream: AsyncIterator[bytes],
        content_type: str | None = None,
    ) -> None:
        # Envia um stream de bytes para o S3 com put_object
        ...

