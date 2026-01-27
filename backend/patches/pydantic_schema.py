"""
Patch 1: Pydantic SchemaError workaround

Pydantic 2.11+ has a bug where complex union types with TypeAlias fail validation.
The openai SDK's HttpxRequestFiles type triggers this during schema generation.
We patch it to Any before importing openai._models to avoid the error.

Error: SchemaError: 'cls' must be valid as the first argument to 'isinstance'
Related: https://github.com/pydantic/pydantic/issues/12704
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def apply_pydantic_schema_patch() -> bool:
    """Apply the Pydantic SchemaError workaround.
    
    Returns:
        True if patch was applied, False otherwise.
    """
    try:
        import openai._types
        openai._types.HttpxRequestFiles = Any  # type: ignore[attr-defined]
        logger.debug("Applied pydantic SchemaError workaround for openai._types.HttpxRequestFiles")
        return True
    except (ImportError, AttributeError) as e:
        logger.warning("Failed to apply pydantic workaround: %s", e)
        return False
