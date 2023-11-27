import requests
import re
import os
import random
import math
import string
import codecs

from datetime import datetime
from urllib.parse import urlparse
from requests_toolbelt import MultipartEncoder
from multiprocessing.pool import ThreadPool

from bs4 import BeautifulSoup

from http.cookiejar import CookieJar
from http.cookies import SimpleCookie

from dotenv import load_dotenv

load_dotenv()

class Utils:
    def __init__(self) -> None:
        self.__folder_demo = './demo'

    def write_file(self, filename, data):
        file = open(self.__folder_demo + '/' + filename , 'w', encoding='utf-8')
        file.write(str(data))
        file.close()
        print('Selesai menulis file -> %s' % filename)

    def convert_size(self, size_bytes):
        if size_bytes == 0:
            return "0B"

        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)

        return "%s %s" % (s, size_name[i])
    
    def get_size_file(self, file_path):
        return self.convert_size(os.path.getsize(file_path))
    
    def get_size_file_from_url(self, url):
        return self.convert_size(int(requests.head(url).headers['Content-Length']))

    def search_username_from_url(url):
        cari_username = re.search('^\/profile.php\?id=(\d+)|^\/([a-zA-Z0-9_.-]+)|https:\/\/(?:facebook.com|.*?\.facebook\.com)\/([a-zA-Z0-9_.-]+)\?',url).groups()
        result = next((x for x in cari_username if x is not None), None)

        return result
    
    def upload_photo(self, requests_session, upload_url, input_file_name, file_path, fields = {}):
        max_size = (1000000*4)
        support_file = ['.jpg','.png','.webp','.gif','.tiff','.heif','.jpeg']
        mime = {'.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif', '.tiff': 'image/tiff', '.heif': 'image/heif', '.jpeg': 'image/jpeg'}
        ext = os.path.splitext(file_path)[-1]

        if os.path.getsize(file_path) > max_size: raise Exception('Ukuran file "%s"  terlalu besar, sehingga file tersebut tidak bisa di upload, File harus  berukuran kurang dari %s :)' % (os.path.realpath(file_path), self.convert_size(max_size)))
        if not ext in support_file: raise Exception("Hanya bisa mengupload file dengan extensi \"%s\", tidak bisa mengupload file dengan extensi \"%s\"" % (', '.join([re.sub('^\.','',ext_file) for ext_file in support_file]),ext))

        data = {key:((None,value) if not isinstance(value,tuple) else value) for key,value in fields.items()}
        data[input_file_name] = (os.path.basename(file_path), open(file_path,'rb').read(),mime[ext])

        boundary = '----WebKitFormBoundary' + ''.join(random.sample(string.ascii_letters + string.digits, 16))
        multipart = MultipartEncoder(fields=data,boundary=boundary)
        headers = {"content-type":multipart.content_type}

        submit = requests_session.post(upload_url, data = multipart, headers = headers)

        return submit

class Login(Utils):
    def __init__(self, cookies, free_facebook = False, headers = {}):
        self.__cookies = cookies
        self.free_facebook = free_facebook
        self.__host = ('https://free.facebook.com' if free_facebook else 'https://mbasic.facebook.com')
        self.__session = requests.Session()
        super().__init__()

        self.head = {"Host":("free.facebook.com" if free_facebook else "mbasic.facebook.com"),
        "cache-control":"max-age=0","upgrade-insecure-requests":"1","accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8","accept-encoding":"gzip, deflate","accept-language":"id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,"}

        self.head.update(headers)
        # self.default_head = {'User-Agent': self.head['user-agent']}
        self.__session.headers.update(self.head)

        cookie_dict = self.get_cookie_dict()
        
        # Set Cookie
        for key,value in cookie_dict.items():
            self.__session.cookies[key] = value
        else:
            self.__session.cookies['domain'] = '.facebook.com'
            self.__session.cookies['path'] = '/'

        url = self.__host + '/login.php?next='+self.__host +'/' + (cookie_dict['c_user'] if 'c_user' in cookie_dict.keys() else 'home.php')

        try:
            req = self.__session.get(url, allow_redirects = True)
        except requests.exceptions.TooManyRedirects:
            self.__session.headers.clear()
            self.__session.headers.update(self.default_head)
            req = self.__session.get(url, allow_redirects = True)
        
        if 'checkpoint' in req.url:
            raise Exception('Akun Anda Terkena Checkpoint')
        elif 'login.php' in req.url:
            raise Exception('Cookie Tidak Valid!')
        
        # self.write_file('test.html', req.text);exit()

    def __str__(self):
        return "Facebook Cookie_Login: cookies='%s' free_facebook=%s" % (self.__cookies, self.free_facebook)

    def __repr__(self):
        return "Facebook Cookie_Login: cookies='%s' free_facebook=%s" % (self.__cookies, self.free_facebook)
    
    @property
    def _sessiom(self):
        return self.__session
    
    @property
    def _host(self):
        return self.__host

    def get_cookie_dict(self):
        simple_cook = SimpleCookie()
        simple_cook.load(self.__cookies)
        
        cookie_dict = {}
        if len(simple_cook.items()) != 0:
            for key, value in simple_cook.items():
                cookie_dict[key] = value.value
        else:
            for i in self.__cookies.split('; '):
                cookie_dict = dict(i.split('=', 1))

        return cookie_dict
    
    def get_cookie_str(self):
        return self.__cookies
    
