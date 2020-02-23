import json

data = {}
data['people'] = []
data['people'].append({
    'name': 'CJ',
    'id': '0',
})
with open('data.txt', 'w') as outfile:
    json.dump(data, outfile)