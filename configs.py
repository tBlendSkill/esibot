class config:
    edt_id = None
    channel_id = None
    replace_by_id = {}
    name = None

    height = None
    width = None
    background_color = None
    background_image = None
    header_color = None
    headertext_color = None
    text_color = None
    timeline_color = None

    Name_Dictionary = None
    Color_Dictionary = None
    

_1A_Name_Dictionary = {'MA121': 'Maths (MA121)',
                      'DS MA121 - F. Tran-Minh': "DS Maths :'(",
                      'PH101': 'Physique (PH101)',
                      'PH141': 'Physique (PH141)',
                      'EE121': 'Électronique (EE121)',
                      'DS EE121 - L. Guilloton' : 'DS Électronique',
                      'AC101': 'Automatique (AC101)',
                      'CS101': 'Informatique (CS101)',
                      'SP101': 'Sport (Escalade)',
                      'LA101': 'Anglais (LA101)',
                      'IN101': 'Intégration (IN101)',
                      'PX111-Auto':'PX111 Automatique',
                      'PX111-Elec': 'PX111 Électronique',
                      'PX111-Info':'PX111 Informatique'}

_1A_Color_Dictionary = {'MA121': '#FFC551',
                        'DS MA121 - F. Tran-Minh': '#FFC551',
                        'PH101': '#FFA775',
                        'PH141': '#FFA775',
                        'EE121': '#FFFC6D',
                        'DS EE121 - L. Guilloton' : '#FFFC6D',
                        'AC101': '#A8FF8C',
                        'CS101': '#75D7FF',
                        'SP101': '#606BFF',
                        'LA101': '#E48CFF',
                        'IN101': '#42FFB0',
                        'PX111-Auto':'#A8FF8C',
                        'PX111-Elec':'#FFFC6D',
                        'PX111-Info':'#75D7FF'}


_1ATP1TEST = config()
_1ATP1TEST.edt_id = 5957
_1ATP1TEST.channel_id = 883450350345015410
_1ATP1TEST.name = "EDT TP1"
_1ATP1TEST.height = 1080
_1ATP1TEST.width = 1920
_1ATP1TEST.background_color = "#353535"
_1ATP1TEST.background_image = 'https://cutewallpaper.org/21/background-hd-black/59-Dark-Desktop-Background-on-WallpaperSafari.jpg'
_1ATP1TEST.header_color = "#353535"
_1ATP1TEST.headertext_color = 'white'
_1ATP1TEST.text_color = "black"
_1ATP1TEST.timeline_color = "red"
_1ATP1TEST.Name_Dictionary = _1A_Name_Dictionary
_1ATP1TEST.Color_Dictionary = _1A_Color_Dictionary

_1ATP1 = config()
_1ATP1.edt_id = 5957
_1ATP1.channel_id = 887383777716895764
_1ATP1.name = "EDT TP1"
_1ATP1.height = 1080
_1ATP1.width = 1920
_1ATP1.background_color = "#353535"
_1ATP1.header_color = "#353535"
_1ATP1.headertext_color = 'white'
_1ATP1.text_color = "black"
_1ATP1.timeline_color = "red"
_1ATP1.Name_Dictionary = _1A_Name_Dictionary
_1ATP1.Color_Dictionary = _1A_Color_Dictionary

_1ATP2 = config()
_1ATP2.edt_id = 5956
_1ATP2.channel_id = 887390067159629914
_1ATP2.name = "EDT TP2"
_1ATP2.height = 1080
_1ATP2.width = 1920
_1ATP2.background_color = "#353535"
_1ATP2.header_color = "#353535"
_1ATP2.headertext_color = 'white'
_1ATP2.text_color = "black"
_1ATP2.timeline_color = "red"
_1ATP2.Name_Dictionary = _1A_Name_Dictionary
_1ATP2.Color_Dictionary = _1A_Color_Dictionary

_1ATP3 = config()
_1ATP3.edt_id = 5941
_1ATP3.channel_id = 887390086344368158
_1ATP3.name = "EDT TP3"
_1ATP3.height = 1080
_1ATP3.width = 1920
_1ATP3.background_color = "#353535"
_1ATP3.header_color = "#353535"
_1ATP3.headertext_color = 'white'
_1ATP3.text_color = "black"
_1ATP3.timeline_color = "red"
_1ATP3.Name_Dictionary = _1A_Name_Dictionary
_1ATP3.Color_Dictionary = _1A_Color_Dictionary

_1ATP4 = config()
_1ATP4.edt_id = 5953
_1ATP4.channel_id = 887390195274621028
_1ATP4.name = "EDT TP4"
_1ATP4.height = 1080
_1ATP4.width = 1920
_1ATP4.background_color = "#353535"
_1ATP4.header_color = "#353535"
_1ATP4.headertext_color = 'white'
_1ATP4.text_color = "black"
_1ATP4.timeline_color = "red"
_1ATP4.Name_Dictionary = _1A_Name_Dictionary
_1ATP4.Color_Dictionary = _1A_Color_Dictionary

#ConfigList = [_1ATP1TEST, _1ATP1, _1ATP2, _1ATP3, _1ATP4]
ConfigList = [_1ATP1TEST]