class Chats(Utils):
    def __init__(self, chats_url, requests_session):
        self.__session = requests_session
        self.__host = ('https://'+self.__session.headers['host'] if 'host' in self.__session.headers.keys() else "https://mbasic.facebook.com")

        self.__chats_url = chats_url

        # print(self.__chats_url)

        req = self.__session.get(self.__chats_url)
        self.__res = BeautifulSoup(req.text,'html.parser')
        self.__send_url = self.__res.find('form', action = re.compile('\/messages\/send\/'))
        self.__action_redirect  = self.__res.find('form', action = re.compile('\/messages\/action_redirect'))

        if self.__send_url is not None: self.__send_url = self.__host + self.__send_url['action']
        if self.__action_redirect is not None: self.__action_redirect = self.__host + self.__action_redirect['action']

        self.__data = {}
        self.__chat_info = {}
        self.__data_other = {}

        for i in self.__res.findAll('input'):
            if i.get('name') not in ['search', 'search_source','query', 'like', 'send_photo','unread', 'delete', 'delete_selected', 'archive', 'ignore_messages', 'block_messages', 'message_frx','unarchive','unblock_messages','add_people','leave_conversation', None]:
                self.__data[i.get('name')] = i.get('value')
            else:
                self.__data_other[i.get('name')] = i.get('value')

        self.__chat_info['name'] = self.__res.find('title').text
        self.__chat_info['id'] = None
        self.__chat_info['chat_id'] = (re.search("tid=cid\.(.?)\.((\d+:\d+)|\d+)",requests.utils.unquote(chats_url)).group(2) if 'tid' in chats_url else None)
        self.__chat_info['chat_url'] = chats_url
        self.__chat_info['chat_type'] = ('group' if 'leave_conversation' in self.__data_other else 'user')
        self.__chat_info['blocked'] = 'unblock_messages' in self.__data_other.keys()

        for x in self.__data.keys():
            if re.match('ids\[\d+\]',x):
                self.__chat_info['id'] = self.__data[x]
                break

        self.name = self.__chat_info['name']
        self.id = self.__chat_info['id']
        self.chat_id = self.__chat_info['chat_id']
        self.chat_url = self.__chat_info['chat_url']
        self.chat_type = self.__chat_info['chat_type']
        self.blocked = self.__chat_info['blocked']

        super().__init__()

    @property
    def chat_info(self):
        return self.__chat_info
    
    def __str__(self):
        return "Facebook Chats : name='%s' id=%s chat_id=%s type='%s'" % (self.name, self.id, self.chat_id, self.chat_type)

    def __repr__(self):
        return "Facebook Chats : name='%s' id=%s chat_id=%s type='%s'" % (self.name, self.id, self.chat_id, self.chat_type)

    def __enter__(self):
        return self
    
    def __getitem__(self, item):
     return (self.__chat_info[item] if item in self.__chat_info.keys() else None)

    def __get_messages(self, chat_url):
        data = {'chat':[]}
        req = self.__session.get(chat_url)
        self.__res_get_chat = BeautifulSoup(req.text,'html.parser')
        ah = self.__res_get_chat.find('div', id = 'see_older')

        if ah is None:
          ah = self.__res_get_chat.find('div', id='messageGroup')

        if ah is None: return data

        chat = ah.find_next('div')

        for i in chat.contents:
            profile = i.find('a', href = re.compile('^\/([a-zA-Z0-9_.-]+|profile\.php)\?'))
            if profile is None: continue
            uh = {'name':None,'username':None, 'message':[], 'file':[],'stiker':[],'time':None}
            uh['name'] = profile.text
            if 'profile.php' not in profile['href']: uh['username'] = re.match('^\/([a-zA-Z0-9_.-]+)\?',profile['href']).group(1)
            content = profile.find_previous('div')

            for x in content.findAll('img', src = re.compile(''), class_ = True, alt = True):
                stiker_url = x['src']
                stiker_name = x['alt']
                stiker = {'stiker_name':stiker_name, 'stiker_url':stiker_url}
                uh['stiker'].append(stiker)

            for br in content.findAll('br'):
                br.replace_with('\n')

            for y in content.findAll('span', attrs = {'aria-hidden':False, 'class':False}):
                if len(y.text) == 0: continue
                uh['message'].append(y.text)

            waktu = i.find('abbr')
            uh['time'] = waktu.text
            data['chat'].append(uh)

            for jpg in i.findAll('a', href = re.compile('\/messages\/attachment_preview')):
                link = jpg.find_next('img', src = re.compile('^https:\/\/z-m-scontent(\.fbpn4-1\.fna\.fbcdn\.net|\.fsri(.*?)\.fna\.fbcdn\.net)'))
                if link is None: continue
                content_id = re.search("(\d+_\d+_\d+)",link['src']).group(1)
                preview = self.__host + jpg['href']
                data['chat'][-1]['file'].append({'link':link['src'],'id':content_id, 'preview':preview,'content-type':'image/jpeg'})

            for mp4 in i.findAll('a', href = re.compile('\/video_redirect\/')):
                vidurl = re.search('src=(.*)',requests.utils.unquote(mp4['href'])).group(1)
                vidid = re.search('&id=(\d+)',vidurl).group(1)
                thumb_nail = mp4.find_next('img', src = re.compile('https:\/\/z-m-scontent\.(fbpn\d-\d|fsri\d-\d)\.fna\.fbcdn\.net'))['src']
                data['chat'][-1]['file'].append({'link':vidurl,'id':vidid,'preview':thumb_nail,'content-type':'video/mp4'})

        return data
    
    def get_chat(self, limit = 5, sort = True):
        data = []
        previos_chat = self.__chats_url

        while True:
            get = self.__get_messages(previos_chat)
            data.extend(get['chat'])
            previos_chat = self.__res_get_chat.find('div', id = 'see_older')
            if len(get['chat']) == 0 or previos_chat is None or len(data) >= limit: break
            previos_chat = self.__host + previos_chat.find_next('a')['href']

        if len(data) != 0 and sort: data.reverse()

        return data[0:limit]
    
    def send_text(self, message):
        if self['blocked']: raise Exception('Pesan tidak bisa di kirim karena anda telah memblokir akun "%s"!!!' % (self['name']))
        if self.__send_url is None: raise Exception('Tidak dapat mengirim pesan kepada %s' % (self.name))
        if not re.match('^\S',message): raise Exception('Panjang pesan minimal 1 karakter, dan harus di awali dengan non-white space character!!.')

        message = codecs.decode(codecs.encode(message,'unicode_escape'),'unicode_escape')

        data = self.__data.copy()
        data.update({'body':message})
        res = self.__session.post(self.__send_url, data = data)
        html_res = BeautifulSoup(res.text,'html.parser')

        if html_res.find('a', href = re.compile('\/home\.php\?rand=\d+')):
            err_div = html_res.find('div', id = 'root')
            err_msg = ("Terjadi Kesalahan!" if err_div is None else err_div.find('div', class_ = True).get_text(separator = '\n'))
            raise Exception(err_msg)
        
        return res.ok
    
    def send_image(self, file, message = ''):
        if self['blocked']: raise Exception('Pesan tidak bisa di kirim karena anda telah memblokir akun "%s"!!!' % (self['name']))
        if self.__send_url is None: raise Exception('Tidak dapat mengirim pesan kepada %s' % (self.name))

        message = codecs.decode(codecs.encode(message,'unicode_escape'),'unicode_escape')
        form = self.__res.find('form', action = re.compile('https:\/\/(?:z-upload|upload)\.facebook\.com'))

        if form is None:
            data = self.__data.copy()
            data['send_photo'] = self.__data_other['send_photo']
            post = self.__session.post(self.__send_url, data = data)
            form = BeautifulSoup(post.text,'html.parser').find('form', action = re.compile('https:\/\/(?:z-upload|upload)\.facebook\.com'))

        form_data = {i.get('name'):(None,i.get('value')) for i in form.findAll('input', attrs = {'name':True,'type':'hidden'})}
        form_data['body'] = (None, message)
        
        submit = self.upload_photo(requests_session = self.__session, upload_url = form['action'], input_file_name = 'file1', file_path = file, fields = form_data)

        return submit.ok
    
    def send_like_stiker(self):
        if self.__send_url is None: raise Exception('Tidak dapat mengirim pesan kepada %s' % (self.name))

        if self['blocked']: raise Exception('Stiker tidak bisa di kirim karena anda telah memblokir akun "%s"!!!' % (self['name']))

        data = self.__data.copy()
        data['like'] = (self.__data_other['like'] if 'like' in self.__data_other.keys() else 'like')

        req = self.__session.post(self.__send_url, data = data)

        html_res = BeautifulSoup(req.text,'html.parser')
        if html_res.find('a', href = re.compile('\/home\.php\?rand=\d+')):
            err_div = html_res.find('div', id = 'root')
            err_msg = ("Terjadi Kesalahan!" if err_div is None else err_div.find('div', class_ = True).get_text(separator = '\n'))
            raise Exception(err_msg)

        return req.ok
    
    def delete_chat(self):
        if self.__action_redirect is None or 'delete' not in self.__data_other.keys(): return False
        data = self.__data.copy()
        data['delete'] = self.__data_other['delete']

        a = self.__session.post(self.__action_redirect, data = data)
        b = BeautifulSoup(a.text,'html.parser')
        url = self.__host + b.find('a', href = re.compile('\/messages\/action\/\?mm_action=delete'))['href']
        req = self.__session.get(url)

        return req.ok
    
    def block_chat(self):
        if self.__action_redirect is None or 'block_messages' not in self.__data_other.keys(): return False

        data = self.__data.copy()
        data['block_messages'] = self.__data_other['block_messages']

        a = self.__session.post(self.__action_redirect, data = data)
        b = BeautifulSoup(a.text,'html.parser')

        url = self.__host + b.find('a', href = re.compile('(.*)\/block_messages\/'))['href']
        req = self.__session.get(url)

        self.refresh()
        return req.ok
    
    def unblock_chat(self):
        if self.__action_redirect is None or 'unblock_messages' not in self.__data_other.keys(): return False

        data = self.__data.copy()
        data['unblock_messages'] = self.__data_other['unblock_messages']

        a = self.__session.post(self.__action_redirect, data = data)
        b = BeautifulSoup(a.text,'html.parser')

        url = self.__host + b.find('a', href = re.compile('(.*)\/unblock_messages\/'))['href']
        req = self.__session.get(url)

        self.refresh()
        return req.ok

    def refresh(self):
        self.__init__(self.__chats_url, self.__session)

