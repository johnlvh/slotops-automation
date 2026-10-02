# ==============================================================================
# Author       : John
# Description  : SlotOps Config Validation & Change-Impact Pipeline entry point.
# ==============================================================================

import argparse
import logging
import sys

from slotops import (
    generate_code,
    print_comparison_report,
    run_batch_validation,
    validate_rules,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logging.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_full_pipeline(strict: bool = False) -> int:
    logger.info("="*69)
    logger.info("SLOTOPS CONFIG VALIDATION & CHANGE-IMPACT PIPELINE")

    logger.info("="*69)
    logger.info("[Phase 1/4] Generating validator from rules...")
    generate_code()

    logger.info("="*69)
    logger.info("[Phase 2/4] Validating rules & config template...")
    if not validate_rules():
        return 1

    logger.info("="*69)
    logger.info("[Phase 3/4] Semantic change-impact comparison (V1 vs V2)...")
    print_comparison_report(
        "configs/v1/slot_cleopatra_001.json",
        "configs/v2/slot_cleopatra_001.json",
    )

    logger.info("="*69)
    logger.info("[Phase 4/4] Batch validation on configs/v2...")
    stats = run_batch_validation("configs/v2")

    if strict and stats["errors"] > 0:
        logger.error("Strict mode: %d config(s) with ERROR — failing.", stats["errors"])
        return 1

    logger.info("="*69)
    logger.info("Pipeline completed successfully.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="SlotOps validation pipeline")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any config has ERROR (use in CI).",
    )
    args = parser.parse_args()
    sys.exit(run_full_pipeline(strict=args.strict))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unexpected failure!")
        sys.exit(2)
