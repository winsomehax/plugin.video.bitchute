import routing
from urllib.parse import quote_plus,unquote_plus
import xbmc
import xbmcaddon
from xbmcgui import Dialog, INPUT_ALPHANUM

import KODIMenu as kodi_menu
import bitchute_access
from comment_window import CommentWindow

plugin = routing.Plugin()
menu = kodi_menu.KODIMenu(plugin)
addon = xbmcaddon.Addon()
iconURL = 'special://home/addons/plugin.video.bitchute/resources/icon.png'

@plugin.route('/')
def index():
    build_main_menu()

@plugin.route('/subscriptions')
def subscriptions():
    build_subscriptions()

@plugin.route('/notifications')
def notifications():
    build_notifications(0)

@plugin.route('/notifications_offset')
def notifications_offset():
    page = int(plugin.args['page'][0])
    build_notifications(page)

@plugin.route('/favourites')
def favourites():
    build_playlist("favorites", 0)

@plugin.route('/watch-later')
def watch_later():
    build_playlist("watch-later", 0)

@plugin.route('/playlist_offset/<item_val>')
def playlist_offset(item_val):
    page = int(plugin.args['page'][0])
    build_playlist(item_val, page)

@plugin.route('/popular')
def popular():
    build_popular(0)

@plugin.route('/popular_offset')
def popular_offset():
    page = int(plugin.args['page'][0])
    last = plugin.args['last'][0]
    build_popular(page, last)

@plugin.route('/trending')
def trending():
    build_trending()

@plugin.route('/video_by_id')
def video_by_id():
    d = Dialog()
    v = d.input(loc(30030))
    if v.strip() == "":
        return
    play_video(v)

@plugin.route('/play_now/<item_val>')
def play_now(item_val):
    play_video(item_val)

@plugin.route('/feed/')
def feed():
    build_feed(0)

@plugin.route('/feed_offset')
def feed_offset():
    page = int(plugin.args['page'][0])
    last = plugin.args['last'][0]
    build_feed(page, last)

@plugin.route('/channel/<item_val>')
def channel(item_val):
    build_a_channel(item_val, 0)

@plugin.route('/channel_offset/<item_val>')
def channel_offset(item_val):
    page = int(plugin.args['page'][0])
    build_a_channel(item_val, page)

@plugin.route('/categories')
def categories():
    build_categories()

@plugin.route('/category/<item_val>')
def category(item_val):
    build_a_category(item_val, 0)

@plugin.route('/category_offset/<item_val>')
def category_offset(item_val):
    page = int(plugin.args['page'][0])
    build_a_category(item_val, page)

@plugin.route('/channels')
def channels():
    build_channels(0)

@plugin.route('/channels_offset')
def channels_offset():
    page_off = int(plugin.args['page'][0])
    build_channels(page_off)

@plugin.route('/open_settings')
def open_settings():
    build_open_settings()

@plugin.route('/search')
def search():
    dlg = Dialog()
    query = dlg.input(loc(30029), type=INPUT_ALPHANUM)
    if query.strip() == "":
        return

    search_pager(query=query, page=0)
    xbmc.executebuiltin('Container.Update(%s,replace)' % plugin.url_for(search_pager, query=quote_plus(query), page=0))

@plugin.route('/search/<query>/<page>')
def search_pager(query, page):
    query = unquote_plus(query)
    page = int(page)
    menu.start_folder()
    channels, videos = bitchute_access.search(query, str(page))
    subscribed_ids = subscribed_channel_ids()
    for ch in channels:
        description = ch.description
        if ch.subscribers:
            description = loc(30063) + ": " + ch.subscribers + "\n\n" + description
        menu.new_folder_item(item_name=ch.name, description=description,
                             iconURL=ch.channel_image, func=channel, item_val=ch.channel,
                             context_menu=channel_context_menu(ch, subscribed_ids))
    entries_to_listitems(videos, finalize_folder=False, show_empty=(0 == len(channels)))
    has_next = len(channels) == bitchute_access.SEARCH_PAGE_SIZE or len(videos) == bitchute_access.SEARCH_PAGE_SIZE
    add_page_navigation(page, search_pager, has_next, query=query)
    menu.end_folder()

@plugin.route('/clear_cache')
def clear_cache():
    bitchute_access.clear_cache()

@plugin.route('/comments/<video_id>')
def comments(video_id):
    w = CommentWindow(video_id=video_id)

@plugin.route('/toggle_subscription/<item_val>')
def toggle_subscription(item_val):
    result = bitchute_access.toggle_subscription(item_val)

    if result.get("success"):
        if result.get("state") == "Subscribed":
            notify(loc(30067))
        else:
            notify(loc(30068))
        xbmc.executebuiltin('Container.Refresh')
    else:
        Dialog().ok(loc(30069), loc(30070))

