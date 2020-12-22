# plugin.video.bitchute

## NOTE: this branch is for KODI 19 - there is only one change. Addon.xml has its python dependency set to 3.0.0 to allow to be installed in the KODI 19 Matrix Beta 2

Welcome to my Bitchute addon for KODI

Watch Bitchute within KODI. You will need a login user id and password from the www.bitchute.com website. 

Once you have the login, either:

Select the settings option for this add-on
or
Open the add-on and select the first option on the main menu "Set your Bitchute user"

Enter your bitchute user id and password in to the settings panel. Select OK

Once you have completed your user details, you will then be able to use the options for subscriptions, notifications, favourites and watch later.

The plugin has to rely on scraping using the Beautiful Soup 4 library because there is no documented API for Bitchute. If anyone knows the API, and where 
the documentation is... feel free to let me know in the github issues. If there is a proper authentication mechanism (OAUTH2 for example) then it could remove
the need to store user_ids and password in KODI settings and making working with the site much easier and more reliable.

Certain options such as "Popular" and "Trending" function without login details as they are 'scraped' from the front page. I'm hoping to allow users 
to explore the site using KODI (without the need to have a login), but it's a matter of how to translate that into KODI's awkward interface 
and its code.

Please note: I don't care if you have a problem with Bitchute and its stance on free speech. That's your choice. Use something else instead.

## Disclaimer

It's yours. If you break it, you can keep the pieces. If you want to add stuff feel free. You just need to follow the GPL and make your improvements available to others.

Like KODI, this add-in code is free and will remain so. If you'd like to support work on it, then it would be appreciated. Throw a few satoshis (Bitcoin) to:

![BC](assets/bcaddress.png)

3LNnxm4NbpcSs1eqSnndvx83zCx6mwqf7K