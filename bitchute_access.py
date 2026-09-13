import base64
import datetime
import json
import pickle
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import xbmcaddon
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from xbmcgui import Dialog
import xbmc

from cache import data_cache, login_cache, reaction_cache
from comment_window import CommentWindow

USER_AGENT = "Bitchute Kodi-Addon/1"
REQUEST_TIMEOUT = 15
addon = xbmcaddon.Addon()

class VideoUnavailableError(Exception):
    """Raised when a video's media URL cannot be extracted from its page."""
    pass

class Subscription():
    def __init__(self, name, channel, description, channel_image, subscribers=None,
                 channel_id=None):
        self.name = name
        self.channel = channel
        self.description = description
        self.channel_image = channel_image
        self.subscribers = subscribers
        self.channel_id = channel_id

class Video():
    def __init__(self, video_id, video_url, poster, title):
        self.video_id = video_id
        self.video_url = video_url
        self.poster = poster
        self.title = title

class NotificationEntry():
    def __init__(self, video_id, title, description, channel_name=u"", channel_id=None):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.channel_name = channel_name
        self.channel_id = channel_id

class SearchEntry():
    def __init__(self, video_id, description, title, poster, channel_name,
                 upvotes=None, downvotes=None, channel_id=None, user_vote=0):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.poster = poster
        self.channel_name = channel_name
        self.upvotes = upvotes
        self.downvotes = downvotes
        self.channel_id = channel_id
        self.user_vote = user_vote

class ChannelEntry():
    def __init__(self, video_id, title, description, channel_name=u"", date=0, duration=0, poster="",
                 upvotes=None, downvotes=None, channel_id=None, user_vote=0):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.channel_name = channel_name
        self.date = date
        self.duration = duration
        self.poster = poster
        self.upvotes = upvotes
        self.downvotes = downvotes
        self.channel_id = channel_id
        self.user_vote = user_vote

class PlaylistEntry():
    def __init__(self, video_id, description, title, channel_name=u"", duration=u"", date=u"", poster="",
                 upvotes=None, downvotes=None, channel_id=None, user_vote=0):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.channel_name = channel_name
        self.date = date
        self.duration = duration
        self.poster = poster
        self.upvotes = upvotes
        self.downvotes = downvotes
        self.channel_id = channel_id
        self.user_vote = user_vote

class CommentEntry():
    def __init__(self, id, parent_id, creator, fullname, content, upvote_count, downvote_count, user_vote, profile_picture_url, created_by_current_user):
        self.id = id
        self.parent_id = parent_id
        self.creator = creator
        self.fullname = fullname
        self.content = content
        self.upvote_count = upvote_count
        self.downvote_count = downvote_count
        self.user_vote = 0 if user_vote == None else 1 if user_vote == True else -1
        self.profile_picture_url = profile_picture_url
        self.created_by_current_user = created_by_current_user

DEFAULT_HEADERS = {"User-Agent": USER_AGENT}

# Shared session for connection pooling and transparent retries. urllib3's
# default retry method set excludes POST, so comment/vote writes are never
# replayed; only idempotent requests are retried.
_session = requests.Session()
_retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.5,
    status_forcelist=(500, 502, 503, 504),
)
_adapter = HTTPAdapter(max_retries=_retry)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

# Bitchute browse categories. Ordered as presented in the site's nav.
# (slug, display name)
CATEGORIES = [
    ("animation", "Anime & Animation"),
    ("arts", "Arts & Literature"),
    ("vehicles", "Auto & Vehicles"),
    ("beauty", "Beauty & Fashion"),
    ("finance", "Business & Finance"),
    ("cuisine", "Cuisine"),
    ("diy", "DIY & Gardening"),
    ("education", "Education"),
    ("entertainment", "Entertainment"),
    ("gaming", "Gaming"),
    ("health", "Health & Medical"),
    ("music", "Music"),
    ("news", "News & Politics"),
    ("family", "People & Family"),
    ("animals", "Pets & Wildlife"),
    ("science", "Science & Technology"),
    ("spirituality", "Spirituality & Faith"),
    ("sport", "Sports & Fitness"),
    ("travel", "Travel"),
    ("vlogging", "Vlogging"),
]

# Videos served per category page / per extend call.
CATEGORY_PAGE_SIZE = 24

# Channels served per discovery page / per extend call.
CHANNEL_PAGE_SIZE = 24

# Results served per search page, per result kind (videos/channels).
SEARCH_PAGE_SIZE = 10

# Videos served per homepage listing (popular/subscribed) extend call.
LISTING_PAGE_SIZE = 24

# Notifications served per page / per extend call.
NOTIFICATION_PAGE_SIZE = 10

# Videos served per playlist page / per extend call.
PLAYLIST_PAGE_SIZE = 10

# Parallel workers used to fetch per-video vote counts and reactions. The
# beta API verifies credentials per request, so reactions benefit from more
# concurrency.
VOTE_FETCH_WORKERS = 16

# Seconds a per-video reaction is cached. Matches the data cache so listings
# are rebuilt with the same reaction state they were enriched with.
REACTION_CACHE_TTL = 900

def _get(url, cookies=[], headers=DEFAULT_HEADERS):
    resp = _session.get(url, cookies=cookies, timeout=REQUEST_TIMEOUT, headers=headers)
    xbmc.log(f"GET request: {url} ({resp.status_code})")
    return resp

def _post(url, data, cookies=[], headers=DEFAULT_HEADERS):
    resp = _session.post(url, data=data, headers=headers, cookies=cookies,
                         timeout=REQUEST_TIMEOUT)
    xbmc.log(f"POST request: {url} ({resp.status_code})")
    return resp

