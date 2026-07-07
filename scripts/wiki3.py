#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "wiki3.json"
DECIDE_PROMPT_PATH = ROOT / "schema" / "prompts" / "decide-action.md"
RENDER_PROMPT_PATH = ROOT / "schema" / "prompts" / "render-synthesis.md"
DECIDE_SCHEMA_PATH = ROOT / "schema" / "json" / "decide-action.schema.json"
RENDER_SCHEMA_PATH = ROOT / "schema" / "json" / "render-synthesis.schema.json"


@dataclass
class Bundle:
    id: str
    ts: str
    origin: str
    title: str
    summary: str
    content: str
    topics: list[str]
    artifacts: list[str]
    provenance: dict[str, Any]
    path: Path


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def trimmed_text(text: str, limit: int) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def topic_from_title(title: str) -> str | None:
    low = title.lower()
    mapping = [
        ("unitree", ("unitree", "宇樹", "宇树")),
        ("qwen", ("qwen", "千問", "千问")),
        ("deepseek", ("deepseek",)),
        ("huawei", ("huawei", "華為", "华为")),
        ("openclaw", ("openclaw",)),
        ("home-assistant", ("home assistant", "home-assistant")),
        ("autonomous-driving", ("waymo", "drivepi", "drivejudge", "robotaxi", "自動運転")),
        ("llm-ai", ("anthropic", "claude", "openai", "codex", "gemini", "hy3", "混元")),
        ("image-sensor", ("image sensor", "センサ", "sensor")),
        ("tech_china", ("中国テック", "china tech", "中国")),
        ("tech_news", ("関心特化テックニュース", "tailored tech")),
    ]
    for topic, keys in mapping:
        if any(key.lower() in low for key in keys):
            return topic
    return None


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    if yaml is None:
        raise RuntimeError("PyYAML is required.")
    return yaml.safe_load(raw) or {}, body