def loc(label):
    return(xbmcaddon.Addon().getLocalizedString(label))

def notify(message):
    Dialog().notification(addon.getAddonInfo('name'), message)

def subscribed_channel_ids():
    try:
        return bitchute_access.get_subscribed_channel_ids()
    except Exception as e:
        xbmc.log("Could not determine subscribed channels: {}".format(e))
        return set()

def channel_context_menu(channel, subscribed_ids):
    channel_id = getattr(channel, 'channel_id', None)
    if not channel_id:
        return None

    if channel_id in subscribed_ids:
        label = loc(30066)  # Unsubscribe
    else:
        label = loc(30065)  # Subscribe

    return [(label, 'RunPlugin(%s)' % plugin.url_for(toggle_subscription, item_val=channel_id))]

def add_page_navigation(page, func, has_next, has_previous=True, **kwargs):
    global menu
    if has_previous and page > 0:
        menu.new_folder_item(loc(30064), loc(30064), None, func, page=page-1, **kwargs) # Previous page
    if has_next:
        menu.new_folder_item(loc(30035), loc(30035), None, func, page=page+1, **kwargs) # Next page

def entries_to_listitems(entries, finalize_folder=True, show_empty=True):
    global menu
    if finalize_folder:
        menu.start_folder()

    if 0 == len(entries):
        if show_empty:
            menu.new_info_item(loc(30028))
    else:
        subscribed_ids = None
        for n in entries:
            duration = None
            description = ""
            poster = iconURL
            if not isinstance(n, bitchute_access.NotificationEntry):
                description += "[B]" + n.channel_name + "[/B]\n"
                if getattr(n, 'upvotes', None) is not None:
                    description += "[COLOR=orange]" + str(n.upvotes) + "/" + str(n.downvotes) + "[/COLOR]\n"
                if not isinstance(n, bitchute_access.SearchEntry):
                    description += loc(30058) + ": " + n.date + "\n"

                    try:
                        d = 0
                        m = 1
                        toks = n.duration.split(":")
                        ntoks = len(toks)
                        for i in range(ntoks):
                            d = d + m*int(toks[ntoks-i-1])
                            m = m*60
                        duration = d
                    except (AttributeError, ValueError):
                        duration = None

                poster = n.poster
            if description != "":
                description += "\n"

            description += n.description

            video_url = "http://127.0.0.1:" + addon.getSetting('proxy_port') + "/" + n.video_id

            context_menu = []
            context_menu.append((loc(30039), 'RunPlugin(%s)' % plugin.url_for(comments, video_id=n.video_id)))

            channel_id = getattr(n, 'channel_id', None)
            if channel_id:
                if subscribed_ids is None:
                    subscribed_ids = subscribed_channel_ids()
                label = loc(30066) if channel_id in subscribed_ids else loc(30065)
                context_menu.append((label, 'RunPlugin(%s)' % plugin.url_for(toggle_subscription, item_val=channel_id)))

            menu.new_video_item(item_name=n.title, url=video_url,
                                description=description, iconURL=poster, duration=duration,
                                context_menu=context_menu)

    if finalize_folder:
        menu.end_folder()

def build_main_menu():
    global menu
    menu.start_folder()
    menu.new_folder_item(item_name=loc(30022), description=loc(30023), iconURL=iconURL, item_val=None, func=feed)
    menu.new_folder_item(item_name=loc(30006), description=loc(30007), iconURL=iconURL, item_val=None, func=subscriptions)
    menu.new_folder_item(item_name=loc(30010), description=loc(30011), iconURL=iconURL, item_val=None, func=notifications)
    menu.new_folder_item(item_name=loc(30018), description=loc(30019), iconURL=iconURL, item_val=None, func=popular)
    menu.new_folder_item(item_name=loc(30020), description=loc(30021), iconURL=iconURL, item_val=None, func=trending)
    menu.new_folder_item(item_name=loc(30056), description=loc(30057), iconURL=iconURL, item_val=None, func=categories)
    menu.new_folder_item(item_name=loc(30016), description=loc(30017), iconURL=iconURL, item_val=None, func=channels)
    menu.new_folder_item(item_name=loc(30012), description=loc(30013), iconURL=iconURL, item_val=None, func=favourites)
    menu.new_folder_item(item_name=loc(30014), description=loc(30015), iconURL=iconURL, item_val=None, func=watch_later)
    menu.new_folder_item(item_name=loc(30008), description=loc(30009), iconURL=iconURL, item_val=None, func=search)
    menu.new_folder_item(item_name=loc(30004), description=loc(30005), iconURL=iconURL, item_val=None, func=open_settings)
    menu.new_folder_item(item_name=loc(30024), description=loc(30025), iconURL=iconURL, item_val=None, func=video_by_id)
    menu.end_folder()