def _post_json(url, data, cookies=[], headers=DEFAULT_HEADERS, auth=None):
    resp = _session.post(url, json=data, headers=headers, cookies=cookies,
                         auth=auth, timeout=REQUEST_TIMEOUT)
    xbmc.log(f"POST request: {url} ({resp.status_code})")
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

def _channel_id_from_image(image_url):
    """Extract the channel ID from a channel or video cover image URL.

    Channel images are served from
    ``https://static-3.bitchute.com/live/channel_images/<channel_id>/<hash>.jpg``
    and video covers from
    ``https://static-3.bitchute.com/live/cover_images/<channel_id>/<hash>.jpg``.
    The channel ID is what the subscribe endpoint expects.
    """
    if not image_url:
        return None
    match = re.search(r"(?:channel_images|cover_images)/([^/]+)/", image_url)
    return match.group(1) if match else None

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
                             description=description, channel_image=channel_image,
                             channel_id=_channel_id_from_image(channel_image))
            subs.append(sub)
        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(sub))

    subs.sort(key=lambda sub: str.lower(sub.name))

    return pickle.dumps(subs)

def _get_notifications(cookies, page):
    """Return one page (NOTIFICATION_PAGE_SIZE notifications).

    Page 0 fetches ``/notifications/``. Later pages POST to
    ``/notifications/extend/`` (the AJAX mechanism behind the site's
    "SHOW MORE" button) and parse the returned HTML fragment.
    """
    referer = "https://old.bitchute.com/notifications/"

    if page == 0:
        resp = _get(referer, cookies=cookies)
        soup = BeautifulSoup(resp.text, "html.parser")
    else:
        token = cookies['csrftoken']
        post_data = {'csrfmiddlewaretoken': token, 'offset': page * NOTIFICATION_PAGE_SIZE}
        headers = {'referer': referer, "User-Agent": USER_AGENT}
        response = _post(referer + "extend/", data=post_data, headers=headers, cookies=cookies)
        resp = json.loads(response.text)
        soup = BeautifulSoup(resp["html"], "html.parser")

    containers = soup.find_all(class_="notification-item")

    # Notification entries don't carry the channel ID, but the detail text
    # starts with the channel's display name, which can be matched against
    # the subscription list.
    subscriptions = get_subscriptions()

    notifs = []
    for n in containers:
        try:
            video_id = n.find(class_="notification-view").attrs["href"].split("/")[2]
            title = n.find(class_="notification-target").get_text()
            description = n.find(class_="notification-detail").get_text()
            channel_name = description.rsplit(" - ", 1)[0].strip()
            channel = _find_subscription_by_name(channel_name, subscriptions)

            notif = NotificationEntry(video_id=video_id, title=title, description=description,
                                      channel_name=channel_name,
                                      channel_id=getattr(channel, 'channel_id', None) if channel else None)
            notifs.append(notif)
        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    return pickle.dumps(notifs)

def _find_subscription_by_name(name, subscriptions):
    """Return the subscription whose display name matches ``name``."""
    normalized = name.strip().casefold()
    for sub in subscriptions:
        if sub.name.strip().casefold() == normalized:
            return sub
    return None

def _strip_html(text):
    """Return plain text for a snippet of Bitchute HTML."""
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)

def _get_video_counts(cookies, video_id):
    """Fetch the upvote/downvote counts for a video.

    Returns ``(upvotes, downvotes)``, or ``(None, None)`` when the counts
    are unavailable so callers can omit them from the description.
    """
    try:
        token = cookies.get('csrftoken')
    except AttributeError:
        token = None

    if not token:
        token = _session.cookies.get('csrftoken')

    if not token:
        # The counts endpoint only needs a CSRF token, not a login.
        resp = _get("https://old.bitchute.com/")
        token = resp.cookies.get('csrftoken') or _session.cookies.get('csrftoken')

    if not token:
        xbmc.log("No CSRF token available; skipping vote counts for " + video_id)
        return None, None

    url = f"https://old.bitchute.com/video/{video_id}/counts/"
    post_data = {'csrfmiddlewaretoken': token}
    headers = {'referer': f"https://old.bitchute.com/video/{video_id}/",
               "User-Agent": USER_AGENT}

    backoff = 1
    try:
        response = _post(url, data=post_data, headers=headers, cookies=cookies)
        while response.status_code == 429 and backoff <= 4:
            xbmc.log("Vote counts rate limited. Backing off for {} seconds".format(backoff))
            xbmc.sleep(backoff * 1000)
            backoff *= 2
            response = _post(url, data=post_data, headers=headers, cookies=cookies)
    except requests.RequestException as e:
        xbmc.log("Could not fetch vote counts for {}: {}".format(video_id, e))
        return None, None

    if response.status_code != 200:
        xbmc.log("Vote counts request for {} returned {}".format(video_id, response.status_code))
        return None, None

    try:
        result = json.loads(response.text)
    except ValueError:
        xbmc.log("Vote counts for {} returned an unparseable response".format(video_id))
        return None, None

    if not result.get("success"):
        return None, None

    return result.get("like_count"), result.get("dislike_count")

def _get_video_auth():
    """Return the credentials used for Bitchute's beta API, if configured.

    The beta API authenticates with HTTP Basic auth (the same account
    credentials as the site login), which exposes the per-user reaction
    state that the old counts endpoint lacks.
    """
    user = addon.getSetting("user")
    password = addon.getSetting("password")
    if not user or not password:
        return None
    return (user, password)

