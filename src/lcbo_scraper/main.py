# ==============================================================================
#  Copyright 2025 Matthew Pounsett <matt@conundrum.com>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ==============================================================================
"""CLI entry point for LCBO scraper."""

import argparse
import logging
import sys

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from lcbo_scraper import __version__
from lcbo_scraper.scraper import LcboScraper

logger = logging.getLogger(__name__)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="lcbo-scraper",
        description="Search LCBO.com for products and retrieve product information.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-n",
        "--number",
        action="append",
        dest="numbers",
        metavar="PRODUCT_NUMBER",
        help="Product number to search for. Can be specified multiple times.",
    )
    parser.add_argument(
        "-p",
        "--print",
        action="store_true",
        dest="print_table",
        help="Print a table of results to stdout.",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output YAML file path. Use '-' for stdout.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity. Use -vv for debug output.",
    )

    return parser.parse_args(args)


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbosity: Verbosity level (0=warning, 1=info, 2+=debug).
    """
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def print_results_table(products: list, console: Console) -> None:
    """Print a Rich table of product results.

    Args:
        products: List of Product instances.
        console: Rich console for output.
    """
    table = Table(title="LCBO Products")
    table.add_column("Product #", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Price", style="yellow")
    table.add_column("URL", style="blue")

    for product in products:
        table.add_row(
            product.product_number,
            product.name or "Not found",
            product.price or "-",
            product.url or "-",
        )

    console.print(table)


def output_yaml(products: list, output_path: str) -> None:
    """Output product data as YAML.

    Args:
        products: List of Product instances.
        output_path: File path or '-' for stdout.
    """
    data = [product.model_dump() for product in products]

    if output_path == "-":
        yaml.dump(data, sys.stdout, default_flow_style=False, sort_keys=False, allow_unicode=True)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        logger.info("Output written to: %s", output_path)


def main(args: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        args: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parsed_args = parse_args(args)
    setup_logging(parsed_args.verbose)

    if not parsed_args.numbers:
        logger.error("No product numbers specified. Use -n PRODUCT_NUMBER.")
        return 1

    console = Console()
    products = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    )

    total = len(parsed_args.numbers)
    with progress, LcboScraper() as scraper:
        for index, product_number in enumerate(parsed_args.numbers, start=1):
            task = progress.add_task(
                f"[{index}/{total}] Searching for product {product_number}...", total=1
            )
            logger.info("Searching for product: %s", product_number)
            product = scraper.get_product(product_number)
            products.append(product)
            progress.update(task, completed=1)

            if product.name:
                logger.info("Found: %s", product.name)
            else:
                logger.warning("Product not found: %s", product_number)

    if parsed_args.print_table:
        print_results_table(products, console)

    if parsed_args.output:
        output_yaml(products, parsed_args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
