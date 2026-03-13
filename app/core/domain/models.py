from dataclasses import dataclass


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

