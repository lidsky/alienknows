import praw
import requests
import wikipedia
from bs4 import BeautifulSoup
import pyteaser
import HTMLParser
import unicodedata
import urllib2
from boilerpipe.extract import Extractor
from util import get_og_property, get_meta_property, get_twitter_property, htmlParser, is_valid_url
from pprint import pprint
import tldextract
from urlparse import urlparse
import datetime
import calendar
import inflection
import nltk
import json

from pymongo import MongoClient


'''
gif preview (show 1st frame):
1. https://gist.github.com/BigglesZX/4016539#file-gifextract-py-L68
2. http://stackoverflow.com/questions/1412529/how-do-i-programmatically-check-whether-a-gif-image-is-animated


todo:
content-page (full preview and comments)

'''

REQUEST_HEADER = { 'User-Agent': 'alienknows.com summarizer' }
REDDIT_USER_AGENT = 'plz_hire_me_reddit bot (reddit internship application, email:hmr1)'
USERNAME = 'plz_hire_me_reddit'
PASSWORD = '****'



def database_connect():
    client = MongoClient('mongodb://localhost/alienknows-dev')
    db = client['alienknows-dev']
    return db

def article_collection():
    db = database_connect()
    return db.articles


def article_from_db(article_id):
    article = article_collection()
    return article.find_one({'submission_id': article_id})


def website_collection():
    """
    Store domain data to be check against for description_preview
    schema:
    {
        'website': String,
        'title': String,
        'description': String 
    }
    """
    db = database_connect()
    return db.websites


def insert_website_data(collection_obj, website_url, title, description):
    new_website = {'website': website_url, 'title': title, 'description': description}
    print '\nSaving website data: '
    pprint(new_website)
    website_id = collection_obj.insert(new_website)
    print 'Saved website data with id: ', website_id , '\n'
    return


def query_website_data(website_url):
    websites = website_collection()
    website_data = websites.find_one({'website':website_url})
    if website_data:
        print '\ndebugging, website data: '
        pprint(website_data)
        print '\n'
        return website_data['title'], website_data['description']
    else:
        soup = soupify_page(url=website_url)
        title = get_metadata_title(soup)
        description = get_metadata_description(soup)
        insert_website_data(websites, website_url, title, description)
        return title, description


def database_save(collection, article):
    print '\nsaving the following article: '
    pprint(article)
    article_id = collection.insert(article)
    print 'Saved ', article_id, '\n'
    return


def init_praw():
    """
    initalize Reddit object
    """
    reddit = praw.Reddit(user_agent=REDDIT_USER_AGENT)
    reddit.login(USERNAME, PASSWORD)
    return reddit

def get_submissions(reddit_obj, subreddit='', sorting_type='hot', limit=1000):
    """
    returns array of submission instaces
    """
    subreddit_sorting = {
        'top': 'get_top',
        'controversial': 'get_controversial',
        'hot': 'get_hot',
        'new': 'get_new'
    }
    if subreddit:
        subreddit = reddit_obj.get_subreddit(subreddit)
    # ref: http://stackoverflow.com/questions/3061/calling-a-function-from-a-string-with-the-functions-name-in-python
        submissions = getattr(subreddit, subreddit_sorting[sorting_type])(limit=limit)
    else:
        submissions = reddit_obj.get_content('http://www.reddit.com/', limit=limit)
    return [submission for submission in submissions]


