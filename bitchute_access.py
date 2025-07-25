import json
import pickle

import requests
import xbmcaddon
from bs4 import BeautifulSoup
from xbmcgui import Dialog
import xbmc

from cache import data_cache, login_cache

USER_AGENT = "Bitchute Kodi-Addon/1"
REQUEST_TIMEOUT = 15
addon = xbmcaddon.Addon()

class Subscription():
    def __init__(self, name, channel, description, channel_image):
        self.name = name
        self.channel = channel
        self.description = description
        self.channel_image = channel_image

class Video():
    def __init__(self, video_id, video_url, poster, title):
        self.video_id = video_id
        self.video_url = video_url
        self.poster = poster
        self.title = title

class NotificationEntry():
    def __init__(self, video_id, title, description):
        self.video_id = video_id
        self.title = title
        self.description = description

class SearchEntry():
    def __init__(self, video_id, description, title, poster, channel_name):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.poster = poster
        self.channel_name = channel_name

class ChannelEntry():
    def __init__(self, video_id, title, description, channel_name=u"", date=0, duration=0, poster=""):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.channel_name = channel_name
        self.date = date
        self.duration = duration
        self.poster = poster

class PlaylistEntry():
    def __init__(self, video_id, description, title, channel_name=u"", duration=u"", date=u"", poster=""):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.channel_name = channel_name
        self.date = date
        self.duration = duration
        self.poster = poster

DEFAULT_HEADERS = {"User-Agent": USER_AGENT}

def _get(url, cookies=[], headers=DEFAULT_HEADERS):
    xbmc.log("GET request: " + url)
    resp = requests.get(url, cookies=cookies, timeout=REQUEST_TIMEOUT, headers=headers)
    return resp

def _post(url, data, cookies=[], headers=DEFAULT_HEADERS):
    xbmc.log("POST request: " + url)
    resp = requests.post(url, data=data, headers=headers, cookies=cookies,
                         timeout=REQUEST_TIMEOUT)
    return resp

def BitchuteLogin(username, password):
    url = "https://old.bitchute.com/accounts/login/"
    resp = _get(url)

    if (resp.status_code!=200):
        return None, False

    csrfJar = resp.cookies
    baseURL = "https://old.bitchute.com"
    post_data = { 'csrfmiddlewaretoken': resp.cookies["csrftoken"],
                 'username': username, 'password': password }
    headers = { 'Referer': baseURL + "/", 'Origin': baseURL, "User-Agent": USER_AGENT }
    response = _post(baseURL + "/accounts/login/", data=post_data,
                             headers=headers, cookies=resp.cookies)

    # it's the cookies that carry forward the token/ids
    logged_in = False
    if 200 == response.status_code:
        if json.loads(response.text)['success'] == True:
            csrfJar = response.cookies
            logged_in = True

    # the cookies object has to be pickled or Kodi's cache will never recognise it as cache and keep refreshing it
    return pickle.dumps(csrfJar), logged_in

def bt_login(show_dialog=True):
    global login_cache
    username = xbmcaddon.Addon().getSetting("user")
    password = xbmcaddon.Addon().getSetting("password")
    pickled_cookies, success = login_cache.cacheFunction(BitchuteLogin, username, password)

    if not success:
        clear_cache(login=True, data=True)
        if show_dialog:
            q = Dialog()
            q.ok("Login failed", "Unable to login to Bitchute with the details provided")

        return [], False

    cookies = pickle.loads(pickled_cookies)
    return cookies, True

def _get_subscriptions(cookies):
    url = "https://old.bitchute.com/subscriptions/"
    resp = _get(url, cookies=cookies)

    soup = BeautifulSoup(resp.text, "html.parser")
    containers = soup.find_all(class_="subscription-container")

    subs = []
    for sub in containers:
        try:
            channel = sub.find("a").attrs["href"].split("/")[1]
            channel_image = sub.find("a").find("img").attrs["data-src"]
            name = sub.find(class_="subscription-name").get_text()
            channel = sub.find(class_="spa").attrs["href"].replace("/channel/", "")
            description = sub.find(class_="subscription-description-text").get_text()

            sub = Subscription(name=name, channel=channel,
                             description=description, channel_image=channel_image)
            subs.append(sub)
        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    subs.sort(key=lambda sub: str.lower(sub.name))

    return pickle.dumps(subs)

