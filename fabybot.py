import discord
import discordfaby
import re
import asyncio
import aioDarkSkyAPI
import io
import os
from pytz import timezone
from itertools import chain
from timeit import timeit
from random import randint
from random import choice
from datetime import datetime
from threading import Thread
from queue import Queue, Empty
from time import monotonic
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from config import token
from config import weather_secret
from config import google_secret

async def cEcho(client, message, params={}):
    if len(params.get('ctext')) > 0:
        await message.channel.send(params['ctext'])

async def cRoll(client,message, params={}):
    """Roll dice, format #d#k#
Roll # #-sided die and keep #, keep is optional
supports multiple rolls at once"""
    matches = re.findall('\d*d\d+k*\d*', message.content.lower())
    if len(matches) > 0:
        rkeep = []
        rdrop = []
        rall = []
        response1 = "Rolling "
        response2 = ""
        keeping = False

        for match in matches:
            roll = []
            try:
                n1 = re.search('(\d*)d', match).group(1) or '1'
            except:
                n1 = '1'

            n2 = re.search('d(\d+)', match).group(1)

            try:
                n3 = re.search('k(\d+)', match).group(1)
            except:
                n3 = None

            if int(n1) > 100:
                return
            for i in range(int(n1)):
                roll.append(randint(1, int(n2)))

            if n3:
                if int(n3) > int(n1):
                    await client.message.channel("Would be nice if you could keep more than you had, but you can't.")
                    return

                rall.extend(roll)
                roll.sort()
                rkeep.extend(roll[-int(n3):])
                rdrop.extend(roll[:-int(n3)])
                keeping = True
                response1 += n1 + 'd' + n2 + 'k' + n3 + " + "
            else:
                rall.extend(roll)
                rkeep.extend(roll)

                response1 += n1 + 'd' + n2 + " + "

        for r in rall:
            response2 += str(r) + " + "

        response1 = response1[:-2]
        response1 += "for " + message.author.mention
        response2 = response2[:-2]
        if len(response2) > 750:
            response2 = response2[:150] + " .. " + response2[-150:]

        if keeping:
            response3 = "Keeping: "
            response4 = "Dropped: "

            for r in rkeep:
                response3 += str(r) + " + "
            for r in rdrop:
                response4 += str(r) + " + "
            response3 = response3[:-2]
            response4 = response4[:-2]
            response3 += "= " + str(sum(rkeep))
            if len(response3) > 750:
                response3 = response3[:150] + " .. " + response3[-150:]
            if len(response4) > 750:
                response4 = response4[:150] + " .. " + response4[-150:]
            response = response1 + '\n' + response2 + '\n' + response3 + '\n' + response4
        else:
            response2 += "= " + str(sum(rall))
            response = response1 + '\n' + response2

        await message.channel.send(response)

async def cToken(client,message,params={}):
    '''Tests a Discord API token.'''
    if message.author != client.get_user(103294721119494144):
        await message.channel.send(f"I'm sorry {message.author.mention}, I'm afraid I can't do that.")
        return

    b = '\U0001f171'
    await message.channel.send("Waiting for token in PM!")

    def check(m):
        return m.channel == message.author.dm_channel

    msg = await client.wait_for('message', check=check)
    await message.channel.send("Recieved token in PM! Testing...")
    tokenClient = discord.Client()
    try:
        await tokenClient.login(msg.content)
    except Exception as e:
        await message.channel.send(e)
        return

    await message.channel.send(f"Logged in with token `{msg.content[:5]}{'*' * (len(msg.content)-10)}{msg.content[-5:]}`")
    tokenTask = client.loop.create_task(tokenClient.connect())
    await tokenClient.wait_until_ready()
    appInfo = await tokenClient.application_info()
    owner = appInfo.owner
    await message.channel.send(f"Connected to {appInfo.name}, Guilds: {len(tokenClient.guilds)}")

    q = Queue()

    async def read_stdin():
        def check(m):
            return m.channel == message.channel and m.author == message.author and m.content.startswith(b)
        while not tokenClient.is_closed():
            msg = await client.wait_for('message', check=check)
            if msg.content.startswith(f'{b}close'):
                await tokenClient.close()
            else:
                await owner.send(msg.content[1:])

    async def read_stdout():
        def check(m):
            return m.channel == owner.dm_channel
        while not tokenClient.is_closed():
            msg = await tokenClient.wait_for('message', check=check)
            q.put( f"{msg.author.name}: {msg.content}" )



    stdinTask = client.loop.create_task(read_stdin())
    stdoutTask = client.loop.create_task(read_stdout())
    status = ""
    for guild in tokenClient.guilds:
        for member in guild.members:
            if member == owner:
                status = member.status.name
    await message.channel.send( f"Contacting owner: {owner.mention}({owner.name}#{owner.discriminator}:{owner.id}) Status:{status}")
    embedupdate = monotonic()
    pcoutput = ""
    embedlastout = ""
    newline = '\n'
    warningMsg = f"""**ALERT** {appInfo.owner.mention} Your Discord API Token is posted in your **source code** on **Github**
This makes your account **vulnerable**. Anyone can use your token for malicious purposes. Remove your token immediately.
You need to **refresh** your token at https://discordapp.com/developers/applications/me/{appInfo.id}
For any questions on this process you can message me through your bot, I will assist you until your token is removed."""
    try:
        await owner.send(warningMsg)
    except discord.Forbidden:
        await message.channel.send("Or not, this fool isn't in a guild with his own bot. Let's try the owner of the first guild")
        if len(tokenClient.guilds) > 0:
            owner = tokenClient.guilds[0].owner
            await message.channel.send(f"Contacting owner: {owner.mention}({owner.name}#{owner.discriminator}:{owner.id}) Status:{owner.status.name}")
            await owner.send(warningMsg)
        else:
            await message.channel.send(content=f"Aaaaaaaaaaand the bot isn't in any guilds. Good luck I guess.")
            await tokenClient.close()
            await message.channel.send(content=f"TokenClient was disconnected")
            return

    while not tokenClient.is_closed():
        try:
            line = q.get_nowait()
        except Empty:
            pass
        else:
            await message.channel.send(line)
        await asyncio.sleep(0.05)

    stdinTask.cancel()
    stdoutTask.cancel()

    await message.channel.send(content=f"TokenClient was disconnected")


