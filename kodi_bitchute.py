import routing
from xbmcgui import Dialog, INPUT_ALPHANUM
import xbmcaddon
import KODIMenu as kodi_menu
import bitchute_access

plugin = routing.Plugin()

menu = kodi_menu.KODIMenu(plugin)


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

    build_playlist("favorites")  # NOTE: US spelling. yuck.


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

@plugin.route('/open_settings')
def open_settings():
    build_open_settings()


@plugin.route('/search')
def search():
    build_search()


@plugin.route('/recently_active')
def recently_active():
    build_recently_active()


def loc(label):

    return(xbmcaddon.Addon().getLocalizedString(label))


def build_main_menu():

    global menu
    menu.start_folder()

    menu.new_folder_item(
        item_name=loc(30004), description=loc(30005), item_val=None, func=open_settings)
    menu.new_folder_item(
        item_name=loc(30006), description=loc(30007), item_val=None, func=subscriptions)
    menu.new_folder_item(
        item_name=loc(30008), description=loc(30009), item_val=None, func=search)
    menu.new_folder_item(
        item_name=loc(30010), description=loc(30011), item_val=None, func=notifications)
    menu.new_folder_item(
        item_name=loc(30012), description=loc(30013), item_val=None, func=favourites)
    menu.new_folder_item(
        item_name=loc(30014), description=loc(30015), item_val=None, func=watch_later)
    menu.new_folder_item(
        item_name=loc(30016), description=loc(30017), item_val=None, func=recently_active)
    menu.new_folder_item(
        item_name=loc(30018), description=loc(30019), item_val=None, func=popular)
    menu.new_folder_item(
        item_name=loc(30020), description=loc(30021), item_val=None, func=trending)
    menu.new_folder_item(
        item_name=loc(30022), description=loc(30023), item_val=None, func=feed)
    menu.new_folder_item(
        item_name=loc(30024), description=loc(30025), item_val=None, func=video_by_id)
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


def build_recently_active():

    global menu
    menu.start_folder()

    subscriptions = bitchute_access.get_recently_active()

    if 0 == len(subscriptions):
        menu.new_info_item(loc(30026))
    else:
        for sub in subscriptions:
            menu.new_folder_item(
                item_name=sub.name, func=channel, item_val=sub.channel, iconURL=sub.channel_image, description=sub.description)

    menu.end_folder()


def build_notifications():

    global menu
    menu.start_folder()

    notifications = bitchute_access.get_notifications()

    if 0 == len(notifications):
        menu.new_info_item(loc(30027))
    else:
        for n in notifications:
            menu.new_folder_item(item_name=n.title, description=n.description, func=play_now, item_val=n.video_id,
                                 iconURL="https://www.bitchute.com/static/v129/images/logo-full-day.png")

    menu.end_folder()


def build_a_channel(item_val, page):

    global menu
    menu.start_folder()

    videos = bitchute_access.get_channel(item_val, page)

    if(page>0):
        menu.new_folder_item2(item_name="<<<< Previous page >>>>", func=channel_offset, item_val=item_val, item_val2=(page-1), description="Previous page", iconURL=None)

    for v in videos:
        menu.new_folder_item(
            item_name=v.title, func=play_now, item_val=v.video_id, description=v.channel_name+"\nDate: "+str(v.date)+"\nDuration: "+str(v.duration)+"\n"+v.description, iconURL=v.poster, label2=str(v.date))

    if len(videos)==25:
        menu.new_folder_item2(item_name="<<<< Next page >>>>", func=channel_offset, item_val=item_val, item_val2=(page+1), description="Next page", iconURL=None)


    menu.end_folder()


def build_playlist(playlist):
    global menu
    menu.start_folder()

    entries = bitchute_access.get_playlist(playlist)

    if 0 == len(entries):
        menu.new_info_item(loc(30028))
    else:
        for n in entries:
            menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, description=n.description, iconURL=n.poster)

    menu.end_folder()


def build_feed():

    global menu
    menu.start_folder()

    entries = bitchute_access.get_feed()

    if 0 == len(entries):
        menu.new_info_item(loc(30028))
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
        menu.new_info_item(loc(30028))
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
        menu.new_info_item(loc(30028))
    else:
        for n in entries:

            menu.new_folder_item(
                item_name=n.title, func=play_now, item_val=n.video_id, description=n.channel_name+"\n"+n.description, iconURL=n.poster)

    menu.end_folder()


def build_search():

    dlg = Dialog()
    d = dlg.input(loc(30029), type=INPUT_ALPHANUM)
    if d.strip() == "":
        return

    global menu
    menu.start_folder()

    results = bitchute_access.search(d)

    if 0 == len(results):
        menu.new_info_item(loc(30028))
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
    bitchute_access.bt_login()
