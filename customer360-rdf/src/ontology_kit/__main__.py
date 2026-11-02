"""python -m ontology_kit [--config 檔案] <指令>"""

import argparse
from datetime import date
import json
import sys

from . import build as builder
from . import components, versioning
from .config import Config
from .release import ReleaseError, run


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m ontology_kit", description="客戶360 本體：組成元件、版本控制、建置、推理發佈")
    parser.add_argument("--config", help="設定檔路徑（預設 config.yaml，或環境變數 C360_CONFIG）")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="版號一致性＋類別組成元件驗證")
    sub.add_parser("components", help="輸出類別組成元件統計與問題")
    sub.add_parser("diff", help="與前一版（或基準快照）比對")
    build = sub.add_parser("build", help="合併全部模組到 build/（Turtle 與 RDF/XML）")
    build.add_argument("--check", action="store_true", help="只驗證 build/ 與來源一致，不寫檔")
    bump = sub.add_parser("bump", help="升版：預設只列出要改的檔案，加 --apply 才寫入")
    bump.add_argument("version")
    bump.add_argument("--date", default=date.today().isoformat())
    bump.add_argument("--apply", action="store_true")
    release = sub.add_parser("release", help="產出 release/<版號>/")
    release.add_argument("--force", action="store_true", help="覆寫已存在且內容不同的 release")
    args = parser.parse_args(argv)
    cfg = Config(args.config)

    def show(value):
        print(json.dumps(value, ensure_ascii=False, indent=2))

    if args.command == "check":
        mismatches = versioning.check(cfg)
        _, classes, properties, issues = components.build(cfg)
        errors = [i for i in issues if i["level"] == "error"]
        show({"version": cfg.version, "version_mismatches": mismatches, "component_issues": issues,
              "classes": len(classes), "properties": len(properties),
              "hardcoded_version_elsewhere": versioning.scan_literals(cfg, cfg.version)})
        return 1 if mismatches or errors else 0
    if args.command == "components":
        _, classes, properties, issues = components.build(cfg)
        print(components.render_markdown(cfg, classes, properties, issues, cfg.version))
        return 1 if any(i["level"] == "error" for i in issues) else 0
    if args.command == "diff":
        _, classes, properties, _ = components.build(cfg, cfg.release_modules())
        result = versioning.diff(cfg, versioning.load_previous(cfg), classes, properties)
        print(versioning.render_changelog(cfg, result))
        return 1 if result["gate"] else 0
    if args.command == "build":
        try:
            show(builder.check(cfg) if args.check else builder.build(cfg))
        except (builder.StaleBuild, ReleaseError) as error:
            print(error, file=sys.stderr)
            return 1
        return 0
    if args.command == "bump":
        edits = versioning.plan_bump(cfg, args.version, args.date)
        if args.apply:
            versioning.apply_edits(edits)
        show({"from": cfg.version, "to": args.version, "date": args.date, "applied": args.apply,
              "files": [versioning.display(cfg, p) for p in edits],
              "next_steps": ["python -m ontology_kit build", "python pg/build_cypher.py",
                             "python pg/export_metric_tables.py", "python -m ontology_kit release"],
              "still_hardcoded_old_version": versioning.scan_literals(cfg, cfg.version) if args.apply else None})
        return 0
    if args.command == "release":
        try:
            show(run(cfg, force=args.force))
        except ReleaseError as error:
            print(error, file=sys.stderr)
            return 1
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
