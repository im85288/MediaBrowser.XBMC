﻿import xbmc, xbmcgui, xbmcaddon, urllib, httplib, os, time, requests
__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ) 

_MODE_BASICPLAY=12

#################################################################################################
# menu item loader
# this loads the favourites.xml and sets the windows props for the menus to auto display
#################################################################################################
import xml.etree.ElementTree as xml

def loadMenuOptions():
    favourites_file = os.path.join(xbmc.translatePath('special://userdata'), "favourites.xml")
    
    WINDOW = xbmcgui.Window( 10000 )
    menuItem = 0
    
    tree = xml.parse(favourites_file)
    rootElement = tree.getroot()
    for child in rootElement.findall('favourite'):
        name = child.get('name')
        action = child.text

        index = action.find("plugin://plugin.video.xbmb3c")
        if(index > -1 and len(action) > 10):
            action_url = action[index:len(action) - 2]
            
            WINDOW.setProperty("xbmb3c_menuitem_name_" + str(menuItem), name)
            WINDOW.setProperty("xbmb3c_menuitem_action_" + str(menuItem), action_url)
            xbmc.log("xbmb3c_menuitem_name_" + str(menuItem) + " : " + name)
            xbmc.log("xbmb3c_menuitem_action_" + str(menuItem) + " : " + action_url)
            
            menuItem = menuItem + 1

loadMenuOptions()

#################################################################################################
# end menu item loader
#################################################################################################

#################################################################################################
# http image proxy server 
# This acts as a HTTP Image proxy server for all thumbs and artwork requests
# this is needed due to the fact XBMC can not use the MB3 API as it has issues with the HTTP response format
# this proxy handles all the requests and allows XBMC to call the MB3 server
#################################################################################################

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import os
import mimetypes
from threading import Thread
from SocketServer import ThreadingMixIn
from urlparse import parse_qs
from urllib import urlretrieve

class MyHandler(BaseHTTPRequestHandler):
    
    def logMsg(self, msg, debugLogging):
        if(debugLogging == "true"):
            xbmc.log("XBMB3C Image Proxy -> " + msg)
    
    #overload the default log func to stop stderr message from showing up in the xbmc log
    def log_message(self, format, *args):
        debugLogging = __settings__.getSetting('debug')
        if(debugLogging == "true"):
            the_string = [str(i) for i in range(len(args))]
            the_string = '"{' + '}" "{'.join(the_string) + '}"'
            the_string = the_string.format(*args)
            xbmc.log("XBMB3C Image Proxy -> BaseHTTPRequestHandler : " + the_string)
        return    
    
    def do_GET(self):
    
        mb3Host = __settings__.getSetting('ipaddress')
        mb3Port = __settings__.getSetting('port')
        debugLogging = __settings__.getSetting('debug')   
        
        params = parse_qs(self.path[2:])
        self.logMsg("Params : " + str(params), debugLogging)
        itemId = params["id"][0]
        requestType = params["type"][0]

        imageType = "Primary"
        if(requestType == "b"):
            imageType = "Backdrop"
        elif(requestType == "logo"):
            imageType = "Logo"
        elif(requestType == "banner"):
            imageType = "Banner"
        elif(requestType == "disc"):
            imageType = "Disc"
        elif(requestType == "clearart"):
            imageType = "Art"
        elif(requestType == "landscape"):
            imageType = "Thumb"
            
        remoteUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Items/" + itemId + "/Images/" + imageType + "?Format=png"
        
        self.logMsg("MB3 Host : " + mb3Host, debugLogging)
        self.logMsg("MB3 Port : " + mb3Port, debugLogging)
        self.logMsg("Item ID : " + itemId, debugLogging)
        self.logMsg("Request Type : " + requestType, debugLogging)
        self.logMsg("Remote URL : " + remoteUrl, debugLogging)
        
        # get the remote image
        self.logMsg("Downloading Image", debugLogging)
        requesthandle = urllib.urlopen(remoteUrl, proxies={})
        pngData = requesthandle.read()
        requesthandle.close()
        
        datestring = time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        length = len(pngData)
        
        self.logMsg("ReSending Image", debugLogging)
        self.send_response(200)
        self.send_header('Content-type', 'image/png')
        self.send_header('Content-Length', length)
        self.send_header('Last-Modified', datestring)        
        self.end_headers()
        self.wfile.write(pngData)
        self.logMsg("Image Sent", debugLogging)
        
    def do_HEAD(self):
        datestring = time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.send_response(200)
        self.send_header('Content-type', 'image/png')
        self.send_header('Last-Modified', datestring)
        self.end_headers()        
        
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

