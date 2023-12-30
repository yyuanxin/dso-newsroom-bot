import os
import boto3
import feedparser
import fileinput
import re
import requests
import telebot

from abc import ABC, abstractmethod
from datetime import timedelta, datetime
from dateutil import parser

BOT_TOKEN = os.environ['BOT_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']
bot = telebot.TeleBot(BOT_TOKEN)

s3 = boto3.resource('s3')
s3 = boto3.client('s3')

HOURS = int(os.environ['HOURS'])
CACHED_FILE = "cached.txt"
S3_BUCKET = "rss-code"
FILE = "/tmp/" + CACHED_FILE

def gmtToUtcTimeFormat(date):
    """Converts GMT time to UTC time format
        Example:
        [Input] Fri, 03 Mar 2023 18:38:23 GMT
        [Output] 2023-03-04T18:38:23+00:00

    :param string date: gmt time
    :rctype: string
    :return: string of UTC time
    """
    gmtFormat = "%a, %d %b %Y %H:%M:%S GMT"
    utcFormat = "%Y-%m-%dT%H:%M:%S+00:00"
    dt = datetime.strptime(date,gmtFormat).strftime(utcFormat)
    return dt

def isRecent(date):
    """Checks if published date is within 24 hrs

    :param string date: utc time
    :rctype: boolean
    :return: true if published within a day, else false
    """
    now_date = datetime.utcnow()
    parsed_date = parser.parse(date).replace(tzinfo=None)
    return (now_date - parsed_date) < timedelta(hours=HOURS)

def loadCached():
    s3.download_file(S3_BUCKET,CACHED_FILE,FILE)

def getCached(name, keyword):
    with open(FILE) as f:
        for line in f:
            if keyword in line:
                return line.split(',')[-1]
        raise Exception("No cached value stored for " + name)

def updateCached(name, keyword, value):
    with fileinput.input(FILE, inplace=True) as f:
        for line in f:
            if keyword in line:
                x = line.split(',')
                updated_line = line.replace(x[-1], value)
                print(updated_line, end='')
                break

def uploadCached():
    s3.upload_file(FILE, S3_BUCKET, CACHED_FILE)

def isBreakingChange(content):
    keywords = ['breaking change', 'breaking changes', 'major release']
    if any(content.lower() == keyword for keyword in keywords):
        return true
    else:
        return false

class RSS(ABC):
    def __init__(self, name, link):
        self.name = name
        self.link = link
    
    @abstractmethod
    def checkRSS(self):
        return
    def getMessage(self, entry):
        """ Craft message to send. This is a helper function for sendMessage 
        """
        header = '_' + self.name + ' Update_'
        if isBreakingChange(entry.content[0].value):
            message = header + '\n' + entry.title + '\n' +  entry.link + ''
        else:
            message = header + '\n' + entry.title + '\n' +  entry.link + '\n' + '** This is a breaking change release. Please read the changelog. **'
        return message
    def sendMessage(self, entry):
        message = self.getMessage(entry)
        url_req = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage" + "?chat_id=" + CHANNEL_ID + "&text=" + message + "&parse_mode=markdown"
        results = requests.get(url_req)
        print(results.json())

class CommonRSS(RSS):
    def checkRSS(self):
        print(self.name + " in")
        rss_feed = feedparser.parse(self.link)
        stack = [] # LIFO to store all new release rss entries
        for entry in rss_feed.entries:
            if isRecent(entry.updated):
                # store new release entry in stack
                stack.append(entry)
            else:
                # exit loop when no more new releases
                break

        while stack:
            entry = stack.pop()
            self.sendMessage(entry) # declared in parent RSS class
        print(self.name + " out")          
    def getMessage(self, entry):
        """ Craft message to send. This is a helper function for sendMessage 
        """
        header = '_' + self.name + ' Update_'
        message = header + '\n' + entry.title + '\n' +  entry.description + '\n' +  entry.link
        return message

class BurpsuiteRSS(RSS):
    def isEnterprise(self, title):
        """Checks if rss entry is enterprise release

        This function simply checks if title contains the burp keyword.
        Before check, converts input to lowercase and assumes burp keyword is in lowercase.
        BURP_KEYWORD is declared within function.

        :param string title: title of the rss entry
        :rctype: boolean
        :return: true if entry is enterprise related, else false
        """
        BURP_KEYWORD = 'enterprise'
        return BURP_KEYWORD in title.lower()   
    def checkRSS(self):
        print(self.name + " in")
        rss_feed = feedparser.parse(self.link)
        for entry in rss_feed.entries:
            utc_date = gmtToUtcTimeFormat(entry.published)
            if isRecent(utc_date):
                if self.isEnterprise(entry.title):
                    self.sendMessage(entry) # declared in parent RSS class
            else:
                break
        print(self.name + " out")
        return

