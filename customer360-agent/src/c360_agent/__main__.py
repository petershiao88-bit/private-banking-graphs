"""命令列入口：python -m c360_agent <指令>。

  ping                 檢查地端 Qwen 端點：模型清單、思考格式、工具呼叫支援、/tokenize
  pack                 產出各角色 context 包到 packs/<版號>/
  show-pack ROLE       印出某角色的 context 包（--level full、--skeleton）
  tool NAME [JSON]     直接呼叫本體工具（除錯用）
  ask "問題"           問一題（--mode、--role），印出完整過程
  chat                 互動問答（同 ask，可連續問）
  eval                 跑評測題庫，輸出 runs/<時間>/report.md、report.html
  report RUN_DIR       重新產生某次評測的報告
  check                檢查題庫與本體是否一致
  backlog RUN_DIR      把某次評測的質疑紀錄整理成本體維護待辦（backlog.md）
"""

import argparse
import json
from pathlib import Path
import sys
import time

from . import evaluate, packs, report, settings as settings_mod
from .agent import MODES, Agent
from .knowledge import Knowledge
from .llm import LLMError, OpenAICompatible, ScriptedLLM
from .tools import ToolBox


def main(argv=None):
    parser = argparse.ArgumentParser(prog="c360_agent", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="設定檔（預設為專案根目錄的 config.yaml）")
    parser.add_argument("--backend", choices=["openai", "heuristic"], default="openai",
                        help="openai＝地端 Qwen（預設）；heuristic＝不用模型的離線流程檢查")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ping")
    p.add_argument("--skip-tools", action="store_true")

    p = sub.add_parser("pack")
    p.add_argument("--tokenize", action="store_true", help="用端點的 /tokenize 實測 token 數（vLLM）")

    p = sub.add_parser("show-pack")
    p.add_argument("role")
    p.add_argument("--level", default=None)
    p.add_argument("--skeleton", action="store_true")

    p = sub.add_parser("tool")
    p.add_argument("name")
    p.add_argument("arguments", nargs="?", default="{}")
    p.add_argument("--role", default=None)

    for name in ("ask", "chat"):
        p = sub.add_parser(name)
        if name == "ask":
            p.add_argument("question")
        p.add_argument("--mode", choices=MODES, default="plan")
        p.add_argument("--role", default=None)
        p.add_argument("--level", default=None)
        p.add_argument("--json", action="store_true", help="輸出完整 JSON 紀錄")
        p.add_argument("--thinking", action="store_true", help="一併印出模型的思考內容")

    p = sub.add_parser("eval")
    p.add_argument("--modes", default=None, help="逗號分隔，例如 context,plan（預設看 config.eval.modes）")
    p.add_argument("--ids", default=None, help="只跑這些題目 ID（逗號分隔）")
    p.add_argument("--category", default=None, help="只跑某個題型")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--repeat", type=int, default=None)
    p.add_argument("--level", default=None)
    p.add_argument("--resume", default=None, help="接續某個 runs/<資料夾>（跳過已完成的題目）")
    p.add_argument("--out", default=None, help="輸出資料夾（預設 runs/<時間>-<模型>）")
    p.add_argument("--thinking", choices=["keep", "off"], default=None, help="覆寫 llm.thinking（比較開關思考）")

    p = sub.add_parser("report")
    p.add_argument("run_dir")

    sub.add_parser("check")

    p = sub.add_parser("backlog")
    p.add_argument("run_dir")

    args = parser.parse_args(argv)
    cfg = settings_mod.load(args.config)
    try:
        return COMMANDS[args.cmd](cfg, args)
    except (LLMError, ValueError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------- 共用


def make_llm(cfg, args, kb=None):
    if args.backend == "heuristic":
        from .offline import HeuristicResponder
        return ScriptedLLM(responder=HeuristicResponder(kb or Knowledge(cfg)), model="heuristic")
    return OpenAICompatible(cfg.llm)


def default_role(cfg, args):
    return getattr(args, "role", None) or cfg.agent.get("default_role", "rm")


# ---------------------------------------------------------------------- 指令


def cmd_ping(cfg, args):
    llm = OpenAICompatible(cfg.llm)
    print(f"端點：{cfg.llm.base_url}")
    try:
        models = llm.models()
        print("模型：" + ("、".join(models) if models else "（/models 沒有回傳）"))
    except LLMError as exc:
        print(f"✗ 讀不到 /models：{exc}")
        print("  請確認 Qwen 服務已啟動、config.yaml 的 llm.base_url 正確（vLLM 通常是 http://主機:8000/v1）。")
        return 1
    model = llm.resolve_model()
    print(f"使用模型：{model}")
    start = time.time()
    result = llm.chat([{"role": "user", "content": "用一句繁體中文回答：1+1 等於多少？"}], max_tokens=512)
    print(f"✓ 聊天：{result.content[:80]!r}（{time.time() - start:.1f} 秒，usage={result.usage}）")
    if result.thinking:
        print(f"  偵測到思考內容（{len(result.thinking)} 字），已自動分離。若想關閉思考以加速：")
        print("  vLLM／SGLang 在 llm.extra_body 加上 {chat_template_kwargs: {enable_thinking: false}}")
    if not args.skip_tools:
        schema = [{"type": "function", "function": {"name": "search_terms", "description": "查業務用語",
                                                     "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                                                                    "required": ["query"]}}}]
        try:
            llm.tool_mode = "native"
            r = llm.chat([{"role": "user", "content": "請呼叫 search_terms 查詢「基金手收」。"}], tools=schema, max_tokens=1024)
            if r.tool_calls and r.tool_mode == "native":
                print(f"✓ 原生工具呼叫可用：{r.tool_calls[0]['name']}({r.tool_calls[0]['arguments']})")
                hint = "native"
            elif r.tool_calls:
                print("△ 伺服器沒有解析工具呼叫，但模型輸出了 <tool_call>，程式會自行解析（建議 tool_calling: prompt）")
                hint = "prompt"
            else:
                print(f"△ 模型沒有呼叫工具：{r.content[:120]!r}（建議 tool_calling: prompt）")
                hint = "prompt"
        except LLMError as exc:
            print(f"△ 伺服器不接受 tools 參數（{str(exc)[:160]}）；建議 tool_calling: prompt")
            hint = "prompt"
        print(f"  建議設定：llm.tool_calling: {hint}（目前 {cfg.llm.tool_calling}；auto 也會自動處理）")
    count = llm.tokenize("基金手收")
    print(f"{'✓' if count else '△'} /tokenize：{count if count else '不支援（token 數會用估計值）'}")
    return _check_context_length(cfg, llm)


def _check_context_length(cfg, llm):
    """送一份完整的理專 context 包，看伺服器回報的輸入 token 數；明顯偏少代表 context 被截斷（Ollama 常見）。"""
    kb = Knowledge(cfg)
    pack = packs.build(kb, cfg.agent.get("default_role", "rm"), cfg.agent.get("pack_level", "compact"))
    expected = llm.tokenize(pack["markdown"]) or pack["tokens_est"]
    r = llm.chat([{"role": "system", "content": pack["markdown"]},
                  {"role": "user", "content": "只回覆「收到」兩個字。"}], max_tokens=256)
    got = int(r.usage.get("prompt_tokens") or 0)
    if not got:
        print("△ context 長度：伺服器沒有回報 usage.prompt_tokens，無法自動確認是否截斷")
    elif got < expected * 0.7:
        print(f"✗ context 長度：送出約 {expected} token，伺服器只收到 {got}，context 很可能被截斷。")
        print("  Ollama：設定環境變數 OLLAMA_CONTEXT_LENGTH=16384（或 Modelfile 的 PARAMETER num_ctx 16384）後重啟。")
        print("  vLLM：確認 --max-model-len 至少 16384。")
        return 1
    else:
        print(f"✓ context 長度：送出約 {expected} token，伺服器收到 {got} token，沒有截斷")
    return 0


def cmd_pack(cfg, args):
    kb = Knowledge(cfg)
    out, manifest = packs.write_all(kb, cfg.packs_dir)
    if args.tokenize:
        llm = OpenAICompatible(cfg.llm)
        for p in manifest["packs"]:
            p["tokens_exact"] = llm.tokenize((out / p["file"]).read_text(encoding="utf-8"))
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"本體 v{kb.version}（{'與 release 一致' if kb.release['matches_release'] else '工作版本'}），輸出到 {out}")
    for p in manifest["packs"]:
        exact = f"，實測 {p['tokens_exact']}" if p.get("tokens_exact") else ""
        print(f"  {p['file']:<24} 指標 {p['metrics']:>2}  估計 {p['tokens_est']:>5} token{exact}")
    return 0


def cmd_show_pack(cfg, args):
    kb = Knowledge(cfg)
    level = args.level or cfg.agent.get("pack_level", "compact")
    print(packs.build(kb, args.role, level, skeleton=args.skeleton)["markdown"])
    return 0


def cmd_tool(cfg, args):
    kb = Knowledge(cfg)
    box = ToolBox(kb, default_role(cfg, args))
    print(json.dumps(box.call(args.name, args.arguments), ensure_ascii=False, indent=2))
    return 0


def _print_transcript(t, show_thinking=False):
    print(f"\n── 模式 {t['mode']}｜角色 {t['role']}｜模型 {t.get('model')}｜context ≈{t['pack']['tokens_est']} token")
    for call in t["calls"]:
        print(f"\n[{call['stage']} #{call['round']}] {call['latency']} 秒  usage={call['usage']}")
        if show_thinking and call["thinking"]:
            print("  （思考）" + call["thinking"][:2000].replace("\n", "\n  "))
        for c, res in zip(call["tool_calls"], call["tool_results"] or [None] * len(call["tool_calls"])):
            print(f"  🔧 {c['name']}({c['arguments']})")
            print("     → " + json.dumps(res, ensure_ascii=False)[:300])
        if call["content"] and not call["tool_calls"]:
            print("  " + call["content"][:1500].replace("\n", "\n  "))
    for i, g in enumerate(t["gate"], 1):
        state = "通過" if g["passed"] else "未通過"
        print(f"\n本體檢查 #{i}（{'強制' if g.get('enforced') else '只記錄'}）：{state}")
        for e in g["errors"]:
            print(f"  ✗ [{e['code']}] {e['message']}")
        for w in g["warnings"]:
            print(f"  ! [{w['code']}] {w['message']}")
    print(f"\n決策：{t['decision']}｜指標：{', '.join(t['metrics']) or '（無）'}")
    print("回答：\n" + (t["answer"] or t.get("error") or "（無）"))
    print(f"\n合計：呼叫 {t.get('llm_calls')} 次、工具 {t.get('tool_calls')} 次、token {t.get('usage')}、{t.get('latency')} 秒")


def cmd_ask(cfg, args):
    kb = Knowledge(cfg)
    agent = Agent(kb, make_llm(cfg, args, kb), default_role(cfg, args), args.mode, level=args.level)
    t = agent.ask(args.question)
    if args.json:
        print(json.dumps(t, ensure_ascii=False, indent=2))
    else:
        _print_transcript(t, args.thinking)
    return 0 if t["decision"] not in ("error",) else 1


def cmd_chat(cfg, args):
    kb = Knowledge(cfg)
    agent = Agent(kb, make_llm(cfg, args, kb), default_role(cfg, args), args.mode, level=args.level)
    print(f"模式 {args.mode}｜角色 {agent.role}｜輸入問題後按 Enter，空白行結束。")
    while True:
        try:
            q = input("\n問題> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        _print_transcript(agent.ask(q), args.thinking)
    return 0


def cmd_eval(cfg, args):
    kb = Knowledge(cfg)
    questions = evaluate.load_questions(cfg.questions, kb)
    if args.ids:
        wanted = [x.strip() for x in args.ids.split(",") if x.strip()]
        questions = [q for q in questions if q["id"] in wanted]
    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
    if args.limit:
        questions = questions[:args.limit]
    modes = [m.strip() for m in (args.modes.split(",") if args.modes else cfg.eval.get("modes", MODES))]
    bad = [m for m in modes if m not in MODES]
    if bad:
        raise ValueError(f"不認得的模式：{bad}")
    repeat = args.repeat or int(cfg.eval.get("repeat", 1))
    if args.thinking:
        cfg.llm.thinking = args.thinking
    llm = make_llm(cfg, args, kb)
    model = llm.resolve_model()
    if args.resume:
        run_dir = Path(args.resume)
    elif args.out:
        run_dir = Path(args.out)
    else:
        run_dir = cfg.runs_dir / (time.strftime("%Y%m%d-%H%M%S") + "-" + _slug(model))
    run_dir.mkdir(parents=True, exist_ok=True)
    meta_path = run_dir / "run.json"
    if not meta_path.exists():
        pack_dir, manifest = packs.write_all(kb, cfg.packs_dir)
        if args.backend == "openai":
            for p in manifest["packs"]:
                p["tokens_exact"] = llm.tokenize((pack_dir / p["file"]).read_text(encoding="utf-8"))
        window = cfg.llm.context_window
        biggest = max(p.get("tokens_exact") or p["tokens_est"] for p in manifest["packs"])
        if biggest > window * 0.7:
            print(f"⚠️ 最大的 context 包約 {biggest} token，接近 llm.context_window={window}，請確認伺服器的 context 長度")
        meta = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "backend": args.backend,
                "backend_note": "不用語言模型的關鍵字檢索" if args.backend == "heuristic" else "",
                "model": model, "base_url": cfg.llm.base_url if args.backend == "openai" else None,
                "tool_calling": cfg.llm.tool_calling, "temperature": cfg.llm.temperature,
                "max_tokens": cfg.llm.max_tokens, "extra_body": cfg.llm.extra_body, "thinking": cfg.llm.thinking,
                "ontology_version": kb.version,
                "ontology_state": "與 release 一致" if kb.release["matches_release"] else "工作版本",
                "knowledge_fingerprint": kb.fingerprint(), "modes": modes, "repeat": repeat,
                "question_count": len(questions), "question_ids": [q["id"] for q in questions],
                "level": args.level or cfg.agent.get("pack_level", "compact"), "packs": manifest["packs"]}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"評測：{len(questions)} 題 × {len(modes)} 模式 × {repeat} 次 → {run_dir}")
    runner = evaluate.Runner(kb, llm, run_dir, modes=modes, level=args.level)
    runner.run(questions, repeat=repeat, resume=True)
    summary = report.write(run_dir)
    from . import backlog
    backlog.write(run_dir)
    print("\n模式        正確        默默答錯   保守未答  格式錯誤  越權  自編ID")
    for mode, s in summary["modes"].items():
        print(f"{mode:<10} {s['correct']:>3}/{s['n']:<3}({_pct(s['accuracy']):>4})  {s['silent_wrong']:>4}      "
              f"{s['safe_miss']:>4}     {s['format_error']:>4}    {s['leaks']:>3}   {s['invalid_ids']:>3}")
    print(f"\n報告：{run_dir / 'report.md'}\n      {run_dir / 'report.html'}")
    return 0


def cmd_report(cfg, args):
    summary = report.write(Path(args.run_dir))
    print(json.dumps(summary["modes"], ensure_ascii=False, indent=2))
    return 0


def cmd_check(cfg, args):
    kb = Knowledge(cfg)
    questions = evaluate.load_questions(cfg.questions, kb)
    cats = {}
    for q in questions:
        cats[q["category"]] = cats.get(q["category"], 0) + 1
    print(f"題庫 {len(questions)} 題，與本體 v{kb.version} 一致。" + "、".join(f"{k} {v}" for k, v in cats.items()))
    return 0


def cmd_backlog(cfg, args):
    from . import backlog
    items = backlog.write(Path(args.run_dir))
    false = sum(i["false_count"] for i in items)
    fixed = sum(i["fixed_count"] for i in items)
    valid = sum(i["valid_count"] for i in items)
    print(f"誤質疑 {false} 次、促成修正 {fixed} 次、答案仍錯 {valid} 次 → {Path(args.run_dir) / 'backlog.md'}")
    return 0


def _pct(x):
    return "—" if x is None else f"{x * 100:.0f}%"


def _slug(text):
    import re
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(text)).strip("-")[-40:] or "model"


COMMANDS = {"ping": cmd_ping, "pack": cmd_pack, "show-pack": cmd_show_pack, "tool": cmd_tool, "ask": cmd_ask,
            "chat": cmd_chat, "eval": cmd_eval, "report": cmd_report, "check": cmd_check,
            "backlog": cmd_backlog}

if __name__ == "__main__":
    sys.exit(main())
