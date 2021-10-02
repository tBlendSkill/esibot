class config:
    edt_id = None
    channel_id = None
    replace_by_id = {}
    name = None

    height = None
    width = None
    background_color = None
    header_color = None
    text_color = None
    timeline_color = None

    Name_Dictionary = None
    Color_Dictionary = None
    


_1ATP1TEST = config()
_1ATP1TEST.edt_id = 5957
_1ATP1TEST.channel_id = 883450350345015410
_1ATP1TEST.name = "EDT TP1"

_1ATP1TEST.height = 1080
_1ATP1TEST.width = 1920
_1ATP1TEST.background_color = "white"
_1ATP1TEST.header_color = "white"
_1ATP1TEST.text_color = "black"
_1ATP1TEST.timeline_color = "red"

_1ATP1TEST.Name_Dictionary = {'MA121': 'Maths (MA121)',
                              'PH101': 'Physique (PH101)',
                              'EE121': 'Électronique (EE121)',
                              'AC101': 'Automatique (AC101)',
                              'CS101': 'Informatique (CS101)',
                              'SP101': 'Sport (Badminton)',
                              'LA101': 'Anglais (LA101)'}
_1ATP1TEST.Color_Dictionary = {'MA121': '#FFC551',
                               'PH101': '#FFA775',
                               'EE121': '#FFFC6D',
                               'AC101': '#A8FF8C',
                               'CS101': '#75D7FF',
                               'SP101': '#606BFF',
                               'LA101': '#E48CFF'}

ConfigList = [_1ATP1TEST]