def _fetch_video_reaction(video_id):
    """Fetch the logged-in user's reaction to a video.

    Returns ``(is_liked, is_disliked)``; failures degrade to no reaction so
    listings still render.
    """
    auth = _get_video_auth()
    if not auth:
        return False, False

    url = "https://api.bitchute.com/api/beta/video"
    headers = {'origin': "https://www.bitchute.com",
               'referer': "https://www.bitchute.com/",
               "User-Agent": USER_AGENT}
    try:
        response = _post_json(url, {'video_id': video_id}, headers=headers, auth=auth)
    except requests.RequestException as e:
        xbmc.log("Could not fetch reaction for {}: {}".format(video_id, e))
        return False, False

    if response.status_code != 200:
        xbmc.log("Reaction request for {} returned {}".format(video_id, response.status_code))
        return False, False

    try:
        result = response.json()
    except ValueError:
        xbmc.log("Reaction for {} returned an unparseable response".format(video_id))
        return False, False

    return bool(result.get("is_liked")), bool(result.get("is_disliked"))

def _cached_video_vote(video_id):
    """Return the cached vote for a video, or ``None`` when stale.

    The tuple is ``(is_liked, is_disliked, up_delta, down_delta, base_up,
    base_down)``. The deltas are the user's vote changes that Bitchute's
    counts had not reflected yet when the vote was cast, relative to the
    server counts in the base.

    StorageServer is not thread-safe, so this is only called from the main
    thread.
    """
    try:
        cached = reaction_cache.get("reaction_" + video_id)
    except Exception as e:
        xbmc.log("Could not read cached vote for {}: {}".format(video_id, e))
        return None

    if not cached:
        return None

    parts = cached.split(",")
    if len(parts) != 7:
        return None

    try:
        timestamp = float(parts[6])
    except ValueError:
        return None

    if time.time() - timestamp > REACTION_CACHE_TTL:
        return None

    try:
        return (parts[0] == "1", parts[1] == "1", int(parts[2]), int(parts[3]),
                int(parts[4]), int(parts[5]))
    except ValueError:
        return None

def _store_video_vote(video_id, reaction, up_delta=0, down_delta=0, base=(0, 0)):
    """Cache a vote, its optimistic count adjustment and the base counts."""
    is_liked, is_disliked = reaction
    try:
        reaction_cache.set("reaction_" + video_id, "{},{},{},{},{},{},{}".format(
            1 if is_liked else 0, 1 if is_disliked else 0, up_delta, down_delta,
            base[0], base[1], time.time()))
    except Exception as e:
        xbmc.log("Could not cache vote for {}: {}".format(video_id, e))

def apply_vote_adjustment(video_id, upvotes, downvotes, user_vote=0):
    """Apply the locally recorded vote to a video's displayed counts.

    Bitchute updates the public counts asynchronously, so while the server
    still reports the counts seen when the vote was cast, the local
    adjustment is added. Once the server counts move past that base, the
    adjustment is dropped. Also returns the user's current vote so callers
    can colorize the counts.
    """
    vote = _cached_video_vote(video_id)
    if vote is None:
        return upvotes, downvotes, user_vote

    is_liked, is_disliked, up_delta, down_delta, base_up, base_down = vote
    user_vote = 1 if is_liked else -1 if is_disliked else 0

    if upvotes is not None and downvotes is not None and \
       (upvotes, downvotes) == (base_up, base_down):
        upvotes = max(0, upvotes + up_delta)
        downvotes = max(0, downvotes + down_delta)

    return upvotes, downvotes, user_vote

def _get_video_vote(video_id):
    """Return the logged-in user's vote on a video.

    ``1`` for an upvote, ``-1`` for a downvote and ``0`` when the video has
    no vote. Always reads the live reaction so vote actions stay correct.
    """
    is_liked, is_disliked = _fetch_video_reaction(video_id)
    if is_liked:
        return 1
    if is_disliked:
        return -1
    return 0

def _record_vote(video_id, current, reaction, base):
    """Store a vote and the count adjustment Bitchute has not reflected yet.

    ``current`` is the vote before the change (1, -1 or 0), ``reaction`` the
    new one and ``base`` the server counts read just before voting.
    """
    base_up, base_down = base
    if base_up is None or base_down is None:
        # Without a server baseline there is no safe adjustment to make.
        _store_video_vote(video_id, reaction)
        return

    up_delta = (1 if reaction[0] else 0) - (1 if current == 1 else 0)
    down_delta = (1 if reaction[1] else 0) - (1 if current == -1 else 0)

    cached = _cached_video_vote(video_id)
    if cached is not None and (cached[4], cached[5]) == (base_up, base_down):
        # The server still reports the previous base, so keep accumulating.
        up_delta += cached[2]
        down_delta += cached[3]

    _store_video_vote(video_id, reaction, up_delta, down_delta, (base_up, base_down))

def _vote_video(cookies, video_id, vote_type):
    """Set or clear the user's vote on a video.

    ``vote_type`` is ``like``, ``dislike`` or ``clear``. Bitchute's vote
    endpoint toggles the submitted type, so the current vote is read first
    and the request is skipped when it would toggle the wanted vote back off.
    The vote and its count adjustment are recorded locally so descriptions
    can show the result before the server counts catch up.
    """
    if vote_type not in ('like', 'dislike', 'clear'):
        return {}

    auth = _get_video_auth()
    if not auth:
        return {}

    current = _get_video_vote(video_id)
    reaction = (vote_type == 'like', vote_type == 'dislike')
    base = _get_video_counts(cookies, video_id)

    if not ((vote_type == 'like' and current == 1) or
            (vote_type == 'dislike' and current == -1) or
            (vote_type == 'clear' and current == 0)):
        if vote_type == 'like':
            post_type = 'like'
        elif vote_type == 'dislike':
            post_type = 'dislike'
        else:
            # Re-posting the current vote toggles it off.
            post_type = 'like' if current == 1 else 'dislike'

        url = "https://api.bitchute.com/api/beta/video/vote"
        headers = {'origin': "https://www.bitchute.com",
                   'referer': "https://www.bitchute.com/",
                   "User-Agent": USER_AGENT}
        try:
            response = _post_json(url, {'video_id': video_id, 'vote': post_type},
                                  headers=headers, auth=auth)
        except requests.RequestException as e:
            xbmc.log("Could not vote on {}: {}".format(video_id, e))
            return {}

        if response.status_code != 200:
            xbmc.log("Vote on {} returned {}".format(video_id, response.status_code))
            return {}

    _record_vote(video_id, current, reaction, base)
    return {"success": True}

