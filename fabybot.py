import discord
import discordfaby
import re
import asyncio
import aioDarkSkyAPI
import io
import os
import functools
import string
from discordfaby import commands as dcommands
from discordfaby.emoji import emoji
from pytz import timezone
from itertools import chain
from timeit import timeit
from random import randint
from random import choice
from datetime import datetime
from datetime import timedelta
from threading import Thread
from queue import Queue, Empty
from time import monotonic
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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

expected_weather = {
    'Temperature':[
        ['Temperature','temperature','{:.2f}°C'],
        ['Feels like','apparentTemperature','{:.2f}°C'],
        ['Dew Point','dewPoint','{:.2f}°C']
    ],
    'Wind':[
        ['Bearing','windBearing','{}'],
        ['Speed','windSpeed','{:.2f}km/h',3.6],
        ['Gust','windGust','{:.2f}km/h',3.6]
        ],
    'Other':[
        ['UV Index','uvIndex','{}'],
        ['Humidity','humidity','{}%',100],
        ['Cloud Cover','cloudCover','{}%',100],
        ['Visibility','visibility','{:.2f}km'],
        ['Pressure','pressure','{}hPa'],
        ['Ozone','ozone','{:.2f} DU']
    ]
}
expected_weather_extras = {
    'Precipitation':[
        ['Chance', 'precipProbability', '{}%', 100],
        ['Type', 'precipType', '{}'],
        ['Intensity', 'precipIntensity', '{:.4f}mm/h']
    ],
    'Nearest Storm':[
        ['Distance', 'nearestStormBearing', '{}'],
        ['Bearing', 'nearestStormDistance', '{:.0f}km']
    ]
}

