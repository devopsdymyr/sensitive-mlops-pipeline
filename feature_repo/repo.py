"""Feast feature definitions for Iris (batch file source)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32
from feast.value_type import ValueType

_ROOT = Path(__file__).resolve().parents[1]
_FEATURE_TABLE = _ROOT / "data" / "processed" / "iris_features.parquet"

iris_entity = Entity(name="iris", join_keys=["iris_id"], value_type=ValueType.INT64)

iris_batch_source = FileSource(
    name="iris_batch_source",
    path=str(_FEATURE_TABLE.resolve()),
    timestamp_field="event_timestamp",
)

iris_feature_view = FeatureView(
    name="iris_features",
    entities=[iris_entity],
    ttl=timedelta(days=3650),
    schema=[
        Field(name="sepal_length", dtype=Float32),
        Field(name="sepal_width", dtype=Float32),
        Field(name="petal_length", dtype=Float32),
        Field(name="petal_width", dtype=Float32),
    ],
    source=iris_batch_source,
)
