from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from app.models.mapper.mapping import MappingConfig
from app.models.mapper.template import MappingTemplateSummary


TEMPLATES_DIR = Path(__file__).parent.parent / "mapping_templates"


class MappingTemplateRepository:
    def __init__(self) -> None:
        self._templates: dict[str, MappingConfig] = {}
        self._summaries: dict[str, MappingTemplateSummary] = {}
        self._loaded = False

    def _load_templates(self) -> None:
        if self._loaded:
            return

        if not TEMPLATES_DIR.exists():
            self._loaded = True
            return

        for template_file in sorted(TEMPLATES_DIR.rglob("*.json")):
            with template_file.open() as fh:
                raw = json.load(fh)

            template = MappingConfig(**raw)
            summary = MappingTemplateSummary(
                id=template.id,
                name=template.name,
                description=template.description,
                source_type=template.source_type,
                field_mappings_count=len(template.field_mappings),
                conditional_rules_count=len(template.conditional_rules),
                auto_edge_rules_count=len(template.auto_edge_rules),
            )

            self._templates[template.id] = template
            self._summaries[template.id] = summary

        self._loaded = True

    def list(self) -> List[MappingTemplateSummary]:
        self._load_templates()
        return list(self._summaries.values())

    def get(self, template_id: str) -> Optional[MappingConfig]:
        self._load_templates()
        return self._templates.get(template_id)

    def get_summary(self, template_id: str) -> Optional[MappingTemplateSummary]:
        self._load_templates()
        return self._summaries.get(template_id)


mapping_template_repo = MappingTemplateRepository()
