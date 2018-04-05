import discord
import discordfaby
import re
import asyncio
import aioDarkSkyAPI
import io
import os
import functools
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
    blocks = ['currently', 'minutely', 'hourly', 'daily', 'alerts', 'flags']

    forecast = 'hourly' or forecastable.get(params.get('forecast'))
    if not forecast:
        forecast = 'daily'
        await message.channel.send(f'`{params["forecast"]}` is not a valid forecast, defaulting to `daily`')
    blocks.remove(forecast)
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
        if True:
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

async def cWeather(client,message,params={}):
    '''Returns weather information
forecast=minutely/hourly/daily'''
    blocks = ['currently', 'minutely', 'hourly', 'daily', 'alerts', 'flags']

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

    for timeitfunc in timeits:
        timeitafunc = functools.partial(timeit, timeitfunc, number=100)
        timetaken = await client.loop.run_in_executor(None, timeitafunc)
        msg = f'''{msg}[{timeitfunc.__name__}] {timetaken}\n'''
        await asyncio.sleep(0)


    msg = f'''{msg}```'''

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