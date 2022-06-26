from skynet.utilities import create_tcgplayer_arrays, get_tcg_price_data, download_bulk_data, process_bulk_data, update_bearer

def main(option):

    #Download bulk data and process.  This is set to run once a week, so the TCG bearer token will update alongside it
    if option == "l":
        
        print("Downloading bulk data from Scryfall...")
        filepath_in = "C:\\Users\\jonas\\Code\\MagicCodingProjects\\Skynet\\CSVFiles\\bulk-card-data.json"
        filepath_out = "C:\\Users\\jonas\\Code\\MagicCodingProjects\\Skynet\\CSVFiles\\processed_card_data.csv"
        download_bulk_data(filepath_in)
        print("Download complete.")
        print("Processing bulk data...")
        tcg_ids, foiling = process_bulk_data(filepath_in, filepath_out)
        print("Processing complete.")

    #Update prices
    elif option == "u":

        foil, ids = create_tcgplayer_arrays("C:\\Users\\jonas\\Code\\MagicCodingProjects\\Skynet\\CSVFiles\\cards_to_price.csv", 2)
        #print(ids)
        bearer = update_bearer()
        get_tcg_price_data(foil, ids, "C:\\Users\\jonas\\Code\\MagicCodingProjects\\Skynet\\CSVFiles\\card_prices.csv", "w", bearer)

    #Add cards
    elif option == "a":

        foil, ids = create_tcgplayer_arrays("C:\\Users\\jonas\\Code\\MagicCodingProjects\\Skynet\\CSVFiles\\cards_to_price.csv", 2)
        bearer = update_bearer()
        get_tcg_price_data(foil, ids, "C:\\Users\\jonas\\Code\\MagicCodingProjects\\Skynet\\CSVFiles\\card_prices.csv", "a", bearer)

    #Update the bearer token
    elif option == "ub":

        update_bearer()