def _enrich_with_votes(cookies, entries):
    """Add upvote/downvote counts and the user's own vote to each entry.

    Counts and reaction state come from separate endpoints; entries are
    processed concurrently. Reactions are cached, so only videos not seen
    recently cost the extra request.
    """
    if not entries:
        return entries

    cached = {entry.video_id: _cached_video_vote(entry.video_id)
              for entry in entries}

    def fetch_reaction(entry):
        vote = cached[entry.video_id]
        if vote is not None:
            return vote[0], vote[1]
        return _fetch_video_reaction(entry.video_id)

    with ThreadPoolExecutor(max_workers=VOTE_FETCH_WORKERS) as pool:
        count_futures = [pool.submit(_get_video_counts, cookies, entry.video_id)
                         for entry in entries]
        reaction_futures = [pool.submit(fetch_reaction, entry) for entry in entries]
        counts = [future.result() for future in count_futures]
        reactions = [future.result() for future in reaction_futures]

    for entry, (upvotes, downvotes), reaction in zip(entries, counts, reactions):
        entry.upvotes = upvotes
        entry.downvotes = downvotes
        entry.user_vote = 1 if reaction[0] else -1 if reaction[1] else 0
        if cached[entry.video_id] is None:
            _store_video_vote(entry.video_id, reaction)

    return entries

def _build_playlist_from_container(container, cookies):
    """Parse a list of ``.video-card`` elements (e.g. a listing-* tab or an
    ``extend`` response fragment) into a pickled list of PlaylistEntry."""
    containers = container.find_all(class_="video-card")

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
                              channel_name=channel_name, date=date, duration=duration, poster=poster,
                              channel_id=_channel_id_from_image(poster))
            playlist.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    _enrich_with_votes(cookies, playlist)

    return pickle.dumps(playlist)

def _build_playlist_common(listing_id, cookies):
    url = "https://old.bitchute.com/"
    resp = _get(url, cookies=cookies)

    soup = BeautifulSoup(resp.text, "html.parser")
    popular = soup.find(id=listing_id)

    return _build_playlist_from_container(popular, cookies)

def _get_popular(cookies):
    return _build_playlist_common("listing-popular", cookies)

def _get_feed(cookies):
    return _build_playlist_common("listing-subscribed", cookies)

def _get_listing_extend(cookies, name, last):
    """Return the next page (LISTING_PAGE_SIZE videos) of a homepage listing.

    ``name`` selects the listing tab (``popular`` or ``subscribed``) and
    ``last`` is the video id of the final card currently displayed. The site
    paginates these listings with that cursor; the ``offset`` field is only
    used by its JavaScript to decide whether to keep the "SHOW MORE" button
    visible.
    """
    token = cookies['csrftoken']
    post_data = {'csrfmiddlewaretoken': token, 'name': name,
                 'offset': LISTING_PAGE_SIZE, 'last': last}
    headers = {'referer': "https://old.bitchute.com/", "User-Agent": USER_AGENT}
    response = _post("https://old.bitchute.com/extend/", data=post_data,
                     headers=headers, cookies=cookies)
    resp = json.loads(response.text)
    container = BeautifulSoup(resp["html"], "html.parser")

    return _build_playlist_from_container(container, cookies)

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
                              channel_name=channel_name, date=date, duration=duration, poster=poster,
                              channel_id=_channel_id_from_image(poster))
            playlist.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    _enrich_with_votes(cookies, playlist)

    return pickle.dumps(playlist)

def _get_playlist(cookies, playlist_name, page):
    """Return one page (PLAYLIST_PAGE_SIZE videos) of a playlist.

    Page 0 fetches ``/playlist/<name>/``. Later pages POST to
    ``/playlist/<name>/extend/`` (the AJAX mechanism behind the site's
    "SHOW MORE" button) and parse the returned HTML fragment.
    """
    referer = "https://old.bitchute.com/playlist/"+playlist_name+"/"

    if page == 0:
        resp = _get(referer, cookies=cookies)
        soup = BeautifulSoup(resp.text, "html.parser")
    else:
        token = cookies['csrftoken']
        post_data = {'csrfmiddlewaretoken': token, 'offset': page * PLAYLIST_PAGE_SIZE}
        headers = {'referer': referer, "User-Agent": USER_AGENT}
        response = _post(referer + "extend/", data=post_data, headers=headers, cookies=cookies)
        resp = json.loads(response.text)
        soup = BeautifulSoup(resp["html"], "html.parser")

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
                              channel_name=channel_name, duration=duration, date=date, poster=poster,
                              channel_id=_channel_id_from_image(poster))
            playlist.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    _enrich_with_votes(cookies, playlist)

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
        xbmc.log("**************** channel: " + str(channel))
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
                             channel_name=channel, date=date, duration=duration, poster=poster,
                             channel_id=_channel_id_from_image(poster))
            videos.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

        count = count + 1

    _enrich_with_votes(cookies, videos)

    return pickle.dumps(videos)

