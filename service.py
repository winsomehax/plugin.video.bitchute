import xbmc
import xbmcaddon
import bitchute_access

addon = xbmcaddon.Addon()

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)

if __name__ == '__main__':
    monitor = Monitor()
    while not monitor.abortRequested():
        try:
            if addon.getSettingBool('precache_video_links'):
                cookies, success = bitchute_access.bt_login()
                if success:
                    # Refresh the video cache to speed up common
                    xbmc.log("Pre-caching get_feed()")
                    bitchute_access.get_feed()
                    xbmc.log("Pre-caching get_notifications()")
                    bitchute_access.get_notifications()
                    xbmc.log("Pre-caching get_popular()")
                    bitchute_access.get_popular()
                    xbmc.log("Pre-caching get_trending()")
                    bitchute_access.get_trending()
                    xbmc.log("Pre-caching get_recently_active()")
                    bitchute_access.get_recently_active()

        except Exception as e:
            xbmc.log(f'Unhandled exception: {str(e)}')

        if monitor.waitForAbort(15*60): # Wait for 15 minutes
            xbmc.log("Abort requested")

