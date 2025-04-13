# beforeiplay-scraper

A command-line Python tool that scrapes game pages from [beforeiplay.com](https://beforeiplay.com) and saves them as clean, well-formatted Markdown files.

## ✨ Features

- Converts HTML content to Markdown using `markdownify`
- Organizes game files into alphabetized subfolders
- Skips already-saved pages to avoid redundant downloads
- Supports request delay and randomization for polite scraping
- Allows filtering by game title starting letter

## 🚀 Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/glimgeist/beforeiplay-scraper
   cd beforeiplay-scraper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🛠 Usage

```bash
python beforeiplay_scraper.py [options]
```

### Options:

| Option               | Description                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `--limit`            | Limit the number of games to scrape (e.g. `--limit 10`)                     |
| `--output-dir`       | Directory where Markdown files are saved (default: `scraped_games`)         |
| `--delay`            | Delay (in seconds) between requests (default: `1.0`)                        |
| `--randomize-delay`  | Randomizes delay to mimic human browsing (optional flag)                    |
| `--letter` / `-l`    | Only process games starting with a specific letter (e.g. `-l A`, `-l 0`)    |

### Example:

```bash
python beforeiplay_scraper.py --limit 50 --delay 2 --randomize-delay --output-dir output --letter M
```

## 🧾 Output

Markdown files are saved under subdirectories named `A`, `B`, ..., `Z`, `0-9`, or `_` (for special characters), organized based on the game title.

## 📦 Dependencies

- `requests`
- `lxml`
- `markdownify`

Install all via:

```bash
pip install -r requirements.txt
```

## ⚖ License

[MIT License](LICENSE)