keepServing = True
def startServer():

    server = ThreadingHTTPServer(("",15001), MyHandler)
    
    while (keepServing):
        server.handle_request()
    #server.serve_forever()
    
    xbmc.log("XBMB3s -> HTTP Image Proxy Server EXITING")
    
xbmc.log("XBMB3s -> HTTP Image Proxy Server Starting")
Thread(target=startServer).start()
xbmc.log("XBMB3s -> HTTP Image Proxy Server NOW SERVING IMAGES")

#################################################################################################
# end http image proxy server 
#################################################################################################

#################################################################################################
# Recent Info Updater
# 
#################################################################################################
import threading
import json
from datetime import datetime
import time

class RecentInfoUpdaterThread(threading.Thread):

    def logMsg(self, msg, debugLogging):
        if(debugLogging == "true"):
            xbmc.log("XBMB3C Recent Info Thread -> " + msg)
    
    def run(self):
        xbmc.log("RecentInfoUpdaterThread Started")
        
        self.updateRecent()
        lastRun = datetime.today()
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if(secTotal > 300):
                self.updateRecent()
                lastRun = datetime.today()

            xbmc.sleep(1000)
                        
        xbmc.log("RecentInfoUpdaterThread Exited")
        
    def updateRecent(self):
        xbmc.log("updateRecentMovies Called")
        
        mb3Host = __settings__.getSetting('ipaddress')
        mb3Port =__settings__.getSetting('port')    
        userName = __settings__.getSetting('username')     
        debugLogging = __settings__.getSetting('debug')           
        
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"
        
        requesthandle = urllib.urlopen(userUrl, proxies={})
        jsonData = requesthandle.read()
        requesthandle.close()        
        
        userid = ""
        result = json.loads(jsonData)
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")    
                break
        
        xbmc.log("updateRecentMovies UserID : " + userid)
        
        xbmc.log("Updating Recent Movie List")
        
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=DateCreated&Fields=Path&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IncludeItemTypes=Movie&format=json"
        
        requesthandle = urllib.urlopen(recentUrl, proxies={})
        jsonData = requesthandle.read()
        requesthandle.close()     

        result = json.loads(jsonData)
        xbmc.log("Recent Movie Json Data : " + str(result))
        
        result = result.get("Items")
        if(result == None):
            result = []
            
        WINDOW = xbmcgui.Window( 10000 )

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')

            item_id = item.get("Id")
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestMovieMB3." + str(item_count) + ".Title = " + title, debugLogging)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Thumb = " + thumbnail, debugLogging)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Path  = " + playUrl, debugLogging)
            
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Path", playUrl)            
            
            item_count = item_count + 1
        
        xbmc.log("Updating Recent TV Show List")
        
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=DateCreated&Fields=Path&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&format=json"
        
        requesthandle = urllib.urlopen(recentUrl, proxies={})
        jsonData = requesthandle.read()
        requesthandle.close()         
        
        result = json.loads(jsonData)
        xbmc.log("Recent TV Show Json Data : " + str(result))
        
        result = result.get("Items")
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            seriesName = "Missing Name"
            if(item.get("SeriesName") != None):
                seriesName = item.get("SeriesName").encode('utf-8')   

            eppNumber = "X"
            if(item.get("IndexNumber") != None):
                eppNumber = str(item.get("IndexNumber"))

            item_id = item.get("Id")
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".EpisodeTitle = " + title, debugLogging)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".ShowTitle = " + seriesName, debugLogging)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".EpisodeNo = " + eppNumber, debugLogging)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Thumb = " + thumbnail, debugLogging)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Path  = " + playUrl, debugLogging)
            
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".EpisodeTitle", title)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".ShowTitle", seriesName)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".EpisodeNo", eppNumber)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Path", playUrl)            
            
            item_count = item_count + 1
        
        
