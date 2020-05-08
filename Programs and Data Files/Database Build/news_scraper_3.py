import sys
import json
import itertools
import calendar
import time
from datetime import datetime, timedelta
from threading import Thread
from random import randint
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from scraper_api import ScraperAPIClient

articles_per_month = 5

with open('apiclient_key.txt', 'r') as fo:
    apiclient_key = fo.read()
with open('csedeveloper_key.txt', 'r') as fo:
    csedeveloper_key = fo.read()
with open('cse_id.txt', 'r') as fo:
    cse_id = fo.read()
    
_scraper_client = ScraperAPIClient(apiclient_key)
_cse = build('customsearch', 'v1', developerKey = csedeveloper_key).cse()
output_file = open('output.txt', mode='w', encoding='utf-8')


def download_article(article):
    attempt = 0
    while True:
        if attempt > 5:
            break
        attempt += 1
        try:
            payload = _scraper_client.get(url = article['link']).text
            break
        except:
            continue
    return payload


def extract_text(payload):
    soup = BeautifulSoup(payload, 'html.parser')
    text = str()
    for paragraph in soup.find_all('p'):
        text += str(paragraph.text) + '\n'
    return text


def process_thread(articles, index, prefix):
    payload = download_article(articles[index])
    text = '\n\n** ' + articles[index]['title'] + ' **\n'
    text += extract_text(payload)
    file_name = prefix + str(index)
    with open(file_name, mode = 'w', encoding = 'utf-8') as output_file:
        output_file.write(text)


def process_articles(articles, prefix):
    threads = list()
    for i in range(len(articles)):
        worker = Thread(target = process_thread, args = [articles, i, prefix])
        worker.start()
        threads.append(worker)
    for thread in threads:
        thread.join()


def get_date_bound(date):
    from_date = date.replace(day = 1) - timedelta(days = 1)
    from_time = ' after:' + from_date.strftime('%Y-%m-%d')
    to_date = date.replace(day = calendar.monthrange(
        date.year, date.month)[1]) + timedelta(days = 1)
    to_time = ' before:' + to_date.strftime('%Y-%m-%d')
    return from_time, to_time


def google_query(phrase, site, start_date, end_date):
    curr_date = start_date
    while True:
        if curr_date > end_date:
            break
        from_time, to_time = get_date_bound(curr_date)
        start_pos = 1
        articles = list()
        while True:
            if start_pos > 100:
                break
            res = _cse.list(q = from_time + to_time,
                            exactTerms = phrase,
                            cx = cse_id,
                            lr = 'lang_en',
                            siteSearch = site,
                            fields = 'queries/nextPage,items/title,items/link').execute()
            if 'items' in res:
                articles.extend(res['items'])
            if 'nextPage' not in res:
                break
            start_pos += 10

        curr_month = str(curr_date.month) + '-' + str(curr_date.year)
        prefix = site + '_' + curr_month + '_'

        if len(articles) > articles_per_month:
            for i in range(articles_per_month):
                selection = randint(0, len(articles) - 1)
                articles[i], articles[selection] = articles[selection], articles[i]
            articles = articles[:articles_per_month]
        process_articles(articles, prefix)

        curr_date = curr_date + timedelta(days = 31)
        curr_date.replace(day = 1)
        time.sleep(0.5)


def main():
    if len(sys.argv) > 1:
        file_name = sys.argv[1]
    else:
        file_name = 'input.json'
    with open(file_name) as input_file:
        input_data = json.load(input_file)
        phrases = input_data['phrases']
        sites = input_data['sites']
        start_date = datetime.strptime(input_data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(input_data['end_date'], '%Y-%m-%d')
        for pair in itertools.product(phrases, sites):
            google_query(pair[0], pair[1], start_date, end_date)


if __name__ == '__main__':
    main()
