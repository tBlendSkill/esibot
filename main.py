import urllib3
import urllib.request
import datetime
import pytz
import discord
import configs
from discord.ext import tasks
from PIL import Image, ImageDraw, ImageFont
import io
import time
import os
import sys

#Mes identifiants Agalan (variables secrètes)
AGALAN_USERNAME = os.environ['AGALAN_USERNAME']
AGALAN_PASSWORD = os.environ['AGALAN_PASSWORD']

#Token du bot
BOT_TOKEN = os.environ['BOT_TOKEN']

#Identifiants des TPs pour accéder à leur EDT
PROMOTION_IDs = {"1ATP1":"5957", "1ATP2":"5956", "1ATP3":"5941", "1ATP4":"5953"}


now = None

client = discord.Client()


#Met à jour la date à prendre en compte dans le programme
def UpdateTime():
    global now
    now = datetime.datetime.now(pytz.timezone('Europe/Paris'))
    #now = now - datetime.timedelta(7)


#Retourne la date du Lundi et du Vendredi de la semaine à afficher
def GetFirstAndLastEDTDays():
    first = None
    last = None

    if now.weekday() <= 4: #Si on est en semaine, prendre le Lundi et le Vendredi de la semaine actuelle
        first = now - datetime.timedelta(now.weekday())
        last = now + datetime.timedelta(4-now.weekday())
    else: #Si on est en week-end, prendre le Lundi et le Vendredi de la semaine suivante
        first = now + datetime.timedelta(7-now.weekday())
        last = now + datetime.timedelta((7-now.weekday())+4)

    return (first, last)


#Retourne les deux années correspondants à l'année scolaire en cours
def GetSchoolYears():
    first = now.year if now.month >= 7 else now.year - 1 #Dépend de si on est avant ou après juillet
    second = first+1

    return(first, second)


#Télécharge l'emploi du temps correspondant à l'id fournit
def DownloadEDT(id):
    firstlastdays = GetFirstAndLastEDTDays()

    http = urllib3.PoolManager()
    headers = urllib3.util.make_headers(basic_auth=AGALAN_USERNAME + ":" + AGALAN_PASSWORD)
    url = "https://edt.grenoble-inp.fr/directCal/" + str(GetSchoolYears()[0]) + "-" + str(GetSchoolYears()[1]) + "/etudiant/esisar?resources=" + str(id) + "&startDay=" + str(firstlastdays[0].day).zfill(2) + "&startMonth=" + str(firstlastdays[0].month).zfill(2) + "&startYear=" + str(firstlastdays[0].year)  + "&endDay=" + str(firstlastdays[1].day).zfill(2)  + "&endMonth=" + str(firstlastdays[1].month).zfill(2)  + "&endYear=" + str(firstlastdays[1].year)
    
    r = http.request('GET',url,headers=headers)
    result = r.data.decode('utf-8')
    return result

#Classe permettant de représenter les informations d'une matière
class Event:
    def __init__(self):
        self.Start = None
        self.End = None
        self.Name = None
        self.Location = None
        self.ID = None
        self.Professor = None

#Classe contenant la liste de chaque matière (classe Event) pour chaque jour, et les heures minimales et maximales atteintent dans la semaine
class EDT:
    def __init__(self):
        self.Lundi = []
        self.Mardi = []
        self.Mercredi = []
        self.Jeudi = []
        self.Vendredi = []

        self.Min = 1440
        self.Max = 0
        

