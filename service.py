from http.server import HTTPServer, BaseHTTPRequestHandler
import pickle
import requests
import threading
import bitchute_access

import xbmc
import xbmcaddon

addon = xbmcaddon.Addon()
http = None
cache = {}
stop_event = threading.Event()
thread = None
port = int(addon.getSetting('proxy_port'))

class ResolveVideoUrlProxy(BaseHTTPRequestHandler):
    def do_GET(self):
        video_id = self.path.lstrip('/')
        if video_id == 'quit':
            self.send_response(400)
            self.end_headers()
            return

        if video_id in cache:
            vid = cache[video_id]
        else:
            if len(cache) == 1000:
                cache.clear()

            vid = bitchute_access.get_video(video_id)
            cache[video_id] = vid

        self.send_response(302)
        self.send_header('Location', vid.video_url)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

def proxy_thread():
    global http
    global port
    try:
        server_address = ('', port)
        http = HTTPServer(server_address, ResolveVideoUrlProxy)
        xbmc.log("Start video resolver proxy server on Port " + str(port))
        while not stop_event.is_set():
            http.handle_request()
        xbmc.log("Stopped video resolver proxy server")
    except Exception as e:
        xbmc.log("Video resolver proxy server quit unexpectedly:" + str(e))
    http = None

def start_proxy():
    global thread
    thread = threading.Thread(target=proxy_thread)
    thread.daemon = True
    thread.start()

def stop_proxy():
    stop_event.set()
    requests.get(url="http://localhost:" + str(port) + "/quit")
    thread.join()
    stop_event.clear()

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        global addon
        global port
        global restart_server
        global thread

        addon = xbmcaddon.Addon()

        new_port = int(addon.getSetting('proxy_port'))
        if port != new_port:
            bitchute_access.clear_cache(login=False, data=True)
            stop_proxy()
            port = new_port
            start_proxy()

        xbmc.log("Settings changed")

if __name__ == '__main__':
    start_proxy()
    monitor = Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort():
            stop_proxy()
            xbmc.log("Abort requested")

