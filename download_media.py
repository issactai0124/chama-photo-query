import pandas as pd
import requests
import logging
import os
import asyncio
from playwright.async_api import async_playwright

# set logging to print to console
logger = logging.getLogger()
logger.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setLevel(level=logging.INFO)
formatter =  logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

def get_twitter_media(url):
    download_count = 0
    # API call to fxtwitter
    tweet_json = requests.get(url.replace("x.com", "api.fxtwitter.com")).json()
    if tweet_json.get("code") == 200:
        if tweet_json.get("tweet").get("media") is not None:
            # Download all medias
            for media in tweet_json.get("tweet").get("media").get("all"):
                try:
                    media_url = media.get("url")
                    media_type = media_url.split('.')[-1].split('?')[0]
                    with open(f"./media/x-{url.split("/")[-1]}_{download_count}.{media_type}", "wb") as f:
                        f.write(requests.get(media_url).content)
                    download_count = download_count + 1
                except Exception as e:
                    logging.error(f"[URL: {url}] Error downloading Twitter image: {e}")

            if download_count > 0:
                logging.info(f"[URL: {url}] {download_count} Image(s) saved to ./media.")
    else:
        logging.error(f"[URL: {url}] api.fxtwitter.com seems not working: {tweet_json}")
    return download_count

# Function to get all image URLs from a YouTube post using Playwright
async def get_youtube_post_images(url):
    async with async_playwright() as p:
        download_count = 0
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(5000)  # wait for full render

        image_elements = await page.query_selector_all("img")
        for img in image_elements:
            try:
                src = await img.get_attribute("src")
                if src and "https" in src:
                    # check if src contains "=s1024"
                    if "=s1024" in src:
                        # replace s1024 with s0 to get original size
                        media_url = src.replace("=s1024", "=s0")
                        with open(f"./media/yt-{url.split("/")[-1]}_{download_count}.webp", "wb") as f:
                            f.write(requests.get(media_url).content)
                        download_count = download_count + 1
            except Exception as e:
                logging.error(f"[URL: {url}] Error downloading YT image: {e}")

        if download_count > 0:
            logging.info(f"[URL: {url}] {download_count} Image(s) saved to ./media.")

        await browser.close()
    return download_count

def download_media(url, post_type):
    download_count = 0
    if post_type == "twitter":
        download_count = get_twitter_media(url)
    elif post_type == "youtube_post":
        download_count = asyncio.run(get_youtube_post_images(url))
    else:
        logging.error(f"[URL: {url}] Unknown post type: {post_type}. Skipping download.")
    return download_count

def main():
    download_count = 0

    # read files in ./media
    os.makedirs('./media', exist_ok=True)
    files = os.listdir('./media') 
    logging.info(f"Found {len(files)} files in ./media")

    # get file_ids from filenames: remove extension and the last 2 characters from filenames
    file_ids = set([os.path.splitext(f)[0][:-2] for f in files])

    # read the CSV file into a DataFrame
    df = pd.read_csv('data.csv', sep='\t')

    logging.info(f"Step 1: Starting to download images...")
    for url in df['links'].tolist():
        post_type = "unknown"
        post_id = ""
        # check if url is Twitter
        if url.find("x.com") != -1:
            post_id = "x-" + url.split("/")[-1]
            post_type = "twitter"
        elif url.find("youtube.com/post") != -1:
            post_id = "yt-" + url.split("/")[-1]
            post_type = "youtube_post"

        if post_type != "unknown":
            if post_id in file_ids:
                logging.debug(f"[URL: {url}] {post_id} already exists in ./media. Skipping download.")
            else:
                download_count = download_count + download_media(url, post_type)

    logging.info(f"Step 1 completed. Downloaded {download_count} media files to ./media.")

if __name__ == "__main__":
    main()