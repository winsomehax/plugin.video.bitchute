from bs4 import BeautifulSoup
import requests


class Video():

    def __init__(self, videoURL, poster, title, description):

        self.videoURL = videoURL
        self.poster = poster
        self.title = title
        self.description=description


class ChannelEntry():

    def __init__(self, video_id, poster, title, description):
        self.video_id = video_id
        self.poster = poster
        self.title = title
        self.description=description

class Subscription():

    def __init__(self, name, channel, last_video, description_text, channel_image):
        self.name = name
        self.channel = channel.replace("/channel/", "")
        self.last_video = last_video
        self.description_text = description_text
        self.channel_image = channel_image


class Notification():

    def __init__(self, video_id, notification_detail):
        self.video_id = video_id
        self.channel_id = video_id
        # split(vid"/video/5vnIKCCYzJIo/?list=notifications&amp;randomize=false"
        self.notification_detail = notification_detail

class PlaylistEntry():

    def __init__(self, video_id, description, title, poster):
        self.video_id = video_id
        self.description = description
        self.title = title
        self.poster = poster

class BitChute():

    def __init__(self, user, password):

        self.username = user
        self.password = password
        self.logged_in = False
        token = ""
        url = "https://www.bitchute.com/accounts/login/"
        req = requests.get(url)
        csrfJar = req.cookies
        soup = BeautifulSoup(req.text, "html.parser")
        metas = soup.find_all("input")
        for meta in metas:
            if meta.attrs['name'] == "csrfmiddlewaretoken":
                token = meta.attrs['value']

        if token != "":

            baseURL = "https://www.bitchute.com"
            post_data = {'csrfmiddlewaretoken': token,
                         'username': self.username, 'password': self.password}
            headers = {'Referer': baseURL + "/", 'Origin': baseURL}
            response = requests.post(
                baseURL + "/accounts/login/", data=post_data, headers=headers, cookies=csrfJar)

            # it's the cookies that carry forward the token/ids
            self.csrfJar = response.cookies
            self.logged_in = True

    def subscriptions(self):

        if not self.logged_in:
            return

        subs = []

        url = "https://www.bitchute.com/subscriptions/"
        req = requests.get(url, cookies=self.csrfJar)
        self.csrfJar = req.cookies

        soup = BeautifulSoup(req.text, "html.parser")

        containers = soup.find_all(class_="subscription-container")

        for sub in containers:
            name = sub.find(class_="subscription-name").contents[0]
            channel = sub.find(class_="spa").attrs["href"]
            last_video = sub.find(class_="subscription-last-video").contents[0]
            description_text = sub.find(
                class_="subscription-description-text").contents
            channel_image = sub.find(
                class_="subscription-image lazyload").attrs['data-src']

            s = Subscription(name=name, channel=channel, last_video=last_video,
                             description_text=description_text, channel_image=channel_image)
            subs.append(s)

        return subs

    def notifications(self):

        if not self.logged_in:
            return

        notifs = []

        url = "https://www.bitchute.com/notifications/"
        req = requests.get(url, cookies=self.csrfJar)
        self.csrfJar = req.cookies

        soup = BeautifulSoup(req.text, "html.parser")

        containers = soup.find_all(class_="notification-item")

        for n in containers:

            video_id = n.find(class_="notification-view").attrs["href"]
            notification_detail = n.find(
                class_="notification-detail").contents[0]

            s = Notification(video_id=video_id,
                             notification_detail=notification_detail)
            notifs.append(s)

        return notifs

    def get_channel(self, channel):

        if not self.logged_in:
            return

        videos = []

        url = "https://www.bitchute.com/channel/"+channel
        req = requests.get(url, cookies=self.csrfJar)
        self.csrfJar = req.cookies

        soup = BeautifulSoup(req.text, "html.parser")

        containers = soup.find_all(class_="channel-videos-container")

        for n in containers:
            t = n.find(class_="channel-videos-title").find("a")
            video_id=t.attrs["href"].replace("/video/", "").strip("/")
            title=t.contents[0]     
            description = n.find(class_="channel-videos-text").get_text()
            poster=n.find(class_="channel-videos-image").find("img").attrs['data-src']
            s = ChannelEntry(video_id=video_id,description=description, title=title,poster=poster)
            print("&&&& ", title, poster)
            videos.append(s)

        return videos

    def get_playlist(self, playlist_name):

        #"favorites", "watch-later"

        if not self.logged_in:
            return

        playlist = []

        url = "https://www.bitchute.com/playlist/"+playlist_name+"/"

        req = requests.get(url, cookies=self.csrfJar)
        self.csrfJar = req.cookies

        soup = BeautifulSoup(req.text, "html.parser")

        containers = soup.find_all(class_="playlist-video")

        for n in containers:
            t = n.find(class_="text-container").find("a")
            video_id=t.attrs["href"].replace("/video/", "").split("/")[0]
            title=n.find(class_="title").find("a").contents[0]     
            description = n.find(class_="description hidden-xs").get_text()
            poster=n.find(class_="image-container").find("img").attrs['data-src']

            s = PlaylistEntry(video_id=video_id,description=description, title=title,poster=poster)
            playlist.append(s)

        return playlist

    def get_video(self, video_id):
        url = "https://www.bitchute.com/video/"+video_id
        req = requests.get(url, cookies=self.csrfJar)
        self.csrfJar = req.cookies

        soup = BeautifulSoup(req.text, "html.parser")

        videoURL = soup.find("source").attrs["src"]
        poster = soup.find("video").attrs["poster"]
        title = soup.find(id="video-title").contents[0]

        video = Video(videoURL=videoURL, poster=poster, title=title, description="")

        return (video)