#Crée un EDT à partir des informations téléchargées
def ParseEDT(edt):
    index = 0
    lines = edt.splitlines()

    VeventList = []
    edt = EDT()

    IsInVevent = False
    for line in lines: #Pour chaque ligne du fichier
        if line.startswith("BEGIN:VEVENT") and IsInVevent == False: #Si c'est un début d'évènement et qu'on n'est pas déjà dans un évènement
            IsInVevent = True
            VeventList.append(Event()) #Ajouter un nouvel évènement dans la liste

        elif line.startswith("END:VEVENT") and IsInVevent == True: #Si c'est la fin d'un évènement et qu'on était dans un évènement
            IsInVevent = False
            
            #Ajoute le dernier évènement dans la liste de l'EDT correspondant au jour de l'évènement
            weekday = VeventList[-1].Start.weekday()
            if weekday == 0:
                edt.Lundi.append(VeventList[-1])
            elif weekday == 1:
                edt.Mardi.append(VeventList[-1])
            elif weekday == 2:
                edt.Mercredi.append(VeventList[-1])
            elif weekday == 3:
                edt.Jeudi.append(VeventList[-1])
            elif weekday == 4:
                edt.Vendredi.append(VeventList[-1])

            #Modifie si besoin les heures minimales et maximales de l'EDT
            startinminutes = VeventList[-1].Start.hour * 60 + VeventList[-1].Start.minute
            endinminutes = VeventList[-1].End.hour * 60 + VeventList[-1].End.minute
            edt.Min = min(startinminutes, edt.Min)
            edt.Max = max(endinminutes, edt.Max)

        elif IsInVevent: #Si on est dans un évènement
            if line.startswith("DTSTART:"): #Si la ligne indique l'heure de début de l'évènement
                data = line.replace("DTSTART:", "")
                year = int(data[0:4])
                month = int(data[4:6])
                day = int(data[6:8])
                hour = int(data[9:11]) + int(now.utcoffset().total_seconds()/60/60) #Prend en compte le décalage horaire
                minute = int(data[11:13])
                date = datetime.datetime(year, month, day, hour, minute, 0, 0)
                VeventList[-1].Start = date #Modifie la date de début du dernier évènement ajouté (donc celui qui est en train d'être lu)

            if line.startswith("DTEND:"): #Si la ligne indique l'heure de fin de l'évènement
                data = line.replace("DTEND:", "")
                year = int(data[0:4])
                month = int(data[4:6])
                day = int(data[6:8])
                hour = int(data[9:11]) + int(now.utcoffset().total_seconds()/60/60) #Prend en compte le décalage horaire
                minute = int(data[11:13])
                date = datetime.datetime(year, month, day, hour, minute, 0, 0)
                VeventList[-1].End = date

            if line.startswith("SUMMARY:"): #Si la ligne indique le nom de l'évènement (nom de la matière)
                VeventList[-1].Name = line.replace("SUMMARY:", "")

            if line.startswith("LOCATION:"): #Si la ligne indique le lieu de l'évènement (salle)
                VeventList[-1].Location = line.replace("LOCATION:", "")

            if line.startswith("DESCRIPTION:"): #La description contient (entre autre) l'ID de la matière et le nom du professeur
                data = line.replace("DESCRIPTION:", "").split('\\n')
                VeventList[-1].ID = data[2]
                if not(data[3].startswith('(Exporté')):
                    VeventList[-1].Professor = data[3]
        
    return edt
        
#Obtient la prochaine matière et retourne le texte "Prochain cours : ..." à envoyer sur Discord
def GetNextMatiere(edt, config):
    weekday = now.weekday()
    minutetime = now.hour*60 + now.minute


    if weekday == 5:
        return 'Bon week-end !'
        #return 'Bonnes vacances !'

    elif weekday == 6:
        weekday = -1
    

    smallestDelta = (None, 15000)
    for matiere in edt.Lundi + edt.Mardi + edt.Mercredi + edt.Jeudi + edt.Vendredi: #Pour chaque matière dans l'EDT
        minutestart = matiere.Start.hour * 60 + matiere.Start.minute
        delta = minutestart - minutetime + 24*60*(matiere.Start.weekday() - weekday) #Calcule le temps entre maintenant et le début de la matière

        if delta >= 0 and delta < smallestDelta[1]: #Si le temps est inférieur au temps minimal déjà calculé et que la matière n'a pas encore commencé
            smallestDelta = (matiere, delta)

    if smallestDelta[0] != None:
        name = ""
        if smallestDelta[0].Name != None:
            name = smallestDelta[0].Name
        else:
            name = smallestDelta[0].ID.split('_')[0][3:].strip()

        if name in config.Name_Dictionary:
            name = config.Name_Dictionary[name]

        if  len(smallestDelta[0].ID.split('_')) == 5:
            type = smallestDelta[0].ID.split('_')[3]
            name = type + " " + name
        
        if smallestDelta[0].Location != "":
            return "Prochain cours: " + name + " en salle " + smallestDelta[0].Location.replace(' (V)', '').replace('\\,', ' / ') + " à " + str(smallestDelta[0].Start.hour).zfill(2) + ":" + str(smallestDelta[0].Start.minute).zfill(2) + "."
        else:
            return "Prochain cours: " + name + " à " + str(smallestDelta[0].Start.hour).zfill(2) + ":" + str(smallestDelta[0].Start.minute).zfill(2) + "."
    else:
      return ""

