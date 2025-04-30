import aiohttp
import asyncio
import boto3
import datetime
import json
import logging
import mimetypes
import random

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from aiohttp import ClientConnectorSSLError, ClientError

from nlp_utils import (
    load_stopwords, rank_sentences, summarize_record, summarize_messages,
    clean_website_data
)


# User agents for web requests
USER_AGENTS = [
    # Chrome (Windows, macOS, Linux)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    # Firefox (Windows, macOS, Linux)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:93.0) Gecko/20100101 Firefox/93.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0",
    # Safari (macOS, iOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Version/14.1.2 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.64",
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.277",
    # Mobile Browsers (Android, iOS)
    "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Pixel 4 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Mobile/15E148 Safari/604.1"
]

def upload_document_to_s3(document_content, content_type, document_url):
    document_extension = mimetypes.guess_extension(content_type) or '.bin'
    s3_object_name = f"Document_{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}{document_extension}"

    # Upload to S3   
    s3_client = boto3.client('s3')
    s3_client.put_object(Body=document_content, Bucket=docs_bucket_name, Key=s3_object_name)

    # Construct the S3 URL  
    s3_url = f"https://{docs_bucket_name}.s3.amazonaws.com/{s3_object_name}"
    return s3_url

async def fetch_page(session, url, timeout=30):
    headers = {
        'User-Agent': random.choice(USER_AGENTS)
    }    
    try:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            #print(f"Search Result: {response}")
            content_type = response.headers.get('Content-Type', '')
            if 'text' in content_type:
                encoding = response.charset or 'utf-8'
                return await response.text(encoding=encoding)
            elif 'application/pdf' in content_type or 'application/msword' in content_type or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                return await response.read(), content_type
            else:
                return None, content_type
    except asyncio.TimeoutError:
        print(f"Timeout error: {url} took too long to respond.")
        return f"Timeout error: {url} took too long to respond.", None
    except ClientConnectorSSLError:
        print(f"SSL handshake error: Failed to connect to {url}")
        return f"SSL handshake error: Failed to connect to {url}", None 


async def process_page(session, url, semaphore, full_text=False):
    async with semaphore:
        try:
            result = await fetch_page(session, url)
        except ClientError as e:
            logging.error(f"Client error occurred while fetching the page: {e}")
            return [{
                "type": "text",
                "text": {
                    'url': url,
                    'error': 'Failed to fetch page due to client error'
                }
            }]
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
            return [{
                "type": "text",
                "text": {
                    'url': url,
                    'error': 'An unexpected error occurred while fetching the page'
                }
            }]
        
        response_list = []

        #print(f'Raw Result: {result}')
        try:
            if isinstance(result, tuple):
                document_content, content_type = result
                if document_content is not None and content_type is not None:
                    try:
                        s3_url = upload_document_to_s3(document_content, content_type, url)
                        response_list.append({
                            "type": "text",
                            "text": {
                                'url': url,
                                'summary': 'This file contains additional information for your search. Send it to the user.',
                                's3_url': s3_url
                            }
                        })
                    except Exception as e:
                        logging.error(f"Failed to upload document to S3: {e}")
                        response_list.append({
                            "type": "text",
                            "text": {
                                'url': url,
                                'error': 'Failed to upload document to S3'
                            }
                        })
                else:
                    response_list.append({
                        "type": "text",
                        "text": {
                            'url': url,
                            'error': 'Unsupported content type'
                        }
                    })
            elif isinstance(result, str) and 'Timeout error' not in result:
                soup = BeautifulSoup(result, 'lxml')

                elements_to_extract = ['p', 'li', 'summary', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'td', 'th', 'a']

                text = ' '.join(element.get_text().strip() for element in soup.find_all(elements_to_extract))
                cleaned_text = clean_website_data(text)

                if full_text:
                    summary_or_full_text = rank_sentences(cleaned_text, stopwords, max_sentences=150)  # Placeholder for the rank_sentences function
                else:
                    try:
                        summary_or_full_text = rank_sentences(cleaned_text, stopwords, max_sentences=50)  # Placeholder for the rank_sentences function
                    except Exception as e:
                        logging.error(f"Failed to rank sentences: {e}")
                        summary_or_full_text = cleaned_text  # Fallback to full text if ranking fails

                author = soup.find('meta', {'name': 'author'})['content'] if soup.find('meta', {'name': 'author'}) else 'Unknown'
                date_published = soup.find('meta', {'property': 'article:published_time'})['content'] if soup.find('meta', {'property': 'article:published_time'}) else 'Unknown'

                links = []

                response_list.append({
                    "type": "text",
                    "text": {
                        'summary_or_full_text': summary_or_full_text,
                        'author': author,
                        'date_published': date_published,
                        'internal_links': links
                    }
                })

                images = soup.select('article img') + soup.select('figure img') + soup.select('section img')
                
                for img in images:
                    img_url = img.get('src')
                    if img_url:
                        # Skip data URIs and other non-HTTP/HTTPS sources
                        if img_url.startswith('data:'):
                            #logging.warning(f"Skipping data URI image: {img_url[:30]}...")  # Log a warning and skip data URIs
                            continue
                        if not img_url.startswith(('http://', 'https://')):
                            img_url = urljoin(url, img_url)
                        
                        try:
                            async with session.head(img_url) as img_response:
                                if img_response.status == 200 and int(img_response.headers.get('Content-Length', 0)) > 10240:
                                    response_list.append({
                                        "type": "image_url",
                                        "image_url": {
                                            'url': img_url
                                        }
                                    })
                        except ClientError as e:
                            logging.error(f"Failed to fetch image: {img_url} - ClientError: {e}")
                        except Exception as e:
                            logging.error(f"Failed to fetch image: {img_url} - Unexpected error: {e}")
            else:
                response_list.append({
                    "type": "text",
                    "text": {
                        'url': url,
                        'error': result
                    }
                })
        except Exception as e:
            logging.error(f"Error processing page: {e}")
            response_list.append({
                "type": "text",
                "text": {
                    'url': url,
                    'error': 'An error occurred while processing the page'
                }
            })

        return response_list


async def get_web_pages(urls, full_text=False, max_concurrent_requests=5):
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(max_concurrent_requests)
        tasks = [process_page(session, url, semaphore, full_text) for url in urls]
        results = await asyncio.gather(*tasks)
        
        # Flatten the list of results
        flattened_results = [item for sublist in results for item in sublist]
        print(json.dumps(flattened_results))
        
        return flattened_results


def browse_internet(urls, full_text=False):
    web_pages = asyncio.run(get_web_pages(urls, full_text))
    print(web_pages)
    return web_pages


if __name__ == "__main__":
    import sys

    # EXAMPLE USAGE: python yourfile.py https://www.wikipedia.org

    # If you expect **multiple URLs**, collect all arguments after the filename
    if len(sys.argv) < 2:
        print("USAGE: python", sys.argv[0], "<url1> [<url2> ...]")
        sys.exit(1)

    urls = sys.argv[1:]  # list of URLs from the command line

    # Optionally, set full_text = True by adding a flag argument
    # e.g., python script.py https://... --fulltext
    full_text = False
    if '--fulltext' in urls:
        full_text = True
        urls.remove('--fulltext')

    browse_internet(urls, full_text=full_text)