from enum import Enum


class TransformType(str, Enum):
    """Transformation types for field mapping."""

    DIRECT = "direct"          # source_path -> target_field directly
    TEMPLATE = "template"      # String template with placeholders
    CONDITIONAL = "conditional"  # Multiple conditions -> different values
    EXPRESSION = "expression"  # Custom expression evaluation
    LOOKUP = "lookup"          # Lookup table mapping
