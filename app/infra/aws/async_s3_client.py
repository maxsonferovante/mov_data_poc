from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiobotocore.session  # dependência externa aprovada pelo usuário

from app.core.domain.interfaces import AsyncS3Port
from app.core.domain.models import ObjectLocation


class AiobotocoreS3Client(AsyncS3Port):
    # Implementação concreta da porta AsyncS3Port usando aiobotocore

    def __init__(
        self,
        region_name: str | None = None,
    ) -> None:
        self._session = aiobotocore.session.get_session()
        self._region_name = region_name
        self._shared_client_cm = None
        self._shared_client = None

    async def __aenter__(self) -> "AiobotocoreS3Client":
        # Reusa um único cliente S3 durante o ciclo da aplicação para reduzir overhead de conexão.
        self._shared_client_cm = self._session.create_client(
            "s3", region_name=self._region_name
        )
        self._shared_client = await self._shared_client_cm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._shared_client_cm is not None:
            await self._shared_client_cm.__aexit__(exc_type, exc, tb)
        self._shared_client_cm = None
        self._shared_client = None

    @asynccontextmanager
    async def _client_scope(self):
        # Usa cliente compartilhado quando disponível; fallback para cliente temporário.
        if self._shared_client is not None:
            yield self._shared_client
            return

        async with self._session.create_client("s3", region_name=self._region_name) as client:
            yield client

    async def list_objects(
        self,
        bucket: str,
        prefix: str,
    ) -> AsyncIterator[ObjectLocation]:
        # Lista objetos de forma paginada usando list_objects_v2
        async with self._client_scope() as client:
            continuation_token: str | None = None

            while True:
                params: dict[str, object] = {
                    "Bucket": bucket,
                    "Prefix": prefix,
                    "MaxKeys": 1000,
                }
                if continuation_token:
                    params["ContinuationToken"] = continuation_token

                response = await client.list_objects_v2(**params)

                for item in response.get("Contents", []):
                    key = item["Key"]
                    size_bytes = int(item.get("Size", 0))
                    yield ObjectLocation(bucket=bucket, key=key, size_bytes=size_bytes)

                if not response.get("IsTruncated"):
                    break

                continuation_token = response.get("NextContinuationToken")

    async def stream_object(
        self,
        bucket: str,
        key: str,
        chunk_size: int,
    ) -> AsyncIterator[bytes]:
        # Faz streaming do corpo do objeto em chunks de tamanho fixo
        async with self._client_scope() as client:
            response = await client.get_object(Bucket=bucket, Key=key)
            body = response["Body"]

            try:
                while True:
                    chunk = await body.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            finally:
                # Em alguns ambientes, close() é síncrono e não pode ser aguardado
                close = getattr(body, "close", None)
                if callable(close):
                    result = close()
                    # Se close retornar um awaitable, aguarda; senão ignora
                    if hasattr(result, "__await__"):
                        await result

    async def multipart_upload_stream(
        self,
        bucket: str,
        key: str,
        data_stream: AsyncIterator[bytes],
        content_type: str | None = None,
    ) -> None:
        # Envia um stream de bytes para o S3 utilizando multipart upload sequencial.
        async with self._client_scope() as client:
            extra_args: dict[str, object] = {}
            if content_type:
                extra_args["ContentType"] = content_type

            create_resp = await client.create_multipart_upload(
                Bucket=bucket,
                Key=key,
                **extra_args,
            )
            upload_id = create_resp["UploadId"]
            parts: list[dict[str, object]] = []
            part_number = 1

            try:
                async for chunk in data_stream:
                    if not chunk:
                        continue

                    part_resp = await client.upload_part(
                        Bucket=bucket,
                        Key=key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk,
                    )
                    parts.append(
                        {
                            "ETag": part_resp["ETag"],
                            "PartNumber": part_number,
                        }
                    )
                    part_number += 1

                if not parts:
                    await client.abort_multipart_upload(
                        Bucket=bucket,
                        Key=key,
                        UploadId=upload_id,
                    )
                    return

                await client.complete_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
            except Exception:
                await client.abort_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id,
                )
                raise

    async def put_object_stream(
        self,
        bucket: str,
        key: str,
        data_stream: AsyncIterator[bytes],
        content_type: str | None = None,
    ) -> None:
        # Envia stream com put_object consolidando o conteúdo em memória (uso para arquivos pequenos).
        async with self._client_scope() as client:
            body_chunks: list[bytes] = []
            async for chunk in data_stream:
                if chunk:
                    body_chunks.append(chunk)

            if not body_chunks:
                return

            extra_args: dict[str, object] = {}
            if content_type:
                extra_args["ContentType"] = content_type

            await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=b"".join(body_chunks),
                **extra_args,
            )

