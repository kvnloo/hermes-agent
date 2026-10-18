"""Credential-free projection for native model inventory consumers.

Endpoint URLs and discovery errors can embed login secrets. Preserve every provider
and model identity; omit private routes, arbitrary extras, account labels and raw errors.
"""
_SAFE_FIELDS = (
    'slug', 'name', 'models', 'total_models', 'is_current', 'is_user_defined', 'source',
    'authenticated', 'auth_type', 'aliases', 'unavailable_models', 'pricing', 'capabilities',
    'pricing_pending', 'free_tier', 'free_tier_pending', 'featured_models',
)


def safe_provider_rows(rows):
    return [{key: row[key] for key in _SAFE_FIELDS if key in row} for row in rows]
