# -*- coding: utf-8 -*-
"""
Bot is the discord bot which is responsible for holding all the state necessary
to initialize and run.

Created on Wed Jan 10 20:05:03 2018

@author: 14flash and NGnius
"""

import discord
import asyncio

from libs import dataloader, savetome, loader
from libs import command, plugin, addon
from libs import reaction as reactioncommand
import importlib
# import traceback
# from os import listdir
from os import listdir
from os.path import isfile, join
from collections import OrderedDict

DEFAULT = 'DEFAULT'
CHANNEL_LOC = 'channelsloc'
MSG_BACKUP_LOCATION = 'msgbackuploc'
WATCH_MSG_LOCATION = 'alwayswatchmsgloc'
ROLE_MSG_LOCATION = 'rolemessagesloc'
LOADING_WARNING = "Things are loading"
ADMINS = ["106537989684887552", "255041793417019393"]

COMMANDS = 'commands'
REACTIONS = 'reactions'
PLUGINS = 'plugins'

# saved stuff
# in the event of a crash, the data stored here can be used instead of loading
# from storage and/or internet (slow)
_messages = None
_commands = None
_reactions = None
_plugins = None
_packages = None

EMOJIS_LOCATION = 'emojiloc'
PERMISSIONS_LOCATION = 'permissionsloc'
CONFIGEND = 'configend'


