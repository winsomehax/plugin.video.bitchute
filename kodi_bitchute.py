import routing
from xbmcgui import Dialog, INPUT_ALPHANUM
import xbmcaddon
import bitchute_query
import KODIMenu as kodi_menu

plugin = routing.Plugin()

class Config():

    bitchute=None
    menu=None

store=Config


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


@plugin.route('/play_folder/<item_val>')
def play_folder(item_val):

    if not valid_user:
        return

    build_and_play(item_val)


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

    store.menu.new_folder_item(item_name="Your Bitchute user is: " +
                         store.bitchute.username, item_val=None, func=open_settings)
    store.menu.new_folder_item(
        item_name="Subscriptions", item_val=None, func=subscriptions)
    store.menu.new_folder_item(
        item_name="Notifications", item_val=None, func=notifications)
    # menu.new_folder_item(
    #     item_name="View all currently live streams", item_val=None, func=livestreams_all)
    # menu.new_folder_item(item_name="Search currently live streams",
    #                      item_val=None, func=livestreams_search)
    store.menu.end_folder()


def build_subscriptions():

    global store
    store.menu.start_folder()

    subscriptions = store.bitchute.subscriptions()

    if 0 == len(subscriptions):
        store.menu.new_info_item("** YOU HAVE NO SUBSCRIPTIONS **")
    else:
        for sub in subscriptions:
            store.menu.new_folder_item(item_name=sub.name, func=channel, item_val=sub.channel)

    store.menu.end_folder()


def build_notifications():

    global store
    store.menu.start_folder()

    notifications = store.bitchute.notifications()

    if 0 == len(notifications):
        store.menu.new_info_item("** YOU HAVE NO NOTIFICATIONS **")
    else:
        for n in notifications:
            store.menu.new_video_item(displayName=n.notification_detail, title="",
                    playURL=n.videoURL, thumbURL="", duration=0)

    store.menu.end_folder()

def build_a_channel(item_val):

 
    global store
    store.menu.start_folder()

    videos=store.bitchute.get_channel(item_val)

    for v in videos:
        store.menu.new_folder_item(item_name=v.title, func=play_folder, item_val=v.video_id)

    store.menu.end_folder()

def build_and_play(item_val):
    global store

    store.menu.start_folder()
    video=store.bitchute.get_video(item_val)
    store.menu.new_video_item(displayName=video.title, title="", playURL=video.videoURL, thumbURL=video.poster, duration=0)
   
    store.menu.end_folder()


def build_open_settings():
    xbmcaddon.Addon().openSettings()



if store.bitchute is None:
    user=xbmcaddon.Addon().getSetting("user")
    password=xbmcaddon.Addon().getSetting("password")

    store.bitchute = bitchute_query.BitChute(user,password)

if store.menu is None:
    store.menu = kodi_menu.KODIMenu(plugin)