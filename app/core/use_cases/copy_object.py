from typing import AsyncIterator

from app.core.domain.interfaces import AsyncS3Port
from app.core.domain.models import BucketRef, CopyPlan, ObjectLocation
from app.core.use_cases.copy_strategy_factory import CopyStrategyFactory


def build_target_key(source_prefix: str, target_prefix: str, key: str) -> str:
    # Calcula a chave de destino preservando o path relativo
    if key.startswith(source_prefix):
        relative = key[len(source_prefix) :]
    else:
        relative = key
    return f"{target_prefix}{relative}"


class CopyObjectUseCase:
    # Caso de uso para copiar um único objeto via streaming + multipart

    def __init__(
        self,
        s3: AsyncS3Port,
        source: BucketRef,
        target: BucketRef,
        chunk_size_bytes: int,
        strategy_factory: CopyStrategyFactory | None = None,
    ) -> None:
        self._s3 = s3
        self._source = source
        self._target = target
        self._chunk_size_bytes = chunk_size_bytes
        self._strategy_factory = strategy_factory or CopyStrategyFactory(s3=self._s3)

    def build_plan(self, obj: ObjectLocation) -> CopyPlan:
        # Cria o plano de cópia a partir do objeto de origem
        target_key = build_target_key(
            source_prefix=self._source.prefix,
            target_prefix=self._target.prefix,
            key=obj.key,
        )
        return CopyPlan(
            source=obj,
            target=ObjectLocation(bucket=self._target.bucket, key=target_key),
        )

    async def copy_one(self, obj: ObjectLocation) -> None:
        # Executa a cópia de um objeto usando Strategy + Factory por tamanho
        plan = self.build_plan(obj)
        strategy = self._strategy_factory.for_size(obj.size_bytes)
        await strategy.copy(plan=plan, chunk_size_bytes=self._chunk_size_bytes)

