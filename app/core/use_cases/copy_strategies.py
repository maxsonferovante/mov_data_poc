from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol

from app.core.domain.interfaces import AsyncS3Port
from app.core.domain.models import CopyPlan


class CopyStrategy(Protocol):
    async def copy(self, plan: CopyPlan, chunk_size_bytes: int) -> None:
        ...


@dataclass(frozen=True)
class SmallObjectCopyStrategy:
    # Strategy para arquivos pequenos: usa put_object para evitar falhas de multipart mínimo.
    s3: AsyncS3Port

    async def copy(self, plan: CopyPlan, chunk_size_bytes: int) -> None:
        async def data_stream() -> AsyncIterator[bytes]:
            async for chunk in self.s3.stream_object(
                bucket=plan.source.bucket,
                key=plan.source.key,
                chunk_size=chunk_size_bytes,
            ):
                yield chunk

        await self.s3.put_object_stream(
            bucket=plan.target.bucket,
            key=plan.target.key,
            data_stream=data_stream(),
        )


@dataclass(frozen=True)
class LargeObjectCopyStrategy:
    # Strategy para arquivos grandes: usa multipart upload sequencial.
    s3: AsyncS3Port

    async def copy(self, plan: CopyPlan, chunk_size_bytes: int) -> None:
        async def data_stream() -> AsyncIterator[bytes]:
            async for chunk in self.s3.stream_object(
                bucket=plan.source.bucket,
                key=plan.source.key,
                chunk_size=chunk_size_bytes,
            ):
                yield chunk

        await self.s3.multipart_upload_stream(
            bucket=plan.target.bucket,
            key=plan.target.key,
            data_stream=data_stream(),
        )

