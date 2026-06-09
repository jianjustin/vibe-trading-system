"""File-based artifact store with JSON persistence and Markdown rendering."""

from pathlib import Path

from pydantic import BaseModel


class ArtifactStore:
    """Save, load, list, and render typed Pydantic artifacts as JSON files."""

    def __init__(self, base_dir: str | Path = "artifacts"):
        self.base_dir = Path(base_dir)

    def save(self, artifact: BaseModel, artifact_type: str, artifact_id: str) -> Path:
        directory = self.base_dir / artifact_type
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{artifact_id}.json"
        path.write_text(artifact.model_dump_json(indent=2))
        return path

    def load(self, artifact_type: str, artifact_id: str, model_class: type[BaseModel]) -> BaseModel:
        path = self.base_dir / artifact_type / f"{artifact_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        return model_class.model_validate_json(path.read_text())

    def list_ids(self, artifact_type: str) -> list[str]:
        directory = self.base_dir / artifact_type
        if not directory.exists():
            return []
        return sorted(p.stem for p in directory.glob("*.json"))

    def latest(self, artifact_type: str, model_class: type[BaseModel]) -> BaseModel | None:
        ids = self.list_ids(artifact_type)
        if not ids:
            return None
        return self.load(artifact_type, ids[-1], model_class)

    def to_markdown(self, artifact: BaseModel) -> str:
        lines = []
        for field_name, value in artifact.model_dump().items():
            label = field_name.replace("_", " ").title()
            if isinstance(value, list):
                lines.append(f"**{label}:**")
                for item in value:
                    lines.append(f"- {item}")
            else:
                lines.append(f"**{label}:** {value}")
        return "\n".join(lines)
