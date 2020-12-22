import routing
<<<<<<< HEAD
from xbmcgui import Dialog
=======
from xbmcgui import Dialog, INPUT_ALPHANUM
>>>>>>> 07df12de6617544bb708f85cd94d6ea95efdc8e1
import xbmcaddon
import KODIMenu as kodi_menu
import bitchute_access

plugin = routing.Plugin()

menu = kodi_menu.KODIMenu(plugin)

def valid_user():
    return True # temp until I figure out some better error handling


@plugin.route('/')
def index():
    build_main_menu()


@plugin.route('/subscriptions')
def subscriptions():

    if not valid_user():
        return

    build_subscriptions()


@plugin.route('/notifications')
def notifications():
    if not valid_user():
        return

    build_notifications()


@plugin.route('/favourites')
def favourites():
    if not valid_user():
        return

    build_playlist("favorites")  # NOTE: US spelling. yuck.


@plugin.route('/watch-later')
def watch_later():
    if not valid_user():
        return

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
    v = d.input("Enter the video ID")
    play_video(v)


@plugin.route('/play_now/<item_val>')
def play_now(item_val):

    if not valid_user():
        return

    play_video(item_val)


@plugin.route('/feed/')
def feed():

    if not valid_user():
        return

    build_feed()


@plugin.route('/channel/<item_val>')
def channel(item_val):

    if not valid_user():
        return

    build_a_channel(item_val)


@plugin.route('/open_settings')
def open_settings():
    build_open_settings()

@plugin.route('/search')
def search():
    build_search()



def build_main_menu():

    global menu
    menu.start_folder()

    menu.new_folder_item(
        item_name="Set your Bitchute user", description="Enter your Bitchute user and password", item_val=None, func=open_settings)
    menu.new_folder_item(
        item_name="Subscriptions", description="Show the Bitchute channel you are subscribed to", item_val=None, func=subscriptions)
    menu.new_folder_item(
        item_name="Search", description="Search for videos", item_val=None, func=search)
    menu.new_folder_item(
        item_name="Notifications", description="Show the Bitchute notifications outstanding", item_val=None, func=notifications)
    menu.new_folder_item(
        item_name="Favourites", description="Videos you've added to your Bitchute playlist", item_val=None, func=favourites)
    menu.new_folder_item(
        item_name="Watch Later", description="Videos you've marked as watch later on Bitchute", item_val=None, func=watch_later)
    menu.new_folder_item(
        item_name="Popular", description="Videos listed on Bitchute's popular category", item_val=None, func=popular)
    menu.new_folder_item(
        item_name="Trending", description="Videos listed on Bitchute's trending category", item_val=None, func=trending)
    menu.new_folder_item(
        item_name="Feed", description="Show a feed from your subscribed channels", item_val=None, func=feed)
    menu.new_folder_item(
        item_name="Open a video by Bitchute ID", description="Open a video using its Bitchute ID, e.g lfhdo1zEXm3l", item_val=None, func=video_by_id)
    menu.end_folder()


def build_subscriptions():

    global menu
    menu.start_folder()

    subscriptions = bitchute_access.get_subscriptions()

    if 0 == len(subscriptions):
        menu.new_info_item("** YOU HAVE NO SUBSCRIPTIONS **")
    else:
        for sub in subscriptions:
<<<<<<< HEAD
            store.menu.new_folder_item(
=======
            menu.new_folder_item(
>>>>>>> 07df12de6617544bb708f85cd94d6ea95efdc8e1
                item_name=sub.name, func=channel, item_val=sub.channel, iconURL=sub.channel_image, description=sub.description)

    menu.end_folder()


def build_notifications():

    global menu
    menu.start_folder()

    notifications = bitchute_access.get_notifications()

    if 0 == len(notifications):
        menu.new_info_item("** YOU HAVE NO NOTIFICATIONS **")
    else:
        for n in notifications:
            menu.new_folder_item(item_name=n.title, description=n.description, func=play_now, item_val=n.video_id,
                                       iconURL="https://www.bitchute.com/static/v129/images/logo-full-day.png")

    menu.end_folder()


def build_a_channel(item_val):

    global menu
    menu.start_folder()

    videos = bitchute_access.get_channel(item_val)

    for v in videos:
        menu.new_folder_item(
            item_name=v.title, func=play_now, item_val=v.video_id, description=v.channel_name+"\n"+v.description, iconURL=v.poster)

    menu.end_folder()


def build_playlist(playlist):
    global menu
    menu.start_folder()

    entries = bitchute_access.get_playlist(playlist)

    if 0 == len(entries):
        menu.new_info_item("** NO VIDEOS FOUND **")
    else:
        for n in entries:
<<<<<<< HEAD
            store.menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, description=n.description, iconURL=n.poster)
=======
            menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, description=n.description, iconURL=n.poster)

    menu.end_folder()

>>>>>>> 07df12de6617544bb708f85cd94d6ea95efdc8e1

def build_feed():

    global menu
    menu.start_folder()

    entries = bitchute_access.get_feed()

    if 0 == len(entries):
        menu.new_info_item("** NO VIDEOS FOUND **")
    else:
        for n in entries:
            menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, description=n.channel_name+"\n"+n.description, iconURL=n.poster)

    menu.end_folder()


def build_popular():

    global menu
    menu.start_folder()

    entries = bitchute_access.get_popular()

    if 0 == len(entries):
        menu.new_info_item("** NO VIDEOS FOUND **")
    else:
        for n in entries:

            menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, description=n.channel_name+"\n"+n.description, iconURL=n.poster)

    menu.end_folder()


def build_trending():
    global menu
    menu.start_folder()

    entries = bitchute_access.get_trending()

    if 0 == len(entries):
        menu.new_info_item("** NO VIDEOS FOUND **")
    else:
        for n in entries:

            menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, description=n.channel_name+"\n"+n.description, iconURL=n.poster)

    menu.end_folder()


def build_search():

    dlg = Dialog()
    d = dlg.input('Enter search', type=INPUT_ALPHANUM)

    global menu
    menu.start_folder()

    results = bitchute_access.search(d)   

    if 0 == len(results):
        menu.new_info_item("** NO VIDEOS FOUND **")
    else:
        for n in results:

            menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, description=n.channel_name+"\n"+n.description, iconURL=n.poster)

    menu.end_folder()


def play_video(video_id):

    global menu
    v = bitchute_access.get_video(video_id)
    menu.play_now(v.videoURL)


def build_open_settings():
    xbmcaddon.Addon().openSettings()


