import xlwings as xw
import pandas
from datetime import datetime
from skynet_pricer import download_bulk_data, get_tcg_pricing
import win32api

'''
These methods are meant to be called from within macro-activated functions.
They do not establish the active workbook on their own; this should be 
communicated via the wb and sheet parameters. 
'''
def last_row(sheet):
    '''Returns the number of the last row with data in a sheet.'''
    try:
        return sheet.api.Cells.Find(What="*",
                After=sheet.api.Cells(1, 1),
                LookAt=xw.constants.LookAt.xlPart,
                LookIn=xw.constants.FindLookIn.xlFormulas,
                SearchOrder=xw.constants.SearchOrder.xlByRows,
                SearchDirection=xw.constants.SearchDirection.xlPrevious,
                MatchCase=False).Row
    except:
        return 1

def last_column(sheet):
    '''Returns the number of the last column with data in a sheet.'''
    try:
        return sheet.api.Cells.Find(What="*",
                After=sheet.api.Cells(1, 1),
                LookAt=xw.constants.LookAt.xlPart,
                LookIn=xw.constants.FindLookIn.xlFormulas,
                SearchOrder=xw.constants.SearchOrder.xlByColumns,
                SearchDirection=xw.constants.SearchDirection.xlPrevious,
                MatchCase=False).Column
    except:
        return 1
            
def build_master_name(input_card):
    '''Input: [cardname, setname, style, foil, error]
    Creates the search name of the card object.
    Ex. Arid Mesa (Modern Horizons 2) (Retro) (Etched).'''

    if input_card[4] == "Error!": 
        return "Error"

    master_name = input_card[0] + " (" + input_card[1] + ")"
    style = input_card[2]
    foil = input_card[3]
    if style is not None:
        master_name = master_name + " (" + style + ")"
    if foil is not None:
        master_name = master_name + " (" + foil + ")"
    
    return master_name 

def add_cards(sheet, wb):
    '''Adds cards from the entry field into a given sheet.
    sheet: the wb.sheets["name"] sheet that will be manipulated
    wb: the workbook object
    '''
    
    # check the entry field for errors and warn the user
    error_check = wb.sheets["Input"].range("f9").value.split(" ")[2].strip()
    if int(error_check) > 0:
        win32api.MessageBox(wb.app.hwnd, "Errors have been detected in your input! Please check that the card is spelled correctly and that you have assembled a correct " + 
            "combination of set, style, and foiling.\n\nYou can use the Card Search function for additional help.", "Input Error Detected")
        return
    
    # Acquire the input data
    last_input_row = min(260, wb.sheets["Input"].range("B" + str(wb.sheets["Input"].cells.last_cell.row)).end('up').row)
    if last_input_row > 9:
        input_range = wb.sheets["Input"].range("B10:F" + str(last_input_row)).value

        input_list = []
        error_list = []
        error_row_list = []
        count = 1

        # For each input
        for element in input_range:
            
            # Make its master name
            master_name = build_master_name(element)
            
            # If there is an error, save it for an alert later
            if master_name == "Error":
                error_list.append(element[0])
                error_row_list.append(count)
            else:
                input_list.append([master_name])
            
            count += 1

        # Copy the formulas into the next row
        formulas = sheet.range("a2:x2").copy()
        next_sheet_row = last_row(sheet) + 1
        end_input_row = next_sheet_row + len(input_range) - 1 - len(error_list)
        sheet.range("a" + str(next_sheet_row) + ":x" + str(end_input_row)).paste(paste="formulas_and_number_formats")
        
        # Set the B column (names) to the input list
        sheet.range("b" + str(next_sheet_row)).options(ndim=2).value = input_list

        # Issue message box error alerts for any input errors (hopefully none sneak through)
        for idx in range(len(error_list)):
            win32api.MessageBox(wb.app.hwnd, "Input error: " + error_list[idx] + ", row " + str(error_row_list[idx] + 9), "Failure - Input Error")

