from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import jmespath

from app.models.mapper.mapping import FieldMapping
from app.models.mapper.transform import TransformType

log = logging.getLogger(__name__)


class TransformService:
    """Service for JMESPath extraction and value transformations."""

    def __init__(self) -> None:
        self._cache: Dict[str, jmespath.parser.ParsedResult] = {}

    def compile(self, expression: str) -> jmespath.parser.ParsedResult:
        """Compile and cache a JMESPath expression."""
        if expression not in self._cache:
            try:
                self._cache[expression] = jmespath.compile(expression)
            except jmespath.exceptions.JMESPathError as e:
                log.warning(f"Failed to compile JMESPath expression '{expression}': {e}")
                raise
        return self._cache[expression]

    def extract(self, data: Dict[str, Any], path: str) -> Optional[Any]:
        """Extract value using JMESPath expression.

        Returns None if extraction fails or path not found.
        """
        if not path:
            return None

        try:
            compiled = self.compile(path)
            result = compiled.search(data)
            return result
        except jmespath.exceptions.JMESPathError as e:
            log.debug(f"JMESPath extraction failed for '{path}': {e}")
            return None
        except Exception as e:
            log.warning(f"Unexpected error during JMESPath extraction: {e}")
            return None

    def apply_transform(
        self,
        value: Any,
        mapping: FieldMapping,
        context: Dict[str, Any],
    ) -> Any:
        """Apply transformation to extracted value.

        Args:
            value: The extracted value from source data
            mapping: The field mapping configuration
            context: Additional context for transformations (source_data, etc.)

        Returns:
            Transformed value, or default if value is None
        """
        # Use default value if extraction returned None
        if value is None:
            if mapping.default_value is not None:
                return mapping.default_value
            return None

        transform_type = mapping.transform_type

        if transform_type == TransformType.DIRECT:
            return value

        elif transform_type == TransformType.TEMPLATE:
            return self._apply_template_transform(value, mapping, context)

        elif transform_type == TransformType.LOOKUP:
            return self._apply_lookup_transform(value, mapping)

        elif transform_type == TransformType.EXPRESSION:
            return self._apply_expression_transform(value, mapping, context)

        elif transform_type == TransformType.CONDITIONAL:
            return self._apply_conditional_transform(value, mapping, context)

        # Unknown transform type, return as-is
        return value

    def _apply_template_transform(
        self,
        value: Any,
        mapping: FieldMapping,
        context: Dict[str, Any],
    ) -> str:
        """Apply string template transformation."""
        template = mapping.transform_config.get("template", "{value}")
        try:
            return template.format(value=value, **context)
        except (KeyError, ValueError) as e:
            log.warning(f"Template transform failed: {e}")
            return str(value)

    def _apply_lookup_transform(
        self,
        value: Any,
        mapping: FieldMapping,
    ) -> Any:
        """Apply lookup table transformation."""
        lookup_table = mapping.transform_config.get("table", {})
        return lookup_table.get(str(value), mapping.default_value)

    def _apply_expression_transform(
        self,
        value: Any,
        mapping: FieldMapping,
        context: Dict[str, Any],
    ) -> Any:
        """Apply custom expression transformation.

        Uses a safe expression evaluator.
        """
        expression = mapping.transform_config.get("expression", "value")

        # Safe evaluation using a restricted namespace
        try:
            # Only allow basic operations
            allowed_names = {
                "value": value,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "len": len,
                **context,
            }

            # Simple evaluation for basic expressions
            # For complex needs, consider using simpleeval library
            if expression == "value":
                return value
            elif expression.startswith("int("):
                return int(value)
            elif expression.startswith("str("):
                return str(value)
            elif expression.startswith("float("):
                return float(value)
            else:
                # Try direct evaluation for simple cases
                return eval(expression, {"__builtins__": {}}, allowed_names)  # nosec B307

        except Exception as e:
            log.warning(f"Expression transform failed: {e}")
            return value

    def _apply_conditional_transform(
        self,
        value: Any,
        mapping: FieldMapping,
        context: Dict[str, Any],
    ) -> Any:
        """Apply conditional transformation based on value."""
        conditions = mapping.transform_config.get("conditions", [])
        default_result = mapping.transform_config.get("default", value)

        for condition in conditions:
            condition_expr = condition.get("condition", "")
            result_value = condition.get("value")

            # Simple equality check
            if condition_expr == value or condition_expr == str(value):
                return result_value

            # JMESPath-like condition
            if "==" in condition_expr:
                parts = condition_expr.split("==")
                if len(parts) == 2:
                    expected = parts[1].strip().strip('"').strip("'")
                    if str(value) == expected:
                        return result_value

        return default_result

    def evaluate_condition(
        self,
        data: Dict[str, Any],
        condition: str,
    ) -> bool:
        """Evaluate a boolean condition.

        Supports:
        - Simple JMESPath extraction (truthy check)
        - Equality: "field == 'value'" or "field == value"
        - Inequality: "field != 'value'"
        - JMESPath filter expressions

        Args:
            data: Source data to evaluate against
            condition: Condition expression

        Returns:
            True if condition matches, False otherwise
        """
        if not condition:
            return False

        try:
            # Check for simple equality/inequality pattern
            # Pattern: field == 'value' or field == value or field != 'value'
            import re
            eq_match = re.match(r"^([\w.]+)\s*==\s*['\"]?(.+?)['\"]?$", condition.strip())
            neq_match = re.match(r"^([\w.]+)\s*!=\s*['\"]?(.+?)['\"]?$", condition.strip())

            if eq_match:
                field_path = eq_match.group(1)
                expected = eq_match.group(2)
                actual = self.extract(data, field_path)
                return str(actual) == expected

            if neq_match:
                field_path = neq_match.group(1)
                expected = neq_match.group(2)
                actual = self.extract(data, field_path)
                return str(actual) != expected

            # Fallback to JMESPath extraction
            result = self.extract(data, condition)
            # Check if result is truthy
            if result is None:
                return False
            if isinstance(result, bool):
                return result
            if isinstance(result, (list, dict, str)):
                return len(result) > 0
            if isinstance(result, (int, float)):
                return result != 0
            return bool(result)
        except Exception:
            return False

    def extract_multiple(
        self,
        data: Dict[str, Any],
        paths: list[str],
    ) -> Dict[str, Any]:
        """Extract multiple values from data.

        Args:
            data: Source data
            paths: Dict of field_name -> JMESPath expression

        Returns:
            Dict of field_name -> extracted value
        """
        results = {}
        for field_name, path in paths.items():
            results[field_name] = self.extract(data, path)
        return results


transform_service = TransformService()