def _get_notifications(cookies):
    url = "https://old.bitchute.com/notifications/"
    resp = _get(url, cookies=cookies)

    soup = BeautifulSoup(resp.text, "html.parser")
    containers = soup.find_all(class_="notification-item")

    notifs = []
    for n in containers:
        try:
            video_id = n.find(class_="notification-view").attrs["href"].split("/")[2]
            title = n.find(class_="notification-target").get_text()
            description = n.find(class_="notification-detail").get_text()

            notif = NotificationEntry(video_id=video_id, title=title, description=description)
            notifs.append(notif)
        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    return pickle.dumps(notifs)

def _build_playlist_common(listing_id, cookies):
    url = "https://old.bitchute.com/"
    resp = _get(url, cookies=cookies)
    cookies = resp.cookies

    soup = BeautifulSoup(resp.text, "html.parser")
    popular = soup.find(id=listing_id)
    containers = popular.find_all(class_="video-card")

    playlist = []
    for n in containers:
        try:
            poster = n.find("img").attrs["data-src"]
            video_id = n.find(class_="video-card-id hidden").get_text()
            title = n.find(class_="video-card-title").find("a").get_text()
            channel_name = n.find(
                class_="video-card-channel").find("a").get_text()
            description = ""
            duration = n.find(class_="video-duration").get_text()
            date = n.find(class_="video-card-published").get_text()

            s = PlaylistEntry(video_id=video_id, description=description, title=title,
                              channel_name=channel_name, date=date, duration=duration, poster=poster)
            playlist.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    return pickle.dumps(playlist)

def _get_popular(cookies):
    return _build_playlist_common("listing-popular", cookies)

def _get_feed(cookies):
    return _build_playlist_common("listing-subscribed", cookies)

def _get_trending(cookies):
    url = "https://old.bitchute.com/"
    resp = _get(url, cookies=cookies)
    cookies = resp.cookies

    soup = BeautifulSoup(resp.text, "html.parser")
    popular = soup.find(id="listing-trending")
    containers = popular.find_all(class_="video-result-container")

    playlist = []
    for n in containers:
        try:
            video_id = n.find(class_="video-result-image-container").find("a").attrs["href"].split("/")[2].replace("/", "")
            poster = n.find(class_="video-result-image").find("img").attrs["data-src"]
            title = n.find(class_="video-result-title").find("a").get_text()
            channel_name = n.find(class_="video-result-channel").find("a").get_text()
            description = n.find(class_="video-result-text").find("p").get_text()
            duration = n.find(class_="video-duration").get_text()
            date = n.find(class_="video-result-details").find("span").get_text()

            s = PlaylistEntry(video_id=video_id, description=description, title=title,
                              channel_name=channel_name, date=date, duration=duration, poster=poster)
            playlist.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    return pickle.dumps(playlist)

def _get_playlist(cookies, playlist_name):
    url = "https://old.bitchute.com/playlist/"+playlist_name+"/"
    resp = _get(url, cookies=cookies)

    soup = BeautifulSoup(resp.text, "html.parser")
    containers = soup.find_all(class_="playlist-video")

    playlist = []
    for n in containers:
        try:
            t = n.find(class_="text-container").find("a")
            video_id = t.attrs["href"].replace("/video/", "").split("/")[0]
            title = n.find(class_="title").find("a").get_text()
            channel_name = n.find(class_="channel").find("a").get_text()
            description = n.find(class_="description hidden-xs").get_text()
            poster = n.find(class_="image-container").find("img").attrs['data-src']
            duration = n.find(class_="video-duration").get_text()
            date= n.find(class_="details").find("span").get_text()
            s = PlaylistEntry(video_id=video_id, description=description, title=title,
                              channel_name=channel_name, duration=duration, date=date, poster=poster)
            playlist.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    return pickle.dumps(playlist)

