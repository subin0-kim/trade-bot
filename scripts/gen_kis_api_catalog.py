"""KIS API 카탈로그 생성기.

../open-trading-api/examples_llm/ 를 스캔해 카테고리별 API 목록
(함수 원형, 설명, tr_id, URL)을 wiki/shared/brokers/kis/api/ 에 생성한다.

실행: uv run python scripts/gen_kis_api_catalog.py
"""

from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path

SAMPLES_ROOT = Path(__file__).resolve().parents[1].parent / "open-trading-api" / "examples_llm"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "wiki" / "shared" / "brokers" / "kis" / "api"

CATEGORY_NAMES = {
    "auth": "인증",
    "domestic_stock": "국내주식",
    "domestic_bond": "국내채권",
    "domestic_futureoption": "국내선물옵션",
    "overseas_stock": "해외주식",
    "overseas_futureoption": "해외선물옵션",
    "elw": "ELW",
    "etfetn": "ETF/ETN",
}

# 헤더 주석 예: [국내주식] 기본시세 > 주식현재가 시세[v1_국내주식-008]
HEADER_RE = re.compile(r"\[([^\]]+)\]\s*([^>\n]+)>\s*(.+)")


def parse_api_file(py_file: Path) -> dict | None:
    """단일 기능 파일에서 함수 원형·설명·tr_id·URL 추출."""
    try:
        source = py_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = py_file.read_text(encoding="cp949")

    # API_URL, tr_id
    api_urls = re.findall(r'API_URL\s*=\s*"([^"]+)"', source)
    tr_ids = sorted(set(re.findall(r'tr_id\s*=\s*"([^"]+)"', source)))

    # 헤더 주석에서 분류 추출
    subcategory, api_title = "", ""
    for line in source.splitlines()[:60]:
        m = HEADER_RE.search(line)
        if m:
            subcategory = m.group(2).strip()
            api_title = m.group(3).strip()
            break

    # 함수 시그니처 (폴더명과 같은 함수 우선, 없으면 첫 top-level def)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not funcs:
        return None
    target = next((f for f in funcs if f.name == py_file.stem), funcs[0])

    args = target.args
    n_defaults = len(args.defaults)
    required = [a.arg for a in args.args[: len(args.args) - n_defaults]]
    optional_count = n_defaults + len(args.kwonlyargs)

    sig = f"{target.name}({', '.join(required)}"
    if optional_count:
        sig += f"[, +{optional_count} opt]"
    sig += ")"

    # docstring 첫 줄
    doc = ast.get_docstring(target) or ""
    doc_first = doc.strip().splitlines()[0].strip() if doc.strip() else ""

    return {
        "name": target.name,
        "signature": sig,
        "title": api_title or doc_first,
        "subcategory": subcategory or "기타",
        "tr_ids": tr_ids,
        "url": api_urls[0] if api_urls else "(웹소켓)",
        "doc": doc_first,
        "folder": py_file.parent.name,
    }


def generate_category_doc(category: str, apis: list[dict]) -> str:
    ko_name = CATEGORY_NAMES.get(category, category)
    today = date.today().isoformat()

    lines = [
        "---",
        f"name: kis-api-{category.replace('_', '-')}",
        "scope: shared",
        f"updated: {today}",
        "sources:",
        f"  - ../open-trading-api/examples_llm/{category}/ (자동 생성: scripts/gen_kis_api_catalog.py)",
        "---",
        "",
        f"# KIS API 카탈로그 — {ko_name} ({len(apis)}개)",
        "",
        f"> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/{category}/<함수명>/` 참조.",
        "> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).",
        "",
    ]

    by_sub: dict[str, list[dict]] = {}
    for api in apis:
        by_sub.setdefault(api["subcategory"], []).append(api)

    for sub in sorted(by_sub):
        lines.append(f"## {sub}")
        lines.append("")
        lines.append("| 함수 원형 | 설명 | tr_id | URL |")
        lines.append("|---|---|---|---|")
        for api in sorted(by_sub[sub], key=lambda a: a["name"]):
            tr = ", ".join(api["tr_ids"]) or "-"
            title = api["title"].replace("|", "\\|")
            sig = api["signature"].replace("|", "\\|")
            lines.append(f"| `{sig}` | {title} | {tr} | `{api['url']}` |")
        lines.append("")

    return "\n".join(lines)


def main():
    if not SAMPLES_ROOT.exists():
        raise SystemExit(f"샘플 저장소 없음: {SAMPLES_ROOT}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []

    for category_dir in sorted(SAMPLES_ROOT.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith(("_", ".")):
            continue
        category = category_dir.name

        apis = []
        for feature_dir in sorted(category_dir.iterdir()):
            if not feature_dir.is_dir():
                continue
            py_file = feature_dir / f"{feature_dir.name}.py"
            if not py_file.exists():
                # 폴더명과 다른 단일 py (chk_ 제외) 탐색
                candidates = [
                    p for p in feature_dir.glob("*.py") if not p.name.startswith("chk_")
                ]
                if not candidates:
                    continue
                py_file = candidates[0]
            info = parse_api_file(py_file)
            if info:
                apis.append(info)

        if not apis:
            continue

        doc = generate_category_doc(category, apis)
        out_file = OUTPUT_DIR / f"{category}.md"
        out_file.write_text(doc, encoding="utf-8")
        summary.append((category, len(apis)))
        print(f"  {category}: {len(apis)}개 → {out_file.relative_to(OUTPUT_DIR.parents[3])}")

    total = sum(n for _, n in summary)
    print(f"\n총 {total}개 API 추출 완료")


if __name__ == "__main__":
    main()