def remove_cards(sheet, wb):
    '''Removes the cards listed in the entry field from a sheet if they are found.
    sheet: the wb.sheets["name"] sheet that will be manipulated
    wb: the workbook object
    '''

    # Check for erroneous entries and alert
    error_check = wb.sheets["Input"].range("f9").value.split(" ")[2].strip()
    if int(error_check) > 0:
        win32api.MessageBox(wb.app.hwnd, "Errors have been detected in your input! Please check that the card is spelled correctly and that you have assembled a correct " + 
            "combination of set, style, and foiling.\n\nYou can use the Card Search function for additional help.", "Input Error Detected")
        return

    # Save the input data
    last_input_row = min(250, wb.sheets["Input"].range("B" + str(wb.sheets["Input"].cells.last_cell.row)).end('up').row)
    if last_input_row > 9:
        input_range = wb.sheets["Input"].range("B10:F" + str(last_input_row)).value

        input_list = []
        error_list = []
        error_row_list = []
        count = 1
        for element in input_range:
            master_name = build_master_name(element)
            if master_name == "Error":
                error_list.append(element[0])
                error_row_list.append(count)
            else:
                input_list.append(master_name)
            count += 1

        # Pull the cardnames from the sheet        
        last_data_row = last_row(sheet)
        cardnames = sheet.range("b4:b" + str(last_data_row)).value

        # Loop over the cards to remove and the cardname list and store the row numbers to be removed
        rows_to_remove = []
        failed_searches = []
        for element in input_list:
            current_row = 4
            card_found = False
            for name in cardnames:
                try:
                    if name.lower() == element.lower():
                        card_found = True
                        rows_to_remove.append(current_row)
                    current_row += 1
                except:
                    current_row += 1
            if card_found == False:
                failed_searches.append(element)
        
        # Run through the rows that need to be removed and remove them
        rows_removed = 0
        for row in rows_to_remove:
            sheet.range(str(row - rows_removed) + ":" + str(row - rows_removed)).delete()
            rows_removed += 1

        # Send out error alerts
        for idx in range(len(error_list)):
            win32api.MessageBox(wb.app.hwnd, "Input error: " + error_list[idx] + ", row " + str(error_row_list[idx] + 9), "Failure - Input Error")    

        for remnant in failed_searches:
            win32api.MessageBox(wb.app.hwnd, "Card not found error: " + remnant + " not found in " + sheet.name, "Failure - Card Not Found")

def track_prices(wb):

    # Grab the entire price history in the sheet and move it over two columns
    price_tracking = wb.sheets["Price Tracking"]
    ptcolumn = last_column(price_tracking)
    ptrow = last_row(price_tracking)
    old_prices = price_tracking.range("a1", (ptrow, ptcolumn)).copy()
    price_tracking.range("c1").paste()

    # Get the most up to date prices from the pricing sheet and copy it over
    prices = wb.sheets["Pricing"]
    prow = last_row(prices)
    ids = prices.range("a1:a" + str(prow)).copy()
    price_tracking.range("a1").paste()
    new_prices = prices.range("k1:k" + str(prow)).copy()
    price_tracking.range("b1").paste(paste="values")

    # Add the date so the system knows what it is looking at
    prices.range("a1").value = datetime.now().strftime("%m/%d/%Y")

'''
These methods are designed to be called from macros in VBA.
'''
def update_system():
    '''
    Updates the cardlist and pricing of the system.
    '''
    # Set the workbook
    wb = xw.Book.caller()

    # Update price history
    track_prices(wb)

    # Update cards and prices (takes about 3 minutes)
    cards, card_count = download_bulk_data()
    prices = get_tcg_pricing(cards, card_count)

    # Create the dataframes 
    cards_df = pandas.DataFrame.from_dict(cards, orient="index")
    cards_df = cards_df.sort_values(by=['cardname', 'set_name', 'style_type', 'foil_type'])

    prices_df = pandas.DataFrame.from_dict(prices, orient="index")
    prices_df = prices_df.sort_index()

    # These actions refer to named ranges
    # Update the data in the spreadsheet
    xw.Range("Cards").clear()
    xw.Range("Cards").value = cards_df

    xw.Range("CurrentPrices").clear()
    xw.Range("CurrentPrices").value = prices_df
    
    # Update the spreadsheet most recent date
    wb.sheets["Pricing"].range("a1").value = datetime.now().strftime("%m/%d/%Y")

def eternal_add():

    wb = xw.Book.caller()
    sheet = wb.sheets["Eternal Case"]
    add_cards(sheet, wb)

def standard_add():

    wb = xw.Book.caller()
    sheet = wb.sheets["Standard Case"]
    add_cards(sheet, wb)

def new_set_add():

    wb = xw.Book.caller()
    sheet = wb.sheets["New Set Case"]
    add_cards(sheet, wb)

def eternal_remove():

    wb = xw.Book.caller()
    sheet = wb.sheets["Eternal Case"]
    remove_cards(sheet, wb)

def standard_remove():

    wb = xw.Book.caller()
    sheet = wb.sheets["Standard Case"]
    remove_cards(sheet, wb)

def new_set_remove():

    wb = xw.Book.caller()
    sheet = wb.sheets["New Set Case"]
    remove_cards(sheet, wb)
