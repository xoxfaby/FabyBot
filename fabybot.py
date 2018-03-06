import discord
import discordfaby
import re
from random import randint

from config import token

async def cRoll(message, params={}):
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

            if n1 > 100:
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



commands = {
    'roll':[['dice','die'],cRoll,True]
}
client = discordfaby.Client(token=token,commands=commands)




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

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name='you sleep.'))

    await client.process_ready()


client.run(client.token)