forecastable = {
    'minute':'minutely',
    'minutes':'minutely',
    'minutely':'minutely',
    'hour':'hourly',
    'hours':'hourly',
    'hourly':'hourly',
    'day':'daily',
    'days':'daily',
    'daily':'daily',
}

async def cWeather(client,message,params={}):
    '''Returns weather information
forecast=minutely/hourly/daily'''
    blocks = ['currently', 'minutely', 'hourly', 'daily', 'alerts', 'flags']
    if params.get('forecast'):
        forecast = forecastable.get(params.get('forecast')) or 'daily'
        blocks.remove(forecast)
        resp = await WeatherClient.gforecast(params['ctext'],exclude=blocks)
        weather = resp[forecast]['data']
        weather_summary = 'summary will go here w/e'# resp[forecast][0]['summary']

        if forecast == 'minutely':
            plott = [datetime.fromtimestamp(datapoint['time']).strftime('%H:%M') for datapoint in weather]
        elif forecast == 'hourly':
            plott = [datetime.fromtimestamp(datapoint['time']).strftime('%H:%M') for datapoint in weather]
        else:
            plott = [datetime.fromtimestamp(datapoint['time']).strftime('%Y-%m-%d') for datapoint in weather]

        fig = plt.figure()
        ax, ax2 = fig.subplots(2,1,True,False,subplot_kw={'facecolor':'#36393e'}, gridspec_kw = {'height_ratios':[1, 10],'wspace':0,'hspace':0})

        ax.tick_params(axis='both', which='both', left=False, color="#FFFFFF")
        ax2.tick_params(axis='both', which='both',  color="#FFFFFF")

        ax.margins(0,0)
        ax2.margins(0,0)
        plt.setp(ax2.get_xticklabels()[0], visible=False)

        ax.fill_between(plott,
                        [datapoint['cloudCover'] for datapoint in weather],
                        [0 - datapoint['cloudCover'] for datapoint in weather],
                        label="Cloud Cover",color = '#99AAB5')
        if forecast == 'daily':
            ax2.fill_between(plott,
                            [datapoint['temperatureLow'] for datapoint in weather],
                            [datapoint['temperatureHigh'] for datapoint in weather],
                            label = "Apparent Temperature")
            ax2.plot(plott,
                    [(datapoint['temperatureLow'] + datapoint['temperatureHigh'] )/2 for datapoint in weather],
                    'r--', label = "Temperature Low")
        else:
            ax2.plot(plott, [datapoint['temperature'] for datapoint in weather],linestyle='--',color='#ffFF00', label="Temperature")
            ax2.plot(plott, [datapoint['apparentTemperature'] for datapoint in weather], linestyle='--',color='#ffa500', label="Feels Like")
        ax.set_title(f"{forecast.capitalize()} forecast for {resp['g']['formatted_address']}\n{weather_summary}")
        fig.legend(loc=4,frameon=False)
        fig.autofmt_xdate()
        with io.BytesIO() as bPic:
            fig.savefig(bPic, format='png', bbox_inches='tight',pad_inches=0,facecolor="#36393e",edgecolor="#FFFFFF")
            bPic.seek(0)
            await message.channel.send(file=discord.File(bPic, filename='plot.png'))
            plt.close(fig)

    else:
        blocks.remove('currently')
        try:
            resp = await WeatherClient.gforecast(params['ctext'],exclude=blocks)
        except LookupError:
            await message.channel.send(f'Could not locate `{params["ctext"]}`')
            return
        weather = resp['currently']
        embed=discord.Embed(title=f"Weather for {resp['g']['formatted_address']}", description=f"**{weather['summary']}**  Requested by {message.author.mention}", color=discord.Color.green())
        embed.add_field(name='Temperature', value=f'**Apparent**: {(weather["apparentTemperature"]):.2f}°C\n**Actual**: {(weather["temperature"]):.2f}°C\n**Dew Point**: {(weather["dewPoint"]):.2f}°C\n', inline=True)
        embed.add_field(name='Wind', value=f"**Bearing**: {weather['windBearing']}\n**Speed**: {(weather['windSpeed']*3.6):.2f}km/h\n**Gust**: {(weather['windGust']*3.6):.2f}km/h", inline=True)
        embed.add_field(name='Other', value=f"**UV Index**: {weather['uvIndex']}\n**Visibility**: {weather['visibility']}km\n**Humidity**: {(weather['humidity']*100):.2f}%", inline=True)
        embed.set_footer(text=f'{datetime.fromtimestamp(weather["time"]).astimezone(timezone(resp["timezone"])).strftime("%Y-%m-%d %H:%M")} Local Time')

        await message.channel.send( embed=embed)

