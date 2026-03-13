from typing import AsyncIterator

from app.core.domain.interfaces import AsyncS3Port
from app.core.domain.models import BucketRef, ObjectLocation


class ListObjectsToCopyUseCase:
    # Caso de uso responsável por listar os objetos que serão copiados

    def __init__(self, s3: AsyncS3Port, source: BucketRef) -> None:
        self._s3 = s3
        self._source = source

    async def execute(self) -> AsyncIterator[ObjectLocation]:
        # Propaga o iterador de objetos, mantendo o domínio desacoplado do cliente S3
        async for obj in self._s3.list_objects(
            bucket=self._source.bucket,
            prefix=self._source.prefix,
        ):
            yield obj

