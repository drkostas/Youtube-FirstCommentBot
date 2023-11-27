from bs4 import BeautifulSoup
import requests
import pprint as pp


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'

urls_file = 'channels_likes.csv'
ids_file = 'channels_likes.txt'

with open(urls_file, 'r') as f:
    urls = f.readlines()
open(ids_file, 'w').close()

for url in urls:
    url, likes = url.replace('\n', '').split(',')
    ch_id = None
    response = requests.get(url, headers={'User-Agent':USER_AGENT})
    soup = BeautifulSoup(response.text, 'lxml')
    for meta in soup.find_all("meta", {"property": "og:url"}):
        ch_id = meta['content'].split('/')[-1]
        with open(ids_file, 'a') as f:
            f.write(f"{ch_id},{likes}\n")
        break
    if ch_id is None:
        print(url)