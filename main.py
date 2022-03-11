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

#Token du bot pour se connecter à Discord (variable secrète)
BOT_TOKEN = os.environ['BOT_TOKEN']


#L'heure ne doit pas changer entre le début et la fin d'une mise à jour, donc elle est stockée temporairement dans la variable now
now = None

#Le client permet au bot d'intéragir avec Discord
client = discord.Client()


#Sauvegarde la date et l'heure actuelle dans 'now'
def update_time():
    global now
    now = datetime.datetime.now(pytz.timezone('Europe/Paris'))

    #Décommenter la ligne ci-dessous pour retarder 'now' de 7 jours. Pour debugger.
    #now = now - datetime.timedelta(7)


#Retourne la date du lundi et du vendredi de la semaine à afficher
def get_monday_and_friday_dates():
    monday = now - datetime.timedelta(now.weekday())
    friday = monday + datetime.timedelta(4)

    if now.weekday() > 4: #Si c'est le week-end, prendre les dates de la semaine suivante
        monday += datetime.timedelta(7)
        friday += datetime.timedelta(7)

    return (monday, friday)


#Retourne les deux années de l'année scolaire en cours
def get_school_year():
    first = now.year
    if now.month < 7: #Si on est avant juillet, on est dans la 2ème partie de l'année scolaire donc il faut enlever 1 année.
        first -= 1

    second = first+1

    return(first, second)


#Télécharge l'emploi du temps correspondant à l'id fournit
def download_edt(id):
    monday = get_monday_and_friday_dates()[0]
    friday = get_monday_and_friday_dates()[1]

    http = urllib3.PoolManager()
    headers = urllib3.util.make_headers(basic_auth=AGALAN_USERNAME + ":" + AGALAN_PASSWORD)

    base_url = "https://edt.grenoble-inp.fr/directCal/" + str(get_school_year()[0]) + "-" + str(get_school_year()[1]) + "/etudiant/esisar?"
    parameters = {'resources':str(id), 'startDay':str(monday.day).zfill(2), 'startMonth':str(monday.month).zfill(2), 'startYear':str(monday.year), 'endDay':str(friday.day).zfill(2), 'endMonth':str(friday.month).zfill(2), 'endYear':str(friday.year)}

    for param in parameters.keys():
        base_url += param + '=' + parameters[param] + '&'
    
    url = base_url[:-1] #Supprimer le dernier &

    r = http.request('GET', url, headers=headers)
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
        

