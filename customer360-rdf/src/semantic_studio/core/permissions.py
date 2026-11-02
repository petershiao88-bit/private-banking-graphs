"""類別權限：規則沿 rdfs:subClassOf（含 OWL 推理）往子類別繼承；詞條由對應的類別組合推出權限。

- 規則只有一個類別：套用到該類別與所有子類別。
- 規則有多個類別（組合規則）：只套用到「對應的類別（含上層）同時涵蓋這些類別」的詞條。
- 同一角色只要命中任何 deny 就拒絕（取最嚴格）；都沒命中時依 default_effect。
"""

import yaml

from .common import EFFECTS, ID_PATTERN, StudioError, expand

POLICY_HEADER = ("# 類別權限。規則的 classes 只有一個類別時，套用到該類別與所有子類別；\n"
                 "# 有多個類別時是「組合規則」，只套用到同時涵蓋這些類別（含上層）的字典詞條。\n"
                 "# 同一角色有任何 deny 命中就拒絕（取最嚴格）；都沒命中時依 default_effect。\n")


def normalize(cfg, classes, data):
    default = data.get("default_effect", "allow")
    if default not in EFFECTS:
        raise StudioError("default_effect 只能是 allow 或 deny")
    roles = []
    for role in data.get("roles") or []:
        if not ID_PATTERN.match(str(role.get("id", ""))):
            raise StudioError(f"角色 ID 不合法：{role.get('id')!r}")
        roles.append({"id": role["id"], "label": str(role.get("label") or role["id"])})
    role_ids = {r["id"] for r in roles}
    if len(role_ids) != len(roles):
        raise StudioError("角色 ID 重複")
    rules, rule_ids = [], set()
    for rule in data.get("rules") or []:
        rule_id = str(rule.get("id", ""))
        if not ID_PATTERN.match(rule_id) or rule_id in rule_ids:
            raise StudioError(f"規則 ID 不合法或重複：{rule_id!r}")
        if rule.get("role") not in role_ids:
            raise StudioError(f"規則 {rule_id} 的角色未定義：{rule.get('role')}")
        if rule.get("effect") not in EFFECTS:
            raise StudioError(f"規則 {rule_id} 的 effect 只能是 allow 或 deny")
        targets = [expand(cfg, c) for c in rule.get("classes") or []]
        if not targets:
            raise StudioError(f"規則 {rule_id} 至少要有一個類別")
        for uri in targets:
            if uri not in classes:
                raise StudioError(f"規則 {rule_id} 的類別未在本體宣告：{cfg.curie(uri)}")
        rule_ids.add(rule_id)
        rules.append({"id": rule_id, "role": rule["role"], "effect": rule["effect"], "classes": targets,
                      "note": str(rule.get("note") or "")})
    return {"default_effect": default, "roles": roles, "rules": rules}


def load(cfg, classes):
    path = cfg.path_of("access_policy")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return normalize(cfg, classes, data or {})


def write(cfg, policy):
    payload = {"default_effect": policy["default_effect"], "roles": policy["roles"],
               "rules": [{"id": r["id"], "role": r["role"], "effect": r["effect"],
                          "classes": [cfg.curie(c) for c in r["classes"]], "note": r["note"]}
                         for r in policy["rules"]]}
    path = cfg.path_of("access_policy")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(POLICY_HEADER + yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=1000),
                    encoding="utf-8")


class Evaluator:
    def __init__(self, cfg, policy, ancestors):
        self.cfg, self.policy, self.ancestors = cfg, policy, ancestors

    def cover(self, uris):
        """被涵蓋的類別 → 由哪個對應類別帶來。"""
        cover = {}
        for uri in uris:
            cover.setdefault(uri, uri)
            for ancestor in self.ancestors.get(uri, []):
                cover.setdefault(ancestor, uri)
        return cover

    def decide(self, matches):
        if any(m["effect"] == "deny" for m in matches):
            return "deny"
        if any(m["effect"] == "allow" for m in matches):
            return "allow"
        return self.policy["default_effect"]

    def for_class(self, uri, role):
        cover = self.cover([uri])
        matches = [{"rule": r["id"], "effect": r["effect"], "note": r["note"],
                    "via": [{"rule_class": self.cfg.curie(r["classes"][0]), "inherited": r["classes"][0] != uri}]}
                   for r in self.policy["rules"]
                   if r["role"] == role and len(r["classes"]) == 1 and r["classes"][0] in cover]
        return {"effect": self.decide(matches), "matches": matches}

    def for_term(self, term, role):
        mapped = [m["class"] for m in term["mappings"]]
        cover = self.cover(mapped)
        matches = []
        for rule in self.policy["rules"]:
            if rule["role"] == role and mapped and all(c in cover for c in rule["classes"]):
                matches.append({"rule": rule["id"], "effect": rule["effect"], "note": rule["note"],
                                "combination": len(rule["classes"]) > 1,
                                "via": [{"rule_class": self.cfg.curie(c), "mapped_class": self.cfg.curie(cover[c]),
                                         "inherited": cover[c] != c} for c in rule["classes"]]})
        return {"effect": self.decide(matches) if mapped else "unmapped", "matches": matches}

    def all_roles(self, fn, item):
        return {r["id"]: fn(item, r["id"]) for r in self.policy["roles"]}
