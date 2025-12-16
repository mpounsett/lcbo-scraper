# LCBO Scraper

A command-line tool to search and retrieve product information from the LCBO (Liquor Control Board of Ontario) website.

## Features

- Search for products by LCBO product number
- Retrieve product name, price, URL, and detailed attributes
- Output results as a formatted table or YAML
- Support for multiple product lookups in a single command
- Progress indicator for batch operations

## Requirements

- Python 3.14+

## Installation

```bash
pip install .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

Search for a product by number:

```bash
lcbo-scraper -n 12345
```

Search for multiple products:

```bash
lcbo-scraper -n 12345 -n 67890 -n 11111
```

Print results as a table:

```bash
lcbo-scraper -n 12345 -p
```

Output results to a YAML file:

```bash
lcbo-scraper -n 12345 -o products.yaml
```

Output YAML to stdout:

```bash
lcbo-scraper -n 12345 -o -
```

Increase verbosity for debugging:

```bash
lcbo-scraper -n 12345 -v    # Info level
lcbo-scraper -n 12345 -vv   # Debug level
```

### Options

| Option | Description |
|--------|-------------|
| `-n`, `--number` | Product number to search for (can be specified multiple times) |
| `-p`, `--print` | Print a table of results to stdout |
| `-o`, `--output` | Output YAML file path (use `-` for stdout) |
| `-v`, `--verbose` | Increase verbosity (use `-vv` for debug) |
| `--version` | Show version number |

## Output Format

### Table Output (`-p`)

```
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Product #  ┃ Name               ┃ Price   ┃ URL                     ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 12345      │ Example Wine       │ $19.95  │ https://www.lcbo.com/...│
└────────────┴────────────────────┴─────────┴─────────────────────────┘
```

### YAML Output (`-o`)

```yaml
- product_number: '12345'
  name: Example Wine
  url: https://www.lcbo.com/en/example-wine-12345
  price: $19.95
  details:
    Country: France
    Region: Bordeaux
    Varietal: Cabernet Sauvignon
```

## Development

Run linting:

```bash
tox -e ruff
```

Run tests:

```bash
tox
```

## License

Copyright © 2025, Matthew Pounsett <matt@conundrum.com>
Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