#Crée l'EDT à partir des informations téléchargées
def ParseEDT(downloaded_edt):
    edt = EDT()
    index = 0
    lines = downloaded_edt.splitlines() #Sépare chaque ligne du fichier
    vevent_list = [] #Liste des évènements (rempli au fur et à mesure de la lecture des données)
    
    is_in_vevent = False
    for line in lines: #Pour chaque ligne du fichier
        if line.startswith("BEGIN:VEVENT") and is_in_vevent == False: #Si c'est un début d'évènement et qu'on n'est pas déjà dans un évènement
            is_in_vevent = True
            vevent_list.append(Event()) #Ajouter un nouvel évènement vide dans la liste

        elif is_in_vevent: #Si on est dans un événement
            if line.startswith("DTSTART:"): #Si la ligne indique l'heure de début de l'évènement
                #Format des données : DTSTART:yyyymmddThhmm
                data = line.replace("DTSTART:", "")
                year = int(data[0:4])
                month = int(data[4:6])
                day = int(data[6:8])
                hour = int(data[9:11]) + int(now.utcoffset().total_seconds()/3600) #Prend en compte le décalage horaire
                minute = int(data[11:13])
                date = datetime.datetime(year, month, day, hour, minute, 0, 0)
                vevent_list[-1].Start = date #Modifie la date de début du dernier évènement ajouté (donc celui qui est en train d'être lu)

            elif line.startswith("DTEND:"): #Si la ligne indique l'heure de fin de l'évènement
                #Format des données : DTEND:yyyymmddThhmm
                data = line.replace("DTEND:", "")
                year = int(data[0:4])
                month = int(data[4:6])
                day = int(data[6:8])
                hour = int(data[9:11]) + int(now.utcoffset().total_seconds()/3600)
                minute = int(data[11:13])
                date = datetime.datetime(year, month, day, hour, minute, 0, 0)
                vevent_list[-1].End = date

            elif line.startswith("SUMMARY:"): #Si la ligne indique le nom de l'évènement (nom de la matière)
                vevent_list[-1].Name = line.replace("SUMMARY:", "")

            elif line.startswith("LOCATION:"): #Si la ligne indique le lieu de l'évènement (salle)
                vevent_list[-1].Location = line.replace("LOCATION:", "")

            elif line.startswith("DESCRIPTION:"): #La description contient (entre autre) l'ID de la matière et le nom du professeur
                #Exemple de description : \n\n1AMMA122_2021_S2_TD_G1\nTRAN MINH Frederic\n(Exporté le:0
                data = line.replace("DESCRIPTION:", "").split(r'\n') #Enlève DESCRIPTION: et sépare à chaque \n
                vevent_list[-1].ID = data[2]
                if not(data[3].startswith('(Exporté')): #Certaines matières ne donnent pas le nom du professeur
                    vevent_list[-1].Professor = data[3]

            elif line.startswith("END:VEVENT"): #Si la ligne indique la fin d'un évènement
                is_in_vevent = False
            
                #Ajoute à l'EDT la matière qui vient d'être lue (donc en dernière position de vevent_list)
                matiere = vevent_list[-1]
                weekday = matiere.Start.weekday()
                if weekday == 0:
                    edt.Lundi.append(matiere)
                elif weekday == 1:
                    edt.Mardi.append(matiere)
                elif weekday == 2:
                    edt.Mercredi.append(matiere)
                elif weekday == 3:
                    edt.Jeudi.append(matiere)
                elif weekday == 4:
                    edt.Vendredi.append(matiere)

                #Modifie si besoin les heures minimales et maximales de l'EDT
                start_in_minutes = matiere.Start.hour * 60 + matiere.Start.minute #Heure du début de la matière en minutes
                end_in_minutes = matiere.End.hour * 60 + matiere.End.minute #Heure de la fin de la matière en minutes
                edt.Min = min(start_in_minutes, edt.Min)
                edt.Max = max(end_in_minutes, edt.Max)

    return edt
        
#Obtient la prochaine matière et retourne le texte "Prochain cours : ..." à envoyer sur Discord
def GetNextMatiere(edt, config):
    weekday = now.weekday()
    current_time_in_minutes = now.hour*60 + now.minute

    #Pour que les calculs fonctionnent le week-end, il faut modifier weekday
    if weekday == 5:
        weekday = -2
    elif weekday == 6:
        weekday = -1

    smallestDelta = (None, 15000) #Contient la matière la plus proche et le temps en minute entre maintenant et le début de cette matière.
    for matiere in edt.Lundi + edt.Mardi + edt.Mercredi + edt.Jeudi + edt.Vendredi:
        start_in_minutes = matiere.Start.hour * 60 + matiere.Start.minute
        delta = start_in_minutes - current_time_in_minutes + 24*60*(matiere.Start.weekday() - weekday) #Calcule le temps entre maintenant et le début de la matière

        if 0 <= delta < smallestDelta[1]: #Si delta est positif (la matière n'a pas encore commencé) et qu'il est inférieur au delta minimal
            smallestDelta = (matiere, delta)

    if smallestDelta[0] != None: #smallestDelta[0] = None si il n'y a aucun cours de la semaine (vacances)
        name = ""
        if smallestDelta[0].Name != None: #Si la matière a un nom (certaines exceptionnelles n'en ont pas)
            name = smallestDelta[0].Name
        else: #Si elle n'a pas de nom, on peut le retrouver dans l'identifiant de la matière
            name = smallestDelta[0].ID.split('_')[0][3:].strip()

        if name in config.Name_Dictionary: #Si la matière a un nom de remplacement
            name = config.Name_Dictionary[name] #Remplacer le nom

        if  len(smallestDelta[0].ID.split('_')) == 5: #Si le format de l'id est normal (du type 1AMMA122_2021_S2_TD_G1)
            type = smallestDelta[0].ID.split('_')[3]
            name = type + " " + name
        
        if smallestDelta[0].Location != "": #Si la salle est indiquée
            return "Prochain cours: " + name + " en salle " + smallestDelta[0].Location.replace(' (V)', '').replace('\\,', ' / ') + " à " + str(smallestDelta[0].Start.hour).zfill(2) + ":" + str(smallestDelta[0].Start.minute).zfill(2) + "."
        else: #Sinon (comme en sport)
            return "Prochain cours: " + name + " à " + str(smallestDelta[0].Start.hour).zfill(2) + ":" + str(smallestDelta[0].Start.minute).zfill(2) + "."
    else:
      return ''

