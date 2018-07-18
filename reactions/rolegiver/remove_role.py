from libs import reaction as reactioncommand

class Reaction(reactioncommand.AdminReactionRemoveCommand, reactioncommand.RoleReaction):
    def matches(self, reaction, user):
        return reaction.message.id in self.role_messages and reaction.emoji in self.role_messages[reaction.message.id]
    def action(self, reaction, user, bot):
        yield from bot.remove_roles(user, self.role_messages[reaction.message.id][reaction.emoji])