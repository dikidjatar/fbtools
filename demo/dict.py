import re
import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# data = [
#     {'name': 'Adel Lia', 'username': None, 'message': ['🗿'], 'file': [], 'stiker': [], 'time': '1 jam yang lalu'}, {'name': 'Sisil', 'username': None, 'message': ['Mengherankan skli😓'], 'file': [], 'stiker': [], 'time': '1 jam yang lalu'}, {'name': 'hani愛.', 'username': 'unknownpvx', 'message': ['Gkpp Del, lumayan kenang kenangan dari bangsa viking wkwk', 'Masa t4i di samain sama permata hadehh ada² aja 😭🤣'], 'file': [], 'stiker': [], 'time': '1 jam yang lalu'}, {'name': 'Sisil', 'username': None, 'message': [], 'file': [], 'stiker': [], 'time': '1 jam yang lalu'}, {'name': 'Xyzz N', 'username': 'bang.zabanid', 'message': ['Hii gaezz'], 'file': [], 'stiker': [], 'time': '44 menit lalu'}, {'name': 'Adel Lia', 'username': None, 'message': ['/chat-gpt/ Halo'], 'file': [], 'stiker': [], 'time': '57 menit lalu'}, {'name': 'Febriani Skolastika', 'username': None, 'message': ['Haiiii'], 'file': [], 'stiker': [], 'time': '1 jam yang lalu'}, {'name': 'Adel Lia', 'username': None, 'message': ['Aneh ya tpi nyata🤣', 'Ywdh han kita ga punya permata yng di mahkota juga ga pp. Setidak nya kita punya t4i'], 'file': [], 'stiker': [], 'time': '1 jam yang lalu'}, {'name': 'Arham', 'username': 'ikra.fams.5', 'message': ['Perusak rumah tangga orang lain bantu teror...+62 831-6027-6028 wanya simpati sedikit bro kasih pelajaran', 'Bantu share'], 'file': [], 'stiker': [], 'time': '20 menit lalu'}, {'name': 'Agus Kun', 'username': 'agus.mofferz.5', 'message': ['Kiw kiw 🗿', '/chat-gpt/ Sebutkan 3 macam hewan karnivora', 'Apa del'], 'file': [], 'stiker': [], 'time': '28 menit lalu'}
# ]

# data = [{'name': 'Alvin T. S. Telaumbanua', 'username': None, 'message': ['🗿', '/chat-gpt/ Sebutkan 3 macam ikan'], 'file': [], 'stiker': [], 'time': 'Baru saja'}, {'name': 'Sisil', 'username': None, 'message': ['Busett'], 'file': [], 'stiker': [], 'time': '4 menit lalu'}, {'name': 'Alvin T. S. Telaumbanua', 'username': None, 'message': ["Hai para dayang ku"], 'file': [], 'stiker': [], 'time': '28 menit lalu'}, {'name': 'Raisa Ana', 'username': None, 'message': ['Waalaikumsalam', '/chat-gpt/ Apa yang dimaksudkan dengan metabolisme'], 'file': [], 'stiker': [], 'time': '45 menit lalu'}]


exists_msg = []
client = OpenAI(api_key=os.getenv('OPENAI_API'))

while True:
    time.sleep(3)
    users = []
    data = json.loads(open('demo/msg.json', 'r').read())

    for x in data:
        for y in x['message']:
            if '/chat-gpt/' in y.lower():
                x['message'] = y

                if x['message'] in exists_msg:
                    print('pesan sudah dijawab', end='\r')
                    continue
                
                exists_msg.append(x['message'])

                users.append(x)
            else:
                continue

    
    if len(users) != 0:
        for user in users:
            user['message'] = user['message'].split('/', 2)[2].strip()

            completion = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[
                    {"role": "user", "content": user["message"]}
                ]
            )

            result_chatgpt = completion.choices[0].message.content

            reply = f'@{user["name"]}\nPertanyaan: {user["message"]}\nChatGPT:\n{result_chatgpt}'
            print(reply)
    else:
        continue


if len(users) != 0:
    for user in users:
        user['message'] = user['message'].split('/', 2)[2].strip()
        
        print({
            'name': user['name'],
            'message': user['message']
        })

        # completion = client.chat.completions.create(
        #     model='gpt-3.5-turbo',
        #     messages=[
        #         {"role": "user", "content": user["message"]}
        #     ]
        # )

        # result_chatgpt = completion.choices[0].message.content
        
        # reply = f'@{user["name"]}\nPertanyaan: {user["message"]}\nChatGPT:\n{result_chatgpt}'
        # print(reply)
# client = OpenAI(api_key=os.getenv('OPENAI_API'))

# print(users)

exit()