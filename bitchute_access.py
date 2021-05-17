import json
import pickle

import requests
import xbmcaddon
from bs4 import BeautifulSoup
from xbmcgui import Dialog

#import re
#from datetime import datetime

from cache import data_cache, login_cache


class Subscription():

    def __init__(self, name, channel, description, channel_image):
        self.name = name
        self.channel = channel
        self.description = description
        self.channel_image = channel_image


class Notification():

    def __init__(self, video_id, title, description):
        self.video_id = video_id
        self.title = title
        self.description = description


class Video():

    def __init__(self, videoURL, poster, title, description):

        self.videoURL = videoURL
        self.poster = poster
        self.title = title
        self.description = description


class SearchResult():

    def __init__(self, video_id, description, title, poster, channel_name):
        self.video_id = video_id
        self.description = description
        self.title = title
        self.poster = poster
        self.channel_name = channel_name


class ChannelEntry():

    def __init__(self, video_id, poster, title, description, channel_name=u"", date=0, duration=0):
        self.video_id = video_id
        self.poster = poster
        self.title = title
        self.description = description
        self.channel_name = channel_name
        self.date=date
        self.duration=duration


class PlaylistEntry():

    def __init__(self, video_id, description, title, poster, channel_name=u"", duration=u"", date=u""):
        self.video_id = video_id #.replace('&nbsp', ' ')
        self.description = description #.replace('&nbsp', ' ')
        self.title = title #.replace('&nbsp', ' ')
        self.poster = poster #.replace('&nbsp', ' ')
        self.channel_name = channel_name #.replace('&nbsp', ' ')
        self.duration=duration #.replace('&nbsp', ' ')
        self.date=date #.replace('&nbsp', ' ')
        print("Playlist entry: ",video_id, description, title, poster, channel_name, duration, date)

""" 
def conv_bitcoin_date(bt_datestr):
    print ("000000000000000000000000000000: ", bt_datestr)
    conv = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}
    reg = "([A-Za-z]+)\ ([0-9]{1,})\,\ ([0-9]{4})"

    r = re.match(reg, bt_datestr)
    print (
        "100000000000000000000000000000: ",conv[(r.group(1).upper())],
        int(r.group(2)),
        int(r.group(3))
        )

    if r is not None:
        d = datetime(
            month=conv[(r.group(1).upper())],
            day=int(r.group(2)),
            year=int(r.group(3))
            )
    else:
        d=0

    return (d) """



def BitchuteLogin(username, password):

    token  = ""
    logged_in = False
    agent="Bitchute Kodi-Addon/1"

    url: str = "https://www.bitchute.com/accounts/login/"
    headers = {"User-Agent": agent}
    req = requests.get(url, headers=headers)

    if (req.status_code!=200):
        return None, False

    token = req.cookies["csrftoken"]
    csrfJar=req.cookies

    baseURL = "https://www.bitchute.com"
    post_data = {'csrfmiddlewaretoken': token,
                    'username': username, 'password': password}
    headers = {'Referer': baseURL + "/", 'Origin': baseURL, "User-Agent": agent}
    response = requests.post(
        baseURL + "/accounts/login/", data=post_data, headers=headers, cookies=csrfJar)

    # it's the cookies that carry forward the token/ids
    if 200 == response.status_code:
        if json.loads(response.text)['success'] == True:
            csrfJar = response.cookies
            logged_in = True

    # the cookies object has to be pickled or Kodi's cache will never recognise it as cache and keep refreshing it
    return pickle.dumps(csrfJar), logged_in


def bt_login():
    global login_cache
    username = xbmcaddon.Addon().getSetting("user")
    password = xbmcaddon.Addon().getSetting("password")
    pickled_cookies, success = login_cache.cacheFunction(
        BitchuteLogin, username, password)

    if not success:

        login_cache.delete('%')
        data_cache.delete('%')   # clear out the login/data caches
        q = Dialog()
        q.ok("Login failed", "Unable to login to Bitchute with the details provided")

        return [], False

    cookies=pickle.loads(pickled_cookies)
    #expires = next(x for x in cookies if x.name == 'sessionid').expires
    return cookies, True


