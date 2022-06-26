import requests
import json
import csv
import os
from datetime import datetime

#An important function that will update the TCGPlayer API bearer token in the system variables.
#This is needed because the token expires every two weeks.
def update_bearer():
    #Access the keys that allow us to get a bearer token in the first place (they are stored as environment variables)
    
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
    os.environ['TCG_BEARER_TOKEN'] = BEARER_TOKEN
    print("Update successful.  Token will expire on " + str(expire_date))
    return BEARER_TOKEN

#A utility function that will print a nice, legible version
#of any json dictionary that you give it.
def jprint(obj):
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)
    return text

#This function generates an array of TCGPlayer ids from a .csv file that 
#comes from the Nautilus Excel sheet.  It also creates a dictionary of 
#foil/nonfoil data which is used to ensure the program grabs the correct prices.
#Note that this may soon change, as it would be nice to grab foil prices. (7/20/20)
def create_tcgplayer_arrays(csv_filepath, rows_to_skip):
    
    #Parameters
    filepath = csv_filepath
    skip_rows = rows_to_skip

    #The output dictionary and array
    foil_dictionary = {}
    id_array = []

    #Open the .csv file
    with open(filepath) as csv_file:

        #Begin parsing the file
        csv_reader = csv.reader(csv_file, delimiter=',')

        #Start at -skip_rows so that the first line of data is id = 0
        line_count = -skip_rows

        #Iterate through the rows of the file
        for row in csv_reader:
            
            #Skip lines if not yet at the first line of data
            if line_count < 0:
                line_count += 1
                continue
            #Otherwise, grab the desired columns from the row
            else:
                
                if int(row[0]) > 0:
                    add_card = True
                    for i in range(len(id_array)):
                        if id_array[i] == row[0]:
                            add_card = False
                    if add_card:

                        foil_dictionary.update({int(row[0]): row[1]})
                        id_array.append(row[0])
                
                line_count += 1
        
        #Close the file when done
        csv_file.close()
        print(id_array)
    #Return the dictionary
    return foil_dictionary, id_array

#In order to reduce pingload on Scryfall's api, we download the bulk data every day
#(downloading and processing takes approximately 1 minute on my laptop)
def download_bulk_data(filepath):
    url = "https://api.scryfall.com//bulk-data//default_cards"
    response = requests.get(url)
    response_dict = json.loads(response.text)
    data_url = response_dict["download_uri"]
    print(data_url)

    data = requests.get(data_url, allow_redirects=True)

    with open(filepath, mode="w+") as data_file:
        json.dump(data.json(), data_file)