def get_submission_content(submission):
    """
    returns a dict from submission instance containing data from the submission
    """
    #TODO: handle twitter post, ref: http://blog.hubspot.com/marketing/embed-social-media-posts-guide
    #TODO: if description_preview is empty and summary_preview is available, use first few sentences probably??
    #handle google translated page (or just skip it???)
    #TODO: if wikipedia, use first sentence as description, the rest as summary. Also include pcture if you can

    article = article_from_db(submission.id)
    if article:
        
        #debugggggggggggg
        print 'article already exist, reddit comment id:', submission.id
        print 'old upvote: ', article['value'], ' new upvote: ', get_submission_value(submission)
        print 'old comment: ', article['comment_number'], ' new comment: ', get_submission_comment_number(submission)
        
        article['value'] = get_submission_value(submission)
        article['comment_number'] = get_submission_comment_number(submission)
    else:
        print 'processing submission.id', submission.id
        response = ''
        soup = ''
        print 'opening page'
        response = open_page(submission.url)
        if response:
            print 'soupifying page'

            #if type is not text, will stuck at response.text
            if 'content-type' in response.headers:
                if 'text/html' in response.headers['content-type']:
                    soup = soupify_page(html_text=response.text)
        # if soup:

        submission_data = {}

        print 'page domain data'
        domain_title, domain_description = get_domain_data(submission.url)

        submission_data['title'] = get_submission_title(submission)
        page_url = get_submission_url(submission)

        submission_data['url'] = page_url
        submission_data['value'] = get_submission_value(submission)
        submission_data['comment_number'] = get_submission_comment_number(submission)
        submission_data['comment_url'] = get_submission_comment_url(submission)


        print 'page video'
        video_preview = get_submission_video_preview(submission, soup)
        submission_data['video_preview'] = video_preview
        
        print 'page picture'
        submission_data['picture_preview'] = get_submission_picture_preview(submission, soup, video_preview)

        submission_data['self_post_preview'] = get_submission_self_post_preview(submission)

        print 'page title'
        title = get_page_title(soup, domain_title)

        print 'page description'
        description = get_submission_description_preview(submission, soup, title, domain_description)
        submission_data['description_preview'] = description
        summary_target_test = title + ' ' + description

        print 'page summary_preview'
        submission_data['summary_preview'] = get_submission_summary_preview(submission, summary_target_test, title, response)

        submission_data['comment_preview'] = get_submission_comment_preview(submission)
        submission_data['created_utc'] = submission.created_utc
        submission_data['submission_id'] = submission.id
        submission_data['saved_utc'] = get_utc_now()

        return submission_data

    return {}

def get_submission_title(submission):
    decode_html = HTMLParser.HTMLParser()
    return decode_html.unescape(submission.title)

def get_submission_url(submission):
    return submission.url

def get_submission_value(submission):
    #TODO: get facebook and twitter likes/shares/retweets
    return submission.score

def get_submission_comment_number(submission):
    return submission.num_comments

def get_submission_comment_url(submission):
    return submission.permalink

def get_preview_selftext(submission):
    #TODO: summarize/shorten the content if it's too long
    if not submission.selftext:
        return ''
    raw_html = unescape_html(submission.selftext_html)
    soup = soupify_page(html_text=raw_html)
    soup = normalize_html_text(soup, 'http://www.reddit.com/')
    return str(soup)

def get_utc_now():
    now = datetime.datetime.utcnow()
    return calendar.timegm(now.utctimetuple())

def get_page_title(soup, domain_title):
    title = get_metadata_title(soup)
    if title:
        if title != domain_title:
            return title
    return ''

def insert_target_blank(soup):
    if soup:
        for tag in soup.find_all('a'):
            tag['target'] = '_blank'
    return soup


def relative_to_absolute_soup(soup, domain_url):
    if soup:
        for tag in soup.find_all('a'):
            if 'href' in tag.attrs:
                tag.attrs['href'] = relative_to_absolute(tag.attrs['href'], domain_url)
    return soup

def normalize_html_text(soup, domain_url):
    if soup and domain_url:
        soup = insert_target_blank(soup)
        soup = relative_to_absolute_soup(soup, domain_url)
    return soup


def unescape_html(html_text):
    decode_html = HTMLParser.HTMLParser()
    return decode_html.unescape(html_text)


def is_wikipedia(submission):
    return 'wikipedia.org' in submission.domain