def DrawEDT(edt, config):
    img = Image.new('RGB', (config.width, config.height), config.background_color)
    if config.background_image != None:
      backgroundimage = None
      if config.background_image.startswith("http"):
        http = urllib3.PoolManager()
        resp = http.request('GET', config.background_image).data
        backgroundimage = Image.open(io.BytesIO(resp))
      else:
        backgroundimage = Image.open(config.background_image)
      widthratio = config.width /backgroundimage.size[0]
      heightratio = config.height /backgroundimage.size[1]
      bgwidth = int(backgroundimage.size[0] * max(widthratio,heightratio))
      bgheight= int(backgroundimage.size[1] * max(widthratio,heightratio))
      backgroundimage = backgroundimage.resize((bgwidth,bgheight))
      img.paste(backgroundimage,(0,0))


    draw = ImageDraw.Draw(img)

    #Header Part 1
    headerHeight =  round(config.height/21.5)
    draw.rectangle((0, 0, config.width, headerHeight), fill=config.header_color)

    availableHeight = config.height - headerHeight
    maxMinutes = edt.Max - edt.Min
    HeightMinutesRatio = availableHeight / maxMinutes

    #Day Title
    mondaydate = GetFirstAndLastEDTDays()[0]
    TimeLineDrawed = False
    for day in range(5):
        date = mondaydate + datetime.timedelta(day)
        text = ""
        matierelist = []
        if day == 0:
            text = "Lundi " + str(date.day).zfill(2) + "/" + str(date.month).zfill(2) + "/" + str(date.year)
            matierelist = edt.Lundi
        elif day == 1:
            text = "Mardi " + str(date.day).zfill(2) + "/" + str(date.month).zfill(2) + "/" + str(date.year)
            matierelist = edt.Mardi
        elif day == 2:
            text = "Mercredi " + str(date.day).zfill(2) + "/" + str(date.month).zfill(2) + "/" + str(date.year)
            matierelist = edt.Mercredi
        elif day == 3:
            text = "Jeudi " + str(date.day).zfill(2) + "/" + str(date.month).zfill(2) + "/" + str(date.year)
            matierelist = edt.Jeudi
        elif day == 4:
            text = "Vendredi " + str(date.day).zfill(2) + "/" + str(date.month).zfill(2) + "/" + str(date.year)
            matierelist = edt.Vendredi

        draw.text((round(config.width/5)*day + round(config.width/10), round(config.height/72)), text, anchor='mt', fill=config.headertext_color, font=ImageFont.truetype("arial.ttf", round(config.height/72*2)))

        #MatiereRectangle
        for matiere in matierelist:
            name = ""
            if matiere.Name != None:
                name = matiere.Name
            else:
                name = matiere.ID.split('_')[0][3:].strip()

            color = "#ADADAD"
            if name in config.Color_Dictionary:
                color = config.Color_Dictionary[name]

            matiereTopCoord = (headerHeight + (matiere.Start.hour*60 + matiere.Start.minute - edt.Min)*HeightMinutesRatio)
            matiereBottomCoord = (headerHeight + (matiere.End.hour*60 + matiere.End.minute - edt.Min)*HeightMinutesRatio)
            draw.rectangle(((config.width/5)*day, matiereTopCoord, (config.width/5)*(day+1), matiereBottomCoord), fill=color)
            draw.line(((config.width/5)*day, matiereTopCoord, (config.width/5)*(day+1), matiereTopCoord), fill=(0,0,0), width=3)
            draw.line(((config.width/5)*day, matiereBottomCoord, (config.width/5)*(day+1), matiereBottomCoord), fill=(0,0,0), width=3)

            #TimeLine
            isCurrentMatiere = False
            if now.weekday() == day:
                currentMinuteTime = now.hour*60 + now.minute
                if (matiere.Start.hour*60 + matiere.Start.minute) < currentMinuteTime and (matiere.End.hour*60 + matiere.End.minute) > currentMinuteTime:
                    isCurrentMatiere = True
                    LineCoord = headerHeight + (currentMinuteTime - edt.Min)*HeightMinutesRatio
                    draw.line(((config.width/5)*day, LineCoord, (config.width/5)*(day+1), LineCoord), fill=config.timeline_color, width=3)
                    TimeLineDrawed = True


            #ProfessorText
            if matiere.Professor != None:
              draw.text((round(config.width/5)*(day+1)-5, matiereBottomCoord - round(config.height/(60+5))), " ".join(matiere.Professor.split(' ')[0:-1]), anchor='rm', fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/60)))


            hour_anchor = 'mm'
            hour_x = round(config.width/5)*day + round(config.width/10)
            hour_topbottom_margin = round(config.height/(44+5))

            if abs(matiereTopCoord-matiereBottomCoord) < 125:
                hour_anchor = 'lm'
                hour_x = round(config.width/5)*day + 10
                hour_topbottom_margin = round(config.height/(44+10))

            #StartText
            draw.text((hour_x, matiereTopCoord + hour_topbottom_margin), str(matiere.Start.hour).zfill(2) + ":" + str(matiere.Start.minute).zfill(2), anchor=hour_anchor, fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/44)))

            #EndText
            draw.text((hour_x, matiereBottomCoord - hour_topbottom_margin), str(matiere.End.hour).zfill(2) + ":" + str(matiere.End.minute).zfill(2), anchor=hour_anchor, fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/44)))

            #MainText
            if name in config.Name_Dictionary:
                name = config.Name_Dictionary[name]
                
            title = ""
            if  len(matiere.ID.split('_')) == 5:
              type = matiere.ID.split('_')[3]
              title = type + " " + name + "\n" + matiere.Location.replace(' (V)', '').replace('\\,', ' / ') if matiere.Location != '' else type + " " + name
            else:
              title = name + "\n" + matiere.Location.replace(' (V)', '').replace('\\,', ' / ') if matiere.Location != '' else name


            if isCurrentMatiere:
                draw.text((round(config.width/5)*day + round(config.width/10), (matiereTopCoord + matiereBottomCoord)/2), title, anchor='mm', fill=config.text_color, align='center', font=ImageFont.truetype("arialbd.ttf", round(config.height/40)))
            else:
                draw.text((round(config.width/5)*day + round(config.width/10), (matiereTopCoord + matiereBottomCoord)/2), title, anchor='mm', fill=config.text_color, align='center', font=ImageFont.truetype("arial.ttf", round(config.height/40)))
    
            #TimeLine
            if now.weekday() == day and not TimeLineDrawed:
                currentMinuteTime = now.hour*60 + now.minute
                LineCoord = headerHeight + (currentMinuteTime - edt.Min)*HeightMinutesRatio
                draw.line(((config.width/5)*day, LineCoord, (config.width/5)*(day+1), LineCoord), fill=config.timeline_color, width=3)

        #Header Part 2
        draw.line((0, headerHeight, config.width, headerHeight), fill=(0,0,0), width=3)

        #Day Vertical Lines
        draw.line(((config.width/5)*day, 0, (config.width/5)*day, config.height), fill=(0, 0, 0), width=3)

        
    arr = io.BytesIO()
    img.save(arr, format='PNG')
    return arr

