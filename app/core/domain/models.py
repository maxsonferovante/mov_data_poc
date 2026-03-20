from dataclasses import dataclass, field


@dataclass(frozen=True)
class BucketRef:
    # Representa um bucket S3 e um prefixo normalizado
    bucket: str
    prefix: str


@dataclass(frozen=True)
class ObjectLocation:
    # Localização completa de um objeto em um bucket S3
    bucket: str
    key: str
    size_bytes: int = 0


@dataclass(frozen=True)
class CopyPlan:
    # Plano de cópia entre origem e destino
    source: ObjectLocation
    target: ObjectLocation


@dataclass
class CopyStats:
    # Estatísticas consolidadas de uma execução em lote
    total_objects: int = 0
    success_count: int = 0
    error_count: int = 0
    total_bytes_moved: int = 0
    success_items: list[dict[str, object]] = field(default_factory=list)
    failed_items: list[dict[str, object]] = field(default_factory=list)

    def to_serializable(self) -> dict[str, object]:
        # Estrutura pronta para serialização e envio para serviços externos.
        return {
            "total_files_processed": self.total_objects,
            "total_success": self.success_count,
            "total_failed": self.error_count,
            "total_bytes_moved": self.total_bytes_moved,
            "success_items": self.success_items,
            "failed_items": self.failed_items,
        }

