from bs4 import BeautifulSoup
import json
import requests
import xbmcaddon
from xbmcgui import Dialog
import pickle
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

# add version to name so if there is a version bump it avoid cache issues
login_cache = StorageServer.StorageServer(
    "bitchute_logindetails"+xbmcaddon.Addon().getAddonInfo('version'), 24)  # refresh login per day (24hrs)
data_cache = StorageServer.StorageServer(
    "bitchute_data"+xbmcaddon.Addon().getAddonInfo('version'), 0.25)  # reloads subs per 15m


class Subscription():

    def __init__(self, name, channel, description, channel_image):
        self.name = name
        self.channel = channel.replace("/channel/", "")
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

    def __init__(self, video_id, poster, title, description, channel_name=""):
        self.video_id = video_id
        self.poster = poster
        self.title = title
        self.description = description
        self.channel_name = channel_name


class PlaylistEntry():

    def __init__(self, video_id, description, title, poster, channel_name=""):
        self.video_id = video_id
        self.description = description
        self.title = title
        self.poster = poster
        self.channel_name = channel_name


def BitchuteLogin():
    username = xbmcaddon.Addon().getSetting("user")
    password = xbmcaddon.Addon().getSetting("password")
    token = ""

    url = "https://www.bitchute.com/accounts/login/"
    req = requests.get(url)

    csrfJar = req.cookies
    soup = BeautifulSoup(req.text, "html.parser")
    metas = soup.find_all("input")
    for meta in metas:
        if meta.attrs['name'] == "csrfmiddlewaretoken":
            token = meta.attrs['value']

    if token != "":

        baseURL = "https://www.bitchute.com"
        post_data = {'csrfmiddlewaretoken': token,
                     'username': username, 'password': password}
        headers = {'Referer': baseURL + "/", 'Origin': baseURL}
        response = requests.post(
            baseURL + "/accounts/login/", data=post_data, headers=headers, cookies=csrfJar)

        # it's the cookies that carry forward the token/ids
        if 200 == response.status_code:
            if json.loads(response.text)['success'] == True:
                csrfJar = response.cookies

    # the cookies object has to be pickled or Kodi's cache will never recognise it as cache and keep refreshing it
    return pickle.dumps(csrfJar)


def bt_login():
    global login_cache
    cookies = login_cache.cacheFunction(BitchuteLogin)
    return pickle.loads(cookies)


def _get_subscriptions():

    cookies = bt_login()

    url = "https://www.bitchute.com/subscriptions/"
    req = requests.get(url, cookies=cookies)

    #self.csrfJar = req.cookies

    subs = []
    soup = BeautifulSoup(req.text, "html.parser")

    containers = soup.find_all(class_="subscription-container")

    for sub in containers:
        channel = sub.find("a").attrs["href"].split("/")[1]
        channel_image = sub.find("a").find("img").attrs["data-src"]
        name = sub.find(class_="subscription-name").get_text()
        # description = sub.find(
        #    class_="subscription-description").get_text()
        channel = sub.find(class_="spa").attrs["href"]
        #last_video = sub.find(class_="subscription-last-video").get_text()
        description = sub.find(
            class_="subscription-description-text").get_text()
        s = Subscription(name=name, channel=channel,
                         description=description, channel_image=channel_image)
        subs.append(s)

    return pickle.dumps(subs)


def _get_notifications():

    cookies = bt_login()
    notifs = []

    url = "https://www.bitchute.com/notifications/"
    req = requests.get(url, cookies=cookies)

    soup = BeautifulSoup(req.text, "html.parser")

    containers = soup.find_all(class_="notification-item")

    for n in containers:
        video_id = n.find(
            class_="notification-view").attrs["href"].split("/")[2]
        title = n.find(
            class_="notification-target").get_text()
        description = n.find(
            class_="notification-detail").get_text()

        notif = Notification(video_id=video_id, title=title,
                             description=description)
        notifs.append(notif)

    return pickle.dumps(notifs)


def _get_popular():

    cookies = bt_login()

    playlist = []

    url = "https://www.bitchute.com/"

    req = requests.get(url, cookies=cookies)
    cookies = req.cookies

    soup = BeautifulSoup(req.text, "html.parser")

    popular = soup.find(id="listing-popular")

    containers = popular.find_all(class_="video-card")

    for n in containers:
        poster = n.find("img").attrs["data-src"]
        video_id = n.find(class_="video-card-id hidden").get_text()
        title = n.find(class_="video-card-title").find("a").get_text()
        channel_name = n.find(class_="video-card-channel").find("a").get_text()
        description = ""

        s = PlaylistEntry(
            video_id=video_id, description=description, title=title, poster=poster, channel_name=channel_name)
        playlist.append(s)

    return pickle.dumps(playlist)


def _get_trending():

    cookies = bt_login()

    playlist = []

    url = "https://www.bitchute.com/"

    req = requests.get(url, cookies=cookies)
    cookies = req.cookies

    soup = BeautifulSoup(req.text, "html.parser")

    popular = soup.find(id="listing-trending")

    containers = popular.find_all(class_="video-result-container")

    for n in containers:
        video_id = n.find(class_="video-result-image-container").find(
            "a").attrs["href"].split("/")[2].replace("/", "")
        poster = n.find(
            class_="video-result-image").find("img").attrs["data-src"]
        title = n.find(class_="video-result-title").find("a").get_text()
        channel_name = n.find(
            class_="video-result-channel").find("a").get_text()
        description = n.find(class_="video-result-text").get_text()

        s = PlaylistEntry(
            video_id=video_id, description=description, title=title, poster=poster, channel_name=channel_name)
        playlist.append(s)

    return pickle.dumps(playlist)