newThread = RecentInfoUpdaterThread()
newThread.start()

#################################################################################################
# end Recent Info Updater
#################################################################################################

sys.path.append(BASE_RESOURCE_PATH)
playTime=0
def markWatched (url):
    xbmc.log('XBMB3C Service -> Marking watched via: ' + url)
    headers={'Accept-encoding': 'gzip','Authorization' : 'MediaBrowser', 'Client' : 'Dashboard', 'Device' : "Chrome 31.0.1650.57", 'DeviceId' : "f50543a4c8e58e4b4fbb2a2bcee3b50535e1915e", 'Version':"3.0.5070.20258", 'UserId':"ff"}
    resp = requests.post(url, data='', headers=headers)

def setPosition (url, method):
    WINDOW = xbmcgui.Window( 10000 )
    userid=WINDOW.getProperty("userid")
    authString='MediaBrowser UserId=\"' + userid + '\",Client=\"XBMC\",Device=\"XBMB3C\",DeviceId=\"42\",Version=\"0.7.5\"'
    headers={'Accept-encoding': 'gzip','Authorization' : authString}
    xbmc.log('XBMB3C Service -> Setting position via: ' + url)
    if method == 'POST':
        resp = requests.post(url, data='', headers=headers)
    elif method == 'DELETE':
        resp = requests.delete(url, data='', headers=headers)
    
def processPlaybackStop():
    WINDOW = xbmcgui.Window( 10000 )
    if (WINDOW.getProperty("watchedurl") != ""):
        xbmc.log("XBMB3C Service -> stopped at time:" + str(playTime))
        watchedurl = WINDOW.getProperty("watchedurl")
        positionurl = WINDOW.getProperty("positionurl")
        
        runtimeTicks = int(WINDOW.getProperty("runtimeticks"))
        xbmc.log ("XBMB3C Service -> runtimeticks:" + str(runtimeTicks))
        percentComplete = (playTime * 10000000) / runtimeTicks
        markPlayedAt = float(__settings__.getSetting("markPlayedAt")) / 100
        
        xbmc.log ("XBMB3C Service -> Percent Complete:" + str(percentComplete) + " Mark Played At:" + str(markPlayedAt))
        if (percentComplete > markPlayedAt):
            markWatched(watchedurl)
            setPosition(positionurl + '/Progress?PositionTicks=0', 'POST')
        else:
            setPosition(positionurl + '?PositionTicks=' + str(int(playTime * 10000000)), 'DELETE')
            
        WINDOW.setProperty("watchedurl","")
        WINDOW.setProperty("positionurl","")
        WINDOW.setProperty("runtimeticks","")
    
class Service( xbmc.Player ):

    def __init__( self, *args ):
        xbmc.log("XBMB3C Service -> starting monitor service")
        pass

    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
        WINDOW = xbmcgui.Window( 10000 )
        if (WINDOW.getProperty("watchedurl") != ""):
            positionurl = WINDOW.getProperty("positionurl")
            setPosition(positionurl + '/Progress?PositionTicks=0', 'POST')

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        xbmc.log("XBMB3C Service -> onPlayBackEnded")
        processPlaybackStop()

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        xbmc.log("XBMB3C Service -> onPlayBackStopped")
        processPlaybackStop()

montior = Service()
   
while not xbmc.abortRequested:

    if xbmc.Player().isPlaying():
        try:
            playTime = xbmc.Player().getTime()
        except:
            pass

    xbmc.sleep(1000)
    
# stop the image proxy
keepServing = False
try:
    requesthandle = urllib.urlopen("http://localhost:15001/?id=dummy&type=t", proxies={})
except:
    xbmc.log("XBMB3C Service -> Tried to stop image proxy server but it was already stopped")
    
xbmc.log("XBMB3C Service -> Service shutting down")
