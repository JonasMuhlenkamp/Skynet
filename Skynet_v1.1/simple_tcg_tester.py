import os
import requests
import json

PUBLIC_KEY = os.environ.get('TCG_PUBLIC_KEY')
PRIVATE_KEY = os.environ.get('TCG_PRIVATE_KEY')

#Set up the headers and keys for the post request 
headers = {"User-Agent": "Nautilus", "From": "nautilus.application@gmail.com", "application": "x-www-form-urlencoded"}
data = {"grant_type": "client_credentials", "client_id": PUBLIC_KEY, "client_secret": PRIVATE_KEY}

#Request the token
response = requests.post("https://api.tcgplayer.com/token", headers=headers, data=data)
response_dict = json.loads(response.text)

#Save the token in the environment variables
BEARER_TOKEN = response_dict["access_token"]
expire_date = response_dict[".expires"]
#os.environ['TCG_BEARER_TOKEN'] = BEARER_TOKEN
#print("Update successful.  Token will expire on " + str(expire_date))

productId = "268418,268435"
url = "https://api.tcgplayer.com/pricing/product/" + str(productId)
headers = {"User-Agent": "Nautilus", "From": "nautilus.application@gmail.com", "accept": "application/json", "authorization": "bearer " + BEARER_TOKEN}

response = requests.request("GET", url, headers=headers)
response_dict = json.loads(response.text)

def jprint(obj):
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)
    return text

jprint(response_dict)