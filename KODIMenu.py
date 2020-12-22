from xbmcplugin import addDirectoryItem, endOfDirectory, setContent
from xbmcgui import ListItem
from xbmc import Player


class KODIMenu():

    def __init__(self, plugin):
        self.plugin = plugin
        self.h = plugin.handle

    def start_folder(self):
        setContent(self.h, "files")

    def play_now(self, play_url):
        Player().play(play_url)

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
        li.setArt({'icon': thumbURL, 'poster': thumbURL,
                   'thumb': thumbURL, 'banner': thumbURL})

        #li.setInfo('video', { 'plot': 'Left hand desc' })

        addDirectoryItem(self.h, playURL, listitem=li, isFolder=False)

    def new_folder_item(self, item_name, item_val, func, iconURL="", description=""):
<<<<<<< HEAD

        li = ListItem(label=item_name, iconImage="")
        li.setIsFolder(True)

        li.setProperty('IsPlayable', 'True')
        li.setInfo('video', { 'plot': description }) # This is just so that the left hand plot shows up in Kodi

=======

        li = ListItem(label=item_name)
        li.setIsFolder(True)

        li.setProperty('IsPlayable', 'True')
        # This is just so that the left hand plot shows up in Kodi
        li.setInfo('video', {'plot': description})

>>>>>>> 07df12de6617544bb708f85cd94d6ea95efdc8e1
        li.setArt({'icon': iconURL, 'poster': iconURL,
                   'thumb': iconURL, 'banner': iconURL})
        addDirectoryItem(self.h, self.plugin.url_for(func, item_val=item_val),
                         listitem=li, isFolder=True)

    def end_folder(self):
        endOfDirectory(self.h)
