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

def loc(label):
    return(xbmcaddon.Addon().getLocalizedString(label))

def entries_to_listitems(entries, finalize_folder=True):
    global menu
    if finalize_folder:
        menu.start_folder()

    if 0 == len(entries):
        menu.new_info_item(loc(30028))
    else:
        for n in entries:
            description = ""
            if not isinstance(n, bitchute_access.NotificationEntry):
                description += "[B]" + n.channel_name + "[/B]\n"
                if not isinstance(n, bitchute_access.SearchEntry):
                    description += "Date: " + n.date + "\n"
                    description += "Duration: "+n.duration+"\n\n"
            description += n.description

            menu.new_video_item(item_name=n.title, url=n.video.video_url,
                                description=description, iconURL=n.video.poster)

    if finalize_folder:
        menu.end_folder()

def build_main_menu():
    global menu
    menu.start_folder()
    menu.new_folder_item(item_name=loc(30022), description=loc(30023), item_val=None, func=feed)
    menu.new_folder_item(item_name=loc(30006), description=loc(30007), item_val=None, func=subscriptions)
    menu.new_folder_item(item_name=loc(30010), description=loc(30011), item_val=None, func=notifications)
    menu.new_folder_item(item_name=loc(30018), description=loc(30019), item_val=None, func=popular)
    menu.new_folder_item(item_name=loc(30020), description=loc(30021), item_val=None, func=trending)
    menu.new_folder_item(item_name=loc(30012), description=loc(30013), item_val=None, func=favourites)
    menu.new_folder_item(item_name=loc(30014), description=loc(30015), item_val=None, func=watch_later)
    menu.new_folder_item(item_name=loc(30008), description=loc(30009), item_val=None, func=search)
    menu.new_folder_item(item_name=loc(30004), description=loc(30005), item_val=None, func=open_settings)
    menu.new_folder_item(item_name=loc(30024), description=loc(30025), item_val=None, func=video_by_id)
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

def build_notifications():
    entries_to_listitems(bitchute_access.get_notifications())

def build_a_channel(item_val, page):
    global menu
    menu.start_folder()

    videos = bitchute_access.get_channel(item_val, page)

    if(page>0):
        menu.new_folder_item2(item_name="<<<< Previous page >>>>", func=channel_offset, item_val=item_val, item_val2=(page-1), description="Previous page", iconURL=None)

    entries_to_listitems(videos, finalize_folder=False)

    if len(videos)==25:
        menu.new_folder_item2(item_name="<<<< Next page >>>>", func=channel_offset, item_val=item_val, item_val2=(page+1), description="Next page", iconURL=None)

    menu.end_folder()

def build_playlist(playlist):
    entries_to_listitems(bitchute_access.get_playlist(playlist))

def build_feed():
    entries_to_listitems(bitchute_access.get_feed())

def build_popular():
    entries_to_listitems(bitchute_access.get_popular())

def build_trending():
    entries_to_listitems(bitchute_access.get_trending())

def build_search():
    dlg = Dialog()
    d = dlg.input(loc(30029), type=INPUT_ALPHANUM)
    if d.strip() == "":
        return

    entries_to_listitems(bitchute_access.search(d))

def play_video(video_id):
    global menu
    v = bitchute_access.get_video(video_id)
    menu.play_now(v.videoURL)

def build_open_settings():
    xbmcaddon.Addon().openSettings()
    bitchute_access.bt_login()
