import requests
import re
from bs4 import BeautifulSoup as bs4

cookie = 'sb=t1caZRvSiIeoUnJz450G6-w7; datr=t1caZSaR3eRejBBgdR_CPedT; wd=1366x689; c_user=100010450276658; xs=36%3AdHR0Dpop7CbadQ%3A2%3A1700194724%3A-1%3A12205; fr=1uRoEkRhU3WhiBMvw.AWWtFzYshhprn_TU-8inyf0eLWA.BlVBkP.-r.AAA.0.0.BlVumn.AWU2Uj8Tln4; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1700194881571%2C%22v%22%3A1%7D'

def write_file(filename, data):
    folder_path = 'demo/'

    file = open(folder_path + filename, 'w', encoding='utf-8')
    file.write(str(data))
    file.close()
    print('selesai menulis file %s' % filename)

def open_file(filename):
    file = open('data/' + filename).read()
    return str(file)

def get_chat_comunity(cookie, id_comunity):
    host = 'https://mbasic.facebook.com'

    with requests.Session() as r:
        # req = r.get(host + '/' + '/messages/read/?tid=cid.g.' + str(id_comunity), cookies={'cookie': cookie})
        # res = bs4(req.text, 'html.parser')

        chats_data = {'chats': []}

        req = open_file('test.html')
        res = bs4(req, 'html.parser')

        send_url = res.find('form', action = re.compile('\/messages\/send\/'))['action']
        see_older = res.find('div', id = 'see_older')
        
        chat = see_older.find_next('div')
        for i in chat.contents:
            profile = i.find('a', href = re.compile('^\/([a-zA-Z0-9_.-]+|profile\.php)\?'))
            if profile is None:
                continue
            data = {'name':None,'username':None, 'message':[], 'file':[],'stiker':[],'time':None}
            data['name'] = profile.text

            if 'profile.php' not in profile['href']:
                data['username'] = re.match('^\/([a-zA-Z0-9_.-]+)\?',profile['href']).group(1)

            contents = profile.find_previous('div')

            for content in contents.findAll('img', src = re.compile(''), class_ = True, alt = True):
                stiker_url = content['src']
                stiker_name = content['alt']
                stiker = {'stiker_name':stiker_name, 'stiker_url':stiker_url}
                data['stiker'].append(stiker)

            for br in contents.findAll('br'):
                br.replace_with('\n')
            
            for y in contents.findAll('span', attrs = {'aria-hidden':False, 'class':False}):
                if len(y.text) == 0: continue
                data['message'].append(y.text)

            waktu = i.find('abbr')
            data['time'] = waktu.text

            chats_data['chats'].append(data)
        
        print(chats_data)

get_chat_comunity(cookie=cookie, id_comunity='6308243352596238')