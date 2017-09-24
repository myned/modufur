import requests
from bs4 import BeautifulSoup
from lxml import html
from misc import exceptions as exc

def check_match(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    value = soup.find_all('a')[1].get('href')
    if value != '#':
        return value
    else:
        raise exc.MatchError(value)

def find_pool(url):
    r = requests.get(url)
    tree = html.fromstring(r.content)
    post = tree.xpath('/html/body/div[@id="content"]/div[@id="pool-show"]/div[@style="margin-top: 2em;"]/span/a/@href')
    print(post)
    if post:
        return post
    else:
        raise exc.PostError(post)

def find_image_url(url):
    r = requests.get(url)
    tree = html.fromstring(r.content)
    image_url = tree.xpath('/html/body/div[@id="content"]/div[@id="post-view"]/div[@class="content"]/div/img/@src')
    print(image_url)
    if image_url:
        return image_url
    else:
        raise exc.ImageError(image_url)