def _get_subscriptions(cookies):

    url = "https://www.bitchute.com/subscriptions/"
    req = requests.get(url, cookies=cookies, headers={"User-Agent": "Bitchute Kodi-Addon/1"})

    #self.csrfJar = req.cookies

    subs = []
    soup = BeautifulSoup(req.text, "html.parser")

    containers = soup.find_all(class_="subscription-container")

    for sub in containers:

        try:
            channel = sub.find("a").attrs["href"].split("/")[1]
            channel_image = sub.find("a").find("img").attrs["data-src"]
            name = sub.find(class_="subscription-name").get_text()
            # description = sub.find(
            #    class_="subscription-description").get_text()
            channel = sub.find(class_="spa").attrs["href"].replace("/channel/", "")
            #last_video = sub.find(class_="subscription-last-video").get_text()
            description = sub.find(
                class_="subscription-description-text").get_text()
        except AttributeError as e:
            print("**************** ATTRIBUTE_ERROR "+str(e))
            print(str(sub))
            name = description = channel = channel_image = "ERROR PARSING"

        s = Subscription(name=name, channel=channel,
                         description=description, channel_image=channel_image)
        subs.append(s)

    return pickle.dumps(subs)


def _get_notifications(cookies):

    notifs = []

    url = "https://www.bitchute.com/notifications/"
    req = requests.get(url, cookies=cookies, headers={"User-Agent": "Bitchute Kodi-Addon/1"})

    soup = BeautifulSoup(req.text, "html.parser")

    containers = soup.find_all(class_="notification-item")

    for n in containers:
        try:
            video_id = n.find(
                class_="notification-view").attrs["href"].split("/")[2]
            title = n.find(
                class_="notification-target").get_text()
            description = n.find(
                class_="notification-detail").get_text()
        except AttributeError as e:
            print("**************** ATTRIBUTE_ERROR "+str(e))
            print(str(n))
            video_id = title = description = "ERROR PARSING"

        notif = Notification(video_id=video_id, title=title,
                             description=description)
        notifs.append(notif)

    return pickle.dumps(notifs)


def _get_popular(cookies):

    playlist = []

    url = "https://www.bitchute.com/"

    req = requests.get(url, cookies=cookies, headers={"User-Agent": "Bitchute Kodi-Addon/1"})
    cookies = req.cookies

    soup = BeautifulSoup(req.text, "html.parser")

    popular = soup.find(id="listing-popular")

    containers = popular.find_all(class_="video-card")

    for n in containers:
        try:
            poster = n.find("img").attrs["data-src"]
            video_id = n.find(class_="video-card-id hidden").get_text()
            title = n.find(class_="video-card-title").find("a").get_text()
            channel_name = n.find(
                class_="video-card-channel").find("a").get_text()
            description = ""

            duration = n.find(class_="video-duration").get_text()
            date= n.find(class_="video-card-published").get_text()
            print ("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!: ", duration, date)

        except AttributeError as e:
            print("**************** ATTRIBUTE_ERROR "+str(e))
            print(str(n))
            poster = video_id = title = channel_name = description = duration = date = "ERROR PARSING"

        s = PlaylistEntry(
            video_id=video_id, description=description, title=title, poster=poster, channel_name=channel_name, date=date, duration=duration)
        playlist.append(s)

    return pickle.dumps(playlist)


def _get_trending(cookies):

    playlist = []

    url = "https://www.bitchute.com/"

    req = requests.get(url, cookies=cookies, headers={"User-Agent": "Bitchute Kodi-Addon/1"})
    cookies = req.cookies

    soup = BeautifulSoup(req.text, "html.parser")

    popular = soup.find(id="listing-trending")

    containers = popular.find_all(class_="video-result-container")

    for n in containers:
        try:
            video_id = n.find(class_="video-result-image-container").find(
                "a").attrs["href"].split("/")[2].replace("/", "")
            poster = n.find(
                class_="video-result-image").find("img").attrs["data-src"]
            title = n.find(class_="video-result-title").find("a").get_text()
            channel_name = n.find(
                class_="video-result-channel").find("a").get_text()
            description = n.find(class_="video-result-text").get_text()

            duration = n.find(class_="video-duration").get_text()
            date= n.find(class_="video-result-details").find("span").get_text()

        except AttributeError as e:
            print("**************** ATTRIBUTE_ERROR "+str(e))
            print(str(n))
            video_id = poster = title = channel_name = description =date= duration= "ERROR PARSING"

        s = PlaylistEntry(
            video_id=video_id, description=description, title=title, poster=poster, channel_name=channel_name, date=date, duration=duration)
        playlist.append(s)

    return pickle.dumps(playlist)


