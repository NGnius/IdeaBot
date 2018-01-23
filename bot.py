# -*- coding: utf-8 -*-
"""
Bot is the discord bot which is responsible for holding all the state necessary
to initialize and run.

Created on Wed Jan 10 20:05:03 2018

@author: 14flash
"""

import discord
import asyncio
from commands import command

from libs import dataloader

DEFAULT = 'DEFAULT'
CHANNEL_LOC = 'channelsloc'

class Bot(discord.Client):
    '''A Discord client which has config data and a list of commands to try when
    a message is received.'''

    def __init__(self, config, log, checks):
        '''(str, Logger, fun) -> Bot
        config: a string which is the loaction of the base config file
        log: a Logger for dumping info
        checks: a function which checks reddit/forum/twitter for new stuff'''
        super().__init__()
        if not config:
            # TODO: raise some kind of exception
            pass
        self.data_config = dataloader.datafile(config).content[DEFAULT]
        self.log = log
        # TODO(14flash): Plugin refactor, where we won't need a doCheck() func anymore
        self.checks = checks
        self.data = dict()
        self.commands = list()
        self.admin_commands = list()
        self.plugins = list()

    def add_data(self, name, content_from=DEFAULT):
        '''(str, str) -> None
        Adds configuration data to Bot's data dict. It expects that data_config
        contains an entry for 'name' which points to a file that it can extract
        content from. content_from may be specified to get data other than the
        default.'''
        data_file = dataloader.datafile(self.data_config[name])
        self.data[name] = data_file.content[content_from]

    def get_data(self, name, key=None):
        '''(str, str) -> object
        Returns data from a previously read configuration file.'''
        if key:
            return self.data[name][key]
        return self.data[name]

    def register_command(self, cmd):
        '''(Command) -> None
        Registers a Command for execution when a message is received.'''
        if not isinstance(cmd, command.Command):
            raise ValueError('Only commands may be registered in Bot::register_command')
        self.commands.append(cmd)

    def register_admin_command(self, cmd):
        '''(AdminCommand) -> None
        Registers a Command for execution when a PM is received from an admin'''
        if not isinstance(cmd, command.AdminCommand):
            raise ValueError('Only AdminCommands may be registered in Bot::register_admin_command')
        self.admin_commands.append(cmd)

    def register_plugin(self, plugin):
        '''(Plugin) -> None
        Registers a Plugin which executes in a separate process'''
        # TODO(14flash): Plugin refactor.
        pass

    @asyncio.coroutine
    def on_message(self, message):
        yield from self.checks(self)
        for cmd in self.commands:
            if cmd._matches(message):
                yield from cmd._action(message, self.send_message)
                # TOOD(14flash): is break necessary? Can this be done per command?
                break
        for cmd in self.admin_commands:
            if cmd._matches(message):
                yield from cmd._action(message, self.send_message, self)

    @asyncio.coroutine
    def on_ready(self):
        self.log.info('API connection created successfully')
        self.log.info('Username: ' + str(self.user.name))
        self.log.info('Email: ' + str(self.email))
        self.log.info(str([i for i in self.servers]))
        self.setup_channels()
        yield from self.send_message(self.twitterchannel, 'Hello humans...')
        yield from self.checks(self)

    def setup_channels(self):
        '''() -> None
        Convinience fuction for on_ready()'''
        for i in self.get_all_channels(): # play the matchy-matchy game with server names
            if i.name == self.get_data(CHANNEL_LOC, 'twitter'):
                self.twitterchannel = i
                self.log.info('twitter channel found')
            if i.name == self.get_data(CHANNEL_LOC, 'forum'):
                self.forumchannel = i
                self.log.info('forum channel found')
            if i.name == self.get_data(CHANNEL_LOC, 'reddit'):
                self.redditchannel = i
                self.log.info('reddit channel found')