async def cForecast(client,message,params={}):
    blocks = ['currently', 'minutely', 'daily', 'alerts', 'flags']

    forecast = 'hourly'
    try:
        resp = await WeatherClient.gforecast(params['ctext'],exclude=blocks,extend=True)
    except LookupError:
        await message.channel.send(f'Could not locate `{params["ctext"].replace("`","")}`')
        return
    try:
        weather = resp[forecast]['data']
    except KeyError:
        await message.channel.send(f'`{forecast}` forecast not available for `{params["ctext"].replace("`","")}`')
        return
    try:
        weather_summary = resp[forecast]['summary']
    except KeyError:
        try:
            weather_summary = resp[forecast][0]['summary']
        except KeyError:
            weather_summary = "No Summary Available"
    localtz = timezone(resp["timezone"])

    plott = [mdates.date2num(datetime.fromtimestamp(datapoint['time']).astimezone(localtz)) for datapoint in weather]
    plotzero = [0 for _ in weather]

    fig = plt.figure(figsize=(8,6))
    ax, ax2, ax4, ax3 = fig.subplots(4,1,True,False,subplot_kw={'facecolor':'#36393e'}, gridspec_kw = {'height_ratios':[1, 1, 0.5, 10],'wspace':0,'hspace':0})

    ax.tick_params(axis='both', which='both', left=False, color="#FFFFFF")
    ax2.tick_params(axis='both', which='both', left=False, color="#FFFFFF")
    ax3.tick_params(axis='both', which='both',  color="#FFFFFF")

    ax.margins(0,0)
    ax2.margins(0,0)
    ax3.margins(0,0)
    ax4.margins(0,0)
    plt.setp(ax.get_yticklabels(), visible=False)
    plt.setp(ax2.get_yticklabels(), visible=False)
    plt.setp(ax4.get_yticklabels(), visible=False)
    plt.setp(ax3.get_xticklabels(), color='#FFFFFF' )
    plt.setp(ax3.get_yticklabels(), color='#FFFFFF' )

    if forecast == 'hourly':
        ax3.xaxis.set_major_locator(mdates.DayLocator(tz=localtz))
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%a %Y-%m-%d',tz=localtz))
        ax3.xaxis.set_minor_locator(mdates.HourLocator(interval=6,tz=localtz))
        #ax3.xaxis.set_minor_formatter(mdates.DateFormatter('%M:%S',tz=localtz))
        datemin = mdates.date2num(datetime.fromtimestamp(weather[0]['time']).astimezone(localtz).replace(hour=0, minute=0, second=0, microsecond=0))
        datemax = mdates.date2num(datetime.fromtimestamp(weather[-1]['time']).astimezone(localtz).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
        ax3.set_xlim(datemin, datemax)
    else:
        ax3.xaxis.set_major_formatter(mdates.DayLocator(tz=localtz))
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%a %Y-%m-%d',tz=localtz))


    cloud_data = ([datapoint.get('cloudCover') or 0 for datapoint in weather],
                 [0 - (datapoint.get('cloudCover') or 0) for datapoint in weather],
                 [False if datapoint['cloudCover'] == 0 else True for datapoint in weather])
    sun_data = ([datapoint.get('uvIndex') or 0 for datapoint in weather],
                 [0 - (datapoint.get('uvIndex') or 0) for datapoint in weather],
                 [False if datapoint['uvIndex'] == 0 else True for datapoint in weather])

    precip_data = ([0 - (datapoint.get('precipIntensity') or 0) for datapoint in weather],
                  [True if datapoint.get('precipIntensity') else False for datapoint in weather])


    ax.fill_between(plott, sun_data[0],sun_data[1],sun_data[2], label="UV Index",color = '#FFFF00')
    ax2.fill_between(plott, cloud_data[0],cloud_data[1],cloud_data[2], label="Cloud Cover",color = '#99AAB5')
    ax4.fill_between(plott, plotzero, precip_data[0],precip_data[1], label="Precipitation",color = '#5555FF', hatch='///', edgecolor = '#36393e')

    temp_data = [datapoint['temperature'] for datapoint in weather]
    atemp_data = [datapoint['apparentTemperature'] for datapoint in weather]
    precipmax = min(min(precip_data[0]),-0.5)
    tempmin = min(min(temp_data),min(atemp_data),1)
    tempmax = max(max(temp_data),max(atemp_data),-1)
    ax3.set_ylim(tempmin-1, tempmax+1)
    ax4.set_ylim(-0.5, 0)

    ax3.plot(plott, plotzero,color='#FFFFFF')
    ax3.plot(plott, temp_data,color='#ffFF00', label="Temperature")
    ax3.plot(plott, atemp_data, linestyle='--',color='#ffa500', label="Feels Like")



    lines = ax3.get_lines()
    plt.setp(lines, linewidth=1)

    axtitle = ax.set_title(f"{forecast.capitalize()} forecast for {resp['g']['formatted_address']}\n{weather_summary}")
    axtitle.set_color('#FFFFFF')
    fleg = fig.legend(loc=4,frameon=False)
    plt.setp(fleg.get_texts(), color='#FFFFFF' )
    fig.autofmt_xdate()
    with io.BytesIO() as bPic:
        fig.savefig(bPic, format='png', bbox_inches='tight',pad_inches=0,facecolor="#36393e",edgecolor="#FFFFFF")
        bPic.seek(0)
        await message.channel.send(file=discord.File(bPic, filename='plot.png'))
        plt.close(fig)

async def cWeather(client,message,params={}):
    '''Returns current weather information for a location'''
    blocks = ['currently', 'minutely', 'hourly', 'daily', 'alerts', 'flags']
    if params.get('forecast'):
        await message.channel.send('This functionality is deprecated, please use the forecast command.')
        forecast = forecastable.get(params.get('forecast'))
        if not forecast:
            forecast = 'daily'
            await message.channel.send(f'`{params["forecast"]}` is not a valid forecast, defaulting to `daily`')
        blocks.remove(forecast)
        try:
            resp = await WeatherClient.gforecast(params['ctext'],exclude=blocks,extend=params.get('extend'))
        except LookupError:
            await message.channel.send(f'Could not locate `{params["ctext"].replace("`","")}`')
            return
        try:
            weather = resp[forecast]['data']
        except KeyError:
            await message.channel.send(f'`{forecast}` forecast not available for `{params["ctext"].replace("`","")}`')
            return
        try:
            weather_summary = resp[forecast]['summary']
        except KeyError:
            try:
                weather_summary = resp[forecast][0]['summary']
            except KeyError:
                weather_summary = "No Summary Available"
        localtz = timezone(resp["timezone"])

        plott = [mdates.date2num(datetime.fromtimestamp(datapoint['time']).astimezone(localtz)) for datapoint in weather]

        fig = plt.figure(figsize=(8,6))
        ax, ax2 = fig.subplots(2,1,True,False,subplot_kw={'facecolor':'#36393e'}, gridspec_kw = {'height_ratios':[1, 10],'wspace':0,'hspace':0})

        ax.tick_params(axis='both', which='both', left=False, color="#FFFFFF")
        ax2.tick_params(axis='both', which='both',  color="#FFFFFF")

        ax.margins(0,0)
        ax2.margins(0,0)
        plt.setp(ax.get_yticklabels(), visible=False)
        plt.setp(ax2.get_xticklabels(), color='#FFFFFF' )
        plt.setp(ax2.get_yticklabels(), color='#FFFFFF' )
        #%Y-%m-%d %H:%M"

        if forecast == 'minutely':
            ax2.xaxis.set_major_locator(mdates.MinuteLocator(interval=15,tz=localtz))
            ax2.xaxis.set_minor_locator(mdates.MinuteLocator(interval=5,tz=localtz))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S',tz=localtz))
        elif forecast == 'hourly':
            if params.get('extend'):
                ax2.xaxis.set_major_formatter(mdates.DayLocator(tz=localtz))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%a %Y-%m-%d',tz=localtz))
                ax2.xaxis.set_minor_locator(mdates.HourLocator(interval=6,tz=localtz))
                datemin = mdates.date2num(datetime.fromtimestamp(weather[0]['time']).replace(hour=0, minute=0, second=0, microsecond=0))
                datemax = mdates.date2num(datetime.fromtimestamp(weather[-1]['time']).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
                ax2.set_xlim(datemin, datemax)
            else:
                ax2.xaxis.set_major_locator(mdates.HourLocator(interval=4,tz=localtz))
                ax2.xaxis.set_minor_locator(mdates.HourLocator(tz=localtz))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=localtz))
        else:
            ax2.xaxis.set_major_formatter(mdates.DayLocator(tz=localtz))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%a %Y-%m-%d',tz=localtz))

        try:
            cloud_data = ([datapoint['cloudCover'] for datapoint in weather],
                          [0 - datapoint['cloudCover'] for datapoint in weather])
        except KeyError:
            cloud_data = False

        if cloud_data:
            ax.fill_between(plott, cloud_data[0],cloud_data[1], label="Cloud Cover",color = '#99AAB5')
        if forecast == 'daily':
            ax2.fill_between(plott,
                            [datapoint['temperatureLow'] for datapoint in weather],
                            [datapoint['temperatureHigh'] for datapoint in weather],
                            label = "Temperature")
            ax2.plot(plott,
                    [(datapoint['temperatureLow'] + datapoint['temperatureHigh'] )/2 for datapoint in weather],
                    'r--', label = "Temperature Avg")
        else:
            ax2.plot(plott, [datapoint['temperature'] for datapoint in weather],linestyle='--',color='#ffFF00', label="Temperature")
            ax2.plot(plott, [datapoint['apparentTemperature'] for datapoint in weather], linestyle='--',color='#ffa500', label="Feels Like")

        lines = ax2.get_lines()
        plt.setp(lines, linewidth=1)

        axtitle = ax.set_title(f"{forecast.capitalize()} forecast for {resp['g']['formatted_address']}\n{weather_summary}")
        axtitle.set_color('#FFFFFF')
        fleg = fig.legend(loc=4,frameon=False)
        plt.setp(fleg.get_texts(), color='#FFFFFF' )
        fig.autofmt_xdate()
        with io.BytesIO() as bPic:
            fig.savefig(bPic, format='png', bbox_inches='tight',pad_inches=0,facecolor="#36393e",edgecolor="#FFFFFF")
            bPic.seek(0)
            await message.channel.send(file=discord.File(bPic, filename='plot.png'))
            plt.close(fig)

    else:
        blocks.remove('currently')
        blocks.remove('alerts')
        try:
            resp = await WeatherClient.gforecast(params['ctext'],exclude=blocks)
        except LookupError:
            await message.channel.send(f'Could not locate `{params["ctext"].replace("`","")}`')
            return
        localtz = timezone(resp["timezone"])
        weather = resp['currently']
        embed=discord.Embed(title=f"Weather for {resp['g']['formatted_address']}", description=f"**{weather['summary']}**  Requested by {message.author.mention}", color=discord.Color.green())

        try:
            print(weather['precipProbability'])
            if weather['precipProbability'] > 0:
                expected_weather['Precipitation'] = expected_weather_extras['Precipitation']
        except KeyError:
            pass

        if weather.get('nearestStormDistance') is not None:
            expected_weather['Nearest Storm'] = expected_weather_extras['Nearest Storm']

        for title,column in expected_weather.items():
            columntext = ""
            rows = 0
            for row in column:
                try:
                    if len(row) < 4:
                        columntext = f'{columntext}**{row[0]}**: {row[2].format(weather[row[1]])}\n'
                    else:
                        columntext = f'{columntext}**{row[0]}**: {row[2].format(weather[row[1]]*row[3])}\n'
                    rows += 1
                except KeyError:
                    pass
                if rows > 2:
                    rows = 0
                    embed.add_field(name=title,value=columntext,inline=True)
                    columntext = ""
            if len(columntext) > 0:
                embed.add_field(name=title,value=columntext,inline=True)

        for alert in weather.get('alerts') or []:
            columntext = f'**Title**: {alert["title"]}\n' \
                         f'**Description**: {alert["description"]}\n' \
                         f'**Isssued**: {datetime.fromtimestamp(alert["time"]).astimezone(timezone(resp["timezone"])).strftime("%Y-%m-%d %H:%M")}\n' \
                         f'**Expires**: {datetime.fromtimestamp(alert["expires"]).astimezone(timezone(resp["timezone"])).strftime("%Y-%m-%d %H:%M")}\n' \
                         f'**Regions**: {alert["regions"]}\n' \
                         f'**Severity**: {alert["severity"]}\n' \
                         f'**More Info**: [Click]{alert["uri"]}\n'

            embed.add_field(name="ALERT",value=columntext,inline=True)

        embed.set_footer(text=f'{datetime.fromtimestamp(weather["time"]).astimezone(localtz).strftime("%Y-%m-%d %H:%M")} Local Time')

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
    """Gets you a pic
Parameters: random"""
    if params.get("random"):
        pics = all_files(client.dirs['pics'])
        await message.channel.send(file=discord.File(choice(list(pics)).path))

