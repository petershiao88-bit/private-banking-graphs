"""PG 測試共用路徑：一律由 config.yaml 推導，不在個別測試寫死。"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ontology_kit.config import Config  # noqa: E402

CONFIG = Config(ROOT / "config.yaml")
PG_DIR = CONFIG.path_of("pg_models")
ARCHIVE = CONFIG.path_of("archive")
MERGED_TTL = CONFIG.path_of("build_turtle")
MERGED_OWL = CONFIG.path_of("build_xml")
SOURCE_FILES = [m.path for m in CONFIG.modules]
CURRENT_VERSION = CONFIG.version


def external(relative):
    """快照 source-readonly-sha256.json 裡的相對路徑（../../私銀智能問答/…）→ 本儲存庫位置。"""
    return CONFIG.external(relative)


def evidence_file(recorded):
    """PG 證據記錄的檔案路徑（Ontology/私銀智能問答/…）→ 本儲存庫位置。"""
    return CONFIG.external(recorded)
