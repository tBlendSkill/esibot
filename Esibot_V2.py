import urllib3
import datetime
import pytz
import discord
import configs
from discord.ext import tasks
from PIL import Image, ImageDraw, ImageFont
import io

#Constants
AGALAN_USERNAME = ""
AGALAN_PASSWORD = ""
BOT_TOKEN = ""
PROMOTION_IDs = {"1ATP1":"5957", "1ATP2":"5956", "1ATP3":"5941", "1ATP4":"5953"}


#Global Vars
now = None
client = discord.Client()


def UpdateTime():
    global now
    now = datetime.datetime.now(pytz.timezone('Europe/Paris'))
    #now = datetime.datetime(2021, 10, 5, 10, 40)

def GetFirstAndLastEDTDays():
    UpdateTime()

    first = None
    last = None

    if now.weekday() <= 4:
        first = now - datetime.timedelta(now.weekday())
        last = now + datetime.timedelta(4-now.weekday())
    else:
        first = now + datetime.timedelta(7-now.weekday())
        last = now + datetime.timedelta((7-now.weekday())+4)

    return (first, last)

def GetSchoolYears():
    UpdateTime()

    first = now.year if now.month > 8 else now.year - 1
    second = first+1

    return(first, second)


def DownloadEDT(id):
    firstlastdays = GetFirstAndLastEDTDays()

    http = urllib3.PoolManager()
    headers = urllib3.util.make_headers(basic_auth=AGALAN_USERNAME + ":" + AGALAN_PASSWORD)
    url = "https://edt.grenoble-inp.fr/directCal/" + str(GetSchoolYears()[0]) + "-" + str(GetSchoolYears()[1]) + "/etudiant/esisar?resources=" + str(id) + "&startDay=" + str(firstlastdays[0].day).zfill(2) + "&startMonth=" + str(firstlastdays[0].month).zfill(2) + "&startYear=" + str(firstlastdays[0].year)  + "&endDay=" + str(firstlastdays[1].day).zfill(2)  + "&endMonth=" + str(firstlastdays[1].month).zfill(2)  + "&endYear=" + str(firstlastdays[1].year)
    
    r = http.request('GET',url,headers=headers)
    result = r.data.decode('utf-8')
    return result

class Event:
    Start = None
    End = None
    Name = None
    Location = None
    ID = None
    Professor = None

class EDT:
    Lundi = []
    Mardi = []
    Mercredi = []
    Jeudi = []
    Vendredi = []

    Min = 1440
    Max = 0
        
def ParseEDT(edt):
    index = 0
    lines = edt.splitlines()

    VeventList = []
    edt = EDT()

    IsInVevent = False
    for line in lines:
        if line.startswith("BEGIN:VEVENT") and IsInVevent == False:
            IsInVevent = True
            VeventList.append(Event())

        elif line.startswith("END:VEVENT") and IsInVevent == True:
            IsInVevent = False
            
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

            startinminutes = VeventList[-1].Start.hour * 60 + VeventList[-1].Start.minute
            endinminutes = VeventList[-1].End.hour * 60 + VeventList[-1].End.minute

            edt.Min = min(startinminutes, edt.Min)
            edt.Max = max(endinminutes, edt.Max)

        elif IsInVevent:
            if line.startswith("DTSTART:"):
                data = line.replace("DTSTART:", "")
                year = int(data[0:4])
                month = int(data[4:6])
                day = int(data[6:8])
                hour = int(data[9:11]) + 2 #Timezone
                minute = int(data[11:13])
                date = datetime.datetime(year, month, day, hour, minute, 0, 0)
                VeventList[-1].Start = date

            if line.startswith("DTEND:"):
                data = line.replace("DTEND:", "")
                year = int(data[0:4])
                month = int(data[4:6])
                day = int(data[6:8])
                hour = int(data[9:11]) + 2 #Timezone
                minute = int(data[11:13])
                date = datetime.datetime(year, month, day, hour, minute, 0, 0)
                VeventList[-1].End = date

            if line.startswith("SUMMARY:"):
                VeventList[-1].Name = line.replace("SUMMARY:", "")

            if line.startswith("LOCATION:"):
                VeventList[-1].Location = line.replace("LOCATION:", "")

            if line.startswith("DESCRIPTION:"):
                data = line.replace("DESCRIPTION:", "").split('\\n')
                VeventList[-1].ID = data[2]
                VeventList[-1].Professor = data[3]
           

        
    return edt
        
