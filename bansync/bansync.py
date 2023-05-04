import discord
from discord.guild import BanEntry
import asyncio
from redbot.core import commands, checks, Config, utils

# red 3.0 backwards compatibility support
listener = getattr(commands.Cog, "listener", None)

if listener is None:  # thanks Sinbad
    def listener(name=None):
        return lambda x: x

class BanSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._is_consuming = False
        self.config = Config.get_conf(self, 2348123)
        self.config.register_global(sync_list=[], ban_list=[], ban_queue=[])
        self.sync_list = ConfigLock(self.config.sync_list)
        self.ban_list = ConfigLock(self.config.ban_list)
        self.ban_queue = ConfigLock(self.config.ban_queue)
        print('Loaded BanSync...')

    async def in_sync_list(self, guild):
        sync_list = await self.config.sync_list()
        return guild.id in sync_list

    async def synced_guilds(self):
        sync_list = await self.config.sync_list()
        for id in sync_list:
            guild = self.bot.get_guild(id)
            if guild is not None:
                yield guild

    async def in_ban_list(self, user):
        if isinstance(user, discord.Object) or isinstance(user, discord.abc.User):
            user_id = user.id
        else:
            user_id = user
        ban_list = await self.config.ban_list()
        for ban in ban_list:
            if ban['user'] == user_id:
                return True
        return False

    async def sync_ban(self, guild, ban):
        in_list = await self.in_ban_list(ban.user)
        if ban is None or guild is None or ban.user is None or in_list:
            return

        if ban.reason is None:
            reason = '<{0}>'.format(guild.name)
        else:
            reason = '{0} <{1}>'.format(ban.reason, guild.name)
        ban = BanEntry(user=ban.user, reason=reason)

        print("Syncing ban {0} - {1}".format(ban.user.name, ban.reason))
        await self.save_ban(ban)

        async for g in self.synced_guilds():
            if g == guild:
                continue
            await self.queue_action(is_ban=True, guild=g, ban=ban)

    async def collect_guild_bans(self, guild):
        if guild is None:
            return
        async for ban in guild.bans(limit=1000):
            await self.sync_ban(guild, ban)

    async def enact_bans(self, guild):
        ban_list = await self.config.ban_list()
        guild_bans = await guild.bans()
        guild_bans = [ban.user.id for ban in guild_bans]
        for ban in ban_list:
            if not ban['user'] in guild_bans:
                try:
                    await self.queue_action(is_ban=True, guild=guild, user=ban['user'], reason=ban['reason'])
                except Exception as e:
                    print('Failed to queue ban: {1}:{0}'.format(ban,guild))

    async def remove_duplicates(self):
        key, ban_list = await self.ban_list.lock()
        found = []
        for i in range(len(ban_list)-1,-1,-1):
            user_id = ban_list[i]['user']
            if user_id in found:
                print('Removed duplicate {0}'.format(user_id))
                ban_list.pop(i)
            else:
                found.append(user_id)
        await self.ban_list.unlock(key, ban_list)


    @listener()
    async def on_member_ban(self, guild, user):
        if not await self.in_sync_list(guild) or await self.in_ban_list(user):
            return

        try:
            ban = await guild.fetch_ban(user)
        except Exception as e:
            print(e)
            return e

        await self.sync_ban(guild, ban)

    @listener()
    async def on_member_unban(self, guild, user):
        if not await self.in_sync_list(guild) or not await self.in_ban_list(user):
            return

        print("Syncing unban {0}".format(user.name))
        await self.save_unban(user)

        async for g in self.synced_guilds():
            if g == guild:
                continue
            try:
                ban = await g.fetch_ban(user)
            except discord.NotFound:
                continue
            except Exception as e:
                print(e)
                continue  # Add proper error handling

            try:
                await self.queue_action(is_ban=False, user=user, guild=g)
            except Exception as e:
                print(e)
                pass

    @commands.command(name="synctoggle", help="Toggle whether or not a server is synced given its ID")
    @checks.admin()
    @checks.bot_in_a_guild()
    async def syncserver(self, ctx, guild_id: int = None, *, dont_collect: bool = False):
        if guild_id is not None:
            guild = self.bot.get_guild(guild_id)
        else:
            guild = ctx.guild
        if guild is not None:
            id = guild.id
        else:
            return await ctx.send("Unknown id {0}".format(guild_id))

        key, sync_list = await self.sync_list.lock()
        in_list = id in sync_list
        if in_list:
            sync_list.remove(id)
            message = "Removed `{0}` from the sync list".format(guild.name)
        else:
            sync_list.append(id)
            message = "Added `{0}` to the sync list".format(guild.name)
        await self.sync_list.unlock(key, sync_list)
        if not in_list:
            await self.enact_bans(guild)
            if not dont_collect:
                await self.collect_guild_bans(guild)
        await ctx.send(message)

    @commands.command(name="synclist", help="Print list of server set to be synced")
    @checks.admin()
    async def synclist(self, ctx):
        sync_list = await self.config.sync_list()
        message = "Synced servers: "
        for id in sync_list:
            guild = self.bot.get_guild(id)
            message += "**{0}** [{1}], ".format(guild.name, id)
        await ctx.send(message[:-2])

    @commands.command(name="syncedbans", help="Print a list of bans and reasons that have been synced")
    @checks.admin()
    async def syncedbans(self, ctx):
        ban_list = await self.config.ban_list()
        message = "Synced bans:\n"
        for ban in ban_list:
            message += "- <@{0}> `{1}`\n".format(ban['user'], ban['reason'])
        for content in utils.chat_formatting.pagify(message):
            await ctx.send(content)

    @commands.command(name="synctasks", help="Print number of tasks currently queued")
    @checks.admin()
    async def synctasks(self, ctx):
        queue = await self.config.ban_queue()
        await ctx.send('{0} tasks currently in queue'.format(len(queue)))

    @commands.command(name="syncrecover", help="Check ban syncs on all servers")
    @checks.is_owner()
    @checks.bot_in_a_guild()
    async def syncrecover(self, ctx):
        message = await ctx.send('Removing duplicate bans...')
        await self.remove_duplicates()
        await message.edit(content='Syncing bans...')
        async for guild in self.synced_guilds():
            await self.enact_bans(guild)
            await self.collect_guild_bans(guild)
        queue = await self.config.ban_queue()
        await message.edit(content='Sync started {0} tasks until done.'.format(len(queue)))

    async def save_ban(self, ban):
        key, ban_list = await self.ban_list.lock()
        ban_list.append({'user': ban.user.id, 'reason': ban.reason})
        await self.ban_list.unlock(key, ban_list)

    async def save_unban(self, user):
        key, ban_list = await self.ban_list.lock()
        for ban in ban_list:
            if ban['user'] == user.id:
                ban_list.remove(ban)
        await self.ban_list.unlock(key, ban_list)

    async def queue_action(self, *, is_ban=False, user=None, reason=None, guild=None, ban=None):
        user_id = None
        guild_id = None

        if isinstance(user, discord.Object) or isinstance(user, discord.abc.User):
            user_id = user.id
        elif user is None and ban is not None:
            user_id = ban.user.id
            reason = ban.reason

        if isinstance(guild, discord.Object) or isinstance(guild, discord.Guild):
            guild_id = guild.id
        else:
            guild_id = guild

        if user_id is None or guild_id is None:
            raise Exception('User or guild id not provided to ban action')

        key, ban_queue = await self.ban_queue.lock()
        ban_queue.append({'guild': guild_id, 'user': user_id, 'reason': reason, 'ban': is_ban})
        await self.ban_queue.unlock(key, ban_queue)

        if not self._is_consuming:
            self.bot.loop.create_task(self.action_consumer())


    async def action_consumer(self):
        self._is_consuming = True
        print('Consumer started')
        while 1:
            key, ban_queue = await self.ban_queue.lock()
            if len(ban_queue) > 0:
                ban = ban_queue.pop(0)
                await self.ban_queue.unlock(key, ban_queue)
                guild = self.bot.get_guild(ban['guild'])
                if ban.get('ban', False):
                    await guild.ban(discord.Object(ban['user']),reason=ban.get('reason',None))
                else:
                    await guild.unban(discord.Object(ban['user']))
            else:
                await self.ban_queue.unlock(key)
                break
            await asyncio.sleep(0.2)
        self._is_consuming = False
        print('Consumer stopped')

    @commands.command()
    @checks.is_owner()
    async def testban(self, ctx, id: int = None, reason: str = None):
        await ctx.guild.ban(discord.Object(id),reason=reason)


class AsyncLock:
    def __init__(self):
        self.lock_i = 0
        self.lock_active = None
    async def lock(self):
        i = self.lock_i + 1
        self.lock_i = i
        while self.lock_active is not None:
            await asyncio.sleep(0.1)
        self.lock_active = i
        value = await self._get()
        return (i, value)
    async def unlock(self, key, value=None):
        if key == self.lock_active:
            if value is not None:
                await self._set(value)
            self.lock_active = None
        else:
            raise RuntimeError('{0} is not active lock key'.format(key))

class ConfigLock(AsyncLock):
    def __init__(self, configItem):
        super().__init__()
        self._item = configItem
    async def _get(self):
        return await self._item()
    async def _set(self,value):
        return await self._item.set(value)
