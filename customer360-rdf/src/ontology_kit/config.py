"""Load config.yaml: the single source of paths, version, modules and release rules."""

from dataclasses import dataclass
import fnmatch
import os
from pathlib import Path
import re

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/ontology_kit/config.py → 專案根目錄
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
MATURITY_ORDER = ("release", "provisional", "informative")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Module:
    file: str
    iri: str
    layer: str
    topic: str
    maturity: str
    path: Path


@dataclass(frozen=True)
class Layer:
    key: str
    prefix: str
    namespace: str
    governance_level: str
    subsidiary: str | None
    title: str


def default_config_path():
    """C360_CONFIG → 目前資料夾的 config.yaml → 專案根目錄的 config.yaml。"""
    if os.environ.get("C360_CONFIG"):
        return Path(os.environ["C360_CONFIG"])
    if (Path.cwd() / "config.yaml").is_file():
        return Path.cwd() / "config.yaml"
    return PROJECT_ROOT / "config.yaml"


class Config:
    def __init__(self, path=None):
        self.path = Path(path or default_config_path()).resolve()
        data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.data = data
        self.base = self.path.parent
        project = data["project"]
        self.label = project["label"]
        self.ontology_uri = project["ontology_uri"]
        self.version = str(project["version"])
        self.date = str(project["date"])
        self.status = project["status"]
        if not SEMVER.match(self.version):
            raise ConfigError(f"project.version 必須是 X.Y.Z：{self.version}")

        self.paths = {}
        for key, value in data["paths"].items():
            override = os.environ.get("C360_PATH_" + key.upper())
            value = override if override else value
            self.paths[key] = None if value in (None, "", "none") else (self.base / value).resolve()
        self.root = self.paths["root"]

        self.layers = {key: Layer(key, item["prefix"], item["namespace"], item["governance_level"],
                                  item.get("subsidiary"), item.get("title", key))
                       for key, item in data["layers"].items()}
        self.modules = []
        for item in data["modules"]:
            if item["layer"] not in self.layers:
                raise ConfigError(f"模組 {item['file']} 的 layer 未定義：{item['layer']}")
            if item["maturity"] not in MATURITY_ORDER:
                raise ConfigError(f"模組 {item['file']} 的 maturity 必須是 {MATURITY_ORDER}")
            self.modules.append(Module(item["file"], item["iri"], item["layer"], item.get("topic", ""),
                                       item["maturity"], (self.root / item["file"]).resolve()))
        if len({m.file for m in self.modules}) != len(self.modules):
            raise ConfigError("modules 檔名重複")
        outputs = {self.paths.get("build_turtle"), self.paths.get("build_xml")}
        if outputs & {m.path for m in self.modules}:
            raise ConfigError("build 輸出不可覆寫來源模組")

        self.annotations = data["annotations"]
        self.maturity_levels = data["maturity_levels"]
        self.components = data["components"]
        self.versioning = data["versioning"]
        self.release = data["release"]
        self.reasoner = data["reasoner"]
        self.context = data["context"]
        self.evidence = data.get("evidence", {})
        for level in self.release["include_maturity"]:
            if level not in MATURITY_ORDER:
                raise ConfigError(f"release.include_maturity 不認得：{level}")

    def path_of(self, key):
        return self.paths.get(key)

    def release_modules(self):
        return [m for m in self.modules if m.maturity in self.release["include_maturity"]]

    def layer_of(self, uri):
        for layer in self.layers.values():
            if str(uri).startswith(layer.namespace):
                return layer
        return None

    def curie(self, uri):
        layer = self.layer_of(uri)
        if layer:
            return f"{layer.prefix}:{str(uri)[len(layer.namespace):]}"
        for prefix, namespace in (("xsd", "http://www.w3.org/2001/XMLSchema#"),
                                  ("owl", "http://www.w3.org/2002/07/owl#")):
            if str(uri).startswith(namespace):
                return f"{prefix}:{str(uri)[len(namespace):]}"
        return str(uri)

    def version_iri(self, iri, version=None):
        return f"{iri}/{version or self.version}"

    def release_dir(self, version=None):
        return self.paths["release_dir"] / (version or self.version)

    def external(self, recorded):
        """把 PG 證據檔記錄的原工作區路徑（含 evidence.legacy_folder）對應到本儲存庫的位置。"""
        folder = self.evidence.get("legacy_folder")
        text = str(recorded).replace("\\", "/")
        if folder and folder + "/" in text:
            return self.path_of("evidence_root") / text.split(folder + "/", 1)[1]
        return (self.root / text).resolve()

    def literal_files(self):
        found = []
        for pattern in self.versioning.get("literal_files", []):
            found += sorted(p for p in self.root.glob(pattern) if p.is_file())
        return list(dict.fromkeys(found))

    def scan_files(self, suffixes=(".py", ".json", ".ttl", ".xml", ".yaml")):
        exclude = set(self.versioning.get("scan_exclude", []))
        for path in sorted(self.root.rglob("*")):
            relative = path.relative_to(self.root)
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if any(part in exclude or fnmatch.fnmatch(part, "*.egg-info") for part in relative.parts[:-1]):
                continue
            yield path