def _get_category(cookies, category, page):
    """Return one page (24 videos) of a browse category.

    Page 0 fetches ``/category/<slug>/`` and parses the ``#listing-popular``
    tab. Later pages POST to ``/category/<slug>/extend/`` (the same AJAX
    mechanism the site's "SHOW MORE" button uses) and parse the returned HTML
    fragment.
    """
    referer = "https://old.bitchute.com/category/" + category + "/"

    if page == 0:
        url = referer
        resp = _get(url, cookies=cookies)
        soup = BeautifulSoup(resp.text, "html.parser")
        container = soup.find(id="listing-popular")
    else:
        token = cookies['csrftoken']
        post_data = {'csrfmiddlewaretoken': token, 'offset': page * CATEGORY_PAGE_SIZE}
        headers = {'referer': referer, "User-Agent": USER_AGENT}
        url = "https://old.bitchute.com/category/" + category + "/extend/"
        response = _post(url, data=post_data, headers=headers, cookies=cookies)
        resp = json.loads(response.text)
        container = BeautifulSoup(resp["html"], "html.parser")

    if container is None:
        return pickle.dumps([])

    return _build_playlist_from_container(container, cookies)


def _get_feed_sub_legacy(params):
    (sub, cookies) = params
    channel = pickle.loads(_get_channel(cookies, sub.channel, 0, max_count=1))
    feed_item = None
    if len(channel) > 0:
        chan = channel[0]  # The latest video
        feed_item = PlaylistEntry(video_id=chan.video_id, description=chan.description,
                                  title=chan.title, channel_name=sub.name, date=chan.date, duration=chan.duration,
                                  poster=chan.poster, upvotes=chan.upvotes, downvotes=chan.downvotes,
                                  channel_id=chan.channel_id)
    return feed_item

def _get_feed_legacy(cookies):
    subs = get_subscriptions()

    params = []
    for sub in subs:
        params.append((sub, cookies))

    feed = []
    for param in params:
        item = _get_feed_sub_legacy(param)
        if item is not None:
            feed.append(item)

    return pickle.dumps(feed)

def _build_channels_from_container(container):
    """Parse a list of ``.channel-card`` elements into a pickled list of
    Subscription. Works for the initial ``/channels/`` page container or an
    ``extend`` response fragment."""
    containers = container.find_all(class_="channel-card")

    subs = []
    for n in containers:
        try:
            # Strip the trailing slash so the value routes through
            # /channel/<item_val> (routing's <item_val> matches no slashes).
            # _get_channel() accepts either form when building the extend URL.
            channel = n.find("a").attrs["href"].replace("/channel/", "").rstrip("/")
            # The first <img> inside the card carries the poster URL. There are
            # several lazyload imgs (medium/large variants); the first one is the
            # responsive base and is what the site's ``data-src`` resolves to.
            channel_image = n.find("a").find("img").attrs["data-src"]
            name = n.find(class_="channel-card-title").get_text()

            s = Subscription(name=name, channel=channel, description="",
                             channel_image=channel_image,
                             channel_id=_channel_id_from_image(channel_image))
            subs.append(s)

        except AttributeError as e:
            xbmc.log("**************** ATTRIBUTE_ERROR " + str(e))
            xbmc.log(str(n))

    return pickle.dumps(subs)


def _get_recently_active(cookies, page):
    """Return one page (CHANNEL_PAGE_SIZE channels) of Bitchute's channel discovery listing.

    Page 0 fetches ``/channels/`` and parses the ``channel-card`` blocks. Later
    pages POST to ``/channels/extend/`` (the AJAX mechanism behind the site's
    auto-scroll "SHOW MORE") and parse the returned HTML fragment.
    """
    base = "https://old.bitchute.com/channels/"

    if page == 0:
        resp = _get(base, cookies=cookies)
        soup = BeautifulSoup(resp.text, "html.parser")
        # The channel cards sit directly in #content; reuse a wrapper container.
        container = soup
    else:
        token = cookies['csrftoken']
        post_data = {'csrfmiddlewaretoken': token, 'offset': page * CHANNEL_PAGE_SIZE}
        headers = {'referer': base, "User-Agent": USER_AGENT}
        response = _post(base + "extend/", data=post_data,
                         headers=headers, cookies=cookies)
        resp = json.loads(response.text)
        container = BeautifulSoup(resp["html"], "html.parser")

    return _build_channels_from_container(container)


def _get_video(cookies, video_id):
    url = f'https://old.bitchute.com/api/beta9/embed/{video_id}/'
    resp = _get(url, cookies=cookies)
    backoff = 1
    while resp.status_code == 429: # rate limited
        if backoff > 128:
            raise Exception("Max rate-limiting backoff of 256 seconds reached: Aborting")

        xbmc.log("Rate limited. Backing off for {} seconds".format(backoff))
        xbmc.sleep(backoff * 1000)

        resp = _get(url, cookies=cookies)

        backoff *= 2

    # BeautifulSoup can't process JS but the video values are embedded
    # in the embedded video viewer script JS.
    def extract_js_variable(var_name, term_symbol):
        sstr = 'var ' + var_name + ' = '
        off = resp.text.find(sstr)
        if off == -1:
            return None

        soff = resp.text.find(term_symbol, off)
        while soff > 0 and resp.text[soff-1] == '\\':
            soff = resp.text.find(term_symbol, soff+1)
        if soff == -1:
            return None

        eoff = resp.text.find(term_symbol, soff+1)
        while eoff > 0 and resp.text[eoff-1] == '\\':
            eoff = resp.text.find(term_symbol, eoff+1)
        if eoff == -1:
            return None

        return resp.text[soff+1:eoff].replace('\\','')

    video_name = extract_js_variable("video_name", "\"") or ""
    thumbnail_url = extract_js_variable("thumbnail_url", "'") or ""

    if addon.getSettingBool('high_resolution_thumbnails'):
        thumbnail_url = thumbnail_url.replace('320','640').replace('180', '360')

    media_url = extract_js_variable("media_url", "'")

    xbmc.log("Scraping video info: {}\nMedia URL: {}\nThumbnail URL: {}\nScrape URL: {}\n".format(video_name, media_url, thumbnail_url, url))

    if not media_url:
        raise VideoUnavailableError(
            "Could not extract media URL for video {}".format(video_id))

    return pickle.dumps(Video(video_id=video_id, video_url=media_url, poster=thumbnail_url,
                  title=video_name))

