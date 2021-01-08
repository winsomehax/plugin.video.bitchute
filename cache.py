import xbmcaddon

try:
    import StorageServer
except:
    import storageserverdummy as StorageServer


# add version to name so if there is a version bump it avoid cache issues
login_cache = StorageServer.StorageServer(
    "bitchute_logindetails"+xbmcaddon.Addon().getAddonInfo('version'), 24)  # refresh login per day (24hrs)
data_cache = StorageServer.StorageServer(
    "bitchute_data"+xbmcaddon.Addon().getAddonInfo('version'), 0.25)  # reloads subs per 15m
