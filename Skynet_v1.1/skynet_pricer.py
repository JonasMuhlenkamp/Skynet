import requests
import os
import time
import json
import pandas

# Results 6/26/2022: Consistently ~10s, no longer than 25s for card dictionary construction.
# Results 6/27/2022: Just over three minutes is the rough runtime for full price acquisition. 
# Looking at a 4 minute process for full update before considering the time for xlwings.
# Not saving any specific files means that there will likely be some time loss on repetition.

# Config stuff for TCG's API
_PUBLIC_KEY = os.environ.get('TCG_PUBLIC_KEY')
_PRIVATE_KEY = os.environ.get('TCG_PRIVATE_KEY')

def jprint(obj):
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)
    return text

def download_bulk_data():
    '''
    Accesses Scryfall's bulk data download for a .json file containing every default
    card in Magic. The result is a Python dictionary containing every relevant card,
    its set, style, foil type, color, and most importantly its unique TCGPlayer ID.

    Consistently creates the dictionary of ~57000 cards in under 30 seconds.
    '''
    tic = time.perf_counter()

    # Access the api for the link to download the card data
    url = "https://api.scryfall.com//bulk-data//default_cards"
    response = requests.get(url)
    response_dict = json.loads(response.text)
    data_url = response_dict["download_uri"]
    print(data_url)

    # Download the data
    data = requests.get(data_url, allow_redirects=True)
    response_dict = json.loads(data.text)

    # For every card in the bulk data file
    card_count = 0
    cards = {}
    for card in data.json():

        # Check if we want to use the card
        if check_card(card) == False:
            continue

        # Get the info we want in an organized format
        tcg_id, etched_dup, card_info = process_card(card)
        card_info2 = card_info.copy()
        
        # Tick up the card count
        card_count += 1
        card_info["card_id"] = card_count

        # we create the master name for ease of search in Excel
        master_name = card_info["cardname"] + " (" + card_info["set_name"] + ")"
        if card_info["style_type"] != "":
            master_name = master_name + " (" + card_info["style_type"] + ")"
        if card_info["foil_type"] != "":
            master_name = master_name + " (" + card_info["foil_type"] + ")"
        card_info["master_name"] = master_name

        # Add it to our card dictionary
        update = {card_count: card_info}
        cards.update(update)

        # If we need to repeat a card to get all foilings of it, do so
        # The etched version is sent over first, so this instance needs to be non-etched
        if etched_dup:
            card_count += 1
            card_info2["card_id"] = card_count

            # Adjustments for the non-etched version
            card_info2["tcgplayer_id"] = tcg_id
            card_info2["foil_type"] = ""

            # we create the master name for ease of search in Excel
            master_name = card_info2["cardname"] + " (" + card_info2["set_name"] + ")"
            if card_info2["style_type"] != "":
                master_name = master_name + " (" + card_info2["style_type"] + ")"
            if card_info2["foil_type"] != "":
                master_name = master_name + " (" + card_info2["foil_type"] + ")"
            card_info2["master_name"] = master_name

            update = {card_count: card_info2}
            cards.update(update)

    print(card_count)

    toc = time.perf_counter()
    print(f"Run time: {toc - tic:0.4f} s")

    return cards, card_count

