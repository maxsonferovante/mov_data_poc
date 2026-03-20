from dataclasses import dataclass

from app.core.domain.interfaces import AsyncS3Port
from app.core.use_cases.copy_strategies import (
    LargeObjectCopyStrategy,
    SmallObjectCopyStrategy,
)


@dataclass(frozen=True)
class CopyStrategyFactory:
    # Factory que seleciona a strategy de cópia com base no tamanho do objeto.
    s3: AsyncS3Port
    small_threshold_bytes: int = 5 * 1024 * 1024

    def for_size(self, size_bytes: int):
        if size_bytes < self.small_threshold_bytes:
            return SmallObjectCopyStrategy(s3=self.s3)
        return LargeObjectCopyStrategy(s3=self.s3)

