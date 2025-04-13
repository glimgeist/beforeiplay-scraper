import requests
import os
import re
import argparse
from lxml import html
from markdownify import markdownify
import time
import random

BASE_URL = "https://beforeiplay.com"
INDEX_URL = f"{BASE_URL}/index.php?title=Category:Games"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_html(url):
    """Fetches HTML content from a URL and returns a parsed lxml tree."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        # Explicitly decode using UTF-8, common for web pages
        response.encoding = 'utf-8'
        tree = html.fromstring(response.text)
        return tree
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing HTML from {url}: {e}")
        return None

def get_game_links(index_url, limit=None):
    """Extracts game page links from the index URL."""
    print(f"Fetching game index from: {index_url}")
    tree = fetch_html(index_url)
    if tree is None:
        return []

    # Select anchor tags within list items in the specified div
    # //div[@class="mw-category-group"]//li/a
    try:
        link_elements = tree.xpath('//div[@class="mw-category-group"]//li/a')
        game_links = []
        for link in link_elements:
            href = link.get('href')
            title = link.text_content() # Get title for progress display
            if href:
                full_url = BASE_URL + href
                game_links.append({"url": full_url, "title": title})

        print(f"Found {len(game_links)} potential game links.")

        if limit:
            print(f"Limiting to {limit} games.")
            return game_links[:limit]
        return game_links
    except Exception as e:
        print(f"Error extracting links using XPath: {e}")
        return []


def sanitize_filename(name):
    """Removes invalid characters for Windows filenames."""
    if not name:
        return "_unknown_game_"
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace potential problematic sequences like '..'
    name = re.sub(r'\.\.', '_', name)
    # Remove leading/trailing whitespace/dots
    name = name.strip('. ')
    # Replace spaces with underscores (optional, could also remove)
    # name = name.replace(' ', '_')
    # Limit length (Windows max path is ~260, leave room for directory structure)
    max_len = 100
    if len(name) > max_len:
        name = name[:max_len].rsplit(' ', 1)[0] # Try to cut at a space

    if not name: # Handle cases where sanitization results in an empty string
        return "_sanitized_empty_"
    return name

def save_game_page_as_markdown(game_info, base_dir):
    """Fetches a game page, converts its content to Markdown, and saves it.

    Returns:
        tuple: (success: bool, request_made: bool)
    """
    game_url = game_info["url"]
    original_title = game_info.get("title", "Unknown Title")

    # --- Pre-computation before checking existence ---
    # Determine potential filename and path *before* fetching
    # We need this to check if the file exists
    # Try to get title from game_info first for filtering, fallback to placeholder
    temp_page_title = original_title # Use title from index link initially
    filename_safe_title = sanitize_filename(temp_page_title)

    first_char = filename_safe_title[0].upper() if filename_safe_title else '_'
    if '0' <= first_char <= '9':
        target_subdir = '0-9'
    elif 'A' <= first_char <= 'Z':
        target_subdir = first_char
    else:
        target_subdir = '_'

    output_dir = os.path.join(base_dir, target_subdir)
    output_filepath = os.path.join(output_dir, f"{filename_safe_title}.md")

    # Ensure the directory exists *before* checking the file
    os.makedirs(output_dir, exist_ok=True)

    # Check if file already exists to avoid re-scraping
    if os.path.exists(output_filepath):
        print(f"Skipping '{original_title}' ({game_url}), Markdown file already exists at {output_filepath}.")
        return True, False # Indicate success (already done), and no request was made

    # --- If file doesn't exist, proceed with fetching --- 
    print(f"Processing '{original_title}' ({game_url})...")
    tree = fetch_html(game_url)
    if tree is None:
        print(f"Skipping {original_title} due to fetch error.")
        return False, True # Indicate failure, but a request was attempted

    # --- Extract Actual Title and Content --- (Now we have the page)
    title_element = tree.xpath('//h1[@id="firstHeading"]/span/text()')
    page_title = title_element[0].strip() if title_element else original_title

    # Re-sanitize using the *actual* page title if different from the link title
    # This might change the filename slightly, but the existence check used the link title
    # which is usually sufficient. If title differs significantly, could lead to duplicates.
    # Consider if this re-sanitization is necessary or if we stick with the original.
    # Sticking with original might be safer to avoid path mismatches.
    # filename_safe_title = sanitize_filename(page_title)
    # output_filepath = os.path.join(output_dir, f"{filename_safe_title}.md")

    print(f"Actual page title: '{page_title}'") # Log the title found on the page

    # --- Convert Content to Markdown --- 
    content_elements = tree.xpath('//div[@id="mw-content-text"]/div[contains(@class, "mw-parser-output")]')
    if not content_elements:
         content_elements = tree.xpath('//div[@id="mw-content-text"]')

    if content_elements:
        content_html_bytes = html.tostring(content_elements[0], encoding='utf-8')
        content_html_str = content_html_bytes.decode('utf-8')
        markdown_content = markdownify(content_html_str, heading_style="ATX")
    else:
        print(f"Warning: Could not find main content area for '{page_title}'. Saving empty file.")
        markdown_content = f"# {page_title}\n\nContent could not be extracted."

    # --- Save Markdown File ---
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Saved: {output_filepath}")
        return True, True # Indicate success, and a request was made
    except IOError as e:
        print(f"Error saving file {output_filepath}: {e}")
        try:
            os.remove(output_filepath)
        except OSError:
            pass
        return False, True # Indicate failure, request was made
    except Exception as e:
        print(f"An unexpected error occurred during file write for {output_filepath}: {e}")
        return False, True # Indicate failure, request was made


def main():
    parser = argparse.ArgumentParser(description="Scrape game pages from beforeiplay.com and save as Markdown.")
    parser.add_argument("--limit", type=int, help="Limit the number of game pages to process (for testing).")
    parser.add_argument("--output-dir", default="scraped_games", help="Directory to save the markdown files.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between requests (default: 1.0).")
    parser.add_argument("--randomize-delay", action='store_true', help="Randomize delay slightly to mimic human behavior.")
    parser.add_argument("-l", "--letter", type=str, help="Only process games starting with this letter (e.g., 'A', 'B', or '0' for '0-9'). Case-insensitive.")

    args = parser.parse_args()

    # Normalize the letter argument
    target_letter_category = None
    if args.letter:
        args.letter = args.letter.strip().upper()
        if args.letter == '0':
            target_letter_category = '0-9'
        elif len(args.letter) == 1 and 'A' <= args.letter <= 'Z':
            target_letter_category = args.letter
        elif len(args.letter) == 1: # Handle symbols/other edge cases
            target_letter_category = '_'
        else:
            print(f"Warning: Invalid letter specified ('{args.letter}'). Processing all games.")

    print(f"Starting scraper. Output directory: '{args.output_dir}', Limit: {args.limit}, Delay: {args.delay}s")
    if target_letter_category:
        print(f"Filtering for letter/category: '{target_letter_category}'")
    os.makedirs(args.output_dir, exist_ok=True)

    # Get all links first, then filter if needed
    all_game_links = get_game_links(INDEX_URL, None) # Fetch all initially, limit applied later

    if not all_game_links:
        print("No game links found or error fetching index. Exiting.")
        return

    # Filter based on the letter argument
    if target_letter_category:
        filtered_links = []
        for game_info in all_game_links:
            original_title = game_info.get("title", "Unknown Title")
            filename_safe_title = sanitize_filename(original_title)
            if not filename_safe_title: continue # Skip if sanitization failed badly

            first_char = filename_safe_title[0].upper()
            current_category = ''
            if '0' <= first_char <= '9':
                current_category = '0-9'
            elif 'A' <= first_char <= 'Z':
                current_category = first_char
            else:
                current_category = '_'

            if current_category == target_letter_category:
                filtered_links.append(game_info)
        print(f"Filtered down to {len(filtered_links)} games for category '{target_letter_category}'.")
        game_links_to_process = filtered_links
    else:
        game_links_to_process = all_game_links

    # Apply the limit *after* filtering by letter if applicable
    if args.limit is not None:
         if len(game_links_to_process) > args.limit:
             print(f"Applying limit: processing first {args.limit} of {len(game_links_to_process)} games.")
             game_links_to_process = game_links_to_process[:args.limit]
         else:
             print(f"Limit ({args.limit}) is >= number of games ({len(game_links_to_process)}), processing all.")


    if not game_links_to_process:
         print("No games match the specified criteria after filtering. Exiting.")
         return

    processed_count = 0
    error_count = 0
    total_games = len(game_links_to_process) # Use the count of the list we'll iterate over

    print(f"Beginning processing for {total_games} games...")

    for i, game_info in enumerate(game_links_to_process):
        print(f"\n--- Processing game {i+1}/{total_games} ---")
        success, request_made = save_game_page_as_markdown(game_info, args.output_dir)
        if success:
            processed_count += 1
        else:
            error_count += 1

        # Respectful delay ONLY if a request was actually made
        if request_made and (i < total_games - 1):
            delay = args.delay
            if args.randomize_delay:
                delay = random.uniform(delay * 0.5, delay * 1.5)
            print(f"Waiting for {delay:.2f} seconds before next request...")
            time.sleep(delay)


    print(f"\n--- Scraping complete ---")
    print(f"Successfully processed: {processed_count} games")
    print(f"Errors encountered: {error_count} games")
    print(f"Markdown files saved in: '{args.output_dir}'")


if __name__ == "__main__":
    main()