def all_files(path):
    scandir = os.scandir
    file_list = []
    append = file_list.append
    extend = file_list.extend
    for item in scandir(path):
        if item.is_dir():
            extend(all_files(item.path))
        else:
            append(item)
    return file_list









async def cPic(client,message,params={}):
    if params.get("random"):
        pics = all_files(client.dirs['pics'])
        await message.channel.send(file=discord.File(choice(list(pics)).path))

async def cTimeit(client,message,params={}):
    global pics
    global home
    pics = client.dirs['pics']
    home = client.dirs['logs']
    msg = '```'
    msg = f'''{msg}{timeit("print('asd')", number=100)}\n'''
    msg = f'''{msg}{timeit("print('asd')", setup="from __main__ import all_files,pics", number=100)}\n'''
    msg = f'''{msg}{timeit("all_files(home)", setup="from __main__ import all_files,home", number=10)}\n'''
    msg = f'{msg}{timeit("all_files(pics)", setup="from __main__ import all_files,pics", number=10)}\n'
    msg = f'{msg}{timeit("all_files(pics)", setup="from __main__ import all_files,pics", number=10)}\n'
    msg = f'{msg}{timeit("list(all_files(pics))", setup="from __main__ import all_files,pics", number=10)}\n'
    msg = f'{msg}{timeit("list(all_files(pics))", setup="from __main__ import all_files,pics", number=10)}\n'
    msg = f'{msg}{timeit("list(all_files(pics))", setup="from __main__ import all_files,pics", number=10)}\n'

    msg = f'{msg}{timeit("all_files(pics)", setup="from __main__ import all_files,pics", number=100)}\n'
    msg = f'{msg}{timeit("list(all_files(pics))", setup="from __main__ import all_files,pics", number=100)}\n'

    msg = f'{msg}{len(all_files(pics))}\n'
    msg = f'{msg}{len(list(all_files(pics)))}\n'
    msg = f'{msg}```'

    await message.channel.send(msg)

commands = {
    'roll':[['dice','die'],cRoll,True,False],
    'token':[[],cToken,False,True],
    'weather':[['forecast'],cWeather,False,False],
    'echo':[['say'],cEcho,False,True],
    'pic':[['pics'],cPic,False,False],
    'timeit':[[],cTimeit,False,True]
}

dirs = {
    'pics':'pics'
}
client = discordfaby.Client(token=token,commands=commands,dirs=dirs)
WeatherClient = aioDarkSkyAPI.Client(weather_secret,gsecret = google_secret,loop=client.loop, session=client.session)



@client.event
async def on_ready():
    print('Logged in as:')
    print(client.user.name)
    print(client.user.id)
    print('Connected to:')
    for guild in client.guilds:
        print(guild.id)
        print(guild.name)
        print(guild.owner.name)
    timenow =  datetime.utcnow().timestamp()
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name='your bullshit',timestamps={'start':timenow}))

    await client.process_ready()


client.run(client.token)