def _get_channel(cookies, channel, page, max_count=100):
    offset = page*25
    referer = "https://old.bitchute.com/channel/"
    url = "https://old.bitchute.com/channel/"+channel+"/extend/"
    token = cookies['csrftoken']
    post_data = {'csrfmiddlewaretoken': token, 'offset': offset}
    headers = {'referer': referer, "User-Agent": USER_AGENT}
    response = _post(url, data=post_data, headers=headers, cookies=cookies)
    resp = json.loads(response.text)

    soup = BeautifulSoup(resp["html"], "html.parser")
    try:
        containers = soup.find_all(class_="channel-videos-container")
    except AttributeError as e:
        xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
        xbmc.log("****************: ", channel)
        containers = []                   # the looping will skip later

    videos = []
    count = 0
    for n in containers:
        if count > max_count:
            break
        try:
            t = n.find(class_="channel-videos-title").find("a")
            video_id = t.attrs["href"].split("/")[2]
            title = t.get_text()
            date = n.find(class_="channel-videos-details").find("p").get_text()
            duration = n.find(class_="video-duration").get_text()
            description = n.find(class_="channel-videos-text").find("p").get_text()
            poster = n.find(class_="channel-videos-image").find("img").attrs['data-src']

            s = ChannelEntry(video_id=video_id, description=description, title=title,
                             channel_name=channel, date=date, duration=duration, poster=poster)
            videos.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

        count = count + 1

    return pickle.dumps(videos)

def _get_feed_sub_legacy(params):
    (sub, cookies) = params
    channel = pickle.loads(_get_channel(cookies, sub.channel, 0, max_count=1))
    feed_item = None
    if len(channel) > 0:
        chan = channel[0]  # The latest video
        feed_item = PlaylistEntry(video_id=chan.video_id, description=chan.description,
                                  title=chan.title, channel_name=sub.name, date=chan.date, duration=chan.duration, poster=chan.poster)
    return feed_item

def _get_feed_legacy(cookies):
    subs = get_subscriptions()

    params = []
    for sub in subs:
        params.append((sub, cookies))

    feed = []
    for param in params:
        feed.append(_get_feed_sub_legacy(param))

    return pickle.dumps(feed)

def _get_recently_active(cookies):
    url = "https://old.bitchute.com/channels/"
    resp = _get(url, cookies=cookies)

    soup = BeautifulSoup(resp.text, "html.parser")
    containers = soup.find_all(class_="channel-card")

    subs = []
    for n in containers:
        try:
            channel_image = n.find("a").find("img").attrs["data-src"]
            channel = n.find("a").attrs["href"].replace("/channel/", "")
            name = n.find(class_="channel-card-title").get_text()

            s = Subscription(name=name, channel=channel, description="",
                             channel_image=channel_image)
            subs.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    return pickle.dumps(subs)


