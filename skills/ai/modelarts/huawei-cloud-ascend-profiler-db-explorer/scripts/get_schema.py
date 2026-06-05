import argparse
import difflib
import os
import re
import sqlite3
import sys
from typing import Dict, List, Tuple


def _get_reference_doc_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "references", "profiler_db_data_format.md")


def _load_reference_doc() -> Tuple[List[str], str]:
    ref_path = _get_reference_doc_path()
    try:
        with open(ref_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return [], f"❌ errorerror: notfindtoReference Documents {ref_path}"
    except Exception as e:
        return [], f"❌ errorerror: ReadReference Documentslossfailure: {str(e)}"
    return lines, ""


def _normalize_title(title: str) -> str:
    normalized = title.strip()
    normalized = re.sub(r"<a\s+name=\"[^\"]+\"></a>", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.replace("\\_", "_")
    normalized = normalized.replace("\\-", "-")
    return normalized.strip()


def _canonical_key(name: str) -> str:
    key = name.strip().upper()
    key = key.replace("\\_", "_")
    key = re.split(r"[\s( (]", key)[0]
    return key


def _extract_sections(lines: List[str]) -> List[Dict[str, object]]:
    sections: List[Dict[str, object]] = []
    current_title = None
    current_start = None
    title_pattern = re.compile(r"^\*\*(.+?)\*\*$")

    for idx, line in enumerate(lines):
        matched = title_pattern.match(line.strip())
        if not matched:
            continue

        title = _normalize_title(matched.group(1))
        if current_title is not None and current_start is not None:
            sections.append(
                {
                    "title": current_title,
                    "start": current_start,
                    "end": idx,
                }
            )
        current_title = title
        current_start = idx

    if current_title is not None and current_start is not None:
        sections.append(
            {
                "title": current_title,
                "start": current_start,
                "end": len(lines),
            }
        )

    return sections


def list_documented_tables() -> str:
    lines, err = _load_reference_doc()
    if err:
        return err

    sections = _extract_sections(lines)
    names = []
    for sec in sections:
        title = sec["title"]
        canonical = _canonical_key(title)
        if re.fullmatch(r"[A-Z0-9_]+", canonical):
            names.append(canonical)

    if not names:
        return "❌ notinReference DocumentsmiddleParsetotablename. "

    unique_names = sorted(set(names))
    return "\n".join(unique_names)


def _load_db_tables(db_path: str) -> Tuple[List[str], str]:
    if not db_path:
        return [], "❌ errorerror: db_path notabilityasempty. "
    if not os.path.exists(db_path):
        return [], f"❌ errorerror: db filenotkeepin: {db_path}"

    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall() if row and row[0]]
        finally:
            conn.close()
    except Exception as e:
        return [], f"❌ errorerror: Read db tablenamelossfailure: {str(e)}"

    return tables, ""


def list_db_tables(db_path: str) -> str:
    tables, err = _load_db_tables(db_path)
    if err:
        return err
    if not tables:
        return f"❌ db middlenotfindtoanywhattable: {db_path}"
    return "\n".join(tables)


def compare_doc_with_db(db_path: str) -> str:
    doc_lines, err = _load_reference_doc()
    if err:
        return err

    doc_sections = _extract_sections(doc_lines)
    doc_tables = sorted(
        {
            _canonical_key(sec["title"])
            for sec in doc_sections
            if re.fullmatch(r"[A-Z0-9_]+", _canonical_key(sec["title"]))
        }
    )
    db_tables, db_err = _load_db_tables(db_path)
    if db_err:
        return db_err

    doc_set = set(doc_tables)
    db_set = {_canonical_key(name) for name in db_tables}

    both = sorted(doc_set & db_set)
    only_doc = sorted(doc_set - db_set)
    only_db = sorted(db_set - doc_set)

    out = []
    out.append("### Documentsandwhenprevious DB tablenameCompare")
    out.append(f"- Documentstablenumber: {len(doc_set)}")
    out.append(f"- DB tablenumber: {len(db_set)}")
    out.append(f"- exchangeset: {len(both)}")
    out.append("")
    out.append("#### exchangesettable")
    out.append("\n".join(both) if both else " (no) ")
    out.append("")
    out.append("#### onlyDocumentskeepin")
    out.append("\n".join(only_doc) if only_doc else " (no) ")
    out.append("")
    out.append("#### onlyDBkeepin")
    out.append("\n".join(only_db) if only_db else " (no) ")
    return "\n".join(out)


def get_schema_by_table_name(table_name: str) -> str:
    """
    rootdatatablenamefrom profiler_db_data_format.md liftgetCorrespondingchaptersectioninsidecontent. 

    :param table_name: tablename, exampleif TASK / CANN_API / COMMUNICATION_OP. 
    """
    if not table_name:
        return "❌ errorerror: table_name notabilityasempty. "

    lines, err = _load_reference_doc()
    if err:
        return err

    sections = _extract_sections(lines)
    if not sections:
        return "❌ errorerror: Reference DocumentsmiddlenotParsetocanusechaptersection. "

    query_key = _canonical_key(table_name)
    exact_matches = []
    key_to_title = {}

    for sec in sections:
        title = sec["title"]
        title_key = _canonical_key(title)
        key_to_title[title_key] = title
        if title_key == query_key:
            exact_matches.append(sec)

    if not exact_matches:
        candidates = sorted(set(key_to_title.keys()))
        similar = difflib.get_close_matches(query_key, candidates, n=5, cutoff=0.5)
        if similar:
            tips = ", ".join(similar)
            return f"❌ notfindtotable `{table_name}`. youcanabilitydesiresearch: {tips}"
        return f"❌ notfindtotable `{table_name}`. canfirstExecute --list_tables searchseeDocumentsinsidecanusetablename. "

    sec = exact_matches[0]
    start = sec["start"]
    end = sec["end"]
    section_text = "\n".join(lines[start:end]).strip()

    out_lines = []
    out_lines.append("⚠️ ** [Track B tableStructureReference (from profiler_db_data_format.md) ] **")
    out_lines.append(f"### tablename: `{_canonical_key(sec['title'])}`")
    out_lines.append("")
    out_lines.append(section_text)
    return "\n".join(out_lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="according totablenameQuery msprof db DocumentsmiddleoftableStructureDescription")
    parser.add_argument(
        "--db_path",
        type=str,
        help="canselect, itemstandard sqlite db Path; Used forcolumntablenameorDocuments/DB Compare",
    )
    parser.add_argument(
        "--table_name",
        type=str,
        help="itemstandardtablename, exampleif TASK / CANN_API / COMMUNICATION_OP",
    )
    parser.add_argument(
        "--list_tables",
        action="store_true",
        help="columnoutput profiler_db_data_format.md middlecanQueryoftablename",
    )
    parser.add_argument(
        "--list_db_tables",
        action="store_true",
        help="columnoutputitemstandard db middleactualactualkeepinoftablename (needmatchmatch --db_path) ",
    )
    parser.add_argument(
        "--compare_doc_db",
        action="store_true",
        help="CompareDocumentstablenameanditemstandard db tablename (needmatchmatch --db_path) ",
    )

    args = parser.parse_args(argv)

    if args.list_db_tables:
        if not args.db_path:
            print("❌ errorerror: --list_db_tables requiressametimeProvides --db_path")
            return
        print(list_db_tables(args.db_path))
        return

    if args.compare_doc_db:
        if not args.db_path:
            print("❌ errorerror: --compare_doc_db requiressametimeProvides --db_path")
            return
        print(compare_doc_with_db(args.db_path))
        return

    if args.list_tables:
        print(list_documented_tables())
        return

    if args.table_name:
        print(get_schema_by_table_name(args.table_name))
        return

    print("❌ errorerror: pleaseProvides --table_name <tablename>, orUsage --list_tables")


if __name__ == "__main__":
    main(sys.argv[1:])