def _search_api(cookies, query, page, kind, timestamp, nonce, csrf):
    """Request one page of search results of a single kind.

    Bitchute rotates the timestamp/nonce pair on every response, so the
    updated pair is returned for the next call.
    """
    url = "https://old.bitchute.com/api/search/list/"
    post_data = {
            'csrfmiddlewaretoken': csrf,
            'timestamp' : timestamp,
            'nonce': nonce,
            'query': query,
            'kind': kind,
            'duration': '',
            'sort': 'new',
            'page': page,
            }
    headers = {
            'referer': "https://old.bitchute.com/search/",
            'origin': "https://old.bitchute.com",
            "User-Agent": USER_AGENT,
            }
    response = _post(url, data=post_data, headers=headers, cookies=cookies)
    try:
        val = json.loads(response.text)
    except ValueError as e:
        xbmc.log("Search returned an unparseable response: " + str(e))
        return [], timestamp, nonce

    if not val.get("success"):
        xbmc.log("Search request failed: " + str(val.get("error")))
        return [], timestamp, nonce

    return val.get("results", []), val.get("timestamp", timestamp), val.get("nonce", nonce)

def _search(cookies, query, page):
    # Extract timestamp and nonce parameters from searchAuth function
    # embedded in the search HTML page. A new timestamp, nonce pair
    # is required for each search API request.

    url = "https://old.bitchute.com/search/"
    response = _get(url, cookies=cookies)

    text = response.text
    marker = 'searchAuth('
    start = text.find(marker)
    if start != -1:
        start += len(marker)
        end = text.find(")", start)
    else:
        end = -1

    if start == -1 or end == -1:
        xbmc.log("Could not locate searchAuth parameters; search is unavailable.")
        return pickle.dumps(([], []))

    params = text[start:end].split(',', 2)
    if len(params) < 2:
        xbmc.log("Unexpected searchAuth parameter count; search is unavailable.")
        return pickle.dumps(([], []))

    timestamp = params[0].strip()[1:-1]
    nonce = params[1].strip()[1:-1]
    csrf = response.cookies['csrftoken']

    # Each response rotates the timestamp/nonce pair, so the channel
    # request must reuse the pair returned by the video request.
    raw_videos, timestamp, nonce = _search_api(response.cookies, query, page, 'video',
                                               timestamp, nonce, csrf)
    raw_channels, timestamp, nonce = _search_api(response.cookies, query, page, 'channel',
                                                 timestamp, nonce, csrf)

    videos = []
    for result in raw_videos:
        try:
            video_id = result["id"]
            title = result["name"]
            description = result["description"].lstrip().rstrip().replace('<p>','').replace('</p>','')
            channel_name = result["channel_name"]
            poster = result["images"]["thumbnail"]
        except (KeyError, TypeError, AttributeError) as e:
            xbmc.log("Skipping malformed search result: " + str(e))
            continue

        r = SearchEntry(video_id=video_id, title=title, description=description,
                        channel_name=channel_name, poster=poster,
                        channel_id=_channel_id_from_image(poster))
        videos.append(r)

    _enrich_with_votes(cookies, videos)

    channels = []
    for result in raw_channels:
        try:
            name = result["name"]
            channel = result["path"].replace("/channel/", "").rstrip("/")
            description = _strip_html(result.get("description"))
            poster = result["images"]["thumbnail"]
            subscribers = result.get("subscribers")
        except (KeyError, TypeError, AttributeError) as e:
            xbmc.log("Skipping malformed channel search result: " + str(e))
            continue

        channels.append(Subscription(name=name, channel=channel, description=description,
                                     channel_image=poster, subscribers=subscribers,
                                     channel_id=result.get("id")))

    return pickle.dumps((channels, videos))

# Equivalent to the EncodeCommentText() JS function used by Bitchute to encode text
def custom_escape_and_b64encode(e):
    # Equivalent to JSON.stringify(e)
    n = json.dumps(e, ensure_ascii=False)
    o = ""
    for char in n:
        # Equivalent to n.charCodeAt(i)
        t = ord(char)
        if t > 255:
            # For characters > 255, use full Unicode escape (e.g., \\uXXXX)
            o += "\\u" + format(t, '04x')
        elif t >= 128 and t <= 255:
            # For characters between 128 and 255, use \\u00XX format
            o += "\\u00" + format(t, '02x')
        else:
            # For ASCII characters, keep them as is
            o += char

    # Equivalent to btoa(o)
    # The intermediate string 'o' is treated as a binary string (bytes) for btoa
    return base64.b64encode(o.encode('latin-1')).decode('utf-8')

def create_timestamp():
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "")
    return timestamp[:-3] + 'Z'

