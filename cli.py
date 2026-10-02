# ==============================================================================
# Author       : John
# Description  : Ad-hoc CLI — compare 2 configs, validate a folder or a file.
#                Requires the validator to be generated first (python pipeline.py).
# ==============================================================================

import argparse
import logging
import sys

from slotops import print_comparison_report, run_batch_validation, validate_file

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logging.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def cmd_compare(args: argparse.Namespace) -> int:
    print_comparison_report(args.file1, args.file2)
    return 0


def cmd_validate_folder(args: argparse.Namespace) -> int:
    stats = run_batch_validation(args.folder)
    return 1 if stats["errors"] > 0 else 0


def cmd_validate_file(args: argparse.Namespace) -> int:
    try:
        issues = validate_file(args.file)
    except FileNotFoundError:
        logger.error("File not found: %s", args.file)
        return 2

    if not issues:
        logger.info("✓ PASS — %s", args.file)
        return 0

    logger.warning("✗ FAIL — %s (%d issue(s))", args.file, len(issues))
    for i in issues:
        logger.warning("  ↳ %s | %s (%s): %s",
                       i["severity"], i["rule_id"], i["field"], i["message"])
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="slotops", description="SlotOps ad-hoc tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("compare", help="Diff two config files")
    p1.add_argument("file1")
    p1.add_argument("file2")
    p1.set_defaults(fn=cmd_compare)

    p2 = sub.add_parser("validate-folder", help="Batch-validate every *.json in a folder")
    p2.add_argument("folder")
    p2.set_defaults(fn=cmd_validate_folder)

    p3 = sub.add_parser("validate-file", help="Validate a single config file")
    p3.add_argument("file")
    p3.set_defaults(fn=cmd_validate_file)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