def section_text(body: str, title: str) -> str:
    pattern = re.compile(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", re.M | re.S)
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def extract_raw_snapshot(body: str) -> dict[str, Any] | None:
    block = section_text(body, "Raw event snapshot")
    match = re.search(r"```json\n(.*?)\n```", block, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def extract_evidence(body: str) -> list[str]:
    values = []
    for line in section_text(body, "Evidence").splitlines():
        line = line.strip()
        if line.startswith("- "):
            values.append(line[2:].strip().strip("`"))
    return values


def bundle_from_promoted(path: Path, workspace_root: Path, char_limit: int) -> Bundle:
    payload = load_json(path)
    cache = payload.get("cache") or {}
    items = cache.get("items") or []
    titles = [str(item.get("title") or "") for item in items]
    topics = ["tech_china"]
    for item in items:
        topic_key = item.get("topic_key")
        if topic_key:
            topics.append(str(topic_key))
        title_topic = topic_from_title(str(item.get("title") or ""))
        if title_topic:
            topics.append(title_topic)
    deduped_topics: list[str] = []
    for topic in topics:
        if topic and topic not in deduped_topics:
            deduped_topics.append(topic)
    return Bundle(
        id=f"bundle.promoted.{path.stem}",
        ts=str(payload.get("generatedAt") or now_stamp()),
        origin="promoted_digest",
        title=str(payload.get("header") or path.stem),
        summary=trimmed_text(str(payload.get("body") or ""), char_limit),
        content=str(payload.get("body") or ""),
        topics=deduped_topics,
        artifacts=[str(cache.get("cacheFile") or "")],
        provenance={
            "source": payload.get("source"),
            "relative_path": safe_rel(path, workspace_root),
            "item_titles": titles[:10],
        },
        path=path,
    )


def bundle_from_legacy_source(path: Path, workspace_root: Path, char_limit: int) -> Bundle:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    raw_snapshot = extract_raw_snapshot(body) or {}
    title = str(frontmatter.get("title") or path.stem)
    summary = section_text(body, "Summary")
    topics = [str(tag) for tag in frontmatter.get("tags") or []]
    title_topic = topic_from_title(title)
    if title_topic and title_topic not in topics:
        topics.append(title_topic)
    return Bundle(
        id=str(frontmatter.get("id") or f"bundle.legacy.{path.stem}"),
        ts=str(raw_snapshot.get("occurredAt") or frontmatter.get("updatedAt") or now_stamp()),
        origin="legacy_source_page",
        title=title,
        summary=trimmed_text(summary, char_limit),
        content=summary,
        topics=topics,
        artifacts=extract_evidence(body),
        provenance={
            "source": raw_snapshot.get("source"),
            "relative_path": safe_rel(path, workspace_root),
        },
        path=path,
    )


def family_names(config: dict[str, Any]) -> list[str]:
    return list(config["families"].keys())


def family_config(config: dict[str, Any], family: str) -> dict[str, Any]:
    if family not in config["families"]:
        known = ", ".join(family_names(config))
        raise SystemExit(f"unknown family: {family} (known: {known})")
    return config["families"][family]


def ingest_upstream(config: dict[str, Any]) -> list[Path]:
    workspace_root = Path(config["upstream"]["workspace_root"]).resolve()
    bundle_dir = ROOT / config["bundle_dir"]
    created: list[Path] = []
    char_limit = int(config["artifact_char_limit"])

    for pattern in config["upstream"].get("china_promoted_globs") or []:
        for path in workspace_root.glob(pattern):
            if not path.is_file():
                continue
            bundle = bundle_from_promoted(path, workspace_root, char_limit)
            out = bundle_dir / f"{path.stem}.json"
            dump_json(out, bundle.__dict__ | {"path": str(bundle.path)})
            created.append(out)

    for pattern in config["upstream"].get("tailored_source_globs") or []:
        for path in workspace_root.glob(pattern):
            if not path.is_file():
                continue
            bundle = bundle_from_legacy_source(path, workspace_root, char_limit)
            out = bundle_dir / f"{path.stem}.json"
            dump_json(out, bundle.__dict__ | {"path": str(bundle.path)})
            created.append(out)

    return created


def load_bundles(config: dict[str, Any]) -> list[Bundle]:
    bundle_dir = ROOT / config["bundle_dir"]
    bundles: list[Bundle] = []
    for path in sorted(bundle_dir.glob("*.json")):
        payload = load_json(path)
        bundles.append(
            Bundle(
                id=str(payload["id"]),
                ts=str(payload["ts"]),
                origin=str(payload["origin"]),
                title=str(payload["title"]),
                summary=str(payload["summary"]),
                content=str(payload["content"]),
                topics=[str(topic) for topic in payload.get("topics") or []],
                artifacts=[str(item) for item in payload.get("artifacts") or []],
                provenance=dict(payload.get("provenance") or {}),
                path=path,
            )
        )
    return bundles


def page_snapshot(page_path: Path) -> dict[str, Any] | None:
    if not page_path.exists():
        return None
    text = page_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    sections = re.findall(r"^## (.+)$", body, re.M)
    return {
        "path": str(page_path.relative_to(ROOT)),
        "frontmatter": frontmatter,
        "content": text[:4000],
        "sections": sections,
    }


def maybe_read_local_artifact(path_str: str, char_limit: int) -> dict[str, Any] | None:
    candidate = Path(path_str.strip('"'))
    if not candidate.is_absolute() or not candidate.exists() or not candidate.is_file():
        return None
    if candidate.suffix.lower() == ".json":
        try:
            preview = json.dumps(
                json.loads(candidate.read_text(encoding="utf-8")),
                ensure_ascii=False,
                indent=2,
            )[:char_limit]
        except Exception:
            preview = candidate.read_text(encoding="utf-8", errors="replace")[:char_limit]
    else:
        preview = candidate.read_text(encoding="utf-8", errors="replace")[:char_limit]
    return {"path": str(candidate), "preview": preview}


def bundle_matches_family(bundle: Bundle, family_cfg: dict[str, Any]) -> bool:
    filters = family_cfg.get("bundle_filters") or {}
    topics_any = set(filters.get("topics_any") or [])
    origins = set(filters.get("origins") or [])
    if origins and bundle.origin not in origins:
        return False
    if topics_any and not any(topic in topics_any for topic in bundle.topics):
        return False
    return True


def bundles_for_family(config: dict[str, Any], family: str) -> list[Bundle]:
    cfg = family_config(config, family)
    bundles = [bundle for bundle in load_bundles(config) if bundle_matches_family(bundle, cfg)]
    bundles.sort(key=lambda item: (item.ts, item.id), reverse=True)
    return bundles[: int(cfg["max_bundles"])]


def build_evidence_pack(config: dict[str, Any], family: str) -> dict[str, Any]:
    family_cfg = family_config(config, family)
    page_path = ROOT / family_cfg["page_path"]
    bundles = bundles_for_family(config, family)

    artifacts: list[dict[str, Any]] = []
    for bundle in bundles:
        for artifact_path in bundle.artifacts:
            artifact = maybe_read_local_artifact(artifact_path, int(config["artifact_char_limit"]))
            if artifact and artifact not in artifacts:
                artifacts.append(artifact)

    return {
        "phase": "query",
        "family": family,
        "generated_at": now_stamp(),
        "family_config": {
            "kind": family_cfg["kind"],
            "title": family_cfg["title"],
            "slug": family_cfg["slug"],
            "sections": family_cfg["sections"],
            "page_path": family_cfg["page_path"],
        },
        "existing_page": page_snapshot(page_path),
        "bundles": [
            {
                "id": bundle.id,
                "ts": bundle.ts,
                "origin": bundle.origin,
                "title": bundle.title,
                "summary": bundle.summary,
                "topics": bundle.topics,
                "artifacts": bundle.artifacts[:4],
                "provenance": bundle.provenance,
            }
            for bundle in bundles
        ],
        "artifacts": artifacts,
    }


def save_run_json(config: dict[str, Any], stem: str, payload: dict[str, Any]) -> Path:
    path = ROOT / config["run_dir"] / f"{stem}.json"
    dump_json(path, payload)
    return path


def render_page(target: dict[str, Any], rendered: dict[str, Any], bundle_ids: list[str]) -> str:
    if yaml is None:
        raise RuntimeError("PyYAML is required.")
    frontmatter = {
        "title": target["title"],
        "slug": target["slug"],
        "kind": target["kind"],
        "updated_at": datetime.now(UTC).date().isoformat(),
        "bundle_ids": bundle_ids,
    }
    lines = [
        "---",
        yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip(),
        "---",
        "",
        f"# {rendered['title']}",
        "",
    ]
    if rendered.get("summary"):
        lines.extend([str(rendered["summary"]).strip(), ""])
    for section, bullets in rendered["sections"].items():
        lines.extend([f"## {section}", ""])
        for bullet in bullets:
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def rewrite_index() -> None:
    synth_dir = ROOT / "wiki" / "syntheses"
    synth_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# Wiki Index", "", "## Syntheses", ""]
    pages = sorted(synth_dir.glob("*.md"))
    if not pages:
        lines.append("- No syntheses yet.")
    else:
        for page in pages:
            title = page.stem
            match = re.search(r"^# (.+)$", page.read_text(encoding="utf-8"), re.M)
            if match:
                title = match.group(1).strip()
            lines.append(f"- [{title}](syntheses/{page.name})")
    (ROOT / "wiki" / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_log(action: str, family: str, page_path: str, reason: str) -> None:
    path = ROOT / "wiki" / "log.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## [{stamp}] {action} | {family}\n")
        fh.write(f"- target: `{page_path}`\n")
        fh.write(f"- reason: {reason}\n")


def build_query_job(config: dict[str, Any], family: str) -> Path:
    pack = build_evidence_pack(config, family)
    stem = f"{pack['generated_at']}-{family}"
    evidence_path = save_run_json(config, f"{stem}-query-evidence", pack)
    job = {
        "phase": "query",
        "family": family,
        "generated_at": pack["generated_at"],
        "evidence_pack_path": str(evidence_path),
        "decision_output_path": str(ROOT / config["run_dir"] / f"{stem}-decision.json"),
        "render_output_path": str(ROOT / config["run_dir"] / f"{stem}-render.json"),
        "decide_prompt_path": str(DECIDE_PROMPT_PATH),
        "render_prompt_path": str(RENDER_PROMPT_PATH),
        "decision_schema_path": str(DECIDE_SCHEMA_PATH),
        "render_schema_path": str(RENDER_SCHEMA_PATH),
    }
    return save_run_json(config, f"{stem}-query-job", job)


def build_query_batch(config: dict[str, Any], families: list[str]) -> Path:
    jobs = []
    for family in families:
        job_path = build_query_job(config, family)
        jobs.append({"family": family, "job_path": str(job_path)})
    manifest = {"phase": "query", "generated_at": now_stamp(), "families": jobs}
    return save_run_json(config, f"{manifest['generated_at']}-query-batch", manifest)


def apply_query_job(job_path: Path) -> str:
    job = load_json(job_path)
    decision = load_json(Path(job["decision_output_path"]))
    pack = load_json(Path(job["evidence_pack_path"]))
    target = decision["target"]
    if decision["action"] == "hold_source_only":
        append_log(decision["action"], pack["family"], target["page_path"], decision["reason"])
        return "HOLD"
    rendered = load_json(Path(job["render_output_path"]))
    page_path = ROOT / target["page_path"]
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(
        render_page(target, rendered, [bundle["id"] for bundle in pack["bundles"]]),
        encoding="utf-8",
    )
    rewrite_index()
    append_log(decision["action"], pack["family"], target["page_path"], decision["reason"])
    return str(page_path)


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def lint_report(config: dict[str, Any], families: list[str] | None = None) -> dict[str, Any]:
    selected = families or family_names(config)
    all_bundles = load_bundles(config)
    issues: list[dict[str, Any]] = []
    seen_bundle_ids: set[str] = set()
    stale_days = int((config.get("lint") or {}).get("stale_days", 10))

    for family in selected:
        cfg = family_config(config, family)
        page_path = ROOT / cfg["page_path"]
        bundles = bundles_for_family(config, family)
        for bundle in bundles:
            seen_bundle_ids.add(bundle.id)

        page = page_snapshot(page_path)
        if not bundles:
            issues.append(
                {
                    "severity": "warning",
                    "family": family,
                    "code": "no_bundles",
                    "message": "No matching bundles were found for this family.",
                }
            )
            continue

        if page is None:
            issues.append(
                {
                    "severity": "warning",
                    "family": family,
                    "code": "missing_page",
                    "message": "Family has matching bundles but no synthesis page yet.",
                }
            )
            continue

        frontmatter = page.get("frontmatter") or {}
        missing_sections = [section for section in cfg["sections"] if section not in (page.get("sections") or [])]
        if missing_sections:
            issues.append(
                {
                    "severity": "warning",
                    "family": family,
                    "code": "missing_sections",
                    "message": "Synthesis page is missing required visible sections.",
                    "details": {"missing_sections": missing_sections, "page_path": str(page_path.relative_to(ROOT))},
                }
            )

        updated_at = parse_iso_date(str(frontmatter.get("updated_at") or ""))
        if updated_at is None:
            issues.append(
                {
                    "severity": "warning",
                    "family": family,
                    "code": "missing_updated_at",
                    "message": "Synthesis page frontmatter is missing a valid updated_at.",
                    "details": {"page_path": str(page_path.relative_to(ROOT))},
                }
            )
        else:
            age = (datetime.now(UTC).date() - updated_at).days
            if age > stale_days:
                issues.append(
                    {
                        "severity": "info",
                        "family": family,
                        "code": "stale_page",
                        "message": "Synthesis page may be stale relative to current bundles.",
                        "details": {"age_days": age, "page_path": str(page_path.relative_to(ROOT))},
                    }
                )

        page_bundle_ids = {str(item) for item in frontmatter.get("bundle_ids") or []}
        current_bundle_ids = {bundle.id for bundle in bundles}
        if not current_bundle_ids.issubset(page_bundle_ids):
            issues.append(
                {
                    "severity": "info",
                    "family": family,
                    "code": "bundle_coverage_gap",
                    "message": "Current matching bundles are not fully reflected in page bundle_ids.",
                    "details": {
                        "missing_bundle_ids": sorted(current_bundle_ids - page_bundle_ids)[:12],
                        "page_path": str(page_path.relative_to(ROOT)),
                    },
                }
            )

    unmatched = []
    for bundle in all_bundles:
        if bundle.id in seen_bundle_ids:
            continue
        if any(bundle_matches_family(bundle, family_config(config, name)) for name in selected):
            continue
        unmatched.append(
            {
                "bundle_id": bundle.id,
                "title": bundle.title,
                "topics": bundle.topics[:6],
                "origin": bundle.origin,
            }
        )
    if unmatched:
        issues.append(
            {
                "severity": "info",
                "family": "*",
                "code": "unmatched_bundles",
                "message": "Some bundles do not match any current family.",
                "details": {"examples": unmatched[:12]},
            }
        )

    return {
        "phase": "lint",
        "generated_at": now_stamp(),
        "families": selected,
        "issue_count": len(issues),
        "issues": issues,
    }


def run_ingest(_: argparse.Namespace) -> int:
    config = load_json(CONFIG_PATH)
    created = ingest_upstream(config)
    for path in created:
        print(path)
    return 0


def run_query_prepare(args: argparse.Namespace) -> int:
    config = load_json(CONFIG_PATH)
    ingest_upstream(config)
    print(build_query_job(config, args.family))
    return 0


def run_query_batch(args: argparse.Namespace) -> int:
    config = load_json(CONFIG_PATH)
    ingest_upstream(config)
    families = args.families or family_names(config)
    print(build_query_batch(config, families))
    return 0


def run_query_apply(args: argparse.Namespace) -> int:
    print(apply_query_job(Path(args.job)))
    return 0


def run_lint(args: argparse.Namespace) -> int:
    config = load_json(CONFIG_PATH)
    report = lint_report(config, args.families)
    path = save_run_json(config, f"{report['generated_at']}-lint-report", report)
    print(path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def run_collect(args: argparse.Namespace) -> int:
    config = load_json(CONFIG_PATH)
    ingest_upstream(config)
    path = save_run_json(config, f"{now_stamp()}-{args.family}-query-evidence", build_evidence_pack(config, args.family))
    print(path)
    return 0


def run_prepare_openclaw(args: argparse.Namespace) -> int:
    return run_query_prepare(args)


def run_prepare_batch(args: argparse.Namespace) -> int:
    return run_query_batch(args)


def run_apply_openclaw(args: argparse.Namespace) -> int:
    return run_query_apply(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bundle-first LLM wiki prototype")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="Capture upstream artifacts into raw bundles.")
    ingest.set_defaults(func=run_ingest)

    query_prepare = sub.add_parser("query-prepare", help="Build one query job manifest for a family.")
    query_prepare.add_argument("--family", required=True)
    query_prepare.set_defaults(func=run_query_prepare)

    query_batch = sub.add_parser("query-batch", help="Build one batch manifest covering multiple families.")
    query_batch.add_argument("--families", nargs="*")
    query_batch.set_defaults(func=run_query_batch)

    query_apply = sub.add_parser("query-apply", help="Apply LLM outputs from one query job.")
    query_apply.add_argument("--job", required=True)
    query_apply.set_defaults(func=run_query_apply)

    lint = sub.add_parser("lint", help="Check bundle/page quality gaps.")
    lint.add_argument("--families", nargs="*")
    lint.set_defaults(func=run_lint)

    # Compatibility with the earlier wiki3 prototype.
    ingest_old = sub.add_parser("ingest-upstream", help=argparse.SUPPRESS)
    ingest_old.set_defaults(func=run_ingest)

    collect = sub.add_parser("collect", help=argparse.SUPPRESS)
    collect.add_argument("--family", required=True)
    collect.set_defaults(func=run_collect)

    prepare = sub.add_parser("prepare-openclaw", help=argparse.SUPPRESS)
    prepare.add_argument("--family", required=True)
    prepare.set_defaults(func=run_prepare_openclaw)

    batch = sub.add_parser("prepare-batch", help=argparse.SUPPRESS)
    batch.add_argument("--families", nargs="*")
    batch.set_defaults(func=run_prepare_batch)

    apply_openclaw = sub.add_parser("apply-openclaw", help=argparse.SUPPRESS)
    apply_openclaw.add_argument("--job", required=True)
    apply_openclaw.set_defaults(func=run_apply_openclaw)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