#Crée l'image de l'emploi du temps
def DrawEDT(edt, config):
    img = Image.new('RGB', (config.width, config.height), config.background_color)

    if config.background_image != None: #Si il y a une image à afficher en arrière-plan
      backgroundimage = None
      if config.background_image.startswith("http"): #Si c'est une URL, récupérer l'image sur Internet
        http = urllib3.PoolManager()
        resp = http.request('GET', config.background_image).data
        backgroundimage = Image.open(io.BytesIO(resp))
      else: #Sinon elle est juste stockée dans un fichier
        backgroundimage = Image.open(config.background_image)

      #Calcule les proportions de l'image pour qu'elle remplisse tout l'EDT sans être déformée
      widthratio = config.width / backgroundimage.size[0]
      heightratio = config.height / backgroundimage.size[1]
      bgwidth = int(backgroundimage.size[0] * max(widthratio,heightratio))
      bgheight= int(backgroundimage.size[1] * max(widthratio,heightratio))
      backgroundimage = backgroundimage.resize((bgwidth,bgheight))
      img.paste(backgroundimage,(0,0))



    draw = ImageDraw.Draw(img)

    header_height =  round(config.height/21.5) #Hauteur de l'entête de l'EDT (qui contient les jours de la semaine)
    draw.rectangle((0, 0, config.width, header_height), fill=config.header_color)

    body_height = config.height - header_height
    max_time_in_minutes = edt.Max - edt.Min
    minutes_to_pixels_ratio = body_height / max_time_in_minutes

    #Affichage des jours
    timeline_drawed = False
    for day in range(5):
        date = get_monday_and_friday_dates()[0] + datetime.timedelta(day)
        date_string = str(date.day).zfill(2) + "/" + str(date.month).zfill(2) + "/" + str(date.year)

        text = ""
        matiere_list = []

        if day == 0:
            text = "Lundi "
            matiere_list = edt.Lundi
        elif day == 1:
            text = "Mardi "
            matiere_list = edt.Mardi
        elif day == 2:
            text = "Mercredi "
            matiere_list = edt.Mercredi
        elif day == 3:
            text = "Jeudi "
            matiere_list = edt.Jeudi
        elif day == 4:
            text = "Vendredi "
            matiere_list = edt.Vendredi

        text += date_string

        draw.text((round(config.width/5)*day + round(config.width/10), round(config.height/72)), text, anchor='mt', fill=config.headertext_color, font=ImageFont.truetype("arial.ttf", round(config.height/72*2)))

        #Affichage des matières
        for matiere in matiere_list:
            name = ""
            if matiere.Name != None:
                name = matiere.Name
            else: #Les matières exceptionnelles peuvent ne pas avoir de nom, dans ce cas on peut le retrouver dans l'ID de la matière
                name = matiere.ID.split('_')[0][3:].strip()

            color = "#ADADAD"
            if name in config.Color_Dictionary: #Si la matière a une couleur spécifique dans la configuration, l'appliquer
                color = config.Color_Dictionary[name]

            #Dessin du rectangle de la matière
            top_coords = (header_height + (matiere.Start.hour*60 + matiere.Start.minute - edt.Min) * minutes_to_pixels_ratio)
            bottom_coords = (header_height + (matiere.End.hour*60 + matiere.End.minute - edt.Min) * minutes_to_pixels_ratio)
            draw.rectangle(((config.width/5)*day, top_coords, (config.width/5)*(day+1), bottom_coords), fill=color)
            draw.line(((config.width/5)*day, top_coords, (config.width/5)*(day+1), top_coords), fill=(0,0,0), width=3)
            draw.line(((config.width/5)*day, bottom_coords, (config.width/5)*(day+1), bottom_coords), fill=(0,0,0), width=3)

            #TimeLine
            is_matiere_now = False
            if now.weekday() == day:
                current_minute_time = now.hour*60 + now.minute
                if (matiere.Start.hour*60 + matiere.Start.minute) < current_minute_time < (matiere.End.hour*60 + matiere.End.minute): #Si la matière est en cours
                    is_matiere_now = True
                    timeline_coord = header_height + (current_minute_time - edt.Min)*minutes_to_pixels_ratio
                    draw.line(((config.width/5)*day, timeline_coord, (config.width/5)*(day+1), timeline_coord), fill=config.timeline_color, width=3) #Tracer la timeline
                    timeline_drawed = True


            #Nom du professeur
            if matiere.Professor != None:
              draw.text((round(config.width/5)*(day+1)-5, bottom_coords - round(config.height/(60+5))), " ".join(matiere.Professor.split(' ')[0:-1]), anchor='rm', fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/60)))


            hour_anchor = 'mm'
            hour_x = round(config.width/5)*day + round(config.width/10)
            hour_topbottom_margin = round(config.height/(44+5))

            if abs(top_coords-bottom_coords) < 125: #Si la matière est trop courte (ex tiers-temps), modifier la position du texte (sinon le texte se superpose)
                hour_anchor = 'lm'
                hour_x = round(config.width/5)*day + 10
                hour_topbottom_margin = round(config.height/(44+10))

            #Heure de début
            draw.text((hour_x, top_coords + hour_topbottom_margin), str(matiere.Start.hour).zfill(2) + ":" + str(matiere.Start.minute).zfill(2), anchor=hour_anchor, fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/44)))

            #Heure de fin
            draw.text((hour_x, bottom_coords - hour_topbottom_margin), str(matiere.End.hour).zfill(2) + ":" + str(matiere.End.minute).zfill(2), anchor=hour_anchor, fill=config.text_color, font=ImageFont.truetype("arial.ttf", round(config.height/44)))

            #Titre
            if name in config.Name_Dictionary: #Si la matière a un nom customisé dans la configuration, l'appliquer
                name = config.Name_Dictionary[name]
                
            title = ""
            if len(matiere.ID.split('_')) == 5: #Si le format de l'identifiant de la matière est classique
              type = matiere.ID.split('_')[3] #Le type est en 4ème position (CM, TD, TP...)
              if matiere.Location != '': #Si la matière a une salle précisée
                  title = type + " " + name + "\n" + matiere.Location.replace(' (V)', '').replace('\\,', ' / ')
              else: #Sinon (ex: Sport)
                  title = type + " " + name
            else: #Si l'ID n'est pas classique, on ne peut pas connaître le type de cours
              if matiere.Location != '': #Si la matière a une salle précisée
                  title = name + "\n" + matiere.Location.replace(' (V)', '').replace('\\,', ' / ')
              else:
                  title = name

            if is_matiere_now: #Si la matière est en cours, mettre le titre en gras
                draw.text((round(config.width/5)*day + round(config.width/10), (top_coords + bottom_coords)/2), title, anchor='mm', fill=config.text_color, align='center', font=ImageFont.truetype("arialbd.ttf", round(config.height/40)))
            else:
                draw.text((round(config.width/5)*day + round(config.width/10), (top_coords + bottom_coords)/2), title, anchor='mm', fill=config.text_color, align='center', font=ImageFont.truetype("arial.ttf", round(config.height/40)))
    
            #TimeLine (part2)
            if now.weekday() == day and not timeline_drawed: #Si la timeline n'a pas déjà été tracée sur une matière
                current_minute_time = now.hour*60 + now.minute
                if current_minute_time >= edt.Min: #Sans cette condition, la timeline est tracée par dessus le titre des jours. A tester.
                    timeline_coord = header_height + (current_minute_time - edt.Min)*minutes_to_pixels_ratio
                    draw.line(((config.width/5)*day, timeline_coord, (config.width/5)*(day+1), timeline_coord), fill=config.timeline_color, width=3)

                #timeline_drawed = True         #Il faut logiquement le rajouter (même si ça marche sans). A tester plus tard.

        #Trace une ligne pour séparer l'entête et le contenu
        draw.line((0, header_height, config.width, header_height), fill=(0,0,0), width=3)

        #Trace une ligne verticale entre les jours
        draw.line(((config.width/5)*day, 0, (config.width/5)*day, config.height), fill=(0, 0, 0), width=3)

        
    arr = io.BytesIO()
    img.save(arr, format='PNG') #Stocke les données de l'image dans arr, pour pouvoir l'envoyer sur Discord.

    return arr