def _get_playlist(playlist_name):

    #"favorites", "watch-later"
    cookies = bt_login()

    playlist = []

    url = "https://www.bitchute.com/playlist/"+playlist_name+"/"

    req = requests.get(url, cookies=cookies)

    soup = BeautifulSoup(req.text, "html.parser")

    containers = soup.find_all(class_="playlist-video")

    for n in containers:
        if (n.find(class_="text-container")is None):
            q=Dialog()
            q.ok("NULL text-container for",playlist_name)
            print ("**************************** NULL text-container for: ", playlist_name)

        t = n.find(class_="text-container").find("a")
        video_id = t.attrs["href"].replace("/video/", "").split("/")[0]
        title = n.find(class_="title").find("a").get_text()
        description = n.find(class_="description hidden-xs").get_text()
        poster = n.find(
            class_="image-container").find("img").attrs['data-src']

        s = PlaylistEntry(
            video_id=video_id, description=description, title=title, poster=poster)
        playlist.append(s)

    return pickle.dumps(playlist)


def _get_channel(channel):

    cookies = bt_login()

    videos = []

    url = "https://www.bitchute.com/channel/"+channel
    req = requests.get(url, cookies=cookies)

    soup = BeautifulSoup(req.text, "html.parser")

    channel_name = soup.find(
        class_="channel-banner").find(class_="name").find("a").get_text()
    containers = soup.find_all(class_="channel-videos-container")

    for n in containers:

        if n.find(class_="channel-videos-title") is None:
            q=Dialog()
            q.ok("get_channel error channel-vides is NONE",channel)
            print ("**************************** NULL channel-videos-title for: ", channel)

        t = n.find(class_="channel-videos-title").find("a")
        video_id = t.attrs["href"].split("/")[2]
        title = t.get_text()

        description = n.find(class_="channel-videos-text").get_text()

        poster = n.find(
            class_="channel-videos-image").find("img").attrs['data-src']
        s = ChannelEntry(video_id=video_id, description=description,
                         title=title, poster=poster, channel_name=channel_name)
        videos.append(s)

    return pickle.dumps(videos)


def _get_feed():

    subs = get_subscriptions()

    feed = []
    for sub in subs:

        channel = get_channel(sub.channel)
        vid = channel[0]  # The latest video
        feed_item = PlaylistEntry(video_id=vid.video_id, description=vid.description,
                                  title=vid.title, poster=vid.poster, channel_name=vid.channel_name)
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

def _get_recently_active():

    cookies = bt_login()

    subs = []

    url = "https://www.bitchute.com/channels/"

    req = requests.get(url, cookies=cookies)

    soup = BeautifulSoup(req.text, "html.parser")

    containers = soup.find_all(class_="channel-card")

    for n in containers:
        channel_image=n.find("a").find("img").attrs["data-src"]
        channel=n.find("a").attrs["href"]
        name=n.find(class_="channel-card-title").get_text()
        s = Subscription(name=name, channel=channel, description="", channel_image=channel_image)
        subs.append(s)

    return pickle.dumps(subs)


def get_video(video_id):
    cookies = bt_login()

    url = "https://www.bitchute.com/video/"+video_id
    req = requests.get(url, cookies=cookies)

    soup = BeautifulSoup(req.text, "html.parser")

    videoURL = soup.find("source").attrs["src"]
    poster = soup.find("video").attrs["poster"]
    title = soup.find(id="video-title").contents[0]

    video = Video(videoURL=videoURL, poster=poster,
                  title=title, description="")

    return (video)

def _search(search_for):
    cookies = bt_login()

    results=[]

    Referer = "https://www.bitchute.com/search/"

    url="https://www.bitchute.com/api/search/list/"

    token = cookies['csrftoken']

    post_data = {'csrfmiddlewaretoken': token, 'query': search_for, 'kind': 'video'}
    headers = {'Referer': Referer}
    response = requests.post(url, data=post_data, headers=headers, cookies=cookies)
    val=json.loads(response.text)

    for result in val["results"]:
        video_id=result["id"]
        title=result["name"]
        description=result["description"]
        channel_name=result["channel_name"]
        poster=result["images"]["thumbnail"]
        r=SearchResult(video_id=video_id, title=title, description=description, channel_name=channel_name, poster=poster)

        results.append(r)

    return pickle.dumps(results)

# Wrappers to ensure the subs, notifications, playlists are cached for 15 minutes
def get_subscriptions():
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_get_subscriptions))


def get_notifications():
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_get_notifications))


def get_playlist(playlist):
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_get_playlist, playlist))


def get_channel(channel):
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_get_channel, channel))


def get_popular():
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_get_popular))


def get_trending():
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_get_trending))


def get_feed():
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_get_feed))

def search(search_for):
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_search, search_for))

def get_recently_active():
    global data_cache
    return pickle.loads(data_cache.cacheFunction(_get_recently_active))