def build_subscriptions():
    global menu
    menu.start_folder()

    subscriptions = bitchute_access.get_subscriptions()

    if 0 == len(subscriptions):
        menu.new_info_item(loc(30026))
    else:
        subscribed_ids = {getattr(sub, 'channel_id', None) for sub in subscriptions}
        for sub in subscriptions:
            menu.new_folder_item(
                item_name=sub.name, func=channel, item_val=sub.channel, iconURL=sub.channel_image,
                description=sub.description,
                context_menu=channel_context_menu(sub, subscribed_ids))

    menu.end_folder()

def build_channels(page):
    global menu
    menu.start_folder()

    subs = bitchute_access.get_recently_active(page)

    if 0 == len(subs):
        menu.new_info_item(loc(30028))
    else:
        subscribed_ids = subscribed_channel_ids()
        for sub in subs:
            menu.new_folder_item(
                item_name=sub.name, func=channel, item_val=sub.channel, iconURL=sub.channel_image,
                description=sub.description,
                context_menu=channel_context_menu(sub, subscribed_ids))

        add_page_navigation(page, channels_offset, len(subs) == bitchute_access.CHANNEL_PAGE_SIZE)

    menu.end_folder()

def build_notifications(page):
    global menu
    menu.start_folder()

    notifications = bitchute_access.get_notifications(page)

    entries_to_listitems(notifications, finalize_folder=False)

    add_page_navigation(page, notifications_offset, len(notifications) == bitchute_access.NOTIFICATION_PAGE_SIZE)

    menu.end_folder()

def build_a_channel(item_val, page):
    global menu
    menu.start_folder()

    videos = bitchute_access.get_channel(item_val, page)

    entries_to_listitems(videos, finalize_folder=False)

    add_page_navigation(page, channel_offset, len(videos) == 25, item_val=item_val)

    menu.end_folder()

def build_categories():
    global menu
    menu.start_folder()

    for slug, name in bitchute_access.CATEGORIES:
        menu.new_folder_item(item_name=name, description=name, iconURL=iconURL,
                             func=category, item_val=slug)

    menu.end_folder()

def build_a_category(item_val, page):
    global menu
    menu.start_folder()

    videos = bitchute_access.get_category(item_val, page)

    entries_to_listitems(videos, finalize_folder=False)

    add_page_navigation(page, category_offset, len(videos) == bitchute_access.CATEGORY_PAGE_SIZE, item_val=item_val)

    menu.end_folder()

def build_playlist(playlist, page):
    global menu
    menu.start_folder()

    entries = bitchute_access.get_playlist(playlist, page)

    entries_to_listitems(entries, finalize_folder=False)

    add_page_navigation(page, playlist_offset, len(entries) == bitchute_access.PLAYLIST_PAGE_SIZE, item_val=playlist)

    menu.end_folder()

def build_feed(page, last=None):
    global menu
    menu.start_folder()

    entries = bitchute_access.get_feed(page, last)

    entries_to_listitems(entries, finalize_folder=False)

    if not addon.getSettingBool("legacy_feed_behavior") and len(entries) == bitchute_access.LISTING_PAGE_SIZE:
        add_page_navigation(page, feed_offset, True, has_previous=False, last=entries[-1].video_id)

    menu.end_folder()

def build_popular(page, last=None):
    global menu
    menu.start_folder()

    entries = bitchute_access.get_popular(page, last)

    entries_to_listitems(entries, finalize_folder=False)

    if len(entries) == bitchute_access.LISTING_PAGE_SIZE:
        add_page_navigation(page, popular_offset, True, has_previous=False, last=entries[-1].video_id)

    menu.end_folder()

def build_trending():
    entries_to_listitems(bitchute_access.get_trending())

def play_video(video_id):
    global menu
    try:
        v = bitchute_access.get_video(video_id)
    except Exception as e:
        xbmc.log("Failed to resolve video {}: {}".format(video_id, e))
        Dialog().ok(loc(30059), loc(30060))
        return
    menu.play_now(v.video_url)

def build_open_settings():
    addon = xbmcaddon.Addon()
    addon.openSettings()

    # Only attempt a login when credentials are actually configured, otherwise
    # simply opening settings would report a bogus login failure.
    if addon.getSetting("user") and addon.getSetting("password"):
        bitchute_access.bt_login()