def GetNextMatiere(edt, config):
    weekday = now.weekday()
    minutetime = now.hour*60 + now.minute
    if weekday == 5:
        return 'Bon week-end !'
    elif weekday == 6:
        weekday = -1
    
    smallestDelta = (None, 15000)
    for matiere in edt.Lundi + edt.Mardi + edt.Mercredi + edt.Jeudi + edt.Vendredi:
        minutestart = matiere.Start.hour * 60 + matiere.Start.minute
        delta = minutestart - minutetime + 24*60*(matiere.Start.weekday() - weekday)

        if delta >= 0 and delta < smallestDelta[1]:
            smallestDelta = (matiere, delta)

    name = ""
    if smallestDelta[0].ID != None:
        name = smallestDelta[0].ID.split('_')[0][3:]
    else:
        name = smallestDelta[0].Name
    if name in config.Name_Dictionary:
        name = config.Name_Dictionary[name]
    
    if smallestDelta[0].Location != "":
        return "Prochain cours: " + name + " en salle " + smallestDelta[0].Location.replace(' (V)', '') + " à " + str(smallestDelta[0].Start.hour).zfill(2) + ":" + str(smallestDelta[0].Start.minute).zfill(2) + "."
    else:
        return "Prochain cours: " + name + " à " + str(smallestDelta[0].Start.hour).zfill(2) + ":" + str(smallestDelta[0].Start.minute).zfill(2) + "."

def DrawEDT(edt, config):
    img = Image.new('RGB', (config.width, config.height), config.background_color)
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

        draw.text((round(config.width/5)*day + round(config.width/10), round(config.height/72)), text, anchor='mt', fill=(0, 0, 0), font=ImageFont.truetype("arial.ttf", round(config.height/72*2)))

        #MatiereRectangle
        for matiere in matierelist:
            name = ""
            if matiere.ID != None:
                name = matiere.ID.split('_')[0][3:]
            else:
                name = matiere.Name

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
            draw.text((round(config.width/5)*(day+1)-5, matiereBottomCoord - round(config.height/(60+5))), " ".join(matiere.Professor.split(' ')[0:-1]), anchor='rm', fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/60)))

            #StartText
            draw.text((round(config.width/5)*day + round(config.width/10), matiereTopCoord + round(config.height/(44+5))), str(matiere.Start.hour).zfill(2) + ":" + str(matiere.Start.minute).zfill(2), anchor='mm', fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/44)))

            #EndText
            draw.text((round(config.width/5)*day + round(config.width/10), matiereBottomCoord - round(config.height/(44+5))), str(matiere.End.hour).zfill(2) + ":" + str(matiere.End.minute).zfill(2), anchor='mm', fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/44)))

            #MainText
            if name in config.Name_Dictionary:
                name = config.Name_Dictionary[name]
            type = matiere.ID.split('_')[3]

            title = type + " " + name + "\n" + matiere.Location.replace(' (V)', '') if matiere.Location != '' else type + " " + name


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

def Log(message):
    UpdateTime()
    print('{' + str(now.time()) + '}   ' + message)


@client.event
async def on_ready():
    global now

    Log("Esibot est en ligne.")

    Loop.start()


@tasks.loop(minutes=30)
async def Loop():
    UpdateTime()

    if now.hour >= 7 or now.hour <= 22:
        Log("Mise à jour en cours...")
        configsError = []
        for config in configs.ConfigList:
            try:
                UpdateTime()
                edt = ParseEDT(DownloadEDT(config.edt_id))
                edtIMG = DrawEDT(edt, config)
                edtIMG.seek(0)
                await DeleteOldEDT(config)
                await client.get_channel(config.channel_id).send(file=discord.File(edtIMG, filename='EDT.png'), content=config.name + '\nDernière mise à jour: ' + now.strftime("%d/%m/%Y %H:%M:%S") + "\n\n" + GetNextMatiere(edt, config))
                Log(config.name + " mis à jour.")
            except Exception as e:
                Log('Erreur : ' + str(e))
                Log("Nouvelle tentative dans quelques secondes.")
                configsError.append(config)

        if len(configsError) > 0:
            for config in configsError:
                Log("Nouvelle tentative pour " + config.name + ".")
                try:
                    UpdateTime()
                    edt = ParseEDT(DownloadEDT(config.edt_id))
                    edtIMG = DrawEDT(edt, config)
                    edtIMG.seek(0)
                    await DeleteOldEDT(config)
                    await client.get_channel(config.channel_id).send(file=discord.File(edtIMG, filename='EDT.png'), content=config.name + '\nDernière mise à jour: ' + now.strftime("%d/%m/%Y %H:%M:%S") + "\n\n" + GetNextMatiere(edt, config))
                    Log(config.name + " mis à jour.")
                except Exception as e:
                    Log('Erreur : ' + str(e))
                    Log("Abandon de la configuration. Nouvelle tentative lors de la prochaine mise à jour.")

        Log("Mise à jour terminée.")



client.run(BOT_TOKEN)





       