#Supprime le dernier EDT
async def DeleteOldEDT(config):
    async for message in client.get_channel(config.channel_id).history(): #Pour chaque message du salon sur lequel l'EDT est posté
        if message.author == client.user: #Si le message a été envoyé par le bot
            if message.content.startswith(config.name): #Si le message commence par le nom de la configuration
                await message.delete() #Supprimer le message

async def Log(message, send_to_discord=True):
    update_time()
    print('{' + str(now.time()) + '}   ' + message)
    if send_to_discord:
        await client.get_channel(895410453335928863).send(content= '> ' + message)


@client.event
async def on_ready():
    update_time()
    
    await Log("Esibot est en ligne.")

    Loop.start()

interval_update = False #Tout le code lié à interval_update permet de s'assurer que le délai entre deux itérations est actualisé (la fct change_interval a un comportement un peu ambigu)
@tasks.loop(minutes=45)
async def Loop():
    global interval_update

    update_time()

    if not interval_update: 
        await UpdateLoopInterval()

        min_hour = 8 if now.weekday() >= 5 else 7
    
        if min_hour <= now.hour <= 22: #Si il est entre 7h (ou 8h en WE) et 22h
            await Log("Mise à jour en cours...")
            configsError = []
            for config in configs.ConfigList: #Pour chaque configuration
                await Log("• " + config.name)
                try: #Essayer de faire la mise à jour de l'EDT (il peut y avoir des erreurs aléatoires et imprévisibles mais ne doit pas planter)
                    update_time()
                    await Log("    Téléchargement et analyse de l'EDT...")
                    edt = ParseEDT(download_edt(config.edt_id))
                    await Log("    Création de l'image...")
                    edtIMG = DrawEDT(edt, config)
                    edtIMG.seek(0)
                    await Log("    Envoi de l'EDT sur Discord...")
                    await DeleteOldEDT(config)
                    await client.get_channel(config.channel_id).send(file=discord.File(edtIMG, filename='EDT.png'), content=config.name + '\nDernière mise à jour: ' + now.strftime("%d/%m/%Y %H:%M:%S") + "\n\n" + GetNextMatiere(edt, config))
                    await Log('    ' + config.name + " a été mis à jour.")
                except Exception as e: #Si il y a eu une erreur (l'actualisation n'a pas aboutie)
                    await Log('    Erreur : ' + str(e))
                    await Log('    Ligne ' + str(sys.exc_info()[2].tb_lineno))
                    await Log("    Nouvelle tentative dans quelques secondes.")
                    configsError.append(config) #Ajouter la configuration à la liste des configurations qui ont échouées

            if len(configsError) > 0: #Si il y a eu des erreurs
                time.sleep(10) #Attendre 10 secondes (certaines erreurs sont provoquées par un problème de réseau qui se résoud tout seul après quelques secondes)

                #Recommencer la mise à jour des configurations qui ont échouées
                for config in configsError:
                    await Log("• Nouvelle tentative pour " + config.name)
                    try:
                        update_time()
                        await Log("    Téléchargement et analyse de l'EDT...")
                        edt = ParseEDT(download_edt(config.edt_id))
                        await Log("    Création de l'image...")
                        edtIMG = DrawEDT(edt, config)
                        edtIMG.seek(0)
                        await Log("    Envoi de l'EDT sur Discord...")
                        await DeleteOldEDT(config)
                        await client.get_channel(config.channel_id).send(file=discord.File(edtIMG, filename='EDT.png'), content=config.name + '\nDernière mise à jour: ' + now.strftime("%d/%m/%Y %H:%M:%S") + "\n\n" + GetNextMatiere(edt, config))
                        await Log('    ' + config.name + " a été mis à jour.")
                    except Exception as e:
                        await Log('<@!420914917420433408>') #Si il y a encore une erreur, me mentionner sur Discord
                        await Log('    Erreur : ' + str(e))
                        await Log('    Ligne ' + str(sys.exc_info()[2].tb_lineno))
                        await Log("    Abandon de la configuration. Nouvelle tentative lors de la prochaine mise à jour.")

            await Log("Mise à jour terminée.\n")

        #Redémarrer la boucle et la faire 'tourner dans le vide' une fois, pour s'assurer que le délai fixé sera pris en compte
        interval_update = True
        Loop.restart()
    else:
        #Une fois que la boucle a fait une itération pour rien, reprendre un fonctionnement normal
        interval_update = False

