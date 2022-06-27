from calendar import c
import requests
import os
import time
import json
# Results 6/26/2022: Consistently ~10s, no longer than 25s for dictionary construction.
# Need to test csv or pandas construction to insert into Excel 
# Then need to set up the new method for pricing... may as well make it for every card lol
# Only like 600 pings of TCG's API in one go... we can do it!

# Config stuff for TCG's API
_PUBLIC_KEY = os.environ.get('TCG_PUBLIC_KEY')
_PRIVATE_KEY = os.environ.get('TCG_PRIVATE_KEY')
_BEARER_TOKEN = ""


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
        tcg_id, tcg_e_id, etched_dup, card_info = process_card(card)
        
        # Add it to our card dictionary
        card_count += 1
        cards.update({card_count: card_info})

        # If we need to repeat a card to get all foilings of it, do so
        if etched_dup:
            card_info["tcgplayer_id"] = tcg_id
            card_info["foil_type"] = ""
            card_count += 1
            cards.update({card_count: card_info})
    
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

    if card["layout"] == "token" or card["layout"] == "double_faced_token" or card["layout"] == "emblem" or card["layout"] == "art_series":
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
    foil_type = ""
    tcgplayer_etched_id = ""
    etched_dup = False

    # Save the cardname, set, and set code from the json object.
    # There should not be any strange errors with these attributes not existing.
    cardname = card["name"]
    set_name = card["set_name"]
    set_code = card["set"]
    collector_num = card["collector_number"]

    # Unfortunately, some extra processing does need to be done on the card name.
    # This is where problematic characters are removed (currently none known via this method of data collection),
    # as well as multi-face/side/mode cards are stripped down to a single name. We only care about the front face.
    # Note that Kamigawa flips take the top (normal) name and the weird coin flip SLD cards are stripped to one name.
    # Split cards (including aftermath cards) should be entered into the system with a // between card names.
    layout = card["layout"]
    if layout == "transform" or layout == "flip" or layout == "adventure" or layout == "modal_dfc" or layout == "reversible_card":
        name = card["name"].split("//")[0].strip()

    # Card styles:
    # Extended (same art, just zoomed in to full card width)
    # Borderless (different art, no stupid black bars next to the text box lol) (includes English Mystical Archives despite my personal disagreement)
    # Showcase (alternate art + special frame style)
    # Retro ('97 frame on cards printed after the shift to the modern frame styles)
    # Phyrexian (the card is written in phyrexian)
    # Godzilla (the card is part of the Godzilla series, to distinguish from normal borderless in IKO)
    # JP Alt Walker (the card is one of the War of the Spark alt-art planeswalkers)
    # Promo Pack (the card has a planeswalker promo stamp) (only used to distinguish between XXXs and XXXp collector #s)
    # Prerelease (the card has a date stamp) (only used to distinguish between XXXs and XXXp collector #s)
    
    style_type = ""
    try:
        #Showcase and extended variants are listed as frame effects
        for frame_effect in card["frame_effects"]:

            if frame_effect == "showcase":
                style_type = "Showcase"
                break
        
            if frame_effect == "extendedart":
                style_type = "Extended"
                break

    # If there are no relevant frame effects, we move on
    except:
        pass

    # 1997 frame with release after 8th edition - retro frame!
    if card["frame"] == "1997" and time.strptime(card["released_at"], "%Y-%m-%d") > time.strptime("2003-07-28", "%Y-%m-%d"):
        style_type = "Retro"

    # Check border_color for borderless
    if card["border_color"] == "borderless":
        style_type = "Borderless"

    # Now we enter collector number based criteria
    cnum = card["collector_number"]
    
    # JP Walkers - contains U+2605, star
    if card["lang"] == "ja" and cnum.__contains__("\u2605"):
        style_type = "JP Alt Walker"
        pass

    # s is Prerelease
    if cnum.__contains__("s"):
        style_type = "Prerelease"
        pass
    
    # p is Promo Pack
    if cnum.__contains__("p"):
        style_type = "Promo Pack"
        pass

    try:
        # Godzilla - IKO, #275, #370+
        if card["set"] == "iko" and (cnum == "275" or int(cnum) >= 371):
            style_type = "Godzilla"
    except:
        pass
            
    # If the language is phyrexian, the style is Phyrexian
    if card["lang"] == "ph":
        style_type = "Phyrexian"
    
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
            color_sort = "7"
        #Unfortunately, lands are colorless, so we need to separate them
        elif len(colors) == 0:
            typeline = ""
            try:
                typeline = str(card["type_line"]).lower().split(" // ")[0]
            except:
                typeline = str(card["type_line"]).lower()
            if typeline.__contains__("land"):
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
    
    if card["name"] == "Dryad Arbor":
        color_sort = 1

    # Special foil types
    # Etched* (the cards have any of the etched foiling styles, that is, Commander Legends inverted, Mystical Archive highlights, Modern Horizons 2 retro frame)
    # Gilded (the cards have the gilded embossed foil treatment) (***CURRENTLY ONLY CAPABLE OF HANDLING SNC #362-405*** until Scryfall adds gildedness to the API)
    # Textured (the cards have the textured foil treatment) (***CURRENTLY ONLY CAPABLE OF HANDLING 2X2 #573-577*** until Scryfall adds texturedness to the API)

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
        if card["set"] == "snc" and cnum >= 362 and cnum <= 405:
            foil_type = "Gilded"

        if card["set"] == "2x2" and cnum >= 573 and cnum <= 577:
            foil_type = "Textured"
    except:
        pass
    
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
    if foil_type == "Etched":
        output = {"tcgplayer_id": tcgplayer_etched_id, "cardname": cardname, "set_name": set_name, "set_code": set_code, "style_type": style_type, "foil_type": foil_type, "collector_num": collector_num, "color": color, "color_sort": color_sort}
    else:
        output = {"tcgplayer_id": tcgplayer_id, "cardname": cardname, "set_name": set_name, "set_code": set_code, "style_type": style_type, "foil_type": foil_type, "collector_num": collector_num, "color": color, "color_sort": color_sort}
    
    return tcgplayer_id, tcgplayer_etched_id, etched_dup, output

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
    
    toc = time.perf_counter()
    print(total_count)
    print(f"Run time: {toc - tic:0.4f} s")

    return card_prices

cards, card_count = download_bulk_data()
prices = get_tcg_pricing(cards, card_count)
    


# jprint(download_bulk_data())