async def DeleteOldEDT(config):
    async for message in client.get_channel(config.channel_id).history():
        if message.author == client.user:
            if message.content.startswith(config.name):
                await message.delete()

async def Log(message, send_to_discord=True):
    UpdateTime()
    print('{' + str(now.time()) + '}   ' + message)
    if send_to_discord:
        await client.get_channel(895410453335928863).send(content= '> ' + message)


@client.event
async def on_ready():
    global now

    UpdateTime()
    await Log("Esibot est en ligne.")

    Loop.start()

interval_update = False
@tasks.loop(minutes=45)
async def Loop():
    global interval_update

    if not interval_update:
        await UpdateLoopInterval()

        min_hour = 8 if now.weekday() >= 5 else 7
    
        if min_hour <= now.hour <= 22:
            await Log("Mise à jour en cours...")
            configsError = []
            for config in configs.ConfigList:
                await Log("• " + config.name)
                try:
                    UpdateTime()
                    await Log("    Téléchargement et analyse de l'EDT...")
                    edt = ParseEDT(DownloadEDT(config.edt_id))
                    await Log("    Création de l'image...")
                    edtIMG = DrawEDT(edt, config)
                    edtIMG.seek(0)
                    await Log("    Envoi de l'EDT sur Discord...")
                    await DeleteOldEDT(config)
                    await client.get_channel(config.channel_id).send(file=discord.File(edtIMG, filename='EDT.png'), content=config.name + '\nDernière mise à jour: ' + now.strftime("%d/%m/%Y %H:%M:%S") + "\n\n" + GetNextMatiere(edt, config))
                    await Log('    ' + config.name + " a été mis à jour.")
                except Exception as e:
                    await Log('    Erreur : ' + str(e))
                    await Log('    Ligne ' + str(sys.exc_info()[2].tb_lineno))
                    await Log("    Nouvelle tentative dans quelques secondes.")
                    configsError.append(config)

            if len(configsError) > 0:
                time.sleep(10)
                for config in configsError:
                    await Log("• Nouvelle tentative pour " + config.name)
                    try:
                        UpdateTime()
                        await Log("    Téléchargement et analyse de l'EDT...")
                        edt = ParseEDT(DownloadEDT(config.edt_id))
                        await Log("    Création de l'image...")
                        edtIMG = DrawEDT(edt, config)
                        edtIMG.seek(0)
                        await Log("    Envoi de l'EDT sur Discord...")
                        await DeleteOldEDT(config)
                        await client.get_channel(config.channel_id).send(file=discord.File(edtIMG, filename='EDT.png'), content=config.name + '\nDernière mise à jour: ' + now.strftime("%d/%m/%Y %H:%M:%S") + "\n\n" + GetNextMatiere(edt, config))
                        await Log('    ' + config.name + " a été mis à jour.")
                    except Exception as e:
                        await Log('<@!420914917420433408>')
                        await Log('    Erreur : ' + str(e))
                        await Log('    Ligne ' + str(sys.exc_info()[2].tb_lineno))
                        await Log("    Abandon de la configuration. Nouvelle tentative lors de la prochaine mise à jour.")

            await Log("Mise à jour terminée.\n")

        interval_update = True
        Loop.restart()
    else:
        interval_update = False