def get_wikipedia_obj(url):
    wikipedia_obj = ''
    if len(url.split('/wiki/')) < 2 :
        print 'in get_preview_wikipedia, cannot get page url for wiki api:'
        print url
        return ''
    page_url_title = url.split('/wiki/')[1].split('#')[0]
    #NOTE: was giving "KeyError: u'fullurl"
    #solution ref: http://stackoverflow.com/questions/8136788/decode-escaped-characters-in-url
    page_url_title_unquote = urllib2.unquote(page_url_title)
    try:
        wikipedia_obj = wikipedia.page(page_url_title_unquote)
    except:
        print 'problem in get_preview_wikipedia, wikipedia_url: ', url
        pass
    return wikipedia_obj    



def manual_wikipedia_preview(wikipedia_url):
    soup = soupify_page(url=wikipedia_url)
    parent_tag = soup.find(id='mw-content-text')
    if parent_tag:
        p_tags = parent_tag.find_all_next('p')
        if p_tags:
            summary_list = p_tags[:min(len(p_tags), 3)]
            summary_temp = ' '.join([p.get_text() for p in summary_list]).split('.')
            return '.'.join(summary_temp[:min(len(summary_temp), 3)]) + '.'
    print 'failed to manually retreive wikipedia page, url: ', wikipedia_url
    return ''


def get_preview_wikipedia(wikipedia_url):
    wikipedia_obj = get_wikipedia_obj(wikipedia_url)
    if not wikipedia_obj:
        return manual_wikipedia_preview(wikipedia_url)

    wikipedia_title, wikipedia_summary = wikipedia_obj.title, wikipedia_obj.summary
    sentence_num = min(len(wikipedia_summary.split('.')), 3)
    wikipedia_snippet = wikipedia_summary.split('.')[:sentence_num]
    primary_preview = '. '.join(wikipedia_snippet)

    # check for wikipedia subsection
    if '#' not in wikipedia_url:
        return primary_preview

    wikipedia_subsection = wikipedia_url.split('/wiki/')[1].split('#')[1]
    soup = soupify_page(url=wikipedia_url)
    if not soup:
        return primary_preview

    subsection_tag = soup.find(id=wikipedia_subsection)
    if subsection_tag:
        wikipedia_subsection_title = subsection_tag.get_text()
        wikipedia_subsection_soup = subsection_tag.parent.findNextSibling('p')
        if not wikipedia_subsection_soup:
            return primary_preview
        [sup.extract() for sup in wikipedia_subsection_soup.find_all('sup')]
        wikipedia_subsection_text = wikipedia_subsection_soup.get_text()
        subsection_sentence_num = min(wikipedia_subsection_text.split('.'), 3)
        wikipedia_subsection_snippet = wikipedia_subsection_text.split('.')[:subsection_sentence_num]

        return '. '.join(wikipedia_subsection_snippet)
    return primary_preview

def open_page(url, text=False):
    try:
        response = requests.get(url, headers=REQUEST_HEADER)
    except Exception, e:
        print 'problem at open_page, url: ', url
        return ''
    if response.ok:
        if text:
            return response.text
        return response
    return ''


def soupify_page(html_text='', url=''):
    if url and not html_text:
        html_text = open_page(url, text=True)
    try:
        soup = BeautifulSoup(html_text, 'html.parser')
    except:
        print 'in soupify_page, problem with BeautifulSoup(html_text), url: ', url
        return
    return soup


def get_metadata_title(soup):
    og_title = get_og_property(soup, 'title')
    if og_title:
        return og_title
    tw_title = get_twitter_property(soup, 'title')
    if tw_title:
        return tw_title
    meta_title = get_meta_property(soup, 'title')
    if meta_title:
        return meta_title
    if soup:
        if soup.find('title'):
            return soup.find('title').get_text()
    return ''


def get_metadata_description(soup):
    og_desc = get_og_property(soup, 'description')
    if og_desc:
        return og_desc
    tw_desc = get_twitter_property(soup, 'description')
    if tw_desc:
        return tw_desc
    meta_desc = get_meta_property(soup, 'description')
    if not meta_desc:
        meta_desc = get_meta_property(soup, 'Description')
    if meta_desc:
        return meta_desc
    return ''