class Messenger:
    def __init__(self, cookies, headers = {}):
        login = Login(cookies=cookies, headers=headers)
        
        self.__session = login._sessiom
        self.__host = login._host

        req = self.__session.get(self.__host + '/messages')
        res = BeautifulSoup(req.text, 'html.parser')
        self.__new_messages = self.__host + res.find('a',href = re.compile('\/messages\/'))['href']

        a = self.__session.get(self.__new_messages)
        self.__res = BeautifulSoup(a.text, 'html.parser')

        self.__message_pending = self.__res.find('a', href = re.compile('\/messages\/\?folder=pending'))
        self.__message_filter = self.__res.find('a', href = re.compile('\/messages\/\?folder=other'))
        self.__message_archive = self.__res.find('a', href = re.compile('\/messages\/\?folder=action(.*)Aarchived'))
        self.__message_unread = self.__res.find('a', href = re.compile('\/messages\/\?folder=unread'))
        self.__message_spam = self.__res.find('a', href = re.compile('\/messages\/\?folder=spam'))

        self.__message_pending = self.__host + self.__message_pending['href'] if self.__message_pending is not None else None
        self.__message_filter = self.__host + self.__message_filter['href'] if self.__message_filter is not None else None
        self.__message_archive = self.__host + self.__message_archive['href'] if self.__message_archive is not None else None
        self.__message_unread = self.__host + self.__message_unread['href'] if self.__message_unread is not None else None
        self.__message_spam = self.__host + self.__message_spam['href'] if self.__message_spam is not None else None

    def new_chat(self, username):
        a = self.__session.get(self.__host + '/' + str(username))
        b = BeautifulSoup(a.text,'html.parser')

        if b.find('a', href = re.compile('\/home\.php\?rand=\d+')): raise Exception("Akun dengan username \"%s\" Tidak di temukan!" % (username))

        chats_url = b.find('a', href = re.compile('\/messages\/thread\/\d+(.*)'))

        if chats_url is None: raise Exception("Tidak Bisa mengirim chat ke %s" % (b.find('title').text))

        return Chats(self.__host + chats_url['href'], self.__session)
    
    def new_chat_comunity(self, id_comunity):
        # https://mbasic.facebook.com/messages/read/?tid=cid.g.6308243352596238
        chats_url = self.__host + '/messages/read/?tid=cid.g.' + str(id_comunity)
        return Chats(chats_url=chats_url, requests_session=self.__session)
    
    def new_chat_user(self, id_user):
        # https://mbasic.facebook.com/messages/read/?fbid=100066567202174
        # 100066567202174 -> Andromeda
        chats_url = self.__host + '/messages/read/?fbid=' + str(id_user)
        return Chats(chats_url=chats_url, requests_session=self.__session)

    def __get_chat(self, url, limit = 10):
        chat = []
        my_chat = []
        while True:
            a = self.__session.get(url)
            b = BeautifulSoup(a.text,'html.parser')
            c = b.findAll('a',href = re.compile('\/messages\/read\/'))
            chat.extend(c[0:(limit - len(chat))])
            url = b.find('a', href = re.compile('\/messages\/\?pageNum=\d(.*)selectable'))
            if len(chat) >= limit or url is None:
                break
            else:
                url = self.__host + url['href']
        th = ThreadPool(6)
        th.map(lambda x: my_chat.append(Chats(self.__host + x['href'], self.__session)),chat[0:limit])
        return my_chat
    
    def __get_messages(self, url, limit):
        chat_ku = []

        for i in range(limit):
            a = self.__session.get(url)
            b = BeautifulSoup(a.text,'html.parser')
            c = b.findAll('table', class_ = True, role = False)
            if len(c) <= 0: break

            for x in c:
                name = x.find('a', href = re.compile('^\/messages\/read'))
                message = x.find('span', class_ = True)
                waktu = x.find('abbr')
                uid = None

                if name is not None:
                    uid = re.search('tid=cid\.(?:c|g)\.(\d+)',requests.utils.unquote(name['href'])).group(1)

                name = (name.text if name is not None else None)
                message = (message.text if message is not None else None)
                waktu = (waktu.text if waktu is not None else None)

                chat_ku.append({'name':name, 'id':uid, 'last_chat':message,'time':waktu})

            url = b.find('a', href = re.compile('\/messages\/\?pageNum=\d(.*)selectable'))
            if len(chat_ku) >= limit or url is None:break
            else:
                url = self.__host + url['href']


        return chat_ku[0:limit]
    
    def get_chat_pending(self, limit = 10):
        return self.__get_chat(url=self.__message_pending, limit=limit)
    
    def get_chat_filter(self, limit = 10):
        return self.__get_chat(url = self.__message_filter, limit = limit)

    def get_chat_archive(self, limit = 10):
        return self.__get_chat(url = self.__message_archive, limit = limit)

    def get_chat_unread(self, limit = 10):
        return self.__get_chat(url = self.__message_unread, limit = limit)

    def get_chat_spam(self, limit = 10):
        return self.__get_chat(url = self.__message_spam, limit = limit)

    def get_new_chat(self, limit = 10):
        return self.__get_chat(url = self.__new_messages, limit = limit)

    def get_new_message(self, limit = 10):
        return self.__get_messages(url = self.__new_messages, limit = limit)

    def get_message_spam(self, limit = 10):
        return self.__get_messages(url = self.__message_spam, limit = limit)

    def get_message_unread(self, limit = 10):
        return self.__get_messages(url = self.__message_unread, limit = limit)

    def get_message_archive(self, limit = 10):
        return self.__get_messages(url = self.__message_archive, limit = limit)

    def get_message_filter(self, limit = 10):
        return self.__get_messages(url = self.__message_filter, limit = limit)

    def get_message_pending(self, limit = 10):
        return self.__get_messages(url = self.__message_pending, limit = limit)
        