def _get_comment_data(cookies, video_id):
    url = f'https://old.bitchute.com/video/{video_id}/'
    response = _get(url, cookies=cookies)
    pattern = r"initComments\(\s*'https://commentfreely.bitchute.com'\s*,\s*'([^']+)',\s*'([^']+)'\s*,\s*'([^']+)'"
    res = re.compile(pattern, re.DOTALL|re.IGNORECASE).findall(response.text)
    return res[0] if res else None

def _get_comments(cookies, video_id):
    cd = _get_comment_data(cookies, video_id)
    comments = []

    if cd:
        cf_auth = cd[0]
        url = 'https://commentfreely.bitchute.com/api/get_comments/'
        post_data = {
                'cf_auth' : cf_auth,
                'commentCount' : '0',
                'isNameValuesArrays' : True
                }
        headers = {
                'referer': "https://www.bitchute.com",
                'origin': "https://www.bitchute.com/",
                "User-Agent": USER_AGENT,
                }
        response = _post(url, data=post_data, headers=headers, cookies=cookies)
        js = json.loads(response.text)
        names = js['names']

        try:
            id_idx = names.index('id')
            parent_idx = names.index('parent')
            creator_idx = names.index('creator')
            fullname_idx = names.index('fullname')
            content_idx = names.index('content')
            upvote_count_idx = names.index('up_vote_count')
            downvote_count_idx = names.index('down_vote_count')
            user_vote_idx = names.index('user_vote')
            profile_picture_url_idx = names.index('profile_picture_url')
            created_by_current_user_idx = names.index('created_by_current_user')
        except ValueError as e:
            xbmc.log("Unexpected comment schema, missing field: " + str(e))
            return comments

        for comment in js['values']:
            ce = CommentEntry(comment[id_idx], comment[parent_idx],
               comment[creator_idx], comment[fullname_idx],
               comment[content_idx].replace('\n', '  '), comment[upvote_count_idx],
               comment[downvote_count_idx], comment[user_vote_idx],
               comment[profile_picture_url_idx], comment[created_by_current_user_idx])
            comments.append(ce)
    else:
        xbmc.log("Could not extract cf_auth token: Comments cannot be retrieved.")

    return comments

def _create_comment(cookies, video_id, content_in, parent_id):
    cd = _get_comment_data(cookies, video_id)
    if cd:
        content = custom_escape_and_b64encode(content_in)

        timestamp = create_timestamp()
        post_data = {
            'commentData[id]': 'c1',
            'commentData[parent]': parent_id if parent_id else '',
            'commentData[created]': timestamp,
            'commentData[modified]': timestamp,
            'commentData[content]': content,
            'commentData[fullname]': 'You',
            'commentData[profile_picture_url]': cd[2],
            'commentData[created_by_current_user]': 'true',
            'commentData[up_vote_count]': 0,
            'commentData[down_vote_count]': 0,
            'commentData[user_vote]': '',
            'commentData[is_content_encoded]': 'true',
            'cf_auth': cd[0]
        }
        headers = {
                'origin': "https://old.bitchute.com/",
                "User-Agent": USER_AGENT,
                }
        url = 'https://commentfreely.bitchute.com/api/create_comment/'
        response = _post(url, data=post_data, headers=headers, cookies=cookies)
        js = response.text
    else:
        js = {}

    return js

def _remove_comment(cookies, video_id, id, parent_id, creator, fullname):
    cd = _get_comment_data(cookies, video_id)
    if cd:
        timestamp = create_timestamp()
        post_data = {
            'commentData[id]': id,
            'commentData[parent]': parent_id if parent_id else '',
            'commentData[created]': timestamp,
            'commentData[modified]': '',
            'commentData[content]': '',
            'commentData[fullname]': fullname,
            'commentData[created_by_admin]': 'false',
            'commentData[created_by_current_user]': 'true',
            'commentData[up_vote_count]': 0,
            'commentData[down_vote_count]': 0,
            'commentData[user_vote]': '',
            'commentData[is_new]': 'false',
            'commentData[profile_picture_url]': cd[2],
            'commentData[membership_level]': '',
            'commentData[verified]': 'false',
            'commentData[primary_flag_reason]': '',
            'commentData[is_muted]': 'false',
            'cf_auth': cd[0]
        }
        headers = {
                'origin': "https://old.bitchute.com/",
                "User-Agent": USER_AGENT,
                }
        url = 'https://commentfreely.bitchute.com/api/delete_comment/'
        _post(url, data=post_data, headers=headers, cookies=cookies)

def _edit_comment(cookies, video_id, id, parent_id, creator, fullname, content_in):
    cd = _get_comment_data(cookies, video_id)
    if cd:
        content = custom_escape_and_b64encode(content_in)
        timestamp = create_timestamp()
        modified = str(int(time.time()))
        post_data = {
            'commentData[id]': id,
            'commentData[parent]': parent_id if parent_id else '',
            'commentData[created]': timestamp,
            'commentData[modified]': modified,
            'commentData[content]': content,
            'commentData[fullname]': fullname,
            'commentData[profile_picture_url]': cd[2],
            'commentData[created_by_admin]': 'false',
            'commentData[created_by_current_user]': 'true',
            'commentData[is_new]': 'false',
            'commentData[membership_level]': '',
            'commentData[primary_flag_reason]': '',
            'commentData[is_muted]': 'false',
            'commentData[verified]': 'false',
            'commentData[is_universal]': 'false',
            'commentData[up_vote_count]': 0,
            'commentData[down_vote_count]': 0,
            'commentData[user_vote]': '',
            'commentData[is_content_encoded]': 'true',
            'cf_auth': cd[0]
        }
        headers = {
                'origin': "https://old.bitchute.com/",
                "User-Agent": USER_AGENT,
                }
        url = 'https://commentfreely.bitchute.com/api/update_comment/'
        _post(url, data=post_data, headers=headers, cookies=cookies)