def extract_article(html_text):
    try:
        extractor = Extractor(extractor='ArticleExtractor', html=html_text)
        text_string = extractor.getText()
        text_string = htmlParser.unescape(text_string)
        text_string = unicodedata.normalize('NFKD', text_string).encode('ascii','ignore')
    except Exception:
        print 'Error extracting article html'
        text_string = ''
    return text_string

def valid_summary(sentence_array, target):
    min_percentage = 0.3
    relevent_sentence = []
    target_words = [word for word in target.split() if word not in pyteaser.stopWords]
    set_target_words = set(target_words)
    for sentence in sentence_array:
        sentence_words = [word for word in sentence.split() if word not in pyteaser.stopWords]
        relevent_sentence.append(bool(set_target_words & set(sentence_words)))
    num_relevent = len([val for val in relevent_sentence if val])
    num_sent = len(relevent_sentence)*1.0
    return (num_relevent/num_sent) >= min_percentage

def valid_summary_debugger(sentence_array, target):
    print '\n'
    if valid_summary(sentence_array, target):
        print 'Valid summary test is a SUCCESS'
    else:
        print 'Valid summary test FAILED'
    print 'Target:\n', target
    print 'Summary:\n', join_sentence_array(sentence_array)
    print '\n'
    return


def join_sentence_array(sentence_array):
    placeholder_array = []
    if sentence_array:
        for sentence in sentence_array:
            placeholder_array.append(sentence.replace('\n', ' '))
        temp_sentance = ' '.join(placeholder_array)
        # get rid of duplicated whitespaces
        return ' '.join(temp_sentance.split())
    return ''

SKIP_DOMAIN_SUMMARY = ['youtube', 'youtu','reddit', 'wikipedia']
def get_preview_website(url, target_test, title, response):

    #TODO: REFACTORRR!!!!!!
    #TODO: check content-type, if video or article, do not run summarizer

    if get_domain(url) in SKIP_DOMAIN_SUMMARY:
        return ''
    if target_test:
        sentence_array = []
        try:
            sentence_array = pyteaser.SummarizeUrl(url)
        except ZeroDivisionError:
            print ZeroDivisionError
            print 'in get_preview_website, problem with pyteaser.SummarizeUrl, submission.url: ', url
            pass
        except:
            print 'in get_preview_website, problem with pyteaser.SummarizeUrl, submission.url: ', url
        if not sentence_array and title and response and response.ok and 'text/html' in response.headers['content-type']:
            body_text = extract_article(response.text)
            try:
                sentence_array = pyteaser.Summarize(title, body_text)
            except ZeroDivisionError:
                print 'in get_preview_website, problem with pyteaser.Summarize, submission.url: ', url
                pass
        if sentence_array:
            valid_summary_debugger(sentence_array, target_test)
            if valid_summary(sentence_array, target_test):
                return join_sentence_array(sentence_array)                   
    return ''


def get_submission_self_post_preview(submission):
    #TODO: sanitize input (if contains a tag add target="_blank", if href doest contain protocol/domain, add them)
    if submission.is_self:
        return get_preview_selftext(submission)
    return ''


def get_domain(url):
    return tldextract.extract(url).domain

def get_full_domain(url):
    return '.'.join(tldextract.extract(url))

def get_subdomain(url):
    parsed_uri = urlparse(url)
    return parsed_uri.scheme + '://' + parsed_uri.netloc + '/'


def get_domain_data(url):
    subdomain = get_subdomain(url)
    return query_website_data(subdomain)



def valid_description(description, title, domain_description):
    #compare with title
    #compare with domain url
    return description != title and description != domain_description


