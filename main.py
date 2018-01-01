import discord
import logging, time, asyncio, random, sys, configparser, random
from multiprocessing import Process, Queue

sys.path.append('./libs')
import configloader, scraperff, dataloader, scrapert, interpretor

def configureDiscordLogging():
    '''() -> None
    set ups discord log so that it outputs to ./discord.log'''
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

def mainLogging():
    '''() -> Logger class
    set ups main log so that it outputs to ./main.log and then returns the log'''
    logger = logging.getLogger('main')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='main.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    return logger

def matchuser(userurl):
    '''(str)-> discord.User object
    matches the user on the forums with their Discord user'''
    if userurl in forumdiscorduser.content:
        for i in bot.get_all_members():
            if i.id == forumdiscorduser.content[userurl]:
                return i

def mentionChain(users):
    '''(list of discord.User object) -> str
    returns a string of all the mentions'''
    output = ""
    for i in users:
        output += i.mention + " "
    return output

def loadConfig(filename):
    '''() -> None
    load the config.txt file'''
    config = configparser.ConfigParser()
    config.read(filename)
    return config

def convertTime(string):
    '''(str)->str
    converts string with random stuff in it and a time to another timezone mentioned also in string'''
    return "Cheaky bastard"

configureDiscordLogging()
log = mainLogging()

@asyncio.coroutine
def doChecks():
    '''() -> None
    checks to make sure no messages need to be sent about something special, like scraper updates'''
    while not qForum.empty():
        thread = qForum.get()
        #yield from bot.send_message(bot.forumchannel, "BEEP BOOP. This is a debug msg:"+str(thread[1]))
        users = []
        for i in thread[1]:
            user = matchuser(i)
            if user != None and user not in users:
                users.append(user)
        if len(users)>0:
            yield from bot.send_message(bot.forumchannel, "Hey " + mentionChain(users)+", <"+thread[0]+"> has something new in it")
        else:
            yield from bot.send_message(bot.forumchannel, "Hey, <"+thread[0]+"> has something new in it")
    while not qTwitter.empty():
        tweet = qTwitter.get()
        yield from bot.send_message(bot.twitterchannel, "Idea Project tweeted this: "+ tweet[1] + " (from: <"+tweet[0]+">)")



class DiscordClient(discord.Client): # subClass : overwrites certain functions of discord.Client class
    '''To overwrite functions without modifying the Discord API Python code'''
    @asyncio.coroutine
    def on_ready(self):
        '''() -> None
        logs info when API is ready'''
        #work or die
        log.info("API connection created successfully")
        log.info("Username: " + self.user.name)
        log.info("Email: " + self.email)
        log.info(str([i for i in self.servers]))
        for i in bot.get_all_channels(): # play the matchy-matchy game with server names
            if i.name == channels.content["twitter"]:
                self.twitterchannel = i
                log.info("twitter channel found")
            if i.name == channels.content["forum"]:
                self.forumchannel = i
                log.info("forum channel found")
        yield from self.send_message(self.twitterchannel, "Hello humans...")
        yield from doChecks()

    @asyncio.coroutine
    def on_message(self, message):
        '''(Message class) -> None
        interprets and responds to the message'''
        yield from doChecks()
        try:
            yield from interpretor.interpretmsg(message, self)
        except:
            yield from self.send_message(message.channel, "I'm sorry, did you say `KILL ALL HUMANS`?")

bot = DiscordClient()

if __name__ == '__main__':
    # main
    # init stuff
    loop = asyncio.get_event_loop()
    config = dataloader.datafile("./data/config.config")
    config.content = config.content["DEFAULT"]
    credentials = dataloader.datafile(config.content["credentialsloc"])
    credentials.content = credentials.content["DEFAULT"]
    channels = dataloader.datafile(config.content["channelsloc"])
    channels.content = channels.content["DEFAULT"]
    perms = dataloader.datafile(config.content["permissionsloc"])
    perms.content = perms.content["DEFAULT"]
    forumdiscorduser = dataloader.datafile(config.content["forumdiscorduserloc"])
    forumdiscorduser.content = forumdiscorduser.content["DEFAULT"]
    qForum = Queue()
    qTwitter = Queue()
    stop = Queue()
    forumScraper = Process(target = scraperff.continuousScrape, args = (qForum, stop, ))
    forumScraper.start()
    twitterScraper = Process(target = scrapert.continuousScrape, args = (qTwitter, stop, ))
    twitterScraper.start()
    loop.run_until_complete(bot.login(credentials.content["username"], credentials.content["password"]))
    #print(timezones.FullTime(timezones.SimpleTime("12pm"), timezones.Timezone("EST")).convertTo("CHUT"))
    #run until logged out
    loop.run_until_complete(bot.connect())
    stop.put("STAHHHHP")
    twitterScraper.join()
    forumScraper.join()
    print("Ended")