def check_card(card):
    '''
    Eliminates non-useful objects in the data dump, such as online-only versions
    of cards, basic lands, tokens and their ilk.
    Cleans languages too.
    Also a spot to exclude specific sets if you want, but this isn't recommended.
    '''
    paper = False
    for game in card["games"]:
        if game == "paper":
            paper = True
    if len(card["games"]) == 0: #6/26/2022: noticed a few cards (SNC promos) that are in paper that don't have any games in the api
        paper = True
    if paper == False:
        return False

    # Knocking out non-English and non-Phyrexian cards
    if card["lang"] != "en" and card["lang"] != "ph":
        
        # Checking for a very particular subset of JP cards
        # JP exclusive Godzillas, JP-alt Mystical Archives, and JP-alt WAR PWs (also catches JvC alts too lol)
        if card["lang"] == "ja":

            try:
                # Specific collector numbers for Archives  
                cnum = int(card["collector_number"])
                if card["set"] == "sta" and cnum >= 64:
                    return True

                # Specific collector numbers for Godzillas  
                if card["set"] == "iko" and cnum >= 385:
                    return True
            except:
                pass

            # Star for planeswalkers
            if card["collector_number"].__contains__("\u2605") and (card["set"] == "war" or card["set"] == "pwar"):
                return True
            
        return False

    try:
        if card["type_line"].__contains__("Basic") and card["lang"] != "ph":
            return False
    except:
        pass

    if card["set_type"] == "memorabilia" or card["set_type"] == "token":
        return False
    
    if card["set"] == "phuk" or card["set"] == "olgc" or card["set"] == "ovnt":
        return False

    if card["layout"] == "token" or card["layout"] == "double_faced_token" or card["layout"] == "emblem" or card["layout"] == "art_series":
        return False

    if card["variation"] == True and card["name"] != "Tamiyo's Journal":
        return False


    return True

