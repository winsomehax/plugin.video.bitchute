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

    def new_video_item(self, displayName, title, playURL, thumbURL, duration, description=""):
        if displayName is not None:
            str = displayName + ": " + title
        else:
            str = title

        li = ListItem(label=str, path=playURL)
        li.setProperty('IsPlayable', 'True')
        li.addStreamInfo('video', {'duration': duration, 'plot': description})
        li.setArt({'icon': thumbURL, 'poster': thumbURL, 'thumb': thumbURL,
                   'banner': thumbURL})

        addDirectoryItem(self.h, playURL, listitem=li, isFolder=False)

    def new_folder_item(self, item_name, func, iconURL="", description="", item_val=None, label2=""):
        li = ListItem(label=item_name)
        li.setIsFolder(True)
        li.setProperty('IsPlayable', 'True')
        # This is just so that the left hand plot shows up in Kodi
        li.setInfo('video', {'plot': description})
        li.addStreamInfo('video', {'duration': label2, 'plot': description})
        li.setArt({'icon': iconURL, 'poster': iconURL, 'thumb': iconURL,
                   'banner': iconURL})

        addDirectoryItem(self.h, self.plugin.url_for(func, item_val=item_val),
                         listitem=li, isFolder=True)

    def new_folder_item2(self, item_name, func, item_val, item_val2, iconURL="", description=""):
        li = ListItem(label=item_name)
        li.setIsFolder(True)
        li.setProperty('IsPlayable', 'True')
        # This is just so that the left hand plot shows up in Kodi
        li.setInfo('video', {'plot': description})
        li.setArt({'icon': iconURL, 'poster': iconURL, 'thumb': iconURL,
                   'banner': iconURL})
        xbmc.log("!!!!: " + self.plugin.url_for(func, item_val=item_val, item_val2=item_val2))

        addDirectoryItem(self.h, self.plugin.url_for(func, item_val=item_val, item_val2=item_val2),
                         listitem=li, isFolder=True)

    def end_folder(self):
        endOfDirectory(self.h)
