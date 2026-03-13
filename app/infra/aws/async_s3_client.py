from __future__ import annotations

from typing import AsyncIterator

import aiobotocore.session  # dependência externa aprovada pelo usuário

from app.core.domain.interfaces import AsyncS3Port
from app.core.domain.models import ObjectLocation


class AiobotocoreS3Client(AsyncS3Port):
    # Implementação concreta da porta AsyncS3Port usando aiobotocore

    def __init__(self, region_name: str | None = None) -> None:
        self._session = aiobotocore.session.get_session()
        self._region_name = region_name

    async def list_objects(
        self,
        bucket: str,
        prefix: str,
    ) -> AsyncIterator[ObjectLocation]:
        # Lista objetos de forma paginada usando list_objects_v2
        async with self._session.create_client("s3", region_name=self._region_name) as client:
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
                    yield ObjectLocation(bucket=bucket, key=key)

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
        async with self._session.create_client("s3", region_name=self._region_name) as client:
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
        # Envia um stream de bytes para o S3 utilizando multipart upload
        # Objetos pequenos são enviados em um único put_object para evitar EntityTooSmall.
        MIN_PART_SIZE = 5 * 1024 * 1024  # 5MB, limite mínimo do S3 para partes (exceto a última)

        async with self._session.create_client("s3", region_name=self._region_name) as client:
            extra_args: dict[str, object] = {}
            if content_type:
                extra_args["ContentType"] = content_type

            # Lê o primeiro chunk para decidir entre put simples e multipart
            try:
                first_chunk = await anext(data_stream)  # type: ignore[arg-type]
            except StopAsyncIteration:
                # Stream vazio, nada a enviar
                return

            if not first_chunk:
                return

            # Caso de objeto pequeno: faz put_object em uma única chamada
            if len(first_chunk) < MIN_PART_SIZE:
                chunks: list[bytes] = [first_chunk]
                async for chunk in data_stream:
                    if chunk:
                        chunks.append(chunk)

                body = b"".join(chunks)
                await client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=body,
                    **extra_args,
                )
                return

            # Caso de objeto grande: segue com multipart upload
            create_resp = await client.create_multipart_upload(
                Bucket=bucket,
                Key=key,
                **extra_args,
            )
            upload_id = create_resp["UploadId"]
            parts: list[dict[str, object]] = []
            part_number = 1

            try:
                # Envia a primeira parte já lida
                part_resp = await client.upload_part(
                    Bucket=bucket,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=first_chunk,
                )
                parts.append(
                    {
                        "ETag": part_resp["ETag"],
                        "PartNumber": part_number,
                    }
                )
                part_number += 1

                # Envia as demais partes do stream
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

