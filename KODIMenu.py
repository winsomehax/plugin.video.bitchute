from xbmcplugin import addDirectoryItem, endOfDirectory, setContent
from xbmcgui import ListItem
import xbmc

class KODIMenu():
    def __init__(self, plugin):
        self.plugin = plugin
        self.h = plugin.handle

    def start_folder(self):
        setContent(self.h, "files")

    def play_now(self, play_url):
        xbmc.Player().play(play_url)

    def new_info_item(self, info):
        li = ListItem(label=info)
        li.setProperty('IsPlayable', 'False')
        addDirectoryItem(self.h, "", listitem=li, isFolder=False)

    def new_video_item(self, item_name, url, iconURL="", description=""):
        li = ListItem(label=item_name)
        li.setProperty('IsPlayable', 'True')
        li.getVideoInfoTag().setPlot(description)
        li.setArt({'icon': iconURL, 'poster': iconURL,
                   'thumb': iconURL, 'banner': iconURL, 'fanart': iconURL})

        addDirectoryItem(self.h, url, listitem=li, isFolder=False)


    def new_folder_item(self, item_name, description, iconURL, func, **kwargs):
        li = ListItem(label=item_name)
        li.setIsFolder(True)
        li.setProperty('IsPlayable', 'True')
        li.getVideoInfoTag().setPlot(description)
        li.setArt({'icon': iconURL, 'poster': iconURL, 'thumb': iconURL,
                   'banner': iconURL})
        addDirectoryItem(self.h, self.plugin.url_for(func, **kwargs),
                         listitem=li, isFolder=True)

    def end_folder(self):
        endOfDirectory(self.h)
