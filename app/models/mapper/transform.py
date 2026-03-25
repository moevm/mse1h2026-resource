from enum import Enum


class TransformType(str, Enum):
    DIRECT = "direct"
    TEMPLATE = "template"
    CONDITIONAL = "conditional"
    EXPRESSION = "expression"
    LOOKUP = "lookup"