def _get_playlist(cookies, playlist_name):

    #"favorites", "watch-later"

    playlist = []

    url = "https://www.bitchute.com/playlist/"+playlist_name+"/"

    req = requests.get(url, cookies=cookies, headers={"User-Agent": "Bitchute Kodi-Addon/1"})

    soup = BeautifulSoup(req.text, "html.parser")

    containers = soup.find_all(class_="playlist-video")

    for n in containers:

        try:

            t = n.find(class_="text-container").find("a")
            video_id = t.attrs["href"].replace("/video/", "").split("/")[0]
            title = n.find(class_="title").find("a").get_text()
            description = n.find(class_="description hidden-xs").get_text()
            poster = n.find(
                class_="image-container").find("img").attrs['data-src']
            duration = n.find(class_="video-duration").get_text()
            date= n.find(class_="details").find("span").get_text()

        except AttributeError as e:
            print("**************** ATTRIBUTE_ERROR "+str(e))
            print(str(n))
            video_id = title = description = poster = duration = date = "ERROR PARSING"

        s = PlaylistEntry(
            video_id=video_id, description=description, title=title, poster=poster, duration=duration, date=date)
        playlist.append(s)

    return pickle.dumps(playlist)

""" def _get_channel(cookies, channel):
    videos = []

    url = "https://www.bitchute.com/feeds/rss/channel/"+channel
    req = requests.get(url)

    s=req.text.encode('utf8', 'replace') # Python and unicode = shit

    dom = xml.dom.minidom.parseString(s)

    channel_name="xx"#dom.getElementsByTagName("channel").getElementsByTagName("title")

    items = dom.getElementsByTagName("item")
    for item in items:
        title=item.getElementsByTagName('title')[0].childNodes[0].nodeValue
        #print(item.getElementsByTagName('link')[0].childNodes[0].nodeValue)
        description=item.getElementsByTagName('description')[0].childNodes[0].nodeValue
        #print(item.getElementsByTagName('pubDate')[0].childNodes[0].nodeValue)
        video_id=item.getElementsByTagName('guid')[0].childNodes[0].nodeValue
        poster=item.getElementsByTagName('enclosure')[0].attributes['url'].childNodes[0].nodeValue

        s = ChannelEntry(video_id=video_id, description=description,
                         title=title, poster=poster, channel_name=channel_name)
        videos.append(s)

    return pickle.dumps(videos) """

def _get_channel(channel, page, cookies):
    offset=page*25
    
    videos = []

    Referer = "https://www.bitchute.com/channel/"

    url = "https://www.bitchute.com/channel/"+channel+"/extend/"

    token = cookies['csrftoken']

    post_data = {'csrfmiddlewaretoken': token,
                 'offset': offset}
    headers = {'Referer': Referer, "User-Agent": "Bitchute Kodi-Addon/1"}
    response = requests.post(
        url, data=post_data, headers=headers, cookies=cookies)
    
    req=json.loads(response.text)

    soup = BeautifulSoup(req["html"], "html.parser")

    try:
        containers = soup.find_all(class_="channel-videos-container")
    except AttributeError as e:
        print("**************** ATTRIBUTE_ERROR "+str(e))
        print("****************: ", channel)
        containers = []                   # the looping will skip later
        #channel_name = "ERROR PARSING"

    duration=""
    date=""

    for n in containers:

        try:

            t = n.find(class_="channel-videos-title").find("a")
            video_id = t.attrs["href"].split("/")[2]
            title = t.get_text()

            date=n.find(class_="channel-videos-details").find("span").get_text()
            duration=n.find(class_="video-duration").get_text()

            description = n.find(class_="channel-videos-text").get_text()

            poster = n.find(
                class_="channel-videos-image").find("img").attrs['data-src']

        except AttributeError as e:
            print("**************** ATTRIBUTE_ERROR "+str(e))
            print(str(n))
            video_id = title = description = poster = "ERROR PARSING"

        s = ChannelEntry(video_id=video_id, description=description,
                         title=title, poster=poster, channel_name="", date=date, duration=duration)
        videos.append(s)

    return pickle.dumps(videos)


def _get_feed(cookies):

    subs = get_subscriptions()

    feed = []
    for sub in subs:

        channel = get_channel(sub.channel,0)
        vid = channel[0]  # The latest video
        feed_item = PlaylistEntry(video_id=vid.video_id, description=vid.description,
                                  title=vid.title, poster=vid.poster, channel_name=vid.channel_name, date=vid.date, duration=vid.duration)
        feed.append(feed_item)

    return pickle.dumps(feed)

# blocked out for now. This uses a feature of bitchute that returns an RSS feed for a channel - much easier, but it's XML
# the XML processor  ElementTree isn't ready for KODI 19 - with Python 3. So stay with the HTML scraping for now
# def get_channel(self, channel):

