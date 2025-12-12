from feast import Field, FeatureView
from feast.types import Float32, Int64, Bool, String
from entities import user
from data_sources import (
    subs_profile_source,
    usage_agg_30d_source,
    payments_agg_90d_source,
    support_agg_90d_source,
)

# TODO: FeatureView pour le profil d'abonnement
subs_profile_fv = FeatureView(
    name="subs_profile_fv",
    entities=[user],
    ttl=None,
    schema=[
        Field(name="months_active", dtype=Int64),
        Field(name="monthly_fee", dtype=Float32),
        Field(name="paperless_billing", dtype=Bool),
        Field(name="plan_stream_tv", dtype=Bool),
        Field(name="plan_stream_movies", dtype=Bool),
        Field(name="net_service", dtype=String),
    ],
    source=subs_profile_source,
    online=True,
    tags={"owner": "mlops-course"},
)

# TODO: FeatureView pour l'usage 30j
usage_agg_30d_fv = FeatureView(
    name="usage_agg_30d_fv",
    entities=[user],
    ttl=None,
    schema=[
        Field(name="watch_hours_30d", dtype=Float32),
        Field(name="avg_session_mins_7d", dtype=Float32),
        Field(name="unique_devices_30d", dtype=Int64),
        Field(name="skips_7d", dtype=Int64),
        Field(name="rebuffer_events_7d", dtype=Int64),
    ],
    source=usage_agg_30d_source,
    online=True,
    tags={"owner": "mlops-course"},
)

# TODO: FeatureView pour les paiements 90j
payments_agg_90d_fv = FeatureView(
    name="payments_agg_90d_fv",
    entities=[user],
    ttl=None,
    schema=[
        Field(name="failed_payments_90d", dtype=Int64),
    ],
    source=payments_agg_90d_source,
    online=True,
    tags={"owner": "mlops-course"},
)

# TODO: FeatureView pour le support 90j
support_agg_90d_fv = FeatureView(
    name="support_agg_90d_fv",
    entities=[user],
    ttl=None,
    schema=[
        Field(name="support_tickets_90d", dtype=Int64),
        Field(name="ticket_avg_resolution_hrs_90d", dtype=Float32),
    ],
    source=support_agg_90d_source,
    online=True,
    tags={"owner": "mlops-course"},
)