async def cTimeit(client,message,params={}):
    """Debug command"""
    global pics
    global home
    pics = client.dirs['pics']
    home = client.dirs['logs']
    msg = '```py\n'

    timeits = []
    timeits2 = []

    for x in range(100000):
        timeits.append(lambda :dcommands.unique_num(x))
    for x in range(100000):
        timeits2.append(lambda: dcommands.unique_num_slow(x))

    timetaken = []
    timetaken2 = []
    for timeitfunc in timeits:
        timeitafunc = functools.partial(timeit, timeitfunc, number=1)
        timetaken.append( await client.loop.run_in_executor(None, timeitafunc) )
    for timeitfunc in timeits2:
        timeitafunc = functools.partial(timeit, timeitfunc, number=1)
        timetaken2.append(await client.loop.run_in_executor(None, timeitafunc))
        #msg = f'''{msg}[{timeitfunc.__name__}] {timetaken}\n'''


    fig = plt.figure(figsize=(8,6))
    ax = fig.subplots(1,1,True,False,subplot_kw={'facecolor':'#36393e'})

    ax.tick_params(axis='both', which='both', color="#FFFFFF")


    ax.margins(0,0)
    plt.setp(ax.get_yticklabels(), color='#FFFFFF' )
    plt.setp(ax.get_xticklabels(), color='#FFFFFF' )

    ax2 = ax.twinx()
    ax.plot(timetaken,color='#00FFFF')
    ax2.plot(timetaken2,color='#FFFF00')


    lines = ax.get_lines()
    plt.setp(lines, linewidth=1)
    lines2 = ax2.get_lines()
    plt.setp(lines2, linewidth=1)

    fig.autofmt_xdate()
    with io.BytesIO() as bPic:
        fig.savefig(bPic, format='png', bbox_inches='tight',pad_inches=0,facecolor="#36393e",edgecolor="#FFFFFF")
        bPic.seek(0)
        await message.channel.send(file=discord.File(bPic, filename='plot.png'))
        plt.close(fig)


    msg = f'''{msg}Loop finished with {i} errors.'''
    msg = f'''{msg}```'''

    #await message.channel.send(msg)

