import discord
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
import requests
import io
import os
import sys

#Documentation
#Créer un salon textuel nommé esibot_config
#Dans un même message, mettre 'add config' sur la 1ere ligne et mettre les paramètres souhaités sur ce modèle:
#zombini_url:https://edt.zombini.fr/controler/edt.ctrl.php?classe=1A-TP1&page=1
#weekedt_room:883450350345015410            (identifiant du salon où poster l'EDT)

#Parameters
WeekEDT_DayWidth = 384

MatieresNameDictionary = {'CM MA121':'CM Maths\nMA121',
'TD MA121':'TD Maths\nMA121',
'CM PH101':'CM Physique\nPH101',
'TD PH101':'TD Physique\nPH101',
'CM IN101':'CM Intégration\nIN101',
'TD IN101':'TD Intégration\nIN101',
'CM AC101':'CM Automatique\nAC101',
'TD AC101':'TD Automatique\nAC101',
'CM EE121':'CM Électronique\nEE121',
'TD EE121':'TD Électronique\nEE121',
'CM LA101':'CM Anglais\nLA101',
'TD LA101':'TD Anglais\nLA101',
'CM SP101':'CM Sport\nSP101',
'TD SP101':'TD Sport\nSP101',
'CM CS101':'CM Programmation\nCS101',
'TD CS101':'TD Programmation\nCS101',
'CM MB111':'CM Communication écrite\nMB111',
'TD MB111':'TD Communication écrite\nMB111'}
MatieresColorDictionary = {}


guilds = {}


client = discord.Client()

def Log(message):
    print('{' + str(datetime.now().time()) + '}   ' + message)


async def GetEsibotConfigChannels():
    global guilds
    for guild in client.guilds:
        guilds[str(guild.id)] = {}
        guilds[str(guild.id)]['esibot_config_channel'] = discord.utils.get(guild.channels, name='esibot_config')
        
        async for message in guilds[str(guild.id)]['esibot_config_channel'].history():
            if message.content.split('\n')[0] == "add config" and (message.author.id == 420914917420433408): #Si c'est un message de configuration écrit par BlendSkill
                guilds[str(guild.id)][str(message.id)] = {}
                guilds[str(guild.id)][str(message.id)]['weekedt_replacename'] = {}
                guilds[str(guild.id)][str(message.id)]['weekedt_setcolor'] = {}
                lines = message.content.split('\n')
                for line in lines:
                    if line.startswith("zombini_url:"):
                         guilds[str(guild.id)][str(message.id)]['zombini_url'] = line.split(':', 1)[1]
                    if line.startswith("weekedt_channel:"):
                         guilds[str(guild.id)][str(message.id)]['weekedt_channel'] = line.split(':', 1)[1]   
                    if line.startswith("weekedt_header_bg:"):
                         guilds[str(guild.id)][str(message.id)]['weekedt_header_bg'] = line.split(':', 1)[1]

                    if line.startswith("weekedt_replacename:"):
                        msg = line.replace('weekedt_replacename:', '')
                        guilds[str(guild.id)][str(message.id)]['weekedt_replacename'][msg.split('][', 1)[0]] = msg.split('][', 1)[1]

                    if line.startswith("weekedt_setcolor:"):
                        msg = line.replace('weekedt_setcolor:', '')
                        guilds[str(guild.id)][str(message.id)]['weekedt_setcolor'][msg.split('][', 1)[0]] = msg.split('][', 1)[1]

