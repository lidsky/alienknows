import HTMLParser
import nltk
from ftfy import fix_text
from urlparse import urlparse, urljoin

STRING_LITERAL = ['\n', '\\']
htmlParser = HTMLParser.HTMLParser()


def get_og_property(soup, og_prop, deep=False):
    if soup:
        if deep:
            nodes = soup.find_all('meta', {'property': 'og:' + og_prop})
            return [get_content_from_node(node) for node in nodes]
        else:
            node = soup.find('meta', {'property': 'og:' + og_prop})
            return get_content_from_node(node)
    return ''

def get_twitter_property(soup, tw_prop):
    if soup:
        node = soup.find('meta', {'name': 'twitter:' + tw_prop})
        return get_content_from_node(node)
    return ''

def get_meta_property(soup, meta_prop):
    if soup:
        node = soup.find('meta', {'name': meta_prop})
        return get_content_from_node(node)
    return ''

def get_content_from_node(node):
    if node:
        content = node.get('content')
        if content:
            return clean_html(content)
    return None

def is_valid_url(url):
    parsed = urlparse(url)
    return (parsed.scheme == 'http' or parsed.scheme == 'https') and parsed.netloc and len(parsed.netloc.split('.')) > 1

def get_root_url(url):
    parsed = urlparse(url)
    return parsed.scheme + '://' + parsed.netloc

def clean_html(html_string):
    """
    strip html tags and escape html char
    """

    #get rid of html tags using
    text = nltk.clean_html(html_string)
    #replace trash char
    for char in STRING_LITERAL:
        text.replace(char, '')

    # text = fix_text(text) #exclude this for the time being for getting this error: UnicodeError: Hey wait, this isn't Unicode.
    text = htmlParser.unescape(text)
    return text