SKIP_DOMAIN_DESCRIPTION = ['youtube', 'youtu','wikipedia']
def get_preview_description(submission, soup, title, domain_description):
    if get_domain(submission.url) not in SKIP_DOMAIN_DESCRIPTION:
        description = get_metadata_description(soup)
        if valid_description(description, title, domain_description):
            return description
        else:
            print '\ndescription validity test FAILED for url: ', submission.url, '\n'
    return ''

def get_submission_description_preview(submission, soup, title, domain_description):
    preview = ''
    if is_wikipedia(submission):
        #silly but valid url: http://en.wikipedia.org/w/index.php?title=Pneumonoultramicroscopicsilicovolcanoconiosis
        #how to deal with this: http://en.wikipedia.org/wiki/Beef_war
        # and this one: https://en.wikipedia.org/wiki/Category:Filmed_accidental_deaths
        preview = get_preview_wikipedia(submission.url)
    else:
        #TODO: check content of summary/description and their length
        #example bad summary: http://www.democracynow.org/2014/9/10/headlines/philadelphia_set_to_decriminalize_marijuana#.VBBrDmpbsgc.reddit
        #TODO: too long content that it overflows parent div
        #example: http://www.reddit.com/r/Fireteams/comments/2gathq/ps4_22_titan_lf_weekly/
        #TODO:if self post with no selftext, stats on comments will be the default comment. change or check for this mkay... 
        #DEBUG: http://www.reddit.com/r/Showerthoughts/comments/2gijsn/if_we_pop_bubble_wrap_made_in_china_the_air_that/
        preview = get_preview_description(submission, soup, title, domain_description)

    if preview.endswith('comments so far on reddit'):
        preview = '' 

    return preview


def get_submission_summary_preview(submission, target_test, title, response):
    return get_preview_website(submission.url, target_test, title, response)


def get_preview_video(soup):
    #TODO: find using property="twitter:player:url" and "twitter:player:stream:url" 
    # (ref: view-source:https://www.kickstarter.com/projects/1087256999/odiun-a-web-site)
    if soup:
        og_vids = get_og_property(soup, 'video', deep=True)
        for og_vid in og_vids:
            if og_vid.endswith('.mp4'):
                return og_vid
        if len(og_vids) > 0:
            return og_vids[0]
        tw_vid = get_twitter_property(soup, 'player') 
        if tw_vid:
            return tw_vid
        og_vid_url = get_og_property(soup, 'video:url')
        if og_vid_url:
            return og_vid_url
    return ''


def get_preview_picture(soup):
    if soup:
        og_pic = get_og_property(soup, 'image')
        if og_pic:
            return og_pic
        tw_pic = get_twitter_property(soup, 'image')
        if tw_pic:
            return tw_pic
    return ''

def get_last_path(url):
    path_list = url.split('/')
    if path_list:
        return path_list[-1]
    return ''


def wiki_image_helper(soup_obj, class_name):
    image_url = ''
    parent_elt = soup_obj.find(class_= class_name)
    if parent_elt:
        image = parent_elt.find('img')
        if image:
            image_url = image['src'].replace('//', 'http://')
    return image_url


def get_wikipedia_image(soup):
    if soup:
        image_url = wiki_image_helper(soup, 'infobox')
        if not image_url:
            image_url = wiki_image_helper(soup, 'thumbinner')
    return image_url


