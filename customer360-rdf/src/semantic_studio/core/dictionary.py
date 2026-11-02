"""業務字典：詞條正規化、載入（PG 既有＋新詞條）、寫回、匯入、RDF 化與類別建議。"""

import csv
import io
import json
import re

import yaml
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from .common import ID_PATTERN, PG_FIELDS, StudioError, expand

TERMS_HEADER = "# 業務字典詞條與本體類別的對應。由 Semantic Studio 維護，也可以手動編輯。\n"


def normalize(cfg, mapping_roles, raw, source, editable):
    term_id = str(raw.get("id", "")).strip()
    if not ID_PATTERN.match(term_id):
        raise StudioError(f"詞條 ID 只能用英數字、點、底線、連字號：{term_id!r}")
    mappings, seen = [], set()
    for item in raw.get("mappings") or []:
        uri, role = expand(cfg, item["class"]), item.get("role", "primary")
        if role not in mapping_roles:
            raise StudioError(f"不認得的對應角色：{role}")
        if (uri, role) not in seen:
            seen.add((uri, role))
            mappings.append({"class": uri, "role": role})
    return {"id": term_id, "name": str(raw.get("name", "")).strip(),
            "definition": str(raw.get("definition") or "").strip(),
            "source": str(raw.get("source") or source), "origin": "dictionary" if editable else "pg",
            "editable": editable, "mappings": mappings}


def load_terms(cfg, mapping_roles):
    path = cfg.path_of("dictionary_terms")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
    return [normalize(cfg, mapping_roles, t, "業務字典", True) for t in (data or {}).get("terms") or []]


def load_pg_terms(cfg, mapping_roles):
    """pg/ 的既有詞條（唯讀）：五種類別欄位統一轉成對應角色。"""
    terms = []
    for path in sorted(cfg.path_of("pg_models").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "ontology_version" not in data:
            continue
        items = list(data.get("concepts") or [])
        if isinstance(data.get("department"), dict):
            items.append(data["department"])
        for concept in items:
            if not isinstance(concept, dict) or "id" not in concept or "name" not in concept:
                continue
            mappings = []
            for field, role in PG_FIELDS.items():
                values = concept.get(field)
                for uri in ([values] if isinstance(values, str) else values or []):
                    if uri not in {m["class"] for m in mappings}:
                        mappings.append({"class": uri, "role": role})
            terms.append(normalize(cfg, mapping_roles, {"id": concept["id"], "name": concept["name"],
                                                        "definition": concept.get("definition"), "mappings": mappings},
                                   f"{path.parent.name}/{path.name}", False))
    return terms


def write_terms(cfg, terms):
    payload = {"terms": [{"id": t["id"], "name": t["name"], "definition": t["definition"], "source": t["source"],
                          "mappings": [{"class": cfg.curie(m["class"]), "role": m["role"]} for m in t["mappings"]]}
                         for t in sorted(terms, key=lambda t: t["id"])]}
    path = cfg.path_of("dictionary_terms")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TERMS_HEADER + yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=1000),
                    encoding="utf-8")


def parse_import(text, fmt, source):
    """CSV 欄位：id,name,definition,mappings；mappings 以 ; 分隔，角色用 @，例如 fh:FeeIncome@primary;bank:FundProduct@product。"""
    if fmt == "csv":
        rows = list(csv.DictReader(io.StringIO(text.strip())))
    elif fmt == "json":
        rows = json.loads(text)
        rows = rows.get("terms", rows) if isinstance(rows, dict) else rows
    else:
        raise StudioError("格式只支援 csv 或 json")
    raws = []
    for row in rows:
        raw = {"id": row.get("id"), "name": row.get("name"), "definition": row.get("definition"),
               "source": row.get("source") or source, "mappings": row.get("mappings") or []}
        if isinstance(raw["mappings"], str):
            raw["mappings"] = [dict(zip(("class", "role"), (item.split("@") + ["primary"])[:2]))
                               for item in raw["mappings"].split(";") if item.strip()]
        raws.append(raw)
    return raws


def to_graph(namespace, terms):
    graph = Graph()
    graph.bind("dict", namespace)
    for term in terms:
        node = URIRef(namespace + term["id"])
        graph.add((node, RDF.type, namespace.Term))
        if term["name"]:
            graph.add((node, namespace.name, Literal(term["name"], lang="zh-TW")))
        if term["definition"]:
            graph.add((node, namespace.definition, Literal(term["definition"], lang="zh-TW")))
        graph.add((node, namespace.source, Literal(term["source"])))
        for index, mapping in enumerate(term["mappings"]):
            link = URIRef(f"{namespace}{term['id']}__m{index}")
            graph.add((node, namespace.mapsTo, link))
            graph.add((link, RDF.type, namespace.Mapping))
            graph.add((link, namespace["class"], URIRef(mapping["class"])))
            graph.add((link, namespace.role, Literal(mapping["role"])))
    return graph


def suggest(cfg, onto, synonyms, name, definition="", limit=8):
    """依名稱（權重高）與定義（權重低）比對類別名稱，給出候選類別與建議角色。"""
    def clean(s):
        return re.sub(r"[\s（）()／/、，,。－-]+", "", s or "")

    def grams(s):
        s = clean(s)
        return {s[i:i + 2] for i in range(len(s) - 1)} or set(s)

    def with_synonyms(text):
        text = text or ""
        return text + "".join(target for word, target in synonyms.items() if word in text)

    name, definition = with_synonyms(name), with_synonyms(definition)
    name_grams, def_grams = grams(name), grams(definition)
    product = expand(cfg, "fh:FinancialProduct")
    scored = []
    for uri, c in onto.classes.items():
        label = (c["label"] or "").replace("指標", "").replace("商品", "")
        core, label_grams = clean(label), grams(label)
        score = 3.0 if core and core in clean(name) else 0.5 if core and core in clean(definition) else 0.0
        score += (len(label_grams & name_grams) + 0.4 * len(label_grams & def_grams)) / (len(label_grams) or 1)
        if score > 0.45:
            scored.append((score, uri))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [{"class": cfg.curie(uri), "label": onto.classes[uri]["label"],
             "role": "product" if onto.is_a(uri, product) else "primary", "score": round(score, 2)}
            for score, uri in scored[:limit]]