def process_card(card):
    '''
    Processes a json card object by extracting the necessary information.
    We care about name, set, style, color, tcgplayer id, and foil type. 
    '''
    cardname = ""
    set_name = ""
    set_code = ""
    style_type = ""
    collector_num = ""
    color = ""
    color_sort = ""
    tcgplayer_id = ""
    rarity = ""
    foil_type = ""
    tcgplayer_etched_id = ""
    etched_dup = False

    # Save the cardname, set, and set code from the json object.
    # There should not be any strange errors with these attributes not existing.
    cardname = card["name"]
    set_name = card["set_name"]
    set_code = card["set"]
    collector_num = card["collector_number"]
    rarity = card["rarity"]

    # Unfortunately, some extra processing does need to be done on the card name.
    # This is where problematic characters are removed (currently none known via this method of data collection),
    # as well as multi-face/side/mode cards are stripped down to a single name. We only care about the front face.
    # Note that Kamigawa flips take the top (normal) name and the weird coin flip SLD cards are stripped to one name.
    # Split cards (including aftermath cards) should be entered into the system with a // between card names.
    layout = card["layout"]
    if layout == "transform" or layout == "flip" or layout == "adventure" or layout == "modal_dfc" or layout == "reversible_card":
        cardname = card["name"].split("//")[0].strip()

    # For the extremely odd cards that have multiple arts under the same collector number in the same set (ugh) we need to get 
    # a bit creative, sometimes literally. 
    cnum = card["collector_number"]
    if cnum.__contains__("a") or cnum.__contains__("b") or cnum.__contains__("c") or cnum.__contains__("d") or cnum.__contains__("e") or cnum.__contains__("f"):

        # Handling Unstable and Deckmasters (A, B, etc. variants that can be found on TCGPlayer) and Brothers Yamazaki
        if set_code == "ust" or set_code == "dkm" or cardname == "Brothers Yamazaki":
            cardname = cardname + " (" + cnum + ")"
        # One multiple-date PTK prerelease promo lol
        elif cardname.__contains__("Lu Bu") and set_code == "pptk":
            if cnum.__contains__("a"):
                cardname = cardname + " (April 29)"
            else:
                cardname = cardname + " (July 4)"

    # Just stapling the CN to the cardname (for all secret lairs and some other specific cards)
    if set_code == "sld" or (cardname.__contains__("Guildgate") and (set_code == "rna" or set_code == "grn")) or (cardname == "Teferi, Master of Time" and set_code == "m21"):
        cardname = cardname + " (" + cnum + ")"
    elif (cardname == "Runo Stromkirk" and set_code == "vow") or (cardname == "Lightning Bolt" and set_code == "plist"):
        cardname = cardname + " (" + cnum + ")"
    elif set_code == "ugl":
        if cnum == "28":
            cardname = cardname + " (Left)"
        elif cnum == "29":
            cardname = cardname + " (Right)"
    
    # Tamiyo's Journal
    if cardname == "Tamiyo's Journal":
        entry = " (434)"
        if cnum.__contains__("a"):
            entry = " (546)"
        elif cnum.__contains__("b"):
            entry = " (653)"
        elif cnum.__contains__("c"):
            entry = " (711)"
        elif cnum.__contains__("d"):
            entry = " (855)"
        elif cnum.__contains__("e"):
            entry = " (922)"
        
        cardname = cardname + entry

    # The few multi-art cards from Antiquities and Chronicles that I care about
    # Mishra's Factory, Strip Mine, and Urza's lands
    if set_code == "atq":
        if cardname == "Mishra's Factory":
            entry = ""
            if cnum.__contains__("a"):
                entry = " (Spring)"
            elif cnum.__contains__("b"):
                entry = " (Summer)"
            elif cnum.__contains__("c"):
                entry = " (Fall)"
            elif cnum.__contains__("d"):
                entry = " (Winter)"
            
            cardname = cardname + entry
        
        elif cardname == "Strip Mine":
            entry = ""
            if cnum.__contains__("a"):
                entry = " (No Horizon)"
            elif cnum.__contains__("b"):
                entry = " (Uneven Horizon)"
            elif cnum.__contains__("c"):
                entry = " (Tower)"
            elif cnum.__contains__("d"):
                entry = " (Even Horizon)"
            
            cardname = cardname + entry
        
        elif cardname == "Urza's Mine":
            entry = ""
            if cnum.__contains__("a"):
                entry = " (Pulley)"
            elif cnum.__contains__("b"):
                entry = " (Mouth)"
            elif cnum.__contains__("c"):
                entry = " (Clawed Sphere)"
            elif cnum.__contains__("d"):
                entry = " (Tower)"
            
            cardname = cardname + entry
        
        elif cardname == "Urza's Tower":
            entry = ""
            if cnum.__contains__("a"):
                entry = " (Forest)"
            elif cnum.__contains__("b"):
                entry = " (Shore)"
            elif cnum.__contains__("c"):
                entry = " (Plains)"
            elif cnum.__contains__("d"):
                entry = " (Mountains)"
            
            cardname = cardname + entry

        elif cardname == "Urza's Power Plant":
            entry = ""
            if cnum.__contains__("a"):
                entry = " (Sphere)"
            elif cnum.__contains__("b"):
                entry = " (Columns)"
            elif cnum.__contains__("c"):
                entry = " (Bug)"
            elif cnum.__contains__("d"):
                entry = " (Rock in Pot)"
            
            cardname = cardname + entry

    # Chronicles Urza's lands
    elif set_code == "chr":

        if cardname == "Urza's Mine":
            entry = ""
            if cnum.__contains__("a"):
                entry = " (Mouth)"
            elif cnum.__contains__("b"):
                entry = " (Clawed Sphere)"
            elif cnum.__contains__("c"):
                entry = " (Pulley)"
            elif cnum.__contains__("d"):
                entry = " (Tower)"
            
            cardname = cardname + entry
        
        elif cardname == "Urza's Tower":
            entry = ""
            if cnum.__contains__("a"):
                entry = " (Forest)"
            elif cnum.__contains__("b"):
                entry = " (Plains)"
            elif cnum.__contains__("c"):
                entry = " (Mountains)"
            elif cnum.__contains__("d"):
                entry = " (Shore)"
            
            cardname = cardname + entry

        elif cardname == "Urza's Power Plant":
            entry = ""
            if cnum.__contains__("a"):
                entry = " (Rock in Pot)"
            elif cnum.__contains__("b"):
                entry = " (Columns)"
            elif cnum.__contains__("c"):
                entry = " (Bug)"
            elif cnum.__contains__("d"):
                entry = " (Sphere)"
            
            cardname = cardname + entry

    # Card styles:
    # Extended (same art, just zoomed in to full card width)
    # Borderless (different art, no stupid black bars next to the text box lol) (includes English Mystical Archives despite my personal disagreement)
    # Showcase (alternate art + special frame style)
    # Retro ('97 frame on cards printed after the shift to the modern frame styles)
    # Phyrexian (the card is written in phyrexian)
    # Godzilla (the card is part of the Godzilla series, to distinguish from normal borderless in IKO)
    # Dracula (the card is part of the Dracula series, to distinguish from normal borderless in VOW)
    # JP Alt (the card is in Japanese and has alternate art) (currently only handles WAR PWs and Archives)
    # Alt Foil (some Unhinged cards, 10th edition foils, a few specific planeswalkers)
    # Promo Pack (the card has a planeswalker promo stamp) (only used to distinguish between XXXs and XXXp collector #s)
    # Prerelease (the card has a date stamp) (only used to distinguish between XXXs and XXXp collector #s)
    # Promo (bucket for pretty much all other promos that aren't in specific promo sets)
    
    style_type = ""
    try:
        #Showcase and extended variants are listed as frame effects
        for frame_effect in card["frame_effects"]:

            if frame_effect == "showcase":
                style_type = "Showcase"
                break
        
            elif frame_effect == "extendedart":
                style_type = "Extended"
                break

    # If there are no relevant frame effects, we move on
    except:
        pass
    
    # 1997 frame with release after 8th edition - retro frame!
    if card["frame"] == "1997" and time.strptime(card["released_at"], "%Y-%m-%d") > time.strptime("2003-07-28", "%Y-%m-%d") and card["set"] != "unh" and card["set"] != "und" and card["set"] != "plist" and card["set"] != "phed" and card["set"] != "mb1" and card["set"] != "fmb1":
        style_type = "Retro"

    # Check border_color for borderless
    elif card["border_color"] == "borderless":
        style_type = "Borderless"

    # Now we enter collector number based criteria
    # Alternate foils (this catches some oddballs, but I primarily need to distinguish them from their normal counterparts)
    elif (cnum.__contains__("\u2605") and card["lang"] != "ja" and not card["type_line"].__contains__("Scheme")) and not card["set_name"].__contains__("Promo") and not card["set_type"].__contains__("promo") or (card["name"] == "Will Kenrith" and cnum == "255" and card["set"] == "bbd") or (card["name"] == "Rowan Kenrith" and cnum == "256" and card["set"] == "bbd") or (card["name"] == "Kaya, Ghost Assassin" and cnum == "222" and card["set"] == "cn2"):
        style_type = "Alt Foil"
        
    # s is Prerelease
    elif cnum[-1].__contains__("s"):
        style_type = "Prerelease"
    
    # p is Promo Pack
    elif cnum[-1].__contains__("p"):
        style_type = "Promo Pack"

    # If the language is phyrexian, the style is Phyrexian
    elif card["lang"] == "ph":
        style_type = "Phyrexian"

    # These are more specific styles that sometimes also have more basic styles, but I want them separated
    # JP Walkers - contains U+2605, star, JP Archives - set:sta
    if card["lang"] == "ja" and (cnum.__contains__("\u2605") or card["set"] == "sta"):
        style_type = "JP Alt"

    # Godzilla - IKO, #275, #370+, corrections to ikoria showcase cards because stupid
    elif card["set"] == "iko":
        try: 
            if (cnum == "275" or int(cnum) >= 371):
                style_type = "Godzilla"
                cardname = cardname + " (" + card["flavor_name"] + ")"
            elif style_type == "Borderless" and (int(cnum) >= 279 or int(cnum) <= 313):
                style_type = "Showcase"
        except:
            pass

    # Dracula - VOW, #403, #329-345
    elif card["set"] == "vow":
        try: 
            if (cnum == "403" or (int(cnum) >= 329 and int(cnum) <= 345)):
                style_type = "Dracula"
                cardname = cardname + " (" + card["flavor_name"] + ")"
        except:
            pass

    # One last check to fix some promo problems
    if (style_type == "" or style_type == "Extended") and ((card["promo"] == True and card["set_type"] != "promo") or (card["name"] == "Dragonsguard Elite" and cnum == "376")):
        style_type = "Promo"
    
    # Color and color sort
    # Color sort is needed to tell the system what WUBRGMCL is :)
    try:
        colors = []
        
        #Awkwardly, transform cards have their colors within their card_face objects
        if layout == "transform" or layout == "modal_dfc":
            colors = card["card_faces"][0]["colors"]
        else:
            colors = card["colors"]

        #Multiple colors -> multicolored :)
        if len(colors) > 1:
            color = "Multi"
            color_sort = "6"
        #Unfortunately, lands are colorless, so we need to separate them
        elif len(colors) == 0:
            typeline = ""
            try:
                typeline = str(card["type_line"]).lower().split(" // ")[0]
            except:
                typeline = str(card["type_line"]).lower()
            if typeline.__contains__("land"):
                color = "Land"
                color_sort = "8"
            else:
                color = "Colorless"
                color_sort = "7"
        else:
            for card_color in colors:
                if card_color == "W":
                    color = "White"
                    color_sort = "1"
                elif card_color == "U":
                    color = "Blue"
                    color_sort = "2"
                elif card_color == "B":
                    color = "Black"
                    color_sort = "3"
                elif card_color == "R":
                    color = "Red"
                    color_sort = "4"
                elif card_color == "G":
                    color = "Green"
                    color_sort = "5"
                else:
                    pass
    except:
        pass
    
    if card["name"] == "Dryad Arbor":
        color_sort = 8

    # Special foil types
    # Etched* (the cards have any of the etched foiling styles, that is, Commander Legends inverted, Mystical Archive highlights, Modern Horizons 2 retro frame)
    # Gilded (the cards have the gilded embossed foil treatment) (***CURRENTLY ONLY CAPABLE OF HANDLING SNC #362-405*** until Scryfall adds gildedness to the API)
    # Textured (the cards have the textured foil treatment) (***CURRENTLY ONLY CAPABLE OF HANDLING 2X2 #573-577*** until Scryfall adds texturedness to the API)
    # Neon Red, Green, Blue, Yellow (the stupid Hidetsugu, Devouring Chaos ultra rare variants)
    # Galaxy (Unfinity?)
    # Surge (Warhammer 40k?)

    # *Note that cards can be etched and borderless (STA and some secret lair cards), and etched and retro (Modern Horizons 2 and some secret lair cards)
    for finish in card["finishes"]:
        if finish == "etched":
            foil_type = "Etched"
        elif finish == "gilded":
            foil_type = "Gilded"
        elif finish == "textured":
            foil_type = "Textured"

    try:
        cnum = int(card["collector_number"])
        if card["set"] == "snc" and cnum >= 361 and cnum <= 405:
            foil_type = "Gilded"

        if card["set"] == "2x2" and cnum >= 573 and cnum <= 577:
            foil_type = "Textured"
    except:
        pass

    if card["name"] == "Hidetsugu, Devouring Chaos":
        if cnum == 429:
            foil_type = "Neon Red"
        elif cnum == 430:
            foil_type = "Neon Green"
        elif cnum == 431:
            foil_type = "Neon Blue"
        elif cnum == 432:
            foil_type = "Neon Yellow"
    
    # Due to Scryfall's handling of etched cards, some need to be duplicated because their etched entries have been folded into another entry
    # This applies currently to Mystical Archives and Modern Horizons 2 Retro Frames.
    # The good news, however, is that every other attribute of the card that we care about is the same! So we just need to change the foil_type. 
    if foil_type == "Etched":
        try:
            tcgplayer_etched_id = str(card["tcgplayer_etched_id"])

            try:
                tcgplayer_id = str(card["tcgplayer_id"])
                etched_dup = True
            except:
                etched_dup = False
        except:
            pass

    # The final piece of the card object we need is its tcgplayer_id, which might not exist :)
    try:
        tcgplayer_id = str(card["tcgplayer_id"])
    except:
        pass

    # We assemble everything into a dictionary for output
    # If we are sending out an etched card, send it with the etched id
    output = {}
    if foil_type == "Etched":
        output = {"master_name": "", "card_id": "", "cardname": cardname, "set_name": set_name, "style_type": style_type, "foil_type": foil_type, "tcgplayer_id": tcgplayer_etched_id, "set_code": set_code, "rarity": rarity, "collector_num": collector_num, "color": color, "color_sort": color_sort}
    else:
        output = {"master_name": "", "card_id": "", "cardname": cardname, "set_name": set_name, "style_type": style_type, "foil_type": foil_type, "tcgplayer_id": tcgplayer_id, "set_code": set_code, "rarity": rarity, "collector_num": collector_num, "color": color, "color_sort": color_sort}
    
    return tcgplayer_id, etched_dup, output