def _get_video(cookies, video_id):
    url = f'https://old.bitchute.com/api/beta9/embed/{video_id}/'
    resp = _get(url, cookies=cookies)
    backoff = 1
    while resp.status_code == 429: # rate limited
        if backoff > 128:
            raise Exception("Max rate-limiting backoff of 256 seconds reached: Aborting")

        xbmc.log("Rate limited. Backing off for {} seconds".format(backoff))
        xbmc.sleep(backoff)

        resp = _get(url)

        backoff *= 2

    # BeautifulSoup can't process JS but the video values are embedded
    # in the embedded video viewer script JS.
    def extract_js_variable(var_name, term_symbol):
        sstr = 'var ' + var_name + ' = '
        off = resp.text.find(sstr)
        soff = resp.text.find(term_symbol, off)
        while resp.text[soff-1] == '\\':
            soff = resp.text.find(term_symbol, soff+1)
        eoff = resp.text.find(term_symbol, soff+1)
        while resp.text[eoff-1] == '\\':
            eoff = resp.text.find(term_symbol, eoff+1)
        return resp.text[soff+1:eoff].replace('\\','')

    video_name = extract_js_variable("video_name", "\"")
    thumbnail_url = extract_js_variable("thumbnail_url", "'")

    if addon.getSettingBool('high_resolution_thumbnails'):
        thumbnail_url = thumbnail_url.replace('320','640').replace('180', '360')

    media_url = extract_js_variable("media_url", "'")

    xbmc.log("Scraping video info: {}\nMedia URL: {}\nThumbnail URL: {}\nScrape URL: {}\n".format(video_name, media_url, thumbnail_url, url))

    return pickle.dumps(Video(video_id=video_id, video_url=media_url, poster=thumbnail_url,
                  title=video_name))

def _search(cookies, query, page):
    # Extract timestamp and nonce parameters from searchAuth function
    # embedded in the search HTML page. A new timestamp, nonce pair
    # is required for each search API request.

    url = "https://old.bitchute.com/search/"
    response = _get(url, cookies=cookies)

    text = response.text
    str = 'searchAuth('
    s = text.find(str) + len(str)
    e = text.find(")", s+1)
    params = text[s:e].split(',', 2)
    timestamp = params[0].strip()[1:-1]
    nonce = params[1].strip()[1:-1]

    url = "https://old.bitchute.com/api/search/list/"
    post_data = {
            'csrfmiddlewaretoken': response.cookies['csrftoken'],
            'timestamp' : timestamp,
            'nonce': nonce,
            'query': query,
            'kind': 'video',
            'duration': '',
            'sort': 'new',
            'page': page,
            }
    headers = {
            'referer': "https://old.bitchute.com/search/",
            'origin': "https://old.bitchute.com",
            "User-Agent": USER_AGENT,
            }
    response = _post(url, data=post_data, headers=headers, cookies=response.cookies)
    val = json.loads(response.text)

    results = []
    for result in val["results"]:
        video_id = result["id"]
        title = result["name"]
        description = result["description"].lstrip().rstrip().replace('<p>','').replace('</p>','')
        channel_name = result["channel_name"]
        poster = result["images"]["thumbnail"]
        r = SearchEntry(video_id=video_id, title=title, description=description,
                        channel_name=channel_name, poster=poster)
        results.append(r)

    return pickle.dumps(results)

# Wrappers to ensure the subs, notifications, playlists are cached for 15 minutes

def get_page(login, funct, *args):
    if login:
        cookies, success = bt_login()
    else:
        cookies = []
        success = True

    if success:
        if addon.getSettingBool("enable_cache"):
            return pickle.loads(data_cache.cacheFunction(funct, cookies, *args))
        else:
            return pickle.loads(funct(cookies, *args))

    return []

def get_subscriptions():
    return get_page(True, _get_subscriptions)

def get_notifications():
    return get_page(True, _get_notifications)

def get_playlist(playlist):
    return get_page(True, _get_playlist, playlist)

def get_channel(channel, page, max_count=100):
    return get_page(True, _get_channel, channel, page, max_count)

def get_popular():
    return get_page(True, _get_popular)

def get_trending():
    return get_page(True, _get_trending)

def get_feed():
    if xbmcaddon.Addon().getSettingBool("legacy_feed_behavior"):
        get_feed_func = _get_feed_legacy
    else:
        get_feed_func = _get_feed
    return get_page(True, get_feed_func)

def search(query, page):
    return get_page(True, _search, query, page)

def get_recently_active():
    return get_page(True, _get_recently_active)

def get_video(video_id):
    return pickle.loads(_get_video([], video_id))

def clear_cache(login=True, data=True):
    if login:
        login_cache.delete('%')

    if data:
        data_cache.delete('%')
