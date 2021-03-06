'''
Base class and constants for commands, plugins and reactions.

The AddOn class is a basic interface for all add-ons to extend and implement.
libs.command.Command, libs.reaction.Reaction and libs.plugin.Plugin all extend this interface.
Since command, plugin and reaction are all subclasses of addon, addon should be
unecessary to import.

@author: NGnius
'''
# bot api methods accessible to a regular AddOn
# if more functionality is required, consider using an Admin interfance class
SEND_MESSAGE = 'send_message'
EDIT_MESSAGE = 'edit_message'
ADD_REACTION = 'add_reaction'
REMOVE_REACTION = 'remove_reaction'
SEND_TYPING = 'send_typing'
SEND_FILE = 'send_file'

# event constants, from the Discord.py API
READY = 'ready'
LOGIN = 'login'
MESSAGE = 'message'
REACTION = 'reaction'

DEFAULT = 'DEFAULT' # default config file section

# add-on type constants
COMMAND = 'command'
COMMANDS = 'commands'
REACTION = 'reaction'
REACTIONS = 'reactions'
PLUGIN = 'plugin'
PLUGINS = 'plugins'

class AddOn:
    '''Base class for all add-on systems (Commands, Reactions and Plugins).
    Their interfaces are extended from this interface.

    The AddOn interface class should not be used to directly implement a Command/Reaction/Plugin.
    '''
    SEND_MESSAGE = SEND_MESSAGE
    EDIT_MESSAGE = EDIT_MESSAGE
    ADD_REACTION = ADD_REACTION
    REMOVE_REACTION = REMOVE_REACTION
    SEND_TYPING = SEND_TYPING
    SEND_FILE = SEND_FILE

    READY = READY
    LOGIN = LOGIN
    MESSAGE = MESSAGE
    REACTION = REACTION

    DEFAULT = DEFAULT

    COMMAND = COMMAND
    COMMANDS = COMMANDS
    REACTION = REACTION
    REACTIONS = REACTIONS
    PLUGIN = PLUGIN
    PLUGINS = PLUGINS
    ADDON_TYPE_LIST = [COMMAND, COMMANDS, REACTION, REACTIONS, PLUGIN, PLUGINS]

    DEFAULT_HELPSTRING = '''No help information available.
    Please contact a maintainer to fix this.'''
    def _action(self, *args, **kwargs):
        'Action wrapper. This should not be overriden.'
        return self.action(*args, **kwargs)

    def action(self, *args, **kwargs):
        '''Action function
        This should perform the action of your add-on'''
        pass

    def _matches(self, *args, **kwargs):
        'Matches wrapper. This should not be overriden.'
        return self.matches(*args, **kwargs)

    def matches(self, *args, **kwargs):
        '''Matches function
        This should return a boolean, where True means the parametes do match
        the requirements of your add-on

        This is not always used'''
        pass

    def _shutdown(self):
        '''Shutdown wrapper. This should not be overriden'''
        return self.shutdown()

    def shutdown(self):
        '''This is called during bot shutdown, *after* the discord API is disconnected

        Use this to save any variables that need to be loaded again when the bot restarts'''
        pass

    def _help(self, *args, verbose=False, **kwargs):
        'Help wrapper. This should not be overriden.'
        docstring = self.help(*args, verbose=verbose, **kwargs)
        if not docstring: docstring=self.DEFAULT_HELPSTRING
        if verbose:
            classes = [base.__name__ for base in self.__class__.__bases__]
            return docstring+"\n\nSubclasses: "+', '.join(classes)
        return docstring

    def help(self, *args, **kwargs):
        '''Help function
        This should return a helpful string to guide users in using your add-on

        By default, returns the docstring.'''
        return self.__doc__
