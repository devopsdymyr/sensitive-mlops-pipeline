"""Feast feature definitions for sensitive-text risk scoring (batch file source)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32
from feast.value_type import ValueType

_ROOT = Path(__file__).resolve().parents[1]
_FEATURE_TABLE = _ROOT / "data" / "processed" / "sensitive_features.parquet"

record_entity = Entity(name="record", join_keys=["record_id"], value_type=ValueType.INT64)

sensitive_batch_source = FileSource(
    name="sensitive_batch_source",
    path=str(_FEATURE_TABLE.resolve()),
    timestamp_field="event_timestamp",
)

sensitive_feature_view = FeatureView(
    name="sensitive_risk_features",
    entities=[record_entity],
    ttl=timedelta(days=3650),
    schema=[
        Field(name="pan_hits", dtype=Float32),
        Field(name="aadhaar_hits", dtype=Float32),
        Field(name="email_hits", dtype=Float32),
        Field(name="phone_hits", dtype=Float32),
        Field(name="account_hits", dtype=Float32),
        Field(name="keyword_hits", dtype=Float32),
        Field(name="text_length", dtype=Float32),
    ],
    source=sensitive_batch_source,
)