async def WeekEDTLoop():
    global guilds
    guilds = {}


    await GetEsibotConfigChannels()

    for guild in guilds.keys(): #Pour chaque serveur
        Log("Mise à jour du serveur " + client.get_guild(int(guild)).name)
        for config in guilds[guild].keys(): #Pour chaque message de configuration
            if config.isnumeric():#Si c'est bien un msg de configuration
                if "zombini_url" in guilds[guild][config] and 'weekedt_channel' in guilds[guild][config]:
                    Log("   Mise à jour d'après la configuration " + str(config))

                    if not "weekedt_bg" in guilds[guild][config]:
                        guilds[guild][config]["weekedt_bg"] = '#FFFFFF'
                    if not "weekedt_header_bg" in guilds[guild][config]:
                        guilds[guild][config]["weekedt_header_bg"] = '#C7A5FF'

                    edt_dic = GetWeekEDT(guilds[guild][config])
                    edt_arr = DrawWeekEdt(edt_dic, guilds[guild][config])
                    edt_arr.seek(0)
                    edt_file = discord.File(edt_arr, filename='edt.png')

                    edt_next = GetNext(edt_dic)
                    message_edt_next = ""

                    if edt_next != None:
                        if edt_next['Title'] in guilds[guild][config]['weekedt_replacename']:
                            edt_next['Title'] = guilds[guild][config]['weekedt_replacename'][edt_next['Title']].split('\\n')[0]
                        edt_next['Location'] = edt_next['Location'].replace(' (V)', '')

                        message_edt_next = '\n\nProchain cours: ' + edt_next['Title'] + " en salle " + edt_next['Location'] + " à " + edt_next['Start'] + "."

                        if edt_next['Location'] == "":
                            message_edt_next = '\n\nProchain cours: ' + edt_next['Title'] + " à " + edt_next['Start'] + "."
                        
                    else:
                        message_edt_next = "\n\nBon week-end !"

                    async for message in client.get_channel(int(guilds[guild][config]['weekedt_channel'])).history():
                        if message.author == client.user:
                            if message.content.startswith('EDT ' + str(config)):
                                await message.delete()

                    tz = pytz.timezone('Europe/Berlin')
                    await client.get_channel(int(guilds[guild][config]['weekedt_channel'])).send(file=edt_file, content='EDT ' + str(config) + "\nDernière mise à jour: " + datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S") + message_edt_next)
                else:
                    Log("   Erreur: La configuration n°" + str(config) + " n'est pas complète. zombini_url ou weekedt_channel manquant(s).")

    Log("Toutes les mises à jour sont terminées.")
    time.sleep(60)
    await WeekEDTLoop()



@client.event
async def on_ready():
    global guilds

    Log("Esibot est en ligne.")
    guilds = {}
    await WeekEDTLoop()

def GetWeekEDT(config):
    finaledt = {}
    soup = BeautifulSoup(requests.get(config['zombini_url']).text, "html5lib")
       
    lundi = soup.find('div', class_='tab').find('div', class_='jour lundi')
    mardi = soup.find('div', class_='tab').find('div', class_='jour mardi')
    mercredi = soup.find('div', class_='tab').find('div', class_='jour mercredi')
    jeudi = soup.find('div', class_='tab').find('div', class_='jour jeudi')
    vendredi = soup.find('div', class_='tab').find('div', class_='jour vendredi')
    week = [lundi, mardi, mercredi, jeudi, vendredi]
    
    for day in week:
        titleday = day.find('p', class_='dateJour').get_text()
        finaledt[titleday] = {}
        counter = 0
        for matiere in day.find('div', class_='eventsContainer').find_all('div', class_='ev'):
            title = matiere.find(class_='title').get_text()
            location = matiere.find(class_='location').get_text()
            start = matiere.find(class_='start').get_text()
            end = matiere.find(class_='end').get_text()
            finaledt[titleday][str(counter)] = {'Title' : title, 'Location': location, 'Start': start, 'End': end}
            counter+=1
    return finaledt

def GetMinMaxHours(edt):
    min = 1500
    max = -1500

    for i in range(5):
        edtday = list(edt)[i] 
        
        for matiere in edt[edtday]:
            start = int(edt[edtday][matiere]['Start'].split(':')[0])*60 + int(edt[edtday][matiere]['Start'].split(':')[1])
            end = int(edt[edtday][matiere]['End'].split(':')[0])*60 + int(edt[edtday][matiere]['End'].split(':')[1])

            if start < min :
                min = start
            if end > max:
                max = end

    return (min, max)

def DrawWeekEdt(edt, config):
    minmax = GetMinMaxHours(edt)
    WeekEDT_DayHeight = int((minmax[1]-minmax[0])*2.25)

    img = Image.new('RGB', (WeekEDT_DayWidth*5, WeekEDT_DayHeight+50), config['weekedt_bg'])
    draw = ImageDraw.Draw(img)

    daynumber = -1
    time_ = datetime.now().hour * 60 + datetime.now().minute
    if datetime.today().weekday() <= 4:
        daynumber = datetime.today().weekday()

    #daynumber = 2
    #time_ = 660


    draw.rectangle((0, 0, WeekEDT_DayWidth*5, 50), fill=config['weekedt_header_bg'])

    #Ecrire le nom des jours
    for i in range(5):
        edtday = list(edt)[i] 
        draw.text((WeekEDT_DayWidth*i + WeekEDT_DayWidth/2,15), edtday, anchor='mt',fill=(0, 0, 0),font=ImageFont.truetype("arial.ttf", 30))

        if daynumber == i:
            draw.line((WeekEDT_DayWidth*i, (time_-minmax[0])*2.25+50, WeekEDT_DayWidth*(i+1), (time_-minmax[0])*2.25+50), fill=(255,0,0), width=3)

        #Placer les matières
        for matiere in edt[edtday]: #Pour chaque matière
            mstart = int(edt[edtday][matiere]['Start'].split(':')[0])*60 + int(edt[edtday][matiere]['Start'].split(':')[1])
            mend = int(edt[edtday][matiere]['End'].split(':')[0])*60 + int(edt[edtday][matiere]['End'].split(':')[1])
            name = edt[edtday][matiere]['Title']
            if name in config['weekedt_replacename']:
                name = config['weekedt_replacename'][name].replace('\\n', '\n')
            else:
                for line in range((len(name)//20)):
                    name = name[:(line+1)*20] + '\n' + name[(line+1)*20:]
                name = name.strip()
            color = (175, 175, 175)
            if edt[edtday][matiere]['Title'] in config['weekedt_setcolor']:
                color = config['weekedt_setcolor'][edt[edtday][matiere]['Title']]

            draw.rectangle((WeekEDT_DayWidth*i,(mstart-minmax[0])*2.25+50, WeekEDT_DayWidth*(i+1), (mend-minmax[0])*2.25+50), fill=color)
            draw.line((WeekEDT_DayWidth*i, (mstart-minmax[0])*2.25+50, WeekEDT_DayWidth*(i+1), (mstart-minmax[0])*2.25+50), fill=(0,0,0), width=3)
            draw.line((WeekEDT_DayWidth*i, (mend-minmax[0])*2.25+50, WeekEDT_DayWidth*(i+1), (mend-minmax[0])*2.25+50), fill=(0,0,0), width=3)

            #Tracer la ligne du temps
            isactive = False
            if daynumber == i:
                if mstart<=time_ and mend>=time_:
                    draw.line((WeekEDT_DayWidth*i, (time_-minmax[0])*2.25+50, WeekEDT_DayWidth*(i+1), (time_-minmax[0])*2.25+50), fill=(255,0,0), width=3)
                    isactive = True

            text = name
            if edt[edtday][matiere]['Location'] != '':
                text += ('\nSalle ' + edt[edtday][matiere]['Location'].replace(' (V)', ''))
            
            draw.text(((WeekEDT_DayWidth*i + WeekEDT_DayWidth*(i+1))/2, (mstart-minmax[0])*2.25+50+25 ), edt[edtday][matiere]['Start'], anchor='mm', fill=(0, 0, 0),font=ImageFont.truetype("arial.ttf", 25))
            draw.text(((WeekEDT_DayWidth*i + WeekEDT_DayWidth*(i+1))/2, (mend-minmax[0])*2.25+50-25 ), edt[edtday][matiere]['End'], anchor='mm', fill=(0, 0, 0),font=ImageFont.truetype("arial.ttf", 25))
            if isactive:
                draw.text(((WeekEDT_DayWidth*i + WeekEDT_DayWidth*(i+1))/2, ((mstart-minmax[0])*2.25+50 + (mend-minmax[0])*2.25+50)/2), text, anchor='mm', align='center', fill=(0, 0, 0),font=ImageFont.truetype("arialbd.ttf", 27))
            else:
                draw.text(((WeekEDT_DayWidth*i + WeekEDT_DayWidth*(i+1))/2, ((mstart-minmax[0])*2.25+50 + (mend-minmax[0])*2.25+50)/2), text, anchor='mm', align='center', fill=(0, 0, 0),font=ImageFont.truetype("arial.ttf", 27))

    #Tracer les contours du haut et du bas
    draw.line((0, 2, WeekEDT_DayWidth*5, 2), fill=(0, 0, 0), width=5)
    draw.line((0, WeekEDT_DayHeight+50-2, WeekEDT_DayWidth*5, WeekEDT_DayHeight+50-2), fill=(0, 0, 0), width=5)

    #Tracer les colones
    for i in range(6):
        draw.line((WeekEDT_DayWidth*i, 0, WeekEDT_DayWidth*i, WeekEDT_DayHeight+50), fill=(0, 0, 0), width=5)
        
    draw.line((0, 50, WeekEDT_DayWidth*5, 50), fill=(0, 0, 0), width=5)

    arr = io.BytesIO()
    img.save(arr, format='PNG')
    return arr

def GetNext(edt):
    daynumber = datetime.today().weekday()
    time_ = datetime.now().hour * 60 + datetime.now().minute

    if daynumber > 4:
        return None
    
    edtlist = list(edt)

    deltalist = {}

    smallest = (None, 15000)

    for days in edt:
        for cours in edt[days]:
            startm = int(edt[days][cours]["Start"].split(':')[0])*60 + int(edt[days][cours]["Start"].split(':')[1])

            delta = startm - time_ + 24*60*(edtlist.index(days)-daynumber)

            if delta >=0 and delta < smallest[1]:
                smallest = (edt[days][cours], delta)

    return smallest[0]

    

client.run(os.environ['TOKEN'])