async def UpdateLoopInterval():
    UpdateTime()
    if now.hour > 22:
        tomorrow_date = now + datetime.timedelta(days=1)
        tomorrow_date = tomorrow_date.replace(minute=0, second=0, microsecond=0)
        if tomorrow_date.weekday() <= 4:
            tomorrow_date = tomorrow_date.replace(hour=7)
        else:
            tomorrow_date = tomorrow_date.replace(hour=8)

        next_loop_in_seconds = (tomorrow_date - now).seconds
        Loop.change_interval(seconds=next_loop_in_seconds)
        await Log(f'Mise à jour suivante dans : {str(tomorrow_date - now)}.\n')

    elif now.hour < (7 if now.weekday() <= 4 else 8):
        start_date = now
        start_date = start_date.replace(minute=0, second=0, microsecond=0)
        if start_date.weekday() <= 4:
            start_date = start_date.replace(hour=7)
        else:
            start_date = start_date.replace(hour=8)

        next_loop_in_seconds = (start_date - now).seconds
        Loop.change_interval(seconds=next_loop_in_seconds)
        await Log(f'Mise à jour suivante dans : {str(start_date - now)}.\n')

    else:
        if now.weekday() <= 4:
            Loop.change_interval(minutes=45)
            await Log(f'Intervalle de mise à jour fixé à 45 minutes.')
        else:
            Loop.change_interval(hours=2)
            await Log(f'Intervalle de mise à jour fixé à 2 heures.')



client.run(BOT_TOKEN)