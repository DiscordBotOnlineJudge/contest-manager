import os
from pymongo import MongoClient
import contests
import discord
from functools import cmp_to_key
import asyncio

client = discord.Client()

cluster = MongoClient("mongodb+srv://onlineuser:$" + os.getenv("PASSWORD") + "@discord-bot-online-judg.7gm4i.mongodb.net/database?retryWrites=true&w=majority")
db = cluster['database']
settings = db['settings']

def cmp(a, b):
    if a[1] != b[1]:
        return b[1] - a[1]
    return a[2] - b[2]

def getLen(contest):
    return settings.find_one({"type":"contest", "name":contest})['len']

def amt(len):
    h = len // 3600
    len %= 3600
    m = len // 60
    len %= 60
    s = len

    return "{hh} hours, {mm} minutes, and {ss} seconds".format(hh = h, mm = m, ss = s)

def getStatus():
    msg = ""
    for x in settings.find({"type":"judge"}):
        msg += "Judge #" + str(x['num']) + ": " + decode(x['status']).ljust(23)
        if x['status'] != 2:
            msg += "(" + x['runtimes'] + ")"
        msg += "\n"
    return msg

def decode(cde):
    if cde == 0:
        return "Available"
    elif cde == 1:
        return "Submission in Progress"
    elif cde == 2:
        return "Offline"
    else:
        return ""
    
def getScoreboard(contest):
    ct = settings.find_one({"type":"contest", "name":contest})
    if ct is None:
        return "Contest not found!"

    time_bonus = ct['has-time-bonus']
    penalty = ct['has-penalty']

    fnd = settings.find({"type":"access", "mode":contest})
    arr = [x for x in fnd]

    msg = "**Current rankings for participants in contest `" + contest + "`**\n```"
    cnt = 0

    namWid = 0
    pWid = [0] * (ct['problems'] + 1)
    comp = []

    for x in arr:
        namWid = max(namWid, len(x['name']))
        for y in range(1, len(x['solved'])):
            dt = "P" + str(y) + "-" + str(x['solved'][y])

            if time_bonus and x['time-bonus'][y] > 0:
                dt += "(+" + str(x['time-bonus'][y]) + ")"
            if penalty and x['penalty'][y] > 0:
                dt += "(" + str(x['penalty'][y]) + ")"
            pWid[y] = max(pWid[y], len(dt))
    for x in arr:
        m = x['name'].ljust(namWid) + " : "
        total = 0
        for y in range(1, len(x['solved'])):
            dt = "P" + str(y) + "-" + str(x['solved'][y])

            if time_bonus and x['time-bonus'][y] > 0:
                dt += "(+" + str(x['time-bonus'][y]) + ")"
            if penalty and x['penalty'][y] > 0:
                dt += "(" + str(x['penalty'][y]) + ")"
                
            m += dt.ljust(pWid[y]) + " "
            total += x['solved'][y] + x['time-bonus'][y]
        m += "total: " + str(total)
        comp.append((m, total, sum(x['penalty'])))
    
    comp.sort(key = cmp_to_key(cmp))
    idx = 0
    cur = 0
    for i in range(len(comp)):
        cur += 1
        if i == 0 or comp[i - 1][1] != comp[i][1] or comp[i - 1][2] != comp[i][2]:
            idx = cur
        msg += str(idx) + ") " + comp[i][0] + "\n"

    if len(comp) <= 0:
        msg += "---No participants are in this contest yet---\n"
        
    return msg + "```"

async def live_scoreboard(contest):
    global scb
    current_contest = settings.find_one({"type":"livecontests"})['arr']
    for x in range(len(current_contest)):
        if current_contest[x] == contest:
            await scb[x].edit(content = getScoreboard(contest))
            return
    print("Failed to update live scoreboard")

def get_bonus(rem, pts):
    return (pts * rem) // 30000

async def updateScore(contest, problem, user, score, ct):
    post = settings.find_one({"type":"access", "name":user, "mode":contest})
    if post is None:
        print("Failed to update score (no access post)")
        return
    elapsed = contests.compare(post['start'], ct)
    contest_len = getLen(contest)
    if elapsed > contest_len:
        print("Invalid score update")
        return
    arr = post['solved']
    penalty = post['penalty']
    time_bonus = post['time-bonus']

    num = int(problem[len(problem) - 1])

    if score <= arr[num] and arr[num] < 100:
        penalty[num] += 1
    if arr[num] < 100:
        settings.update_one({"_id":post['_id']}, {"$set":{"taken":elapsed}})

    arr[num] = max(arr[num], score)
    time_bonus[num] = max(time_bonus[num], get_bonus(contest_len - elapsed, score))

    settings.update_one({"_id":post['_id']}, {"$set":{"solved":arr, "penalty":penalty, "time-bonus":time_bonus}})
    await live_scoreboard(contest)

def remaining(name):
    acc = settings.find({"type":"access", "name":name})
    msg = ""
    for x in acc:
        if x['mode'] != "admin" and x['mode'] != "owner":
            try:
                total = getLen(x['mode'])
                elapsed = contests.compare(x['start'], contests.current_time())
                rem = total - elapsed
                if rem <= 0:
                    msg += "Time's up! `" + name + "`'s participation in contest `" + x['mode'] + "` has ended.\n"
                else:
                    msg += "`" + name + "` still has `" + amt(rem) + "` left on contest `" + x['mode'] + "`\n"
            except:
                pass
    if len(msg) == 0:
        return "`" + name + "` has not joined any contests"
    return msg

async def sendLiveScoreboards():
    current_contest = settings.find_one({"type":"livecontests"})['arr']

    global scb
    global prev_scb
    scb = [None] * len(current_contest)
    prev_scb = [None] * len(current_contest)
    sbc = client.get_channel(852311780378148914)
    await sbc.purge(limit = 100)

    for x in range(len(current_contest)):
        content = getScoreboard(current_contest[x])
        scb[x] = await sbc.send(content)
        prev_scb[x] = content

async def listen_scoreboard():
    global scb
    global prev_scb
    global status
    global prev_status

    while True:
        current_contest = settings.find_one({"type":"livecontests"})['arr']
        try:
            for x in range(len(current_contest)):
                content = getScoreboard(current_contest[x])
                if content != prev_scb[x] and not scb[x] is None:
                    await scb[x].edit(content = content)
                    prev_scb[x] = content
                    print("Edited content in " + current_contest[x])

            msg = getStatus()
            if msg != prev_status:
                await status.edit(content = ("**Current live judge server statuses:**\n```" + msg + "\n```"))
                prev_status = msg
                print("Edited live status message")
        except Exception as e:
            print("Exception occurred:", e)
        await asyncio.sleep(3)

@client.event
async def on_ready():
    global running
    running = True

    await sendLiveScoreboards()

    global status
    global prev_status
    stat = client.get_channel(851468547414294568)
    await stat.purge(limit = 100)
    prev_status = getStatus()
    status = await stat.send("**Current live judge server statuses:**\n```" + prev_status + "\n```")

    print(f'{client.user} has connected to Discord!')

    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(listen_scoreboard())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if str(message.content).startswith("-set"):
        arr = str(message.content).split()
        
        if settings.find_one({"type":"access", "mode":"admin", "name":str(message.author)}) is None:
            await message.channel.send("Sorry, you do not have sufficient permissions to use this command.")
            return

        settings.update_one({"type":"livecontests"}, {"$set":{"arr":arr[1:]}})
        await sendLiveScoreboards()
        await message.channel.send("Live scoreboard contests set to `" + str(arr[1:]) + "`")

client.run(os.getenv("TOKEN"))