def get_body_page_image(soup):
    #img alt or img title (maybe data-mediaviewer-caption? ref: http://www.nytimes.com/2014/10/03/world/middleeast/un-reports-at-least-26000-civilian-casualties-in-iraq-conflict-this-year.html), 
    # or use iamge url path
    #list of examples:
    # http://www.theguardian.com/world/2014/oct/02/judge-obama-guantanamo-force-feeding-hearing-secret
    # http://www.theguardian.com/science/2014/oct/03/hiv-virus-baby-drug-treatment-anti-retroviral-infection
    # http://www.theguardian.com/uk-news/2014/oct/02/gerry-mccann-madeleine-sunday-times-libel-payout
    # http://9janews2.blogspot.nl/2014/10/swiss-helicopter-crash-in-france-leaves.html
    # http://www.theguardian.com/world/2014/oct/02/russian-investors-north-korea-boost-business
    # http://bigstory.ap.org/article/96e12e16d42c43f08ac01ea48e1238a9/california-teens-arrested-920-chicken-deaths
    # http://bigstory.ap.org/article/034ca44ad33f4c888fa1b26988ce76cf/jpmorgan-says-data-breach-affected-76m-households
    # http://www.theguardian.com/science/2014/oct/02/hiv-aids-pandemic-kinshasa-africa
    # http://www.bbc.com/news/world-asia-india-29441052
    # http://www.theguardian.com/environment/2014/oct/02/uk-nuclear-bomb-factories-rapped-by-watchdogs-over-radioactive-waste
    # http://www.bbc.com/news/world-middle-east-29455204
    # http://www.theguardian.com/world/2014/oct/02/hong-kong-protesters-deadline-police
    # http://www.msn.com/en-us/news/us/thirst-turns-to-desperation-in-rural-california/ar-BB73j6n
    # http://www.navy.mil/submit/display.asp?story_id=83646
    # http://www.theguardian.com/world/2014/oct/02/la-fashion-district-raid-cartel-rules-money-laundering
    # http://www.bbc.com/news/world-europe-29455550
    # http://www.msn.com/en-us/news/crime/california-teens-arrested-in-920-chicken-deaths/ar-BB70GBn
    # https://nakedsecurity.sophos.com/2014/10/02/us-attorney-general-urges-tech-companies-to-leave-back-doors-open-on-gadgets-for-police/
    # https://time.com/3455815/hawaii-potential-ebola-case/
    # http://www.newsweek.com/north-korea-prepares-launch-site-longer-range-rockets-report-274771
    # http://news.sky.com/story/1346233/japan-braces-for-300-mile-wide-typhoon
    # https://news.yahoo.com/us-could-topple-government-kill-argentinas-kirchner-095518100.html
    # http://www.georgianewsday.com/news/crime/292479-grandmother-geneva-robinson-accused-of-dressing-as-witch-to-abuse-child.html
    # http://news.sky.com/story/1346023/raf-tornados-take-out-is-truck-using-guided-bomb




    return ''


def url_content_type(url='', response_obj=''):
    if url and not response_obj:
        response_obj = open_page(url)
    if response_obj:
        if 'content-type' in response_obj.headers.keys():
            return response_obj.headers['content-type']
    return ''

def is_content_type(url, header_list):
    content_type = url_content_type(url=url)
    for header in header_list:
        if header in content_type:
            return True
    return False

def relative_to_absolute(target_url, domain_url):
    if target_url:
        if 'http' not in target_url:
            if target_url.startswith('//'):
                target_url = 'http:' + target_url
            elif target_url.startswith('/'):
                target_url = 'http://' + get_full_domain(domain_url) + target_url
            else:
                target_url = 'http://' + target_url
    return target_url

def is_valid_picture(url):
    return is_content_type(url, PICTURE_HEADERS)


VIDEO_HEADERS = ['video', 'application/x-shockwave-flash']
def get_submission_video_preview(submission, soup):
    preview = ''  
    preview = get_submission_media_preview(submission, VIDEO_HEADERS, 'video', soup)
    return preview