def update_bearer():
    
    #Set up the headers and keys for the post request 
    headers = {"User-Agent": "Nautilus", "From": "nautilus.application@gmail.com", "application": "x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials", "client_id": _PUBLIC_KEY, "client_secret": _PRIVATE_KEY}

    #Request the token
    response = requests.post("https://api.tcgplayer.com/token", headers=headers, data=data)
    response_dict = json.loads(response.text)

    #Save the token in the environment variables
    BEARER_TOKEN = response_dict["access_token"]
    expire_date = response_dict[".expires"]
    print("Update successful.  Token will expire on " + str(expire_date))
    return BEARER_TOKEN

def get_tcg_pricing(cards, card_count):

    # Update the token so that prices can be accessed
    BEARER_TOKEN = update_bearer()

    # We will create a dictionary of all prices
    card_prices = {}

    # We have to go 250 cards at a time
    productId = ""
    priceCounter = 0

    # Run for X complete sets of 250, then run one set of X extra cards
    num_even_cycles = card_count // 250
    extra_cards = card_count % 250

    tic = time.perf_counter()
    # Loop over all cards in the dictionary
    cycle_count = 0
    total_count = 0
    for card in cards.items():
        
        # Build the productId string
        productId += card[1]["tcgplayer_id"] + ","
        priceCounter += 1
        total_count += 1

        # Max 250 ids per ping
        if (priceCounter == 250 or (priceCounter == extra_cards and cycle_count == num_even_cycles)):

            url = "https://api.tcgplayer.com/pricing/product/" + str(productId)
            headers = {"User-Agent": "Nautilus", "From": "nautilus.application@gmail.com", "accept": "application/json", "authorization": "bearer " + BEARER_TOKEN}

            response = requests.request("GET", url, headers=headers)
            response_dict = json.loads(response.text)
            prices = response_dict["results"]

            # Grab and save all the prices
            for price in prices:
                
                # Saving all the data because we may as well
                card_price = {"lowPrice": price["lowPrice"], "midPrice": price["midPrice"], "highPrice": price["highPrice"], "marketPrice": price["marketPrice"], "directLowPrice": price["directLowPrice"], "subTypeName": price["subTypeName"],"productId": price["productId"]}
                
                # Save the card in the dictionary with identifier ID (Foil), i.e. "123456 (Normal)" and "123456 (Foil)"
                card_foiling = price["subTypeName"]
                card_id = str(price["productId"])
                system_id = card_id + " (" + card_foiling + ")"
                card_prices.update({system_id: card_price})

            # Reset for the next cycle
            priceCounter = 0
            productId = ""
            cycle_count += 1

            # break #temp break to save time
    
    toc = time.perf_counter()
    print(total_count)
    print(f"Run time: {toc - tic:0.4f} s")

    return card_prices