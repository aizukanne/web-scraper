# Web Scraper & NLP Summarizer

## Project Overview

This project is an asynchronous web scraper and natural language processing (NLP) toolkit. It fetches web pages, processes their content, and applies NLP techniques such as text cleaning and summarization using a customizable stopwords list. The system supports concurrent scraping, robust error handling, and can upload processed documents to AWS S3.

---

## Features

- **Asynchronous web scraping** with `aiohttp` and `asyncio`
- **HTML parsing** using `BeautifulSoup`
- **NLP utilities** for text cleaning, sentence ranking, and summarization
- **Customizable stopwords** (provided in the `english` file)
- **Upload to AWS S3** for processed documents
- **Support for multiple output formats** (CSV, JSON, Excel, etc.)
- **Robust error handling and logging**

---

## Installation

### Dependencies

- Python 3.8+
- aiohttp
- boto3
- beautifulsoup4
- nltk
- openpyxl
- requests

### Installation Steps

```bash
pip install aiohttp boto3 beautifulsoup4 nltk openpyxl requests
```

(Optional) Download NLTK data if not already present:
```python
import nltk
nltk.download('punkt')
```

---

## Usage

### Example: Scraping and Summarizing Web Pages

```python
from browser import browse_internet

urls = [
    "https://example.com/article1",
    "https://example.com/article2"
]
results = browse_internet(urls, full_text=True)
print(results)
```

- To upload results to S3, configure your AWS credentials and use the `upload_document_to_s3` function.
- To customize stopwords, edit the `english` file.

---

## File Descriptions

- **browser.py**: Main entry point. Handles web scraping, orchestrates concurrent requests, processes pages, and manages uploads to S3. Imports NLP utilities from `nlp_utils.py`.
- **nlp_utils.py**: Provides NLP functions: loading stopwords, ranking sentences, summarizing records/messages, and cleaning website data.
- **english**: A plain text file containing English stopwords, one per line, used by NLP utilities.

---

## API Documentation

### browser.py

#### `upload_document_to_s3(document_content, content_type, document_url)`
Uploads a document to AWS S3 and returns the S3 URL.

- **Parameters:**
  - `document_content` (bytes): The content of the document to upload.
  - `content_type` (str): The MIME type of the document.
  - `document_url` (str): The original URL of the document.
- **Returns:** `str` — The S3 URL of the uploaded document.

#### `async process_page(session, url, semaphore, full_text=False)`
Processes a single web page: fetches, parses, summarizes, and extracts images.

- **Parameters:**
  - `session` (aiohttp.ClientSession): The HTTP session.
  - `url` (str): The URL to process.
  - `semaphore` (asyncio.Semaphore): Controls concurrency.
  - `full_text` (bool): If True, returns more text; otherwise, returns a summary.
- **Returns:** `list` — List of dictionaries with text summaries and image URLs.

#### `async fetch_page(session, url, timeout=30)`
Fetches a web page asynchronously.

- **Parameters:**
  - `session` (aiohttp.ClientSession): The HTTP session.
  - `url` (str): The URL to fetch.
  - `timeout` (int): Timeout in seconds.
- **Returns:** `str` (HTML content) or `(bytes, str)` (for binary files and content type).

#### `async get_web_pages(urls, full_text=False, max_concurrent_requests=5)`
Fetches and processes multiple web pages concurrently.

- **Parameters:**
  - `urls` (list): List of URLs to process.
  - `full_text` (bool): If True, returns more text; otherwise, returns a summary.
  - `max_concurrent_requests` (int): Maximum concurrent requests.
- **Returns:** `list` — Flattened list of results.

#### `browse_internet(urls, full_text=False)`
Synchronous wrapper for scraping and processing web pages.

- **Parameters:**
  - `urls` (list): List of URLs to process.
  - `full_text` (bool): If True, returns more text; otherwise, returns a summary.
- **Returns:** `list` — List of processed results.

---

### nlp_utils.py

#### `load_stopwords(file_path)`
Loads stopwords from a given file.

- **Parameters:**
  - `file_path` (str): Path to the stopwords file.
- **Returns:** `set` — Set of stopwords.

#### `rank_sentences(text, stopwords, max_sentences=10)`
Ranks sentences in the text based on word frequency, returning the top `max_sentences` sentences.

- **Parameters:**
  - `text` (str): The input text.
  - `stopwords` (set): Set of stopwords to ignore.
  - `max_sentences` (int): Number of sentences to return.
- **Returns:** `str` — Summary composed of the top-ranked sentences.

#### `summarize_record(record, stopwords)`
Summarizes a single message record while maintaining key points and brevity.

- **Parameters:**
  - `record` (str): Record in the format `'sort_key: chat_id: role: message'`.
  - `stopwords` (set): Set of stopwords to ignore.
- **Returns:** `dict` — Dictionary with summarized message and metadata.

#### `summarize_messages(data)`
Summarizes messages from a dictionary and returns a dictionary with the summarized conversation.

- **Parameters:**
  - `data` (list): List of message dictionaries.
- **Returns:** `list` — List of summarized records.

#### `clean_website_data(raw_text)`
Cleans up raw website text data, removing common HTML artifacts and excess whitespace.

- **Parameters:**
  - `raw_text` (str): Raw HTML/text content.
- **Returns:** `str` — Cleaned text.

---

## Configuration & Customization

- **Stopwords:**  
  Edit the `english` file to change the stopwords used for NLP.
- **Concurrency:**  
  Adjust `max_concurrent_requests` in `get_web_pages`.
- **User Agents:**  
  Modify the `USER_AGENTS` list in `browser.py` for different scraping profiles.
- **AWS S3:**  
  Ensure your AWS credentials are set up for S3 uploads.

---

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Add your changes and tests.
4. Submit a pull request.

---

## License

[Specify your license here, e.g., MIT, Apache 2.0, etc.]