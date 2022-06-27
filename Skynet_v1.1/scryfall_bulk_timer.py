import requests
import time
import json

def jprint(obj):
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)
    return text

def download_bulk_data():
    url = "https://api.scryfall.com//bulk-data//default_cards"
    response = requests.get(url)
    response_dict = json.loads(response.text)
    data_url = response_dict["download_uri"]
    print(data_url)

    tic = time.perf_counter()
    data = requests.get(data_url, allow_redirects=True)
    # response_dict = json.loads(data.text)
    # card_count = 0
    # cardnames = {}
    # for card in data.json():
    #     card_count += 1
    #     cardnames.update({card["name"]: card["set"]})
    # print(card_count)
    # # print(cardnames)

    # # with open("default.json", mode="w+") as data_file:
    # #     json.dump(data.json(), data_file)
    # toc = time.perf_counter()
    # print(f"Run time, default: {toc - tic:0.4f} s")

    # url = "https://api.scryfall.com//bulk-data//all_cards"
    # response = requests.get(url)
    # response_dict = json.loads(response.text)
    # data_url = response_dict["download_uri"]
    # print(data_url)

    # tic = time.perf_counter()
    # data = requests.get(data_url, allow_redirects=True)
    # card_count = 0
    # cardnames = {}
    # for card in data.json():
    #     if card["lang"] == "en":
    #         card_count += 1
    #         cardnames.update({card["name"]: card["set"]})
    #     elif card["lang"] == "ph":
    #         card_count += 1
    #         cardnames.update({card["name"] + " (Phyrexian)": card["set"]})


    # # with open("all.json", mode="w+") as data_file:
    # #     json.dump(data.json(), data_file)
    # toc = time.perf_counter()
    # print(f"Run time, all: {toc - tic:0.4f} s")

    jprint(data.json()[0])

download_bulk_data()
#Results 6/26/2022: 33.1s for default, 175.1s for all. Torn whether the 6x download time (likely longer than 3min on Freedom wifi) is worth it for like 10 cards.