def _vote_comment(cookies, video_id, id, parent_id, creator, fullname, vote_type):
    cd = _get_comment_data(cookies, video_id)
    if cd:
        timestamp = create_timestamp()
        post_data = {
            'commentData[id]': id,
            'commentData[parent]': parent_id if parent_id else '',
            'commentData[created]': timestamp,
            'commentData[modified]': '',
            'commentData[content]': '',
            'commentData[creator]': creator,
            'commentData[fullname]': fullname,
            'commentData[created_by_admin]': 'false',
            'commentData[created_by_current_user]': 'true',
            'commentData[up_vote_count]': 0,
            'commentData[down_vote_count]': 0,
            'commentData[user_vote]': '' if vote_type == '' else 'true' if vote_type == 'like' else 'false',
            'commentData[is_new]': 'false',
            'commentData[profile_picture_url]': cd[2],
            'commentData[membership_level]': '',
            'commentData[verified]': 'false',
            'commentData[primary_flag_reason]': '',
            'commentData[is_muted]': 'false',
            'cf_auth': cd[0]
        }
        headers = {
                'origin': "https://old.bitchute.com/",
                "User-Agent": USER_AGENT,
                }

        url = 'https://commentfreely.bitchute.com/api/vote_on_comment/'
        _post(url, data=post_data, headers=headers, cookies=cookies)

def _toggle_subscription(cookies, channel_id):
    """Toggle the subscription state of a channel.

    Returns the site's JSON response, which carries ``success``, the new
    ``state`` ("Subscribed" or "Subscribe") and the updated subscriber
    ``count``.
    """
    url = f"https://old.bitchute.com/channel/{channel_id}/sub/"
    post_data = {'csrfmiddlewaretoken': cookies['csrftoken']}
    headers = {'referer': f"https://old.bitchute.com/channel/{channel_id}/",
               "User-Agent": USER_AGENT}
    response = _post(url, data=post_data, headers=headers, cookies=cookies)
    try:
        return response.json()
    except ValueError:
        xbmc.log("Subscription toggle for {} returned an unparseable response".format(channel_id))
        return {}

# Wrappers to ensure the subs, notifications, playlists are cached for 15 minutes

def get_page(login, allow_cache, funct, *args):
    if login:
        cookies, success = bt_login()
    else:
        cookies = []
        success = True

    if success:
        if allow_cache and addon.getSettingBool("enable_cache"):
            return pickle.loads(data_cache.cacheFunction(funct, cookies, *args))
        else:
            res = funct(cookies, *args)
            if allow_cache:
                res = pickle.loads(res)
            return res

    return []

def get_subscriptions():
    return get_page(True, True, _get_subscriptions)

def get_subscribed_channel_ids():
    """Return the IDs of the channels the user is subscribed to."""
    return {getattr(sub, 'channel_id', None) for sub in get_subscriptions()
            if getattr(sub, 'channel_id', None)}

def toggle_subscription(channel_id):
    result = get_page(True, False, _toggle_subscription, channel_id)
    if not isinstance(result, dict):
        result = {}

    if result.get("success"):
        # The subscription listing and feed are cached, so drop them.
        clear_cache(data=True)

    return result

def vote_video(video_id, vote_type):
    result = get_page(True, False, _vote_video, video_id, vote_type)
    if not isinstance(result, dict):
        result = {}
    return result

def get_notifications(page):
    return get_page(True, True, _get_notifications, page)

def get_playlist(playlist, page):
    return get_page(True, True, _get_playlist, playlist, page)

def get_channel(channel, page, max_count=100):
    return get_page(True, True, _get_channel, channel, page, max_count)

def get_category(category, page):
    return get_page(True, True, _get_category, category, page)

def get_popular(page, last=None):
    if page == 0:
        return get_page(True, True, _get_popular)
    return get_page(True, True, _get_listing_extend, "popular", last)

def get_trending():
    return get_page(True, True, _get_trending)

def get_feed(page, last=None):
    if xbmcaddon.Addon().getSettingBool("legacy_feed_behavior"):
        return get_page(True, True, _get_feed_legacy)
    if page == 0:
        return get_page(True, True, _get_feed)
    return get_page(True, True, _get_listing_extend, "subscribed", last)

def search(query, page):
    result = get_page(True, True, _search, query, page)
    if not result:
        return [], []
    return result

def get_recently_active(page):
    return get_page(True, True, _get_recently_active, page)

def get_video(video_id):
    return pickle.loads(_get_video([], video_id))

def get_comments(video_id):
    return get_page(True, False, _get_comments, video_id)

def create_comment(video_id, content, parent_id):
    return json.loads(get_page(True, False, _create_comment, video_id, content, parent_id))

def remove_comment(video_id, id, parent_id, creator, fullname):
    return get_page(True, False, _remove_comment, video_id, id, parent_id, creator, fullname)

def edit_comment(video_id, id, parent_id, creator, fullname, content):
    return get_page(True, False, _edit_comment, video_id, id, parent_id, creator, fullname, content)

def vote_comment(video_id, id, parent_id, creator, fullname, vote_type):
    return get_page(True, False, _vote_comment, video_id, id, parent_id, creator, fullname, vote_type)

def clear_cache(login=True, data=True, reactions=True):
    if login:
        login_cache.delete('%')

    if data:
        data_cache.delete('%')

    if reactions:
        reaction_cache.delete('%')