class User:
    def __init__(self, username, requests_session):
        self.__usr = username

        self.__session = requests_session
        self.__host = 'https://mbasic.facebook.com'

        self.__req = self.__session.get(self.__host + '/' + str(username) + '/about?v=info')
        self.__res = BeautifulSoup(self.__req.text, 'html.parser')

        if self.__res.find('a', href = re.compile('\/home\.php\?rand=\d+')):
            raise Exception("Akun dengan username \"%s\" Tidak di temukan!" % (username))
        
        self.__user_info = {
            'name':'',
            'first_name':'',
            'middle_name':'',
            'last_name':'',
            'alternate_name':'',
            'about':'',
            'username':'',
            'id':'',
            'contact_info':{},
            'profile_pict':'',
            'basic_info':{},
            'education':[],
            'work':[],
            'living':{},
            'relationship':'',
            'other_name':[],
            'family':[],
            'year_overviews':[],
            'quote': ''
        }

        self.name = ''
        self.first_name = ''
        self.middle_name = ''
        self.last_name = ''
        self.alternate_name = ''
        self.about = ''
        self.username = ''
        self.id = ''
        self.contact_info = {}
        self.profile_pict = ''
        self.basic_info = {}
        self.education = []
        self.work = []
        self.living = {}
        self.relationship = ''
        self.other_name = []
        self.family = []
        self.year_overviews = []
        self.quote = ''

        # Profile Picture
        img = self.__res.find('img', alt = re.compile('.*, profile picture'))
        self.profile_pict = img['src']
        
        name = img.find_next('strong')

        # Nama
        if name is not None:
            alt_name = name.find('span', attrs = {'class':'alternate_name'})
            if alt_name is not None:
                self.alternate_name = re.sub('\(|\)$','',alt_name.text)
                alt_name.extract()
                pisah = name.text.split(' ')
                pisah.pop()
            else:
                pisah = name.text.split(' ')
        else:
            pisah = []

        if len(pisah) !=0: self.first_name = pisah[0]
        if len(pisah) > 2: self.middle_name = pisah[1]
        if len(pisah) >=2: self.last_name = pisah[-1]

        # Bio
        bio = self.__res.find('div', id = 'bio')

        if bio is not None:
            for x in bio.findAll('a', href = re.compile('\/profile\/edit')):
                x.extract()

                bio_ku = bio.findAll(string = True)
                self.about = bio_ku[-1]

        # User ID
        uid = self.__res.find('a', href = re.compile('(\/photo\.php|\/profile\/picture\/view)'))
        if uid is not None:
            ids = re.search('(.*)id=(\d+)&',uid['href'])
            if ids is not None: self.id = ids.group(2)

        # Schools Information
        schools = self.__res.find('div', id = 'education')

        if schools is not None:
            gak_penting = schools.findAll('a', href = re.compile('(\/editprofile\/eduwork\/add\/|\/profile\/edit)'))
            for x in gak_penting:
                x.extract()

            for x in schools.findAll('img', src = re.compile('^https:\/\/z-m-scontent')):
                school_data = x.find_next('div').findAll(string = True)
                jmlh = len(school_data)
                school_dict = {'name':'','type':'','study':'','time':''}

                if jmlh == 3:
                    school_dict.update({'name':school_data[0],'type':school_data[1],'time':school_data[2]})
                elif jmlh == 4:
                    school_dict.update({'name':school_data[0],'type':school_data[1],'study':school_data[2],'time':school_data[3]})

                self.education.append(school_dict)

        # Work
        kerja = self.__res.find('div', id = 'work')
        if kerja is not None:
            loker = kerja.findAll('img', alt = re.compile('(.*), profile picture'))
            for a in loker:
                b = a.find_next('div')
                if b is None: continue

                c = b.findAll(string = True)
                d = c[0] # work name
                e = list(filter(lambda abc: re.match('^(\d{1}|\d{2}|\u200f)(\d{1}|\d{2}|\s)(.*?)\s-(.*?)$', abc), c)) # work time
                e = (e[0] if len(e) != 0 else '')

                self.work.append({'name': d, 'time': e})

        # Living
        home = self.__res.find('div', id = 'living')

        if home is not None:
            for h in home.findAll('a', href = re.compile('\/editprofile\.php')):
                h.extract()

            for span in home.findAll('span', attrs = {'aria-hidden':True}):
                span.extract()
            
            self.living.update(self.__list_to_dict([i.text for i in home.findAll('td')][2:]))

        # Other Name
        on = self.__res.find('div', id = 'nicknames')

        if on is not None:
            for y in on.findAll('span', attrs = {'aria-hidden':True}):
                y.extract()

            for x in on.findAll('a', href = re.compile('^\/profile\/edit\/info\/nicknames')):
                x.extract()

            mn = on.findAll(string = True)
            mn.pop(0)

            if len(mn) % 2 == 1: mn.pop(2)
            
            self.other_name = self.__list_to_dict(mn)

        # love
        cinta = self.__res.find('div', id = 'relationship')

        if cinta is not None:
            for cinta_itu_palsu in cinta.findAll('a', href = re.compile('\/editprofile\.php')):
                cinta_itu_palsu.extract()

        cinta_ku = cinta.findAll(string = True)
        cinta_ku.pop(0)

        self.relationship = ' '.join(cinta_ku)

        # Family Information
        keluarga = self.__res.find('div', id = 'family')

        if keluarga is not None:
            keluarga_ku = keluarga.findAll('img', alt = re.compile('(.*), profile picture'))

            for family in keluarga_ku:
                name = family.find_next('a')
                profile_pict = family["src"]
                username = re.search("^\/[a-zA-Z0-9_.-]+",name['href']).group(0)
                designation = name.find_next('h3')

                self.family.append({'name':name.text,'username':username,'designation':designation.text,'profile_pict':profile_pict})

        # Contact Information
        self.contact_info = self.__get_data_by_div(div_id = 'contact-info', tag_to_find = 'td', attrs = {'valign':'top'})
        if 'Facebook' in self.contact_info.keys():
            self.username = self.contact_info['Facebook'].strip()

        # Basic Information
        self.basic_info = self.__get_data_by_div(div_id = 'basic-info', tag_to_find = 'td', attrs = {'valign':'top'})

        self.name = ' '.join(pisah)

        self.__user_info['name'] = self.name
        self.__user_info['first_name'] = self.first_name
        self.__user_info['middle_name'] = self.middle_name
        self.__user_info['last_name'] = self.last_name
        self.__user_info['about'] = self.about
        self.__user_info['username'] = self.username
        self.__user_info['id'] = self.id
        self.__user_info['contact_info'] = self.contact_info
        self.__user_info['profile_pict'] = self.profile_pict
        self.__user_info['basic_info'] = self.basic_info
        self.__user_info['education'] = self.education
        self.__user_info['work'] = self.work
        self.__user_info['living'] = self.living
        self.__user_info['relationship'] = self.relationship
        self.__user_info['other_name'] = self.other_name
        self.__user_info['family'] = self.family

        cookie_dict = self.__session.cookies.get_dict()
        self.__this_is_me = (self.id == cookie_dict['c_user'] if 'c_user' in cookie_dict.keys() else None)

    def __str__(self):
        return "Facebook User : name='%s' id=%s username='%s'" % (self.__user_info['name'], self.__user_info['id'], self.__user_info['username'])

    def __repr__(self):
        return "Facebook User : name='%s' id=%s username='%s'" % (self.__user_info['name'], self.__user_info['id'], self.__user_info['username'])
    
    @property
    def _user_info(self):
        return self.__user_info.copy()

    def __list_to_dict(self,list_):
        keys = []
        value = []
        data = {}

        for x in range(len(list_)):
            if x % 2 == 0:
                keys.append(list_[x])
            else:
                value.append(list_[x])

        for x in range(len(keys)):
            data.update({keys[x]:value[x]})

        return data
    
    def __get_data_by_div(self,div_id,tag_to_find, attrs = {}):
        data_info = self.__res.find('div', id = div_id)

        data_list = []
        if data_info is not None:
            for x in data_info.findAll(tag_to_find, attrs = attrs):
                data_list.append(re.sub('· (.*)','',x.text).strip())
            return self.__list_to_dict(data_list)
        else:
            return {}
        
    def __action_user(self, re_compiled):
        if self.__this_is_me:
            raise Exception('Tidak dapat melakukan tindakan yang anda minta!')
        
        acc = self.__res.find('a', href = re_compiled)

        if acc is None: return False

        data = {
            'jazoest': self.__res.find('input', attrs = {'name':'jazoest'}).get('value'),
            'fb_dtsg': self.__res.find('input', attrs = {'name':'fb_dtsg'}).get('value')
        }

        req = self.__session.get(self.__host + acc['href'], data = data)
        self.__res = BeautifulSoup(req.text,'html.parser')

        return req.ok
    
    def add_friend(self):
        return self.__action_user(re_compiled = re.compile('^\/a\/friends\/profile\/add'))
    
    def cancel_friends_requests(self):
        return self.__action_user(re_compiled = re.compile('\/a\/friendrequest\/cancel\/\?subject_id=\d+'))
    
    def accept_friends_requests(self):
        return self.__action_user(re_compiled = re.compile('\/a\/friends\/profile\/add\/\?subject_id=\d+(.*)is_confirming'))
    
    def delete_friends_requests(self):
        return self.__action_user(re_compiled = re.compile('\/a\/(.*)\/friends\/reject\/\?subject_id=\d+'))
    
    def remove_friends(self):
        if self.__this_is_me:
            raise Exception('Tidak dapat menghapus diri sendiri!')
        
        confirm_url = self.__res.find('a', href = re.compile('\/removefriend\.php\?friend_id=\d+'))

        if confirm_url is None: return False

        c = self.__session.get(self.__host + confirm_url['href'])
        d = BeautifulSoup(c.text,'html.parser')

        form = d.find('form', action = re.compile('\/a\/friends\/remove\/\?subject_id=\d+'))
        remove_url = self.__host + form["action"]
        data = {}

        for x in form.findAll('input'):
            data[x.get('name')] = x.get('value')

        req = self.__session.post(remove_url, data = data)

        self.__res = BeautifulSoup(req.text,'html.parser')

        return req.ok
        
    def get_friends(self, limit = 10, return_dict = True):
        friend = []
        url = self.__res.find('a', href = re.compile('\/((.*)\/friends\?lst=|profile\.php\?id=\d+(.*?)v=friends|profile\.php\?v=friends)'))
        
        if url is None:
            a = self.__session.get(self.__host + '/' + self.__usr)
            b = BeautifulSoup(a.text,'html.parser')

            url = b.find('a', href = re.compile('\/((.*)\/friends\?lst=|profile\.php\?id=\d+(.*?)v=friends|profile\.php\?v=friends)'))

            if url is None: return friend

        c = self.__host + url['href']
        d = self.__session.get(c)
        e = BeautifulSoup(d.text,'html.parser')

        while len(friend) < limit:
            datas = e.findAll('img', alt = re.compile('(.*), profile picture'), src = re.compile('https:\/\/z-m-scontent(.*)\.fbcdn\.net'))
            del datas[0]
            
            if return_dict:
                for f in datas:
                    profile = f.find_next('a', href = re.compile('(^\/profile\.php|^\/(.*)\?)'))
                    username = re.search('(^\/profile.php\?id=(\d+)|^\/([a-zA-Z0-9_.-]+))',profile['href']).group((2 if 'profile.php' in profile['href'] else 3))
                    nama = profile.text
                    foto_pp = f['src']
                    friend.append({'name':nama, 'profile_pict':foto_pp,'username':username})
            else:
                th = ThreadPool(10)
                th_data = []

                for f in datas:
                    profile = f.find_next('a', href = re.compile('(^\/profile\.php|^\/(.*)\?)'))
                    username = re.search('(^\/profile.php\?id=(\d+)|^\/([a-zA-Z0-9_.-]+)\?)',profile['href'])
                    if username is None: continue
                    th_data.append(username.group((2 if 'profile.php' in profile['href'] else 3)))
                th.map(lambda x: friend.append(User(username = x, requests_session = self.__session)),  th_data)

            next_uri = e.find('a', href = re.compile('^\/[a-zA-Z0-9_.-]+\/friends\?unit_cursor=\w+'))
            if len(friend) >= limit or next_uri is None: break
            d = self.__session.get(self.__host + next_uri['href'])
            e = BeautifulSoup(d.text,'html.parser')
        
        return friend[0:limit]
    
    def get_posts(self, limit = 5): # -> TERTUNDA
        post_data = []

        timeline_url = self.__res.find('a', href = re.compile('^\/([a-zA-Z0-9_.-]+\?v=timeline|profile\.php\?id=\d+(.*?)v=timeline)'))
        timeline_url = (self.__host + timeline_url['href'] if timeline_url is not None else self.__host + '/' + str(self.__usr) + '?v=timeline')

        a = self.__session.get(timeline_url)

        while len(post_data) < limit:
            b = BeautifulSoup(a.text,'html.parser')
            c = b.findAll('div', role = 'article')

            for d in c:
                url = d.find('a', href = re.compile('^\/(story\.php\?story_fbid|[a-zA-Z0-9_.-]+\/posts\/)'), class_ = False)
                # if url is None: continue
                # post_data.append(Posts(self.__session, self.__host + url['href'], json.loads(d.get('data-ft'))))
                # if len(post_data) >= limit: break