#     """
#     get channel uses an interesting feature of Bitchute... generating an RSS feed for a channel by using a
#     URL. Get the channel and the scrape the HTML. Allowing you to view the contents
#     of a channel without actually logging in. Just request the XML and parse it. It just needs the channel name
#     and add the "rss" bit in. Possiblity of maintaining a subs list outside of bitchute
#     """

#     videos = []

#     url = "https://www.bitchute.com/feeds/rss/channel/"+channel
#     req = requests.get(url)

#     s=req.text.encode('utf8', 'replace')   # python2 is crap with unicode. it gets an exception without this
#     root=ET.fromstring(s)

#     items=root.find('channel').findall('item')

#     # channel_id=soup.find(id_="canonical").attrs["href"].replace("https://www.bitchute.com/channel/","").strip("/")
#     channel_id = ""

#     for child in items:

#         title=child.find("title").text
#         video_id=child.find("link").text.split("/")[4]
#         description=child.find("description").text
#         #d=child.find("pubDate").text
#         poster=child.find("enclosure").attrib['url']

#         s = ChannelEntry(video_id=video_id, description=description,
#                             title=title, poster=poster, channel_id=channel_id)
#         videos.append(s)

#     return videos


def _get_recently_active(cookies):

    subs = []

    url = "https://www.bitchute.com/channels/"

    req = requests.get(url, cookies=cookies, headers={"User-Agent": "Bitchute Kodi-Addon/1"})

    soup = BeautifulSoup(req.text, "html.parser")

    containers = soup.find_all(class_="channel-card")

    for n in containers:
        try:
            channel_image = n.find("a").find("img").attrs["data-src"]
            channel = n.find("a").attrs["href"].replace("/channel/", "")
            name = n.find(class_="channel-card-title").get_text()

        except AttributeError as e:
            print("**************** ATTRIBUTE_ERROR "+str(e))
            print(str(n))
            channel_image = channel = name = "ERROR PARSING"

        s = Subscription(name=name, channel=channel,
                         description="", channel_image=channel_image)
        subs.append(s)

    return pickle.dumps(subs)


def _get_video(cookies, video_id):

    url = "https://www.bitchute.com/video/"+video_id
    req = requests.get(url, cookies=cookies, headers={"User-Agent": "Bitchute Kodi-Addon/1"})

    soup = BeautifulSoup(req.text, "html.parser")

    try:
        videoURL = soup.find("source").attrs["src"]
        poster = soup.find("video").attrs["poster"]
        title = str(soup.find(id="video-title").contents[0])

    except AttributeError as e:
        print("**************** ATTRIBUTE_ERROR "+str(e))
        print(video_id)
        videoURL = poster = title = "ERROR PARSING"

    video = Video(videoURL=videoURL, poster=poster,
                  title=title, description="")

    return (pickle.dumps(video))


def _search(cookies, search_for):

    results = []

    Referer = "https://www.bitchute.com/search/"

    url = "https://www.bitchute.com/api/search/list/"

    token = cookies['csrftoken']

    post_data = {'csrfmiddlewaretoken': token,
                 'query': search_for, 'kind': 'video'}
    headers = {'Referer': Referer, "User-Agent": "Bitchute Kodi-Addon/1"}
    response = requests.post(
        url, data=post_data, headers=headers, cookies=cookies)
    val = json.loads(response.text)

    for result in val["results"]:
        video_id = result["id"]
        title = result["name"]
        description = result["description"]
        channel_name = result["channel_name"]
        poster = result["images"]["thumbnail"]
        r = SearchResult(video_id=video_id, title=title,
                         description=description, channel_name=channel_name, poster=poster)

        results.append(r)

    return pickle.dumps(results)

# Wrappers to ensure the subs, notifications, playlists are cached for 15 minutes


def get_subscriptions():
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_subscriptions, cookies))

    return []


def get_notifications():
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_notifications, cookies))

    return []


def get_playlist(playlist):
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_playlist, cookies, playlist))

    return []


def get_channel(channel, page):
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_channel, channel, page, cookies))

    return []


def get_popular():
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_popular, cookies))

    return []


def get_trending():
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_trending, cookies))

    return []


def get_feed():
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_feed, cookies))

    return []


def search(search_for):
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_search, cookies, search_for))

    return []


def get_recently_active():
    global data_cache
    cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_recently_active, cookies))

    return []


def get_video(video_id):
    global data_cache
    cookies = []
    success = True
    #cookies, success = bt_login()
    if success:
        return pickle.loads(data_cache.cacheFunction(_get_video, cookies, video_id))

    return []
