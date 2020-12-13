import routing
from xbmcgui import Dialog, INPUT_ALPHANUM, ListItem
import xbmcaddon
import bitchute_query
import KODIMenu as kodi_menu

plugin = routing.Plugin()


class Config():

    bitchute = None
    menu = None


store = Config


def valid_user():
    global store

    if not store.bitchute.logged_in:
        # Warn the user that it's not a valid user
        dialog = Dialog()
        dialog.ok("Warning", "The Bitchute add-on has not been able to login")
        return False

    return True


@plugin.route('/')
def index():
    build_main_menu()


@plugin.route('/subscriptions')
def subscriptions():

    if not valid_user:
        return

    build_subscriptions()


@plugin.route('/notifications')
def notifications():
    if not valid_user:
        return

    build_notifications()


@plugin.route('/favourites')
def favourites():
    if not valid_user:
        return

    build_playlist("favorites")  # NOTE: US spelling. yuck.


@plugin.route('/watch-later')
def watch_later():
    if not valid_user:
        return

    build_playlist("watch-later")


@plugin.route('/popular')
def popular():
    if not valid_user:
        return

    build_popular()

@plugin.route('/trending')
def trending():
    if not valid_user:
        return

    build_trending()


@plugin.route('/play_now/<item_val>')
def play_now(item_val):

    if not valid_user:
        return

    play_video(item_val)


@plugin.route('/channel/<item_val>')
def channel(item_val):

    if not valid_user:
        return

    build_a_channel(item_val)


@plugin.route('/open_settings')
def open_settings():
    build_open_settings()


def build_main_menu():

    global store
    store.menu.start_folder()

    store.menu.new_folder_item(
        item_name="Set your Bitchute user", item_val=None, func=open_settings)
    store.menu.new_folder_item(
        item_name="Subscriptions", item_val=None, func=subscriptions)
    store.menu.new_folder_item(
        item_name="Notifications", item_val=None, func=notifications)
    store.menu.new_folder_item(
        item_name="Favourites", item_val=None, func=favourites)
    store.menu.new_folder_item(
        item_name="Watch Later", item_val=None, func=watch_later)
    store.menu.new_folder_item(
        item_name="Popular", item_val=None, func=popular)
    store.menu.new_folder_item(
        item_name="Trending", item_val=None, func=trending)
    store.menu.end_folder()


def build_subscriptions():

    global store
    store.menu.start_folder()

    subscriptions = store.bitchute.get_subscriptions()

    if 0 == len(subscriptions):
        store.menu.new_info_item("** YOU HAVE NO SUBSCRIPTIONS **")
    else:
        for sub in subscriptions:
            store.menu.new_folder_item(
                item_name=sub.name, func=channel, item_val=sub.channel, iconURL=sub.channel_image)

    store.menu.end_folder()


def build_notifications():

    global store
    store.menu.start_folder()

    notifications = store.bitchute.get_notifications()

    if 0 == len(notifications):
        store.menu.new_info_item("** YOU HAVE NO NOTIFICATIONS **")
    else:
        for n in notifications:
            store.menu.new_folder_item(item_name=n.notification_detail, func=play_now, item_val=n.video_id,
                                       iconURL="https://www.bitchute.com/static/v129/images/logo-full-day.png")

    store.menu.end_folder()


def build_a_channel(item_val):

    global store
    store.menu.start_folder()

    videos = store.bitchute.get_channel(item_val)

    for v in videos:
        store.menu.new_folder_item(
            item_name=v.title, func=play_now, item_val=v.video_id, iconURL=v.poster)

    store.menu.end_folder()


def build_playlist(playlist):
    global store
    store.menu.start_folder()

    entries = store.bitchute.get_playlist(playlist)

    if 0 == len(entries):
        store.menu.new_info_item("** NO VIDEOS FOUND **")
    else:
        for n in entries:
            store.menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id)

    store.menu.end_folder()


def build_popular():
    global store
    store.menu.start_folder()

    entries = store.bitchute.get_popular()

    if 0 == len(entries):
        store.menu.new_info_item("** NO VIDEOS FOUND **")
    else:
        for n in entries:
            store.menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, iconURL=n.poster)

    store.menu.end_folder()


def build_trending():
    global store
    store.menu.start_folder()

    entries = store.bitchute.get_trending()

    if 0 == len(entries):
        store.menu.new_info_item("** NO VIDEOS FOUND **")
    else:
        for n in entries:
            store.menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, iconURL=n.poster)

    store.menu.end_folder()


def play_video(video_id):

    global store
    v = store.bitchute.get_video(video_id)
    store.menu.play_now(v.videoURL)


def build_open_settings():
    xbmcaddon.Addon().openSettings()
    user = xbmcaddon.Addon().getSetting("user")
    password = xbmcaddon.Addon().getSetting("password")

    store.bitchute = bitchute_query.BitChute(user, password)


if store.bitchute is None:
    user = xbmcaddon.Addon().getSetting("user")
    password = xbmcaddon.Addon().getSetting("password")

    store.bitchute = bitchute_query.BitChute(user, password)

if store.menu is None:
    store.menu = kodi_menu.KODIMenu(plugin)