class Facebook(Login):
    def __init__(self, cookies, save_login = False, free_facebook=False):
        cookies = cookies.strip()
        super().__init__(cookies = cookies, free_facebook = free_facebook)

        self.__session = self._sessiom
        self.__host = self._host

    def Messenger(self):
        return Messenger(self.get_cookie_str())

    def __str__(self):
        return "Facebook : host='%s' cookie='%s'" % (self.__host, self.get_cookie_str())

    def __repr__(self):
        return "Facebook : host='%s' cookie='%s'" % (self.__host, self.get_cookie_str())
    
    def get_profile(self, target):
        return User(username = target, requests_session = self._Login__session)
    
# END CLASS

import time
    
def ask_chat_gpt():
    from openai import OpenAI

    fb = Facebook(cookies='sb=t1caZRvSiIeoUnJz450G6-w7; datr=t1caZSaR3eRejBBgdR_CPedT; wd=1366x689; c_user=100010450276658; xs=36%3AdHR0Dpop7CbadQ%3A2%3A1700194724%3A-1%3A12205; fr=1uRoEkRhU3WhiBMvw.AWWtFzYshhprn_TU-8inyf0eLWA.BlVBkP.-r.AAA.0.0.BlVumn.AWU2Uj8Tln4; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1700194881571%2C%22v%22%3A1%7D', free_facebook=False)

    msg = fb.Messenger()

    exists_msg = []
    client = OpenAI(api_key=os.getenv('OPENAI_API'))

    while True:
        users_ask = []

        user_chat = msg.new_chat_comunity(id_user='9709145459160219')
        # zpu_comunity_chat = msg.new_chat_comunity(id_comunity='9709145459160219')
        messages = user_chat.get_chat(limit=3, sort=True)

        # print('------msg-----')
        # print(messages)
        # print('------msg-----\n')

        for x in messages:

            for y in x['message']:
                if 'x_Reply' in x:
                    continue
                print(x)

                if '/ask/' in y.lower():
                    x['message'] = y

                    if x['message'] in exists_msg:
                        print('pesan sudah dijawab', end='\r')
                        continue

                    exists_msg.append(x['message'])

                    users_ask.append(x)
                else:
                    print('Tidak ada pertanyaan', end='\r')
                    time.sleep(3)
                    continue

        print(users_ask)

        if len(users_ask) != 0:
            for user in users_ask:
                user['message'] = user['message'].split('/', 2)[2].strip()

                completion = client.chat.completions.create(
                    model='gpt-3.5-turbo',
                    messages=[
                        {"role": "user", "content": user["message"]}
                    ]
                )

                result_chatgpt = completion.choices[0].message.content

                reply = f'@{user["name"]}\nPertanyaan: {user["message"]}\nx_Reply:\n{result_chatgpt}'
                print(reply)
                status = user_chat.send_text(message=reply)
                print(f'STATUS KIRIM PESAN: {status}')
        else:
            continue

if __name__ == '__main__':
    ask_chat_gpt()
    # fb = Facebook(cookies='sb=t1caZRvSiIeoUnJz450G6-w7; datr=t1caZSaR3eRejBBgdR_CPedT; wd=1366x689; c_user=100010450276658; xs=36%3AdHR0Dpop7CbadQ%3A2%3A1700194724%3A-1%3A12205; fr=1uRoEkRhU3WhiBMvw.AWWtFzYshhprn_TU-8inyf0eLWA.BlVBkP.-r.AAA.0.0.BlVumn.AWU2Uj8Tln4; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1700194881571%2C%22v%22%3A1%7D', free_facebook=False)
    # msg = fb.Messenger()
    # chat = msg.new_chat_comunity(id_comunity='6308243352596238')
    # print(chat.send_text(message='Hello'))

    # alexia = fb.get_profile('alexia.katharina.7')
    # alexia.get_friends()
    # helna = fb.get_profile('100095349966827')
    # helna.get_posts()
    # fb.get_profile('dikidjatar')
    # user = fb.get_profile('100088846010436')
    # print(user._user_info)
    # print(f'Menghapus teman "{user.name}" {"Berhasil" if user.remove_friends() else "Gagal"}')