class Bot(discord.Client):
    '''A Discord client which has config data and a list of commands to try when
    a message is received.'''

    CHANNEL_LOC = 'channelsloc'
    MSG_BACKUP_LOCATION = 'msgbackuploc'
    WATCH_MSG_LOCATION = 'alwayswatchmsgloc'
    ROLE_MSG_LOCATION = 'rolemessagesloc'
    MAX_MESSAGES = 'maxmessages'

    COMMANDS = COMMANDS
    REACTIONS = REACTIONS
    PLUGINS = PLUGINS

    ADMINS = ADMINS

    commands = OrderedDict()  # maps names to commands
    reactions = OrderedDict()  # maps names to reaction commands
    plugins = OrderedDict()  # maps names to plugins
    packages = dict()

    def __init__(self, config, log):
        '''(str, Logger, fun) -> Bot
        config: a string which is the loaction of the base config file
        log: a Logger for dumping info
        checks: a function which checks reddit/forum/twitter for new stuff'''
        if not config:
            # TODO: raise some kind of exception
            pass
        self.data_config = dataloader.datafile(config).content[DEFAULT]
        if self.MAX_MESSAGES in self.data_config:
            max_messages = int(self.data_config[self.MAX_MESSAGES])
            # NOTE: if value provided is not a valid integer, bot will fail to start. INTENDED!
        else:
            max_messages = None
        super().__init__(max_messages=max_messages)
        self.log = log
        self.data = dict()
        self.always_watch_messages = {LOADING_WARNING}
        self.role_messages = savetome.load_role_messages(self.data_config[ROLE_MSG_LOCATION], self.get_all_emojis)
        self.load_all_addons(reload=True)

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

    def register_command(self, cmd, name, package=None):
        '''(Command, str) -> None
        Registers a Command for execution when a message is received.'''
        global _commands
        if not isinstance(cmd, command.Command):
            raise ValueError('Only commands may be registered in Bot::register_command')
        if name in self.commands:
            self.commands[name] = cmd
        else:
            self.commands[name] = cmd
            for key in list(self.commands.keys()):
                if name == key:
                    break
                elif sorted([name, key])[0] == name:
                    self.commands.move_to_end(key)
        if package != '':
            self.register_package(COMMANDS, name, package)
        _commands = self.commands

    def register_plugin(self, plugin_object, name, package=None):
        '''(Plugin, str) -> None
        Registers a Plugin which executes in a separate process'''
        global _plugins
        if not isinstance(plugin_object, plugin.Plugin):
            raise ValueError('Only plugins may be registered in Bot::register_plugin')
        if isinstance(plugin_object, plugin.AdminPlugin):  # give AdminPlugins access to all this class's variables
            plugin_object.add_client_variable(self)
        if name in self.plugins:
            self.plugins[name] = plugin_object
        else:
            self.plugins[name] = plugin_object
            for key in list(self.plugins.keys()):
                if name == key:
                    break
                elif sorted([name, key])[0] == name:
                    self.plugins.move_to_end(key)
        if package != '':
            self.register_package(PLUGINS, name, package)
        self.loop.create_task(plugin_object._action())
        _plugins = self.plugins

    def register_reaction_command(self, cmd, name, package=None):
        '''(reaction.Command, str) -> None
        Registers a reaction command for execution when a message is reacted to'''
        global _reactions
        if not (isinstance(cmd, reactioncommand.ReactionAddCommand)\
            or isinstance(cmd, reactioncommand.ReactionRemoveCommand)\
            or isinstance(cmd, reactioncommand.Dummy)):
            raise ValueError("%s is not a reaction command. Only reaction add/remove commands may be registered in Bot::register_reaction_command" % name)
        if name in self.reactions:
            self.reactions[name] = cmd
        else:
            self.reactions[name] = cmd
            for key in list(self.reactions.keys()):
                if name == key:
                    break
                elif sorted([name, key])[0] == name:
                    self.reactions.move_to_end(key)
        if package != '':
            self.register_package(REACTIONS, name, package)
        _reactions = self.reactions

    def register_package(self, addon_type, name, package):
        '''(str, str) -> None
        Registers an add-on into a package'''
        global _packages
        if package not in self.packages:
            new_package = {
            self.COMMANDS: list(),
            self.REACTIONS: list(),
            self.PLUGINS: list()
            }
            self.packages[package] = new_package
        if name not in self.packages[package][addon_type]:
            self.packages[package][addon_type].append(name)
        _packages = self.packages

    def get_package(self, name, addon_type):
        for key in self.packages:
            if name in self.packages[key][addon_type]:
                return key

    def load_command(self, filename, name, package=None, reload=False):
        '''(str, str[, str]) -> command.Command
        initilizes a command and then registers it with the bot'''
        # set up params for init_command
        if package:
            if package not in loader.sub_namespaces:
                loader.sub_namespaces[package] = loader.CustomNamespace()
            namespace = loader.sub_namespaces[package]
        else:
            namespace = loader.namespace
        if package is None:
            package_loader = ""
        else:
            package_loader = package
        # init command
        cmd = loader.init_command(filename, namespace, self, 'commands', package_loader, reload)
        # register command to bot
        self.register_command(cmd, name, package=package)
        return self.commands[name]

    def load_reaction(self, filename, name, package=None, reload=False):
        '''(str, str[, str]) -> reaction.Reaction
        initilizes a reaction command and then registers it with the bot'''
        # set up params for init_reaction
        if package:
            if package not in loader.sub_namespaces:
                loader.sub_namespaces[package] = loader.CustomNamespace()
            namespace = loader.sub_namespaces[package]
        else:
            namespace = loader.namespace
        if package is None:
            package_loader = ""
        else:
            package_loader = package
        # init command
        cmd = loader.init_reaction(filename, namespace, self, 'reactions', package_loader, loader.emoji_dir, reload)
        # register reaction to bot
        self.register_reaction_command(cmd, name, package=package)
        return self.reactions[name]

    def load_plugin(self, filename, name, package=None, reload=False):
        '''(str, str[, str]) -> plugin.Plugin
        initilizes a plugin and then registers it with the bot'''
        # set up params for init_command
        if package:
            if package not in loader.sub_namespaces:
                loader.sub_namespaces[package] = loader.CustomNamespace()
            namespace = loader.sub_namespaces[package]
        else:
            namespace = loader.namespace
        if package is None:
            package_loader = ""
        else:
            package_loader = package
        # init command
        cmd = loader.init_plugin(filename, namespace, self, 'plugins', package_loader, reload)
        # register plugin to bot
        self.register_plugin(cmd, name, package=package)
        return self.plugins[name]

    def load_addon(self, filename, name, package=None, reload=False, **kwargs):
        '''(str, str[, str]) -> plugin.Plugin or reaction.Reaction or command.Command
        initilizes an addon and then registers it with the bot
        This determines what sort of add-on the file contains and acts accordingly'''
        if package:
            if package not in loader.sub_namespaces:
                loader.sub_namespaces[package] = loader.CustomNamespace()
            namespace = loader.sub_namespaces[package]
        else:
            namespace = loader.namespace
        if package is None:
            package_loader = ""
        else:
            package_loader = package
        # do loading stuff
        # params for addon init
        bot = self
        config_end = self.data_config[CONFIGEND]
        events = {
        addon.READY: bot.wait_until_ready,
        addon.LOGIN: bot.wait_until_login,
        addon.MESSAGE: bot.wait_for_message,
        addon.REACTION: bot.wait_for_reaction
        }
        api_methods = {
        addon.SEND_MESSAGE: bot.send_message,
        addon.EDIT_MESSAGE: bot.edit_message,
        addon.ADD_REACTION: bot.add_reaction,
        addon.REMOVE_REACTION: bot.remove_reaction,
        addon.SEND_TYPING: bot.send_typing,
        addon.SEND_FILE: bot.send_file
        }
        parameters = {
        'user': lambda: bot.user, # user_func uses lambda to create a closure on bot
        'namespace': namespace,
        'always_watch_messages': bot.always_watch_messages,
        'role_messages': bot.role_messages,
        'api_methods': api_methods,
        'events': events,
        'all_emojis_func': bot.get_all_emojis
        }
        # find config file
        if filename[:-len(".py")]+config_end in self.data_config:
            parameters['config'] = self.data_config[filename[:-len(".py")]+config_end]
        elif isfile(join('addons', package_loader, filename[:-len(".py")]+'.config')):
            parameters['config'] = join('addons', package_loader, filename[:-len(".py")]+'.config')
        else:
            parameters['config'] = None

        if package_loader:
            package_loader = package+'.'
        try:
            temp_lib = importlib.import_module("addons."+package_loader+filename[:-len(".py")])  # import reaction
        except Exception as e:
            print('While loading addons, failed to load python file %s' % filename)
            raise e
        if reload:  # dumb way to do it, ik
            temp_lib = importlib.reload(temp_lib)

        if 'Plugin' in dir(temp_lib):
            try:
                plugin_instance = temp_lib.Plugin(**parameters, **kwargs)  # init plugin
            except Exception as e:
                self.log.warning('Failed to initialize plugin %s' % name)
                raise e
            self.register_plugin(plugin_instance, name, package=package)
            return self.plugins[name]
        elif 'Command' in dir(temp_lib):
            # add command-specific parameters
            perms_dir = self.data_config[PERMISSIONS_LOCATION]
            parameters['perms_loc'] = perms_dir+'c.'+package_loader+filename[:-len(".py")]+".json"
            try:
                cmd_instance = temp_lib.Command(**parameters, **kwargs)  # init command
            except Exception as e:
                self.log.warning('Failed to initialize command %s' % name)
                raise e
            self.register_command(cmd_instance, name, package=package)
            return self.commands[name]
        elif 'Reaction' in dir(temp_lib):
            # add reaction-specific parameters
            perms_dir = self.data_config[PERMISSIONS_LOCATION]
            emoji_dir = self.data_config[EMOJIS_LOCATION]
            parameters['perms_loc'] = perms_dir+'r.'+package_loader+filename[:-len(".py")]+".json"
            parameters['emoji_loc'] = emoji_dir+package_loader+filename[:-len(".py")]+".json"
            try:
                reaction_instance = temp_lib.Reaction(**parameters, **kwargs)  # init reaction
            except Exception as e:
                self.log.warning('Failed to initialize reaction %s' % name)
                raise e
            self.register_reaction_command(reaction_instance, name, package=package)
            return self.reactions[name]

    def load_all_addons(self, reload=False):
        if int(self.data_config['loadoldfolders']):
            if len(self.commands) == 0 or reload:
                loader.load_commands('commands', self, register=True)
            if len(self.reactions) == 0 or reload:
                loader.load_reactions('reactions', self, register=True)
            # always relaod plugins
            if len(self.plugins) != 0:
                self.plugins.clear()
            loader.load_plugins('plugins', self, register=True)
        self.load_addons('addons', register=True)

    def load_addons(self, folder, register=False):
        bot = self
        for item in sorted(listdir(folder)):
            if isfile(join(folder, item)):
                if item[-len(".py"):] == ".py" and item[0]!="_":
                    self.log.info("Loading addon in %s " % item)
                    if register:
                        try:
                            addon=bot.load_addon(item, item[:-len(".py")], package=None)
                            assert addon is not None
                        except AssertionError:
                            self.log.info('No addon found in %s' % join(folder, item))
                        except Exception as e:
                            print('Failed to load addon at %s' % join(folder, item))
                            self.log.error(('Failed to load %s reason: ' % join(folder, item)) + str(e))
            elif item[0] != "_": # second level
                for sub_item in sorted(listdir(join(folder, item))):
                    if isfile(join(folder, item, sub_item)):
                        if sub_item[-len(".py"):] == ".py" and sub_item[0]!="_":
                            self.log.info("Loading addon in %s " % join(item, sub_item))
                            if register:
                                try:
                                    addon=bot.load_addon(sub_item, sub_item[:-len(".py")], package=item)
                                    assert addon is not None
                                except AssertionError:
                                    self.log.info('No addon found in %s' % join(folder, item, sub_item))
                                except Exception as e:
                                    print('Failed to load addon at %s' % join(folder, item, sub_item))
                                    self.log.error(('Failed to load %s reason: ' % join(folder, item, sub_item)) + str(e))

    @asyncio.coroutine
    def on_message(self, message):
        yield from self.message_stuff()
        for cmd in list(self.commands.keys()):
            # list(self.commands.keys()) prevents RuntimeErrors from mutation when loading new command
            try:
                if self.commands[cmd]._matches(message):
                    if isinstance(self.commands[cmd], command.AdminCommand):
                        yield from self.commands[cmd]._action(message, self)
                    else:
                        yield from self.commands[cmd]._action(message)
                    if self.commands[cmd].breaks_on_match:
                        break
            except Exception as e:
                # Catch all problems that happen in matching/executing a command.
                # This means that if there's a bug that would cause execution to
                # break, other commands can still be tried.
                yield from self._on_command_error(cmd, e, message)

    @asyncio.coroutine
    def on_reaction_add(self, rxn, user):
        for cmd in list(self.reactions.keys()):
            if isinstance(self.reactions[cmd], reactioncommand.ReactionAddCommand):
                try:
                    if self.reactions[cmd]._matches(rxn, user):
                        if isinstance(self.reactions[cmd], reactioncommand.AdminReactionCommand):
                            yield from self.reactions[cmd]._action(rxn, user, self)
                        else:
                            yield from self.reactions[cmd]._action(rxn, user)
                        break
                except Exception as e:
                    # Catch and report all errors that happen in matches/action.
                    # This prevents a bug in one reaction command from
                    # breaking execution, so other commands can still be run.
                    yield from self._on_reaction_add_error(cmd, e, rxn, user)

    @asyncio.coroutine
    def on_reaction_remove(self, rxn, user):
        for cmd in list(self.reactions.keys()):
            if isinstance(self.reactions[cmd], reactioncommand.ReactionRemoveCommand):
                try:
                    if self.reactions[cmd]._matches(rxn, user):
                        if isinstance(self.reactions[cmd], reactioncommand.AdminReactionCommand):
                            yield from self.reactions[cmd]._action(rxn, user, self)
                        else:
                            yield from self.reactions[cmd]._action(rxn, user)
                        break
                except Exception as e:
                    # Catch and report all errors that happen in matches/action.
                    # This prevents a bug in one reaction command from
                    # breaking execution, so other commands can still be run.
                    yield from self._on_reaction_remove_error(cmd, e, rxn, user)

    @asyncio.coroutine
    def on_ready(self):
        print("Bot online & running startup (this may take a while)")
        self.log.info('API connection created successfully')
        self.log.info('Username: ' + str(self.user.name))
        # self.log.info('Email: ' + str(self.email))
        self.log.info('Connected to %s servers' % len(self.servers))
        yield from self.load_messages()
        print("All messages loaded. Full functionality enabled")

    @asyncio.coroutine
    def load_messages(self):
        '''(Bot) -> None
        Convenience function for loading the messages the bot might need from before it's last restart'''
        global _messages
        if not int(self.data_config['reloadmessages']):
            print("Skipping message reloading since reloadmessages is 0")
            self.log.warning("Skipping message reloading; Idea will not react to messages seen before startup")
            return
        # load messages from file
        self.always_watch_messages.add(LOADING_WARNING)
        try:
            messagefile = dataloader.datafile(self.data_config[MSG_BACKUP_LOCATION])
        except FileNotFoundError:
            messagefile = dataloader.newdatafile(self.data_config[MSG_BACKUP_LOCATION])
            messagefile.content = list()

        self.log.info("Loading %a messages" % len(messagefile.content))
        if _messages is None:
            for msg_str in messagefile.content:
                channel_id, msg_id = msg_str.strip().split(":")
                try:
                    msg = yield from self.get_message_properly(channel_id, msg_id)
                    if msg.server:  # PATCH: private messages can't be loaded properly, this prevents them from being used
                        self.messages.append(msg)
                except (discord.NotFound, discord.Forbidden, discord.InvalidArgument):
                    self.log.warning("Unable to load %a message" % msg_id)
        else:
            self.messages = messages
        self.log.info("Finished loading messages")

        # load always_watch_messages from file
        try:
            watchfile = dataloader.datafile(self.data_config[WATCH_MSG_LOCATION])
        except FileNotFoundError:
            watchfile = dataloader.newdatafile(self.data_config[WATCH_MSG_LOCATION])
            watchfile.content = list()

        self.log.info("Loading %a watched messages" % len(watchfile.content))
        for msg_str in watchfile.content:
            channel_id, msg_id = msg_str.strip().split(":")
            try:
                msg = yield from self.get_message_properly(channel_id, msg_id)
                if msg.server:  # PATCH: private messages can't be loaded properly, this prevents them from being used
                    if msg not in self.messages:
                        self.messages.append(msg)
                    self.always_watch_messages.add(msg)
            except (discord.NotFound, discord.Forbidden, discord.InvalidArgument):
                # prevents the following, respectively: msg deleted/not-accessible, bot permissions changed, malformed save file
                self.log.warning("Unable to load %a message" % msg_id)
        self.always_watch_messages.remove(LOADING_WARNING)
        self.log.info("Finished loading watched messages")

    @asyncio.coroutine
    def get_message_properly(self, channel_id, msg_id):
        '''(Bot, str, str) -> discord.Message
        retrieves a message with id msg_id from channel_id which has (most) variables properly defined
        unlike the API's darn annoying default thing that doesn't set anything that I didn't already know arrrg!!'''
        msg = yield from self.get_message(discord.Object(channel_id), msg_id)
        # get_message returns a discord.Message which is lacking a certain variables, including .server and .channel
        # match private channel to msg
        for channel in self.private_channels:  # NOTE: private_channels is not loaded at startup, so it will contain nothing initially
            # NOTE: private_channels is loaded when you send a message, though, to make things weirder
            # print(channel.id==channel_id)
            if channel.id == channel_id:
                msg.server = None
                msg.channel = channel
                break
        # match server to msg
        for server in self.servers:
            for channel in server.channels:
                if channel.id == channel_id:
                    msg.server = server
                    msg.channel = channel
                    break
        if isinstance(msg, str):
            print("What the fuck", msg_id)
        return msg

    @asyncio.coroutine
    def message_stuff(self):
        '''(Bot) -> None
        Convenience function for calling save_messages(), save_always_watched_messages() and sync_always_watched() in one line'''
        self.save_messages()
        self.save_always_watched_messages()
        self.sync_always_watched()

    def save_messages(self):
        '''(Bot) -> None
        backup self.messages deque'''
        global _messages
        if LOADING_WARNING not in self.always_watch_messages:  # if not still loading messages (likely from startup)
            messagefile = dataloader.newdatafile(dataloader.datafile("./data/config.config").content["DEFAULT"][MSG_BACKUP_LOCATION])
            for msg in self.messages:
                messagefile.content.append(msg.channel.id + ":" + msg.id)
            messagefile.save()
            # self.log.info("Saved %a messages" % len(messagefile.content))
            _messages = self.messages
        else:
            self.log.info("Messages are still being loaded, skipping save messages")

    def save_always_watched_messages(self):
        '''(Bot) -> None
        backup self.always_watch_messages set'''
        if LOADING_WARNING not in self.always_watch_messages:  # if not still loading messages (likely from startup)
            watchfile = dataloader.newdatafile(dataloader.datafile("./data/config.config").content["DEFAULT"][WATCH_MSG_LOCATION])
            for msg in self.always_watch_messages:
                watchfile.content.append(msg.channel.id + ":" + msg.id)
            watchfile.save()
            # self.log.info("Saved %a watched messages" % len(watchfile.content))
        else:
            self.log.info("Messages are still being loaded, skipping save always watched messages")

    def sync_always_watched(self):
        '''(Bot) -> None
        ensure self.messages contains all the necessary messages in the watch list'''
        for msg in self.always_watch_messages:
            if msg not in self.messages and msg != LOADING_WARNING:
                self.messages.append(msg)

    def _on_command_error(self, cmd_name, error, message):
        '''(Bot, str) -> None
        wrapper method to catch and report errors from commands'''
        # traceback.print_exc()
        self.log.warning('command %s raised an exception during its execution: %s', cmd_name, error)
        yield from self.on_command_error(cmd_name, error, message)

    @asyncio.coroutine
    def on_command_error(self, cmd_name, error, message):
        '''(Bot, str) -> None
        method to catch and report errors from commands
        This should not raise it's own errors!'''
        pass

    def _on_reaction_add_error(self, cmd_name, error, rxn, user):
        '''(Bot, str) -> None
        wrapper method to catch and report errors from reactions'''
        # traceback.print_exc()
        self.log.warning('Reaction %s raised an exception during its execution: %s', cmd_name, error)
        yield from self.on_reaction_add_error(cmd_name, error, rxn, user)

    @asyncio.coroutine
    def on_reaction_add_error(self, cmd_name, error):
        '''(Bot, str) -> None
        method to catch and report errors from reactions
        This should not raise it's own errors!'''
        pass

    def _on_reaction_remove_error(self, cmd_name, error, rxn, user):
        '''(Bot, str) -> None
        wrapper method to catch and report errors from reactions'''
        # traceback.print_exc()
        self.log.warning('Reaction %s raised an exception during its execution: %s', cmd_name, error)
        yield from self.on_reaction_remove_error(cmd_name, error, rxn, user)

    @asyncio.coroutine
    def on_reaction_remove_error(self, cmd_name, error, rxn, user):
        '''(Bot, str) -> None
        method to catch and report errors from reactions
        This should not raise it's own errors!'''
        pass

    def _shutdown(self):
        self.shutdown()

    def shutdown(self):
        # do command shutdown
        for cmd_name in self.commands:
            self.commands[cmd_name]._shutdown()
        for cmd_name in self.reactions:
            self.reactions[cmd_name]._shutdown()
        for cmd_name in self.plugins:
            self.plugins[cmd_name]._shutdown()

        savetome.save_role_messages(self.data_config[ROLE_MSG_LOCATION], self.role_messages)
        self.loop.run_until_complete(self.logout())
        self._cancel_all_tasks()
        # self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        # self.loop.stop()

    def _cancel_all_tasks(self):
        tasks = asyncio.Task.all_tasks()
        for t in tasks:
            t.cancel()