async def cReact(client,message,params={}):
    """React with emoji or letters, parses mentions and ID's messages to respond to, users to respond to their last message and channels find messages/users in
Parameters: search=text_to_search_for"""

    reactmessage = message
    trychannel = message.channel
    for word in params['ctext'].lower().split():
        try:
            wint = int(word)
            if client.get_channel(wint):
                trychannel = client.get_channel(wint)
                break
        except (ValueError,TypeError):
             pass
    for word in params['ctext'].lower().split():
        if any(channel.mention for channel in message.channel_mentions if channel.mention in word):
            trychannel = next(channel.mention for channel in message.channel_mention if channel.mention in word)
            break
        try:
            wint = int(word)
            if client.get_channel(wint):
                trychannel = client.get_channel(wint)
                break
        except (ValueError,TypeError):
             pass
    for word in params['ctext'].lower().split():
        try:
            wint = int(word)
            try:
                reactmessage = await trychannel.get_message(wint)
                break
            except:
                pass
        except (ValueError,TypeError):
             pass
    for word in params['ctext'].lower().split():
        try:
            wint = int(word)
            try:
                user = client.get_user(wint)
                if user:
                    reactmessage = await trychannel.history().get(author=user) or reactmessage
                    break
            except:
                pass
        except (ValueError,TypeError):
             pass
    for mention in message.mentions:
        if mention != client.user:
            new_reactmessage = await trychannel.history().get(author=mention)
            if new_reactmessage:
                reactmessage = new_reactmessage
                break
    if params.get('search'):
        search = ' '.join(params['search'].split('_'))
        reactmessage = await trychannel.history().find(lambda x: search in x.content) or reactmessage
    try:
        for word in params['ctext'].lower().split():
            if any(member.mention in word for member in message.mentions):
                continue
            try:
                wint = int(word)
            except (ValueError,TypeError):
                wint = False
            if wint:
                if client.get_channel(wint):
                    trychannel = client.get_channel(wint)
                    continue
                else:
                    try:
                        reactmessage = await trychannel.get_message(wint)
                        continue
                    except:
                        pass
                    user = client.get_user(wint)
                    if user:
                        reactmessage = await trychannel.history().get(author=user) or reactmessage
                        continue
            if not word.startswith('\\') and emoji.get(word):
                await reactmessage.add_reaction(emoji[word])
            elif not word.startswith('\\') and word in emoji.values():
                await reactmessage.add_reaction(word)
            else:
                for char in word:
                    if char in string.ascii_lowercase:
                        await reactmessage.add_reaction(emoji[f'regional_indicator_{char}'])
                    elif char in string.digits or emoji.get(char):
                        await reactmessage.add_reaction(emoji[char])
    except discord.errors.Forbidden:
        await asyncio.sleep(5)

async def cNumReact(client,message,params={}):
    await dcommands.num_react(client,message,params.get('ctext') or params.get('n'))


commands = {
    'roll':[['dice','die'],cRoll,True,False],
    'token':[[],cToken,False,True],
    'weather':[[],cWeather,False,False],
    'forecast':[[],cForecast,False,False],
    'echo':[['say'],cEcho,False,True],
    'pic':[['pics'],cPic,False,False],
    'react':[['reaction'],cReact,True,False],
    'numreact':dcommands.Command(coroutine=cNumReact, cooldown=True),
    'timeit':[[],cTimeit,False,True],

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