PICTURE_HEADERS = ['image']
def get_submission_picture_preview(submission, soup, video_preview):
    #if self post reddit, find image in the self text
    #find in website <img> tags with relevent alt attribute or img url
    #BBC og:image is a fucking joke, example: http://www.bbc.com/news/world-middle-east-29186506 , 
    #oh nyt too: http://opinionator.blogs.nytimes.com/2014/02/08/how-single-motherhood-hurts-kids/?smid=re-share
    #DEBUG: http://www.reddit.com/r/soccer/comments/2gjm6q/carlo_ancelotti_and_chicharito_before_the_mexican/
    preview = ''
    preview = get_submission_media_preview(submission, PICTURE_HEADERS, 'picture', soup)
    if not preview:
        if is_wikipedia(submission):
            preview = get_wikipedia_image(soup)
        else:
            preview = get_body_page_image(soup)

    preview = relative_to_absolute(preview, submission.url)

    #generic video thumbnail
    if video_preview and not preview:
        preview = 'http://i.imgur.com/shZlsma.png'

    if 'redditstatic.com/icon.png' in preview:
        preview = ''

    if not is_valid_picture(preview):
        if preview:
            print '\n\n\nNOTTTTTTTTTTTT VALIDDDD PIC  URLLLLLLLLL: ', preview
            print 'offending url: ', submission.url,'\n\n\n\n'
        preview = ''


    #TODO: reject default logo, examples
    # http://www.nytimes.com/2014/10/02/us/possible-leak-by-ferguson-grand-juror-is-investigated.html
    # http://news.yahoo.com/why-did-americas-oldest-episcopal-seminary-fire-most-211954728.html
    # http://www.theguardian.com/world/2014/oct/02/florida-speed-trap-town-disbands-police-force
    # http://www.miamiherald.com/news/nation-world/article2484484.html
    # http://www.washingtonpost.com/world/middle_east/us-marine-presumed-lost-in-the-persian-gulf/2014/10/02/33d1814e-4a6e-11e4-a4bf-794ab74e90f0_story.html
    # http://www.meadvilletribune.com/news/article_05d210c2-49a8-11e4-8658-5b91a80b60be.html
    # http://www.bbc.com/news/world-middle-east-29455204
    # http://www.kcra.com/money/fox-news-site-removes-incendiary-interview-about-oklahoma-mosque/28373308
    # http://www.foxnews.com/politics/2014/10/01/court-obama-administration-cant-hide-investigation-into-former-white-house/
    # http://www.law360.com/articles/583257/fcc-chair-calls-city-broadband-as-american-as-you-can-get
    # http://www.nytimes.com/2014/10/03/world/asia/satellite-shows-north-korea-has-upgraded-launch-station.html?_r=0
    # http://seattletimes.com/html/nationworld/2024685420_apxjpmorgandatabreach.html
    # http://www.timesnews.net/article/9081271/gate-city-students-file-lawsuit-against-assistant-principal
    # http://www.ft.com/cms/s/d8938ffc-4a04-11e4-8de3-00144feab7de,Authorised=false.html
    # http://www.buffalonews.com/city-region/environment/new-federal-rule-allows-freighters-to-dump-cargo-remnants-into-great-lakes-20140930
    # http://www.chicagotribune.com/sns-wp-blm-news-bc-australia01-20141001-story.html
    # http://www.al.com/news/index.ssf/2014/10/second_patient_being_monitored.html
    # http://www.sfgate.com/business/energy/article/Feds-to-unveil-cleanup-plan-for-nuke-waste-dump-5790898.php
    # http://www.startribune.com/local/277846091.html
    # http://www.newindianexpress.com/states/tamil_nadu/5700-Schools-in-TN-Lack-Toilets-Survey/2014/09/28/article2453019.ece
    # http://arstechnica.com/tech-policy/2014/10/its-now-legal-to-make-backups-of-movies-music-and-e-books-in-the-uk/
    # http://rbth.com/news/2014/10/01/russia_cancels_participation_in_us_education_program_after_russian_stude_40284.html
    # http://www.huffingtonpost.com/jen-caltrider/hello-america-its-me-colorado_b_5870476.html?utm_hp_ref=denver&amp;ir=Denver
    # http://www.npr.org/2014/10/04/353679002/putin-among-the-surprises-on-nobel-peace-prize-list
    # http://www.forbes.com/sites/jasperhamill/2014/09/29/voice-hackers-will-soon-be-talking-their-way-into-your-technology/

    return preview

def get_submission_media_preview(submission, header_type, media_type, soup):
    preview = ''
    if is_content_type(submission.url, header_type):
        preview = submission.url
    else:
        if media_type == 'video':
            preview = get_page_video(submission.url, soup)
        elif media_type == 'picture': 
            preview = get_preview_picture(soup)
    return preview


