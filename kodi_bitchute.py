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
    build_notifications()

@plugin.route('/favourites')
def favourites():
    build_playlist("favorites")

@plugin.route('/watch-later')
def watch_later():
    build_playlist("watch-later")

@plugin.route('/popular')
def popular():
    build_popular()

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
    build_feed()

@plugin.route('/channel/<item_val>')
def channel(item_val):
    build_a_channel(item_val, 0)

@plugin.route('/channel_offset/<item_val>')
def channel_offset(item_val):
    item_val2=int(plugin.args['item_val2'][0])
    build_a_channel(item_val, item_val2)

@plugin.route('/categories')
def categories():
    build_categories()

@plugin.route('/category/<item_val>')
def category(item_val):
    build_a_category(item_val, 0)

@plugin.route('/category_offset/<item_val>')
def category_offset(item_val):
    item_val2=int(plugin.args['item_val2'][0])
    build_a_category(item_val, item_val2)

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
    for ch in channels:
        description = ch.description
        if ch.subscribers:
            description = loc(30063) + ": " + ch.subscribers + "\n\n" + description
        menu.new_folder_item(item_name=ch.name, description=description,
                             iconURL=ch.channel_image, func=channel, item_val=ch.channel)
    entries_to_listitems(videos, finalize_folder=False, show_empty=(0 == len(channels)))
    if len(channels) == bitchute_access.SEARCH_PAGE_SIZE or len(videos) == bitchute_access.SEARCH_PAGE_SIZE:
        menu.new_folder_item(loc(30035), loc(30035),
                             None, search_pager, query=query, page=page+1) # Next page
    menu.end_folder()

@plugin.route('/clear_cache')
def clear_cache():
    bitchute_access.clear_cache()

@plugin.route('/comments/<video_id>')
def comments(video_id):
    w = CommentWindow(video_id=video_id)

def loc(label):
    return(xbmcaddon.Addon().getLocalizedString(label))

def entries_to_listitems(entries, finalize_folder=True, show_empty=True):
    global menu
    if finalize_folder:
        menu.start_folder()

    if 0 == len(entries):
        if show_empty:
            menu.new_info_item(loc(30028))
    else:
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
        for sub in subscriptions:
            menu.new_folder_item(
                item_name=sub.name, func=channel, item_val=sub.channel, iconURL=sub.channel_image, description=sub.description)

    menu.end_folder()

def build_channels(page):
    global menu
    menu.start_folder()

    subs = bitchute_access.get_recently_active(page)

    if 0 == len(subs):
        menu.new_info_item(loc(30028))
    else:
        for sub in subs:
            menu.new_folder_item(
                item_name=sub.name, func=channel, item_val=sub.channel, iconURL=sub.channel_image, description=sub.description)

        if len(subs) == bitchute_access.CHANNEL_PAGE_SIZE:
            menu.new_folder_item(loc(30035), loc(30035),
                                 None, channels_offset, page=page+1) # Next page

    menu.end_folder()

def build_notifications():
    entries_to_listitems(bitchute_access.get_notifications())

def build_a_channel(item_val, page):
    global menu
    menu.start_folder()

    videos = bitchute_access.get_channel(item_val, page)

    entries_to_listitems(videos, finalize_folder=False)

    if len(videos)==25:
        menu.new_folder_item(loc(30035), loc(30035), None, channel_offset, item_val=item_val, item_val2=page+1) # Next page

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

    if len(videos) == bitchute_access.CATEGORY_PAGE_SIZE:
        menu.new_folder_item(loc(30035), loc(30035), None, category_offset, item_val=item_val, item_val2=page+1) # Next page

    menu.end_folder()

def build_playlist(playlist):
    entries_to_listitems(bitchute_access.get_playlist(playlist))

def build_feed():
    entries_to_listitems(bitchute_access.get_feed())

def build_popular():
    entries_to_listitems(bitchute_access.get_popular())

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
