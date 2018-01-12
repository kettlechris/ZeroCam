#!/usr/bin/env python

import requests
from BeautifulSoup import BeautifulSoup
import os.path
import time
import os

url = "[your cameras ip adress]:[port the SimpleHTTPServer is running on]"
response = requests.get(url)
verbose = False
# parse html
page = str(BeautifulSoup(response.content))


def getURL(page):
    """

    :param page: html of web page (here: Python home page)
    :return: urls in that page
    """
    start_link = page.find("a href")
    if start_link == -1:
        return None, 0
    start_quote = page.find('"', start_link)
    end_quote = page.find('"', start_quote + 1)
    url = page[start_quote + 1: end_quote]
    return url, end_quote

def deletePartial():
    for filename in sorted(os.listdir(".")):
        if filename.endswith('h264'):
            dummyFile = os.stat(filename)
            if dummyFile.st_size < (1.75*1024*1024):
                os.remove(filename)
while True:
    url, n = getURL(page)
    page = page[n:]
    if url:
        if url != "projectfiles/":
            for filename in sorted(os.listdir(".")):
                if filename.endswith('h264'):
                    dummyfile = os.stat(filename)
                    if (((time.time() - dummyfile.st_ctime)) > 17000): #if file is less than 17 seconds old, download again
                        downloadAnyway = True
                    else:
                        downloadAnyway = False
                else:
                    downloadAnyway = False
            if not os.path.isfile(url) or url == 'ZeroCamLog.txt' or downloadAnyway:
                r = requests.get('[your cameras ip adress]:[port the SimpleHTTPServer is running on]/{0}'.format(url))
                if verbose:
                    print ('[your cameras ip adress]:[port the SimpleHTTPServer is running on]'.format(url))
                with open('scrubLog.txt', 'a') as f:
                    f.write("\n{0} downloaded @ {1}".format(url, time.asctime(time.localtime(time.time()))))
                with open(url, 'wb') as f:
                    f.write(r.content)
            else:
                if verbose:
                    print("{0} already downloaded".format(url))
    else:
        break