def get_page_video(url, soup):
    video_url = ''
    if get_domain(url) == 'liveleak':
        video_url = liveleak_video(soup)
    elif get_domain(url) == 'gfycat':
        video_url = gfycat_video(url)
    else:
        video_url_temp = get_preview_video(soup)
        #check validity of video url
        if is_valid_video(video_url_temp):
            video_url = video_url_temp
    return video_url

def is_valid_video(url):
    return is_content_type(url, VIDEO_HEADERS)

def liveleak_video(soup):
    embed_url = 'http://www.liveleak.com/ll_embed?f='
    embed_id_raw = ''
    if soup:
        a_tags = soup.find_all('a')
        for tag in a_tags:
            if tag.text == 'Embed Code':
                if 'onclick' in tag.attrs:
                    embed_id_raw = tag['onclick']
                    break
    if embed_id_raw:
        start_marker = "generate_embed_code_generator_html('"
        end_marker = "'))"
        start = embed_id_raw.find(start_marker) + len(start_marker)
        end = embed_id_raw.find(end_marker)
        return embed_url + embed_id_raw[start:end]
    return ''

def gfycat_video(url):
    gyfcat_api = 'http://gfycat.com/cajax/get/'
    start = url.rfind('/') + 1
    end = url.find('?')
    if end == -1:
        end = len(url)
    api_url = gyfcat_api + url[start:end]
    response = open_page(api_url, text=True)
    json_response = json.loads(response)
    if json_response:
        if 'gfyItem' in json_response:
            if 'mp4Url' in json_response['gfyItem']:
                return json_response['gfyItem']['mp4Url']
    return ''

def soup_to_string(soup):
    if soup:
        return str(soup)
    return ''


def get_submission_comment_preview(submission):
    #TODO: too compact, refactor code/comment
    raw_comments = [{'comment_html': comment.body_html, 'score': comment.score} 
                    for comment in submission.comments if hasattr(comment,'score') and comment.score > 0 ]
    sorted_raw_comments = sorted(raw_comments, key=lambda x:x['score'], reverse=True)[: min(len(raw_comments), 5)]
    comment_html = [comment['comment_html'] for comment in sorted_raw_comments]
    soup_list = map_multiple([unescape_html, soupify_page, insert_target_blank], comment_html)
    for soup in soup_list:
        soup = relative_to_absolute_soup(soup, 'http://www.reddit.com')
    return map(soup_to_string, soup_list)


def map_multiple(input_functions, input_list):
    for input_function in input_functions:
        input_list = map(input_function, input_list)
    return input_list


def main():
    articles = article_collection() #done testing: spacex+teslamotors+elonmusk+news+worldnews+wikipedia+startup
    try:
        reddit = init_praw()
    except:
        print 'problem connecting to reddit, please check if the website is live. Please try again later'
        return
    # submissions = get_submissions(reddit, subreddit='videos+vids+video', sorting_type='top', limit=1000)
    # submissions = get_submissions(reddit, subreddit='spacex+teslamotors+elonmusk+news+worldnews+wikipedia+startup', sorting_type='new', limit=1000)
    # submissions = get_submissions(reddit, subreddit='news+worldnews+wikipedia', sorting_type='new', limit=1000)
    # submissions = get_submissions(reddit, subreddit='trendingsubreddits', sorting_type='hot', limit=100)
    submissions = get_submissions(reddit, limit=5000)
    count = 0
    for submission in submissions:
        count += 1
        print '\nArticle number :', count, '\n'
        #TODO: skip if get_submission_content takes too long
        # ref ?: http://stackoverflow.com/questions/21965484/timeout-for-python-requests-get-entire-response
        new_article = get_submission_content(submission)
        if new_article:
            database_save(articles, new_article)
            # pprint(new_article)
        print '=================='
    return

if __name__=='__main__':
    main()
