'Input Excel File's Full Path
ExcelFilePath = "C:\Users\freed\Skynet\Skynet.xlsm"

'Input Module/Macro name within the Excel File
MacroPath = "Module1.AutoPrice"

'Create an instance of Excel
Set ExcelApp = CreateObject("Excel.Application")

'Do you want this Excel instance to be visible?
ExcelApp.Visible = False

'Prevent any App Launch Alerts (ie Update External Links)
ExcelApp.DisplayAlerts = False

'Open Excel File
Set wb = ExcelApp.Workbooks.Open(ExcelFilePath)

'Execute Macro Code
ExcelApp.Run MacroPath

' 'Give the macro a few seconds to finish refreshing the data
' newHour = Hour(Now())
' newMinute = Minute(Now())
' newSecond = Second(Now()) + 10
' waitTime = TimeSerial(newHour, newMinute, newSecond)
' ExcelApp.Wait waitTime

'Save Excel File (if applicable)
wb.Save

'Reset Display Alerts Before Closing
ExcelApp.DisplayAlerts = True

'Close Excel File
wb.Close

'End instance of Excel
ExcelApp.Quit

'Leaves an onscreen message!
MsgBox "Skynet Case Prices successfully updated at " & TimeValue(Now), vbInformation