#This function is paired with the download_bulk_data function.
#It will create a .csv file with cardname, tcgplayer id, full card text broken into pieces
#(mana, cmc, oracle text, type line, power, toughness, etc.).  The Scryfall price (TCG Market)
#is used to determine what version of a card we query for pricing.
def process_bulk_data(filepath_in, filepath_out):

    json_data = ""
    with open(filepath_in, mode="r") as data_file:
        json_data = json.load(data_file)
    
    tcg_string = ""
    foil_dict = {}
    with open(filepath_out, mode="w", newline="") as csv_file:
        # output.update({"cardname": name, "tcg_id": tcg_id, "foil": foil, "fancy": fancy_type, "setname": set_name, "setcode": set_code, "rarity": rarity, "collector_number": collector_number, "color": color, "color_sort": color_sort, "color_id": color_id, "mana_cost": mana_cost, "converted_mana_cost": cmc, "typeline": type_line, "types": types, "supertypes": supertypes, "subtypes": subtypes, 
        #            "oracle_text": oracle_text, "power": power, "price": price, "toughness": toughness, "loyalty": loyalty, "layout_type": layout, "card_faces": card_face_count})

    
        fieldnames = ["cardname", "tcg_id", "foil", "fancy", "setname", "setcode", "rarity", "reserved", "collector_number", "color", "color_sort", "color_id", "mana_cost", "converted_mana_cost", "typeline", "types", "supertypes", "subtypes", "oracle_text", "power", "toughness", "loyalty", "price", "layout_type", "card_faces"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        card_count = 1
        for card in json_data:
            card_check = check_card(card)
            if card_check:
                #print(card_count)
                card_count += 1
                card_data, tcg, foil = organize_desired_data(card)
                if tcg != "":
                    tcg_string = tcg_string + str(tcg) + ","
                    foil_dict.update({tcg: foil})
                writer.writerow(card_data)   
                    #card_count += 1

    return tcg_string, foil_dict

#A subfunction of process_bulk_data, this function ensures that a card object from the bulk 
#data file is actually useful - i.e., not a promo, not a token, etc.
def check_card(card):
    paper = False
    for game in card["games"]:
        if game == "paper":
            paper = True
    if paper == False:
        return False
    
    if card["lang"] != "en":
        return False
    
    # try:
    #     tcg_id = card["tcgplayer_id"]
    #     if tcg_id == "":
    #         print("No tcg id")
    #         return False
    # except:
    #     return False
    
    #if bool(card["promo"]) == True:
    #    return False

    if card["set"] == "mb1" or card["set"] == "sum" or card["set"] == "fmb1" or card["set"] == "lea" or card["set"] == "leb" or card["set"] == "sld":
        return False
    
    if card["type_line"].__contains__("Basic"):
        return False

    if card["collector_number"].__contains__("p"):
        return False
    
    if card["layout"] == "token" or card["layout"] == "double_faced_token" or card["layout"] == "emblem" or card["layout"] == "art_series":
        return False

    return True

#Also a subfunction of process_bulk_data, this turns an api card object into a dictionary for 
#.csv file addtion
def organize_desired_data(api_card):

    possible_types = ["Tribal", "Enchantment", "Artifact", "Creature", "Land", "Planeswalker", "Instant", "Sorcery", "Conspiracy", "Phenomenon", "Plane ", "Vanguard", "Scheme"]
    possible_supertypes = ["Legendary", "Basic", "Ongoing", "Snow", "World", "Host", "Elite"]
        
    output = {}

    layout = api_card["layout"]
    cmc = api_card["cmc"]
    
    color = ""

    color_id = ""
    for c in api_card["color_identity"]:
        color_id = color_id + c
    if color_id == "":
        color_id = "C"
    
    #For convenience's sake, we take the front name only for DFCs, Adventures, and Kamigawa flip cards
    layout = api_card["layout"]
    name = ""
    if layout == "transform" or layout == "flip" or layout == "adventure" or layout == "modal_dfc":
        name = api_card["name"].split("//")[0].strip()
        print(name)
    else:
        name = api_card["name"]
        
    set_name = api_card["set_name"]
    set_code = api_card["set"]
    collector_number = api_card["collector_number"]
    collector_number = collector_number.replace(u"\u2605", "*")
    rarity = api_card["rarity"]
    
    type_line = api_card["type_line"]
    type_line = type_line.replace(u"\u2014", "-")

    # jpg_uri = ""
    # jpg_uri_2 = ""
    tcg_id = ""
    foil = "False"
    fancy = ""
    mana_cost = ""
    oracle_text = ""
    power = ""
    toughness = ""
    loyalty = ""
    types = ""
    supertypes = ""
    subtypes = ""
    price = ""
    reserved = ""

    try:
        tcg_id = api_card["tcgplayer_id"]
    except:
        pass

    if bool(api_card["nonfoil"]) == False:
        foil = "True"

    if foil == "True":
        price = api_card["prices"]["usd_foil"]
    else:
        price = api_card["prices"]["usd"]

    reserved = api_card["reserved"]

    #For post-Throne of Eldraine cards, there are up to three variants of a single card name.
    fancy_type = ""
    try:
        
        #Showcase and extended variants are listed as frame effects
        for frame_effect in api_card["frame_effects"]:

            if frame_effect == "showcase":
                fancy_type = "Showcase"
                break
        
            if frame_effect == "extendedart":
                fancy_type = "Extended"
                break

            if frame_effect == "legendary" and api_card["set"] == "iko" and api_card["border_color"] == "borderless":
                fancy_type = "Godzilla"
    
    #If there are no frame effects, we check if the card is a borderless planeswalker or Godzilla card
    except:

        try:

            if str(api_card["type_line"]).lower().__contains__("planeswalker"):
                if api_card["border_color"] == "borderless":
                    fancy_type = "Borderless"
            elif fancy_type == "":
                if api_card["set"] == "iko":
                    if api_card["border_color"] == "borderless":
                        fancy_type = "Godzilla"
                elif api_card["set"] == "m21":
                    if api_card["border_color"] == "borderless":
                        fancy_type = "Alternate Art"

        except:
            pass
    
    if fancy_type != "":
        name = name + " (" + fancy_type + ")"

    card_face_count = 0
    try:
       for card_face in api_card["card_faces"]:
           card_face_count += 1
    except:
        card_face_count = 1 

    color = ""
    color_sort = ""
    try:
        colors = []
        
        #Awkwardly, transform cards have their colors within their card_face objects
        if layout == "transform" or layout == "modal_dfc":
            colors = api_card["card_faces"][0]["colors"]
        else:
            colors = api_card["colors"]

        #Multiple colors -> multicolored :)
        if len(colors) > 1:
            color = "Multi"
            color_sort = "7"
        #Unfortunately, lands are colorless, so we need to separate them
        elif len(colors) == 0:
            typeline = ""
            try:
                typeline = str(api_card["type_line"]).lower().split(" // ")[0]
            except:
                typeline = str(api_card["type_line"]).lower()
            if typeline.__contains__("land"):
                print(typeline)
                color = "Land"
                color_sort = "1"
            else:
                color = "Colorless"
                color_sort = "8"
        else:
            for card_color in colors:
                if card_color == "W":
                    color = "White"
                    color_sort = "2"
                elif card_color == "U":
                    color = "Blue"
                    color_sort = "3"
                elif card_color == "B":
                    color = "Black"
                    color_sort = "4"
                elif card_color == "R":
                    color = "Red"
                    color_sort = "5"
                elif card_color == "G":
                    color = "Green"
                    color_sort = "6"
                else:
                    pass
    except:
        pass
    
    if api_card["name"] == "Dryad Arbor":
        color_sort = 1

    if card_face_count == 1:
        # jpg_uri = api_card["image_uris"]["normal"]
        mana_cost = api_card["mana_cost"]
        
        oracle_text = api_card["oracle_text"]
        oracle_text = oracle_text.replace("\n", "; ")
        oracle_text = oracle_text.replace(u"\u2014", "-")
        oracle_text = oracle_text.replace(u"\u2022", "-")
        oracle_text = oracle_text.replace(u"\u2212", "-")
        oracle_text = oracle_text.replace(u"\u2610", "~")
        oracle_text = oracle_text.replace(u"\u221e", "INFINITY")
        oracle_text = oracle_text.replace(u"\u03c0", "PI")

        # for c in api_card["colors"]:
        #     color = color + c
        # if color == "":
        #     color = "C"

        try:
            power = api_card["power"]
            power = power.replace(u"\u221e", "INFINITY")
        except:
            power = "N/A"
        
        try:
            toughness = api_card["toughness"]
        except:
            toughness = "N/A"
        
        try: 
            loyalty = api_card["loyalty"]
        except:
            loyalty = "N/A"

        for type in possible_types:
            if type_line.__contains__(type):
                types = types + type + " "
        types = types.strip()
        
        for supertype in possible_supertypes:
            if type_line.__contains__(supertype):
                supertypes = supertypes + supertype + " "
        supertypes = supertypes.strip()

        if type_line.__contains__("-"):
            subtypes = type_line.split("-")[1]
        subtypes = subtypes.strip()

    else:
        #[mana cost, color, power, toughness, loyalty, oracle, jpg_uri]
        separate_face_colors = False        
        faces = [[],[], [], [], []]
        i = 0
        for card_face in api_card["card_faces"]:
            
            face_mana_cost = ""
            try:
                face_mana_cost = card_face["mana_cost"]
                if face_mana_cost == "":
                    face_mana_cost = "None"
            except:
                face_mana_cost = "N/A"
            faces[i].append(face_mana_cost)
            
            face_color = ""
            # try:
            #     for c in card_face["colors"]:
            #         face_color = face_color + c
            #     if face_color == "":
            #         face_color = "C"
            #     separate_face_colors = True
            # except:
            #     face_color = "None"
            faces[i].append(face_color)

            face_power = ""
            try:
                face_power = card_face["power"]
            except:
                face_power = "N/A"  
            faces[i].append(face_power)

            face_toughness = ""
            try:
                face_toughness = card_face["toughness"]
            except:
                face_toughness = "N/A"
            faces[i].append(face_toughness)
            
            face_loyalty = ""
            try:
                face_loyalty = card_face["loyalty"]
            except:
                face_loyalty = "N/A"
            faces[i].append(face_loyalty)

            face_oracle = card_face["oracle_text"]
            face_oracle = face_oracle.replace("\n", "; ")
            face_oracle = face_oracle.replace(u"\u2014", "-")
            face_oracle = face_oracle.replace(u"\u2022", "-")
            face_oracle = face_oracle.replace(u"\u2212", "-")
            face_oracle = face_oracle.replace(u"\u2610", "~")
            face_oracle = face_oracle.replace(u"\u221e", "INFINITY")
            faces[i].append(face_oracle)

            # if layout == "transform":
            #     faces[i].append(card_face["image_uris"]["normal"])
            # else:
            #     jpg_uri = api_card["image_uris"]["normal"]

            i+=1

        mana_cost = faces[0][0] + " // " + faces[1][0]
        # if separate_face_colors: 
        #     color = faces[0][1] + " // " + faces[1][1]
        # else:
        #     for c in api_card["colors"]:
        #         color = color + c
        #     if color == "":
        #         color = "C"
        power = faces[0][2] + " // " + faces[1][2]
        toughness = faces[0][3] + " // " + faces[1][3]
        loyalty = faces[0][4] + " // " + faces[1][4]
        oracle_text = faces[0][5] + " // " + faces[1][5]
        
        # if layout == "transform":
        #     jpg_uri = faces[0][6]
        #     jpg_uri_2 = faces[1][6]

        type_line_1 = type_line.split("//")[0].strip()
        type_line_2 = ""
        try:
            type_line_2 = type_line.split("//")[1].strip()
        except:
            pass
        
        subtype_line_1 = ""
        subtype_line_2 = ""
        if type_line_1.__contains__("-") and type_line_2.__contains__("-"):
            subtype_line_1 = type_line_1.split("-")[1].strip()
            subtype_line_2 = type_line_2.split("-")[1].strip()
            subtypes = subtype_line_1 + " // " + subtype_line_2
        elif type_line_1.__contains__("-"):
            subtype_line_1 = type_line_1.split("-")[1].strip()
            subtypes = subtype_line_1 + " // None"
        elif type_line_2.__contains__("-"):
            subtype_line_2 = type_line_2.split("-")[1].strip()
            subtypes = "None // " + subtype_line_2

        types_1 = ""
        types_2 = ""
        for type in possible_types:
            if type_line_1.__contains__(type):
                types_1 = types_1 + type + " "
            if type_line_2.__contains__(type):
                types_2 = types_2 + type + " "
        types = types_1.strip() + " // " + types_2.strip()
        
        supertypes_1 = ""
        supertypes_2 = ""
        for supertype in possible_supertypes:
            if type_line_1.__contains__(supertype):
                supertypes_1 = supertypes_1 + supertype + " "
            if type_line_2.__contains__(supertype):
                supertypes_2 = supertypes_2 + supertype + " "
        if supertypes_1 == "" and supertypes_2 == "":
            supertypes = ""
        elif supertypes_1 == "":
            supertypes_1 = "None"
            supertypes = supertypes_1.strip() + " // " + supertypes_2.strip()
        elif supertypes_2 == "":
            supertypes_2 = "None"
            supertypes = supertypes_1.strip() + " // " + supertypes_2.strip()
        else:
            supertypes = supertypes_1.strip() + " // " + supertypes_2.strip()
        

    output.update({"cardname": name, "tcg_id": tcg_id, "foil": foil, "fancy": fancy_type, "setname": set_name, "setcode": set_code, "rarity": rarity, "reserved": reserved, "collector_number": collector_number, "color": color, "color_sort": color_sort, "color_id": color_id, "mana_cost": mana_cost, "converted_mana_cost": cmc, "typeline": type_line, "types": types, "supertypes": supertypes, "subtypes": subtypes, 
                   "oracle_text": oracle_text, "power": power, "price": price, "toughness": toughness, "loyalty": loyalty, "layout_type": layout, "card_faces": card_face_count})

    
    # bad_filename_chars = ["<", ">", ":", "\"", "/", "\\", "|", "?", "*"]
    # corrected_card_name = name
    # for char in bad_filename_chars:
    #     if name.__contains__(char):
    #         corrected_card_name = name.replace(char, "")
    
    # img_1 = requests.get(jpg_uri).content            
    # with open("C:\\Users\\jonas\\OneDrive\\Documents\\Magic\\Collection\\CardImages\\" + corrected_card_name + '.jpg', 'wb') as image:
    #     image.write(img_1)
    #     image.close()
    # if layout == "transform":
    #     img_2 = requests.get(jpg_uri_2).content            
    #     with open("C:\\Users\\jonas\\OneDrive\\Documents\\Magic\\Collection\\CardImages\\" + corrected_card_name + '2.jpg', 'wb') as image:
    #         image.write(img_2)
    #         image.close()


    return output, tcg_id, bool(foil)

#This function grabs cards, 100 at a time, and finds the price data for them on TCGPlayer
def get_tcg_price_data(foil_dict, id_array, export_file, read_mode, bearer):

    PUBLIC_KEY = "890efa26-03ba-4885-b820-d325f76a8a16"
    PRIVATE_KEY = "7b7b85bc-4114-44b8-b215-66c034ef2c9f"

    #will expire Thu Jul 30 16:15:15 GMT
    BEARER_TOKEN =  bearer

    if read_mode != "a":
        open(export_file, "w").close()
    
    foil_dictionary = foil_dict
    num_cards = len(id_array)
    #print(num_cards)
    card_count = 0
    cards_idd = 0
    response_dict = ""
    first_run = True
    while card_count + 1 <= num_cards:
        if card_count % 100 == 0:
            
            productID_string = ""
            for i in range(0, 100):
                #print(card_count + i)
                if card_count + i >= num_cards:
                    break
                else:
                    productID_string = productID_string + str(id_array[card_count + i]) + ","

            productID_string = productID_string[:len(productID_string) - 1]

            base_url = "https://api.tcgplayer.com/pricing/product/"
            url = base_url + productID_string

            headers = {"User-Agent": "Nautilus", "From": "nautilus.application@gmail.com", "accept": "application/json", "authorization": "bearer " + BEARER_TOKEN}

            response = requests.request("GET", url, headers=headers)
            response_dict = json.loads(response.text)
            #jprint(response_dict)
        #id: {directLow: xx.xx, market: xx.xx, lo: xx.xx, mid: xx.xx, hi: xx.xx}
        cards_in_run = 0
        with open(export_file, mode="a", newline="") as csv_file:
        
            fieldnames = ["tcgplayer_id", "directLow", "market", "low", "mid"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            
            if read_mode != "a" and first_run == True:
                writer.writeheader()
                first_run = False
            
            directLow = 0
            market = 0
            low = 0
            mid = 0
            #jprint(response_dict)
            for product in response_dict["results"]:
                product_ID = product["productId"]
                  
                if product["subTypeName"] == "Foil":
                    if(foil_dictionary[product_ID] == "TRUE"):
                        cards_in_run += 1
                    product_ID = str(product_ID) + " (Foil)"
                else:
                    if foil_dictionary[product_ID] == "FALSE":
                        cards_in_run += 1
                    product_ID = str(product_ID) + " (Nonfoil)"
                
                directLow = product["directLowPrice"]
                market = product["marketPrice"]
                low = product["lowPrice"]
                mid = product["midPrice"]
                writer.writerow({"tcgplayer_id": product_ID, "directLow": directLow, "market": market,
                    "low": low, "mid": mid})
                #print(card_count)
                #print(cards_in_run)
                
        print(cards_in_run)
        card_count += cards_in_run
        print(card_count)
