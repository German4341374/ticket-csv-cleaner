"""YAML rules validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ticket_csv_cleaner.config import CleanerConfig, default_config, load_config
from ticket_csv_cleaner.errors import ConfigurationError


def test_default_config_uses_masking_and_core_requirements() -> None:
    config = default_config()
    assert config.mask_personal_data is True
    assert "ticket_id" in config.required_fields
    assert config.status_mapping["pending"] == "In Progress"


def test_loads_valid_yaml_mapping(tmp_path: Path) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(
        "column_mapping:\n  Number: ticket_id\n"
        "probable_duplicate_threshold: 0.95\n"
        "mask_personal_data: false\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.column_mapping == {"Number": "ticket_id"}
    assert config.probable_duplicate_threshold == 0.95
    assert config.mask_personal_data is False


def test_empty_yaml_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    assert load_config(path) == CleanerConfig()


def test_rejects_unknown_configuration_key(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("unexpected: true\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        load_config(path)


def test_rejects_unknown_column_target() -> None:
    with pytest.raises(ValueError, match="unknown canonical columns"):
        CleanerConfig(column_mapping={"ID": "unknown"})


def test_rejects_unknown_required_field() -> None:
    with pytest.raises(ValueError, match="unknown required fields"):
        CleanerConfig(required_fields=("ticket_id", "unknown"))


def test_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="root must be"):
        load_config(path)


def test_missing_rules_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="Unable to read"):
        load_config(tmp_path / "missing.yaml")