class GitlabRSS(RSS):
    def isRecent(self, entry):
        """Checks if RSS entry is recently published

        This function checks against the cached value in a seperate file
        of the last recent sent gitlab release news in telegram. 
        
        The condition to satisfy as recently published:
        entry.link != cached

        :param object entry: rss entry of json feed
        :rctype: boolean
        :return: true if recently published that is not sent to telegram yet, else false
        """
        cached = getCached(self.name, "GITLAB")
        if entry.link != cached:
            return True
        return False
    def checkRSS(self):
        """ Check RSS feed for all new gitlab releases that has yet been send to telegram

        Runs through all rss feed entries until reaches to the last recent release sent to telegram.
        For all new releases, store in a stack with LIFO structure and send all elements in the stack
        s.t. the latest release is sent to telegram last.
        
        RSS feed entries are in desc order where the first entry is always the latest release.
        Hence, a stack ensures that latest release is sent last.

        Lastly, update cached value in cached file with the latest release link

        """
        print(self.name + " in")
        rss_feed = feedparser.parse(self.link)
        stack = [] # LIFO to store all new release rss entries
        for entry in rss_feed.entries:
            if self.isRecent(entry):
                # store new release entry in stack
                stack.append(entry)
            else:
                # exit loop when no more new releases
                break
        
        while stack:
            entry = stack.pop()
            # checks if this is last entry in stack (latest release)
            if not stack:
                # update cache for future checks
                updateCached(self.name, "GITLAB", entry.link)
            self.sendMessage(entry) # declared in parent RSS class
        print(self.name + " out")

class GithubRSS(RSS):
    def checkRSS(self):
        print(self.name + " in")
        rss_feed = feedparser.parse(self.link)
        stack = [] # LIFO to store all new release rss entries
        for entry in rss_feed.entries:
            if isRecent(entry.updated):
                # store new release entry in stack
                stack.append(entry)
            else:
                # exit loop when no more new releases
                break
        
        while stack:
            entry = stack.pop()
            self.sendMessage(entry) # declared in parent RSS class
        print(self.name + " out")

class SonarqubeRSS(RSS):
    def getMessage(self, entry):
        """ Craft message to send. This is a helper function for sendMessage 
        """
        header = '_' + self.name + ' Update_'
        message = header + '\n' + entry.title + '\n' + 'Read Description here: ' +  entry.link
        return message
    def checkRSS(self):
        print(self.name + " in")
        rss_feed = feedparser.parse(self.link)
        for entry in rss_feed.entries:
            if isRecent(entry.published):
                self.sendMessage(entry) # declared in parent RSS class
        print(self.name + " out")

class OpensslRSS(GithubRSS):
    def isVersion(self, tag):
        str = tag.split('/')[-1].lower()
        # expect format to be "openssl_1_1_1x"
        prefix = str.split("openssl")[1][1]
        if prefix == "1":
            return True
        return False

    def checkRSS(self):
        print(self.name + " in")
        rss_feed = feedparser.parse(self.link)
        for entry in rss_feed.entries:
            if isRecent(entry.updated) and self.isVersion(entry.link):
                self.sendMessage(entry) # declared in parent RSS class
        print(self.name + " out")

class NodejsRSS(GithubRSS):
    def isVersion(self, tag):
        str = tag.split('/')[-1].lower()
        nodejs_14_pattern = re.compile("^v14.*")
        nodejs_18_pattern = re.compile("^v18.*")
        if nodejs_14_pattern.match(str.lower()) or nodejs_18_pattern.match(str.lower()):
            return True
        return False

    def checkRSS(self):
        print(self.name + " in")
        rss_feed = feedparser.parse(self.link)
        for entry in rss_feed.entries:
            if isRecent(entry.updated) and self.isVersion(entry.link):
                self.sendMessage(entry) # declared in parent RSS class
        print(self.name + " out")

class AwsCliRSS(GithubRSS):
    def isVersion(self, tag):
        str = tag.split('/')[-1].lower()
        v2_pattern = re.compile("^2.*")
        if v2_pattern.match(str.lower()):
            return True
        return False

    def getMessage(self, entry):
        """ Craft message to send. This is a helper function for sendMessage 
        """
        url = 'https://raw.githubusercontent.com/aws/aws-cli/v2/CHANGELOG.rst'
        header = '_' + self.name + ' Update_'
        message = header + '\n' + entry.title + '\n' + 'Changelog:' + url
        return message

    def checkRSS(self):
        print(self.name + " in")
        rss_feed = feedparser.parse(self.link)
        for entry in rss_feed.entries:
            if isRecent(entry.updated) and self.isVersion(entry.link):
                self.sendMessage(entry) # declared in parent RSS class
        print(self.name + " out")