async def UpdateLoopInterval():
    #Les délais et horaires choisis permettent au bot d'utiliser tout le quota gratuit disponible par mois sans le dépasser sur Heroku

    if now.hour > 22: #Si il est plus de 22h

        #Calcule la date et l'heure de la prochaine mise à jour (le lendemain)
        tomorrow_date = now + datetime.timedelta(days=1)
        tomorrow_date = tomorrow_date.replace(minute=0, second=0, microsecond=0)
        if tomorrow_date.weekday() <= 4:
            tomorrow_date = tomorrow_date.replace(hour=7)
        else:
            tomorrow_date = tomorrow_date.replace(hour=8)

        next_loop_in_seconds = (tomorrow_date - now).seconds #Calcule le délai nécessaire pour que la prochaine itération se fasse le lendemain à 7h ou 8h (selon si c'est le week-end)
        Loop.change_interval(seconds=next_loop_in_seconds) #Applique ce délai
        await Log(f'Mise à jour suivante dans : {str(tomorrow_date - now)}.\n')

    elif now.hour < (7 if now.weekday() <= 4 else 8): #Si il est moins de 7h ou 8h (selon si c'est le week-end)
        start_date = now
        start_date = start_date.replace(minute=0, second=0, microsecond=0)
        if start_date.weekday() <= 4:
            start_date = start_date.replace(hour=7)
        else:
            start_date = start_date.replace(hour=8)

        next_loop_in_seconds = (start_date - now).seconds #Calcule le délai nécessaire pour que la prochaine itération se fasse à 7h ou 8h
        Loop.change_interval(seconds=next_loop_in_seconds) #Applique ce délai
        await Log(f'Mise à jour suivante dans : {str(start_date - now)}.\n')

    else: #Si il est entre 7h (ou 8h) et 22h
        if now.weekday() <= 4: #Si c'est la semaine, délai de 45 minutes
            Loop.change_interval(minutes=45)
            await Log(f'Intervalle de mise à jour fixé à 45 minutes.')
        else:
            Loop.change_interval(hours=2) #Si c'est le week-end, délai de 2 heures
            await Log(f'Intervalle de mise à jour fixé à 2 heures.')



client.run(BOT_TOKEN) #Lance le bot