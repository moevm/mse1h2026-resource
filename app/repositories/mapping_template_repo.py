from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from app.models.mapper.mapping import MappingConfig
from app.models.mapper.template import MappingTemplateSummary


BUNDLED_TEMPLATES_DIR = Path(__file__).parent.parent / "mapping_templates"
UPLOADED_TEMPLATES_DIR = Path(
    os.environ.get("MAPPING_TEMPLATES_UPLOAD_DIR", "/tmp/mapping_templates")
)


class MappingTemplateRepository:
    def __init__(self) -> None:
        self._templates: dict[str, MappingConfig] = {}
        self._summaries: dict[str, MappingTemplateSummary] = {}
        self._loaded = False

    def _load_templates(self) -> None:
        if self._loaded:
            return

        for templates_dir in (BUNDLED_TEMPLATES_DIR, UPLOADED_TEMPLATES_DIR):
            if not templates_dir.exists():
                continue

            for template_file in sorted(templates_dir.rglob("*.json")):
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

    def reload(self) -> int:
        """Force reload templates from disk. Returns count of loaded templates."""
        self._templates.clear()
        self._summaries.clear()
        self._loaded = False
        self._load_templates()
        return len(self._templates)

    def save_uploaded_template(self, filename: str, content: bytes) -> str:
        """Save an uploaded mapping template JSON without overwriting existing files.
        Returns the path where the file was saved."""
        UPLOADED_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

        safe_name = Path(filename).name
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix or ".json"
        dest = UPLOADED_TEMPLATES_DIR / safe_name

        # Avoid overwriting: append -1, -2, etc.
        counter = 1
        while dest.exists():
            dest = UPLOADED_TEMPLATES_DIR / f"{stem}-{counter}{suffix}"
            counter += 1

        dest.write_bytes(content)
        return str(dest)


mapping_template_repo = MappingTemplateRepository()
