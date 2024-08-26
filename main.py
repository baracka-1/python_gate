import cv2
import time
import datetime
import re
import threading
from tkinter import *
from tkinter import messagebox
from PIL import ImageTk, Image
from tesseract_extract import Camera
from gate_manager import Gate
import sys
from algorithms import Algorithms

#TODO:https://azsiacenter.com/elektronika/433mhz-cc1101-usb-vezetek-nelkuli-ado-vevo-modul-23881.html
#TODO:https://shop.tavir.hu/termek/shop/kiegeszitok/kommunikacio/433-mhz-transmitter-ado-vevo-modulpar/
#TODO:https://malnapc.hu/raspberry-pi-4-model-b-1gb?gad=1&gclid=CjwKCAjw67ajBhAVEiwA2g_jEK8dZyTeQLaPfpQASuP6ru-W749aKSt-OqhAi1h3WpKEAhkB-6A2JRoCXAwQAvD_BwE

#TODO: Amikor a kapu kinyílik majd magától visszacsukódik a rendszer újra felismeri azt a képet amivel kinyílt.
#TODO: Lehetséges megoldás, hogy a zárás megkezdésekör csinálunk egy képet, ami nem fut át a Tesseracton. (Valószínűleg sikerült megoldani)

#TODO: Amikor a kapu kinyílik, a tesseract csinál mégegy utolsó képet. Ha a képen ugyancsak egyezik a rendszám,
#TODO: kétszer küld nyitó és csukójelet is. (Lehetséges megoldás, hogy a nyitást 5 másodpercenként engedélyezzük.)

#TODO: Bejelentkezési felület létrehozása

#TODO: Mindegyik programnak/vállalatnak/telepítési helynek legyen egy saját azonosítója.
#TODO: Lekérjük ezt az azonosítót egy felhőből, hogy érvényes-e még az előfizetés

#TODO: Beállítani a megfelelő konfigurációt a Tesseractnek.

isitWithGUI = True
isGateOpen = True                #TODO: Időleges
canGateMove = True
isGateMovedBySystem = False
threshold = 0.81

automaticClosing = None
timefor_gatetochangeposition = None
timefor_gatetocloseafteropening = None

passwordForGui = "b3F9qL6M\n"

pattern1 = r'[A-Z]{3}\d{3}'

authorizedPlate = []
unAuthorizedPlate = []

gateOpenings_thisMonth = 0
gateOpenings_thisWeek = 0
gateOpenings_thisDay = 0

class MessageBox:
    def sendMessageBoxToUser(type, title, text):
        if type == "info":
            messagebox.showinfo(title, text)
        elif type == "warning":
            messagebox.showwarning(title, text)
        elif type == "error":
            messagebox.showerror(title, text)
        else:
            print("Helytelen típus.")
        
class FileManager:
    def sendToLog(function, functionState, licensePlate):
        now = datetime.datetime.now()
        dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
        with open(Algorithms.resourcePath("log.txt"), 'a') as f:
            if licensePlate:
                f.write(dt_string + ": " + function + ": " + functionState + " % Rendszám:" + licensePlate + "\n") 
            else:
                f.write(dt_string + ": " + function + ": " + functionState + "\n")
    def deleteWholeFile(filename):
        with open(Algorithms.resourcePath(""+filename+".txt"), "w") as f:
            f.write("")
        FileManager.sendToLog("Eseménynapló törlése", "Sikeres", None)
    def openFile(string):
        with open(Algorithms.resourcePath(string), 'r') as f:
            if string == "authorizedNumberPlates.txt":
                for line in f:
                    authorizedPlate.append(line.strip())
            elif string == "unauthorizedNumberPlates.txt":
                for line in f:
                    unAuthorizedPlate.append(line.strip())
            elif string == "log.txt":
                logstring = ""
                for line in f:
                    logstring += line.strip() + "\n"
                return logstring
            elif string == "settings.txt":
                lines = f.readlines()
                if len(lines) >= 3:
                    global automaticClosing
                    global timefor_gatetochangeposition
                    global timefor_gatetocloseafteropening
                    automaticClosing = lines[0].strip().lower() == "true"
                    timefor_gatetochangeposition = int(lines[1].strip())  
                    timefor_gatetocloseafteropening = int(lines[2].strip())  
    def refreshVariables():
        global automaticClosing
        global timefor_gatetochangeposition
        global timefor_gatetocloseafteropening
        with open(Algorithms.resourcePath("settings.txt"), 'w') as f:
            f.write(str(automaticClosing) + "\n" + str(timefor_gatetochangeposition) + "\n" + str(timefor_gatetocloseafteropening))

    def saveToFile(numberPlate, img):
        saveImagesTo = "licenseplates/unauthorizedVehicles/unauthorizedVehicle_"+numberPlate+".jpg"
        pictureSaved = cv2.imwrite(Algorithms.resourcePath(saveImagesTo), img)
        if pictureSaved:
            print("Kép mentve")
        else:
            print("Nem sikerült a kép mentése")
        with open(Algorithms.resourcePath("unauthorizedNumberPlates.txt"), 'a') as f:
            f.write(numberPlate + '\n')
    def removeFromFile(numberplate):
        with open(Algorithms.resourcePath("authorizedNumberPlates.txt"), 'r') as f:
            lines = f.readlines()
        with open(Algorithms.resourcePath("authorizedNumberPlates.txt"), "w") as f:
            for line in lines:
                if numberplate not in line:
                    f.write(line)
    def addNewVehicleToAuthorizedVehicles(numberplate):
        with open(Algorithms.resourcePath("authorizedNumberPlates.txt"), "a") as f:
            f.write(numberplate + "\n")
    def writeNumberOfOpenings(duty):
        if duty == "read":
            with open(Algorithms.resourcePath("numberOfGateOpenings.txt"), "r") as f:
                global gateOpenings_thisDay
                global gateOpenings_thisWeek
                global gateOpenings_thisMonth
                gateOpenings_thisDay = 0
                gateOpenings_thisWeek = 0
                gateOpenings_thisMonth = 0
                date = datetime.datetime.now().date()
                weekago = date - datetime.timedelta(days=7)
                monthago = date - datetime.timedelta(days=30)
                lines = f.readlines()
                for line in lines:
                    lineDate = datetime.datetime.strptime(line.strip(), '%Y/%m/%d').date()
                    if lineDate > monthago:
                        gateOpenings_thisMonth += 1
                        if lineDate > weekago:
                            gateOpenings_thisWeek += 1
                            if lineDate == date:
                                gateOpenings_thisDay += 1
                
        elif duty == "write":
            with open(Algorithms.resourcePath("numberOfGateOpenings.txt"), "a") as f:
                date = datetime.datetime.now()
                dtstring = date.strftime("%Y/%m/%d")
                f.write(dtstring + "\n")
            FileManager.writeNumberOfOpenings("read")

class Functions:
    def programStarts():
        FileManager.openFile("authorizedNumberPlates.txt")
        FileManager.openFile("unauthorizedNumberPlates.txt")
        FileManager.openFile("settings.txt")
        print("Engedélyezett rendszámok:")
        for line in authorizedPlate:
            print(line)
        print("Nem engedélyezett rendszámok:")
        for line in unAuthorizedPlate:
            print(line)
        FileManager.writeNumberOfOpenings("read")
        print(f"Kapunyitások; Ebben a hónapban:{gateOpenings_thisMonth} | Ezen a héten:{gateOpenings_thisWeek} | Ezen a napon:{gateOpenings_thisDay}")
    def showRealPlate(input):
        output_string = re.sub(r'\b([A-Za-z]+)(\d+)\b', r'\1-\2', input)
        return output_string
    def openGate():
        global isGateMovedBySystem
        timeOfOpening = datetime.datetime.now()
        FileManager.writeNumberOfOpenings("write");
        Functions.setCanGateMove()
        FileManager.sendToLog("Kapu helyzete", "Nyitva", None)
        print("Kapu nyitás ideje:", timeOfOpening)
        
        if (automaticClosing):
            time.sleep(timefor_gatetocloseafteropening)
            Functions.setCanGateMove()
            isGateMovedBySystem = False
            FileManager.sendToLog("Kapu helyzete", "Zárva", None)
        else:
            isGateMovedBySystem = False
    def isGateMoveableAgain():
        global canGateMove
        global isGateMovedBySystem
        time.sleep(1)
        if isGateMovedBySystem:
            canGateMove = False
        else:
            canGateMove = True
    def setCanGateMove():
        global canGateMove
        global isGateOpen
        canGateMove = False
        if isGateOpen == True:
            Gate.changeGatePosition(1)
            time.sleep(timefor_gatetochangeposition)
            isGateOpen = False
        else:
            Gate.changeGatePosition(0)
            time.sleep(timefor_gatetochangeposition)
            isGateOpen = True
        threading.Thread(target=Functions.isGateMoveableAgain).start()  
    def writeUpPlate(licensePlate, imgToSave):
        print(f"A következő rendszám fel lett ismerve: {licensePlate}")
        if not licensePlate in unAuthorizedPlate:
            unAuthorizedPlate.append(licensePlate)
            print("Rendszámtábla felírva.")
            FileManager.sendToLog("Rendszámtábla felírása", "Sikeres", licensePlate)
            FileManager.saveToFile(licensePlate, imgToSave)
        else:
            print("A rendszámtábla már fel van írva.")
        print("Eddig felírt rendszámok:")
        for n in unAuthorizedPlate:
            print(n)

class OCRBasic:
    def checkPlate(self):
        if self != None: 
            matching_plate = None
            for plate in authorizedPlate:
                distance = Algorithms.levenshtein_distance(self, plate)
                max_length = max(len(self), len(plate))
                accuracy = 1 - (distance / max_length)
                if accuracy >= threshold:
                    matching_plate = plate
                    break
            if matching_plate is not None:
                global isGateMovedBySystem
                isGateMovedBySystem = True
                threading.Thread(target=Functions.openGate).start()
                FileManager.sendToLog("Kapu helyzete", "Nyitva", self)
            else:
                Functions.writeUpPlate(self, cv2.imread(Algorithms.resourcePath("licenseplates/IMG.jpg")))
        else:
            print("Nem található rendszám a stringben.")

class guiFunctions():
    def addAuthorizedVehicleFunction(textBox):
        plate_noticed = re.search(pattern1, textBox)
        if plate_noticed:
            plate_string = plate_noticed.group(0)
            if plate_string not in authorizedPlate:
                authorizedPlate.append(plate_string)
                FileManager.addNewVehicleToAuthorizedVehicles(plate_string)
                realPlate = Functions.showRealPlate(plate_string)
                MessageBox.sendMessageBoxToUser("info", "Siker!", "Sikeresen hozzáadtad a következő rendszámot az engedélyezett rendszámok listájához:\n " + realPlate)
                FileManager.sendToLog("Rendszámtábla hozzáadása az engedélyezett rendszámok listájához", "Sikeres", plate_string)
            else:
                MessageBox.sendMessageBoxToUser("error", "Hiba!", "Már megtalálható ez a rendszám az engedélyezett rendszámok listájában")
                FileManager.sendToLog("Rendszámtábla hozzáadása az engedélyezett rendszámok listájához", "Sikertelen", plate_string)
        else:
            MessageBox.sendMessageBoxToUser("error","Hiba!", "Nem helyes formátum! \n[ABC123]")
            FileManager.sendToLog("Rendszámtábla hozzáadása az engedélyezett rendszámok listájához", "Sikertelen", None)
    def removeAuthorizedVehicleFunction(textBox):
        plate_noticed = re.search(pattern1, textBox)
        if plate_noticed:
            plate_string = plate_noticed.group(0)
            if plate_string in authorizedPlate:
                authorizedPlate.remove(plate_string)
                FileManager.removeFromFile(plate_string)
                realPlate = Functions.showRealPlate(plate_string)
                MessageBox.sendMessageBoxToUser("info", "Siker!", "Sikeresen törlésre került a következő rendszám az engedélyezett rendszámok listájából:\n" + realPlate)
                FileManager.sendToLog("Rendszámtábla törlése az engedélyezett rendszámok listájából", "Sikeres", plate_string)
            else:
                MessageBox.sendMessageBoxToUser("error", "Helytelen rendszám", "Ez a rendszám nem található az engedélyezett rendszámok listájában.")
                FileManager.sendToLog("Rendszámtábla törlése az engedélyezett rendszámok listájából", "Sikertelen", plate_string)
        else:
            MessageBox.sendMessageBoxToUser("error","Helytelen rendszám", "Rossz rendszámformátumot adtál meg!\nHelyes formátum:[ABC123]")
            FileManager.sendToLog("Rendszámtábla törlése az engedélyezett rendszámok listájából", "Sikertelen", None)
    
    def changeGatePosition():
        global isGateOpen
        if canGateMove == True:
            if isGateOpen == False:
                MessageBox.sendMessageBoxToUser("warning","Kapu nyitása", "Az ablak bezárása után a kapu ki fog nyílni!")
                FileManager.sendToLog("Kapu helyzete (Manuális)", "Nyitva", None)
                FileManager.writeNumberOfOpenings("write");
            else:
                MessageBox.sendMessageBoxToUser("warning","Kapu zárása", "Az ablak bezárása után a kapu be fog záródni!")
                FileManager.sendToLog("Kapu helyzete (Manuális)", "Zárva", None)
            threading.Thread(target=Functions.setCanGateMove).start()
        else:
            MessageBox.sendMessageBoxToUser("warning", "Kapu mozgásban", "Kapu mozgásban. Várj!")
    def setGatePosition(positionToSetTo):
        global isGateOpen
        isGateOpen = positionToSetTo
        if positionToSetTo == True:
            MessageBox.sendMessageBoxToUser("info", "Kapu nyitva", "Kapu helyzete jelenleg: Nyitva")
            FileManager.sendToLog("Kapu helyzete (Manuális)", "Nyitva", None)
            FileManager.writeNumberOfOpenings("write");
        else:
            MessageBox.sendMessageBoxToUser("info","Kapu zárva", "Kapu helyzete jelenleg: Zárva")
            FileManager.sendToLog("Kapu helyzete (Manuális)", "Zárva", None)
     
    def processPassword(fromWhere, passIn):
        if fromWhere == "log":
            if passIn == passwordForGui:
                FileManager.deleteWholeFile("log")
                textbox_showlog.delete("1.0", "end")
                MessageBox.sendMessageBoxToUser("info", "Eseménynapló törlése", "Eseménynapló törlése: Sikeres")
                logstr = FileManager.openFile("log.txt")
                textbox_showlog.insert("end", logstr)
            else:
                FileManager.sendToLog("Eseménynapló törlése (Helytelen jelszó miatt)", "Sikertelen", None)
                MessageBox.sendMessageBoxToUser("error", "Eseménynapló törlése", "Eseménynapló törlése: Sikertelen\nHelytelen jelszó!")
        elif fromWhere == "UnauthorizedVehicleList":
            if passIn == passwordForGui:
                printLabelUnauthorized.config(text="")
                unAuthorizedPlate.clear()
                FileManager.deleteWholeFile("unauthorizedNumberPlates")
                FileManager.sendToLog("Illetéktelen járművek törlése", "Sikeres", None)
                MessageBox.sendMessageBoxToUser("info", "Illetéktelen járművek törlése", "Illetéktelen járművek törlése: Sikeres!")
            else:
                FileManager.sendToLog("Illetéktelen járművek törlése (Helytelen jelszó miatt)", "Sikertelen", None)
                MessageBox.sendMessageBoxToUser("error", "Illetéktelen járművek törlése", "Illetéktelen járművek törlése: Sikertelen\nHelytelen jelszó!")    
    
    def setAutomaticClosing(boolean):
        global automaticClosing
        if (boolean):
            automaticClosing = True
            MessageBox.sendMessageBoxToUser("info", "Automatikus bezárás", "Automatikus bezárás funkció bekapcsolása: Sikeres!")
            FileManager.sendToLog("Automatikus kapubezárás bekapcsolása", "Sikeres", None)
        else:
            automaticClosing = False
            MessageBox.sendMessageBoxToUser("info", "Automatikus bezárás", "Automatikus bezárás funkció kikapcsolása: Sikeres!")
            FileManager.sendToLog("Automatikus kapubezárás kikapcsolása", "Sikeres", None)
        FileManager.refreshVariables()
    def setGateToChangePosition(iteration, time):
        if iteration == 1:
            global timefor_gatetochangeposition
            time = int(time)
            if (time >= 10) and (time <= 45):
                timefor_gatetochangeposition = time
                MessageBox.sendMessageBoxToUser("info", "Pozícióváltás idejének állítása", "Kapu pozícióváltás idejének beállítása: Sikeres!")
                FileManager.sendToLog("Kapu pozícióváltás idejének beállítása", "Sikeres", None)
                FileManager.refreshVariables()
            else:
                MessageBox.sendMessageBoxToUser("info", "Pozícióváltás idejének állítása", "Kapu pozícióváltás idejének beállítása: Sikertelen!\nAz érték 10 éa 45 másodperc között lehet!")
        elif iteration == 2:
            global timefor_gatetocloseafteropening
            time = int(time)
            if (time >= 10) and (time <= 300):
                timefor_gatetocloseafteropening = time
                MessageBox.sendMessageBoxToUser("info", "Automatikus bezárás idejének állítása", "Kapu automatikus bezárás idejének beállítása: Sikeres!")
                FileManager.sendToLog("Kapu automatikus bezárás idejének beállítása", "Sikeres", None)
                FileManager.refreshVariables()
            else:
                MessageBox.sendMessageBoxToUser("info", "Automatikus bezárás idejének állítása", "Kapu automatikus bezárás idejének beállítása: Sikertelen!\nAz érték 10 éa 300 másodperc között lehet!")
       
            
def processGate():
    while True:
        while isGateOpen == False and canGateMove == True:
            th = threading.Thread(target=Camera.cameraInstall)
            th.start()
            th.join()
            from tesseract_extract import licenseString
            OCRBasic.checkPlate(licenseString)

class GUI:
        
        root = Tk()
        
        root.title("AutoSense Solutions")
        imageLabel = Label(root)
        root.resizable(False, False)
        root.iconphoto(True, PhotoImage(file=Algorithms.resourcePath("icons/guard.png")))
        def on_closing():
            sys.exit()
            
        root.protocol("WM_DELETE_WINDOW", on_closing)

        def updateImage():
            try:
                imgforGui = Image.open(Algorithms.resourcePath("licenseplates/IMG.jpg"))
                imgforGui = imgforGui.resize((560, 350))
                photo = ImageTk.PhotoImage(imgforGui)
                GUI.imageLabel.configure(image=photo)
                GUI.imageLabel.image = photo
            except OSError as e:
                print("Sikertelen képbeolvasás:", e)
            
            GUI.root.after(1000, GUI.updateImage)
        
        def updateOpenCloseButtonText():
            button_changeGatePosition.config(state="normal")
            if canGateMove == False:
                button_changeGatePosition.config(text="Kapu mozgásban...")
                button_changeGatePosition.config(highlightbackground="#C8A850", foreground="#C8A850")
            elif isGateOpen == True: 
                button_changeGatePosition.config(text="Kapu zárása")
                button_changeGatePosition.config(highlightbackground="#ff5733", foreground="#ff5733")
            elif isGateOpen == False:
                button_changeGatePosition.config(text="Kapu nyitása")
                button_changeGatePosition.config(highlightbackground="#7cc576", foreground="#7cc576")

            GUI.root.after(1000, GUI.updateOpenCloseButtonText)

        def GUIFunc(): 
            global button_changeGatePosition

            def showPasswordPrompt(fromWhere):
                passwordPrompt = Tk()
                passwordPrompt.resizable(False, False)
                passwordPrompt.title("A művelethez jelszóra van szükség")
                textbox_password = Text(passwordPrompt)
                textbox_password.insert("end", "Jelszó...")
                textbox_password.config(width=35, height=1)
                button_sendPassword = Button(passwordPrompt, text="Küldés", command=lambda: guiFunctions.processPassword(fromWhere, textbox_password.get("1.0", END)))
                button_sendPassword.config(width=10, height=1)
                textbox_password.grid(column=0, row=0)
                button_sendPassword.grid(column=1, row=0)
                passwordPrompt.mainloop()
            def updateNumberOfOpeningsText():
                label_numberOfOpenings.config(text=f"Kapunyitások száma:\n Ebben a Hónapban: {gateOpenings_thisMonth} | Ezen a Héten: {gateOpenings_thisWeek} | Ma: {gateOpenings_thisDay}")
                GUI.root.after(1000, updateNumberOfOpeningsText)
            def listAuthorizedVehicles():
                stri = "Engedélyezett járművek listája:"
                for vehicles in authorizedPlate:
                    realPlate = Functions.showRealPlate(vehicles)
                    stri = stri + "\n" + realPlate
                listVehiclesWindow = Tk()
                listVehiclesWindow.resizable(False, True)
                listVehiclesWindow.title("Engedélyezett járművek listája")
                printLabel = Label(listVehiclesWindow, text=stri)
                printLabel.grid(column=0, row=0)
            def listunAuthorizedVehicles():
                global printLabelUnauthorized
                stri = "Illetéktelen járművek listája:"
                for vehicles in unAuthorizedPlate:
                    realPlate = Functions.showRealPlate(vehicles)
                    stri = stri + "\n" + realPlate
                listVehiclesWindow = Tk()
                listVehiclesWindow.resizable(False, True)
                listVehiclesWindow.title("Illetéktelen járművek listája")
                printLabelUnauthorized = Label(listVehiclesWindow, text=stri)
                printLabelUnauthorized.grid(column=0, row=0)
                button_clearUnauthorizedVehicleList = Button(listVehiclesWindow, text="Lista törlése", command=lambda:showPasswordPrompt("UnauthorizedVehicleList"))
                button_clearUnauthorizedVehicleList.grid(column=0, row=1)
                listVehiclesWindow.mainloop()
            def addAuthorizedVehicleWithinGUI():
                addVehicleWindow = Tk()
                addVehicleWindow.resizable(False, False)
                addVehicleWindow.title("Engedélyezett jármű hozzáadása")
                printLabel = Label(addVehicleWindow, text="Add meg a rendszámot, amit hozzá szeretnél adni a rendszerhez")
                printLabel.grid(column=0, columnspan=3, row=0)
                textLabel_licenseplate = Text(addVehicleWindow)
                textLabel_licenseplate.insert("end", "[ABC123]")
                button_addNewLicensePlateButton = Button(addVehicleWindow, text="Küldés", command=lambda: guiFunctions.addAuthorizedVehicleFunction(textLabel_licenseplate.get("1.0", END)))
                textLabel_licenseplate.grid(column=0, row=1)
                textLabel_licenseplate.config(width=40, height=1)
                button_addNewLicensePlateButton.grid(column=2, row=1)
                addVehicleWindow.mainloop()
            def removeAuthorizedVehicleWithinGUI():
                removeVehicleWindow = Tk()
                removeVehicleWindow.title("Engedélyezett jármű letiltása")
                removeVehicleWindow.resizable(False, False)
                printLabel = Label(removeVehicleWindow, text="Add meg a rendszámot, amit ki szeretnél venni a rendszerből.")
                textLabel = Text(removeVehicleWindow)
                textLabel.insert("end", "[ABC123]")
                button_removeLicensePlateButton = Button(removeVehicleWindow, text="Küldés", command=lambda: guiFunctions.removeAuthorizedVehicleFunction(textLabel.get("1.0", END)))
                textLabel.config(width=50, height=1)
                printLabel.grid(columnspan=2, column=0, row=0)
                textLabel.grid(column=0, row=1)
                button_removeLicensePlateButton.grid(column=1, row=1)
                removeVehicleWindow.mainloop()
            def setGatePosition():
                gatePositionWindow = Tk()
                gatePositionWindow.title("Jelenlegi kapuhelyzet beállítása")
                gatePositionWindow.resizable(False, False)
                printLabel = Label(gatePositionWindow, text="Add meg a kapu jelenlegi beállítását.")
                printLabel.grid(columnspan=2, column=0, row=0)
                button_setGateToOpen = Button(gatePositionWindow, text="Kapu nyitva", command=lambda: guiFunctions.setGatePosition(True))
                button_setGateToClosed = Button(gatePositionWindow, text="Kapu zárva", command=lambda: guiFunctions.setGatePosition(False))
                button_setGateToOpen.grid(column=0, row=1)
                button_setGateToOpen.config(width=15, height=1)
                button_setGateToClosed.grid(column=1, row=1)
                button_setGateToClosed.config(width=15, height=1)
                gatePositionWindow.mainloop()
            def showLogToUser():
                logstr = FileManager.openFile("log.txt")
                global textbox_showlog
                logWindow = Tk()
                logWindow.title("Eseménynapló")
                logWindow.resizable(False, False)
                label_logwindowtext = Label(logWindow, text="Itt találhatod az eseménynaplót\nAz eseménynapló törölhető a jelszó megadásával.")
                
                button_resetLog = Button(logWindow, text="LOG törlése", command=lambda: showPasswordPrompt("log"))
                textbox_showlog = Text(logWindow)
                textbox_showlog.insert("end", logstr)
                
                label_logwindowtext.grid(column=0, row=0)
                button_resetLog.grid(column=0, row=1)
                textbox_showlog.grid(column=0, row=2)
                textbox_showlog.config(width=100, height=30)
                logWindow.mainloop()
            def setAutomaticClosing():
                automaticClosingWindow = Tk()
                automaticClosingWindow.title("Automatikus bezárás beállítása")
                automaticClosingWindow.resizable(False, False)
                printLabel = Label(automaticClosingWindow, text="Add meg, hogy a kapu automatikus bezáruljon-e rendszámfelismerés után!")
                printLabel.grid(columnspan=2, column=0, row=0)
                button_setAutomaticClosingTrue = Button(automaticClosingWindow, text="Automatikus bezárás bekapcsolása", command=lambda: guiFunctions.setAutomaticClosing(True))
                button_setAutomaticClosingFalse = Button(automaticClosingWindow, text="Automatikus bezárás kikapcsolása", command=lambda: guiFunctions.setAutomaticClosing(False))
                button_setAutomaticClosingTrue.grid(column=0, row=1)
                button_setAutomaticClosingTrue.config(width=22, height=1)
                button_setAutomaticClosingFalse.grid(column=1, row=1)
                button_setAutomaticClosingFalse.config(width=22, height=1)
                automaticClosingWindow.mainloop()
            def settimefor_gatetoChangePosition():
                gateToChangePositionWindow = Tk()
                gateToChangePositionWindow.title("Kapu pozícióváltás idejének beállítása")
                gateToChangePositionWindow.resizable(False, False)
                printLabel = Label(gateToChangePositionWindow, text="Add meg, mennyi időbe telik a kapunak a pozícióváltás befejezése.")
                textLabel = Text(gateToChangePositionWindow)
                textLabel.insert("end", "[10-45] másodperc")
                button_timefor_gatetochangeposition = Button(gateToChangePositionWindow, text="Küldés", command=lambda: guiFunctions.setGateToChangePosition(1, textLabel.get("1.0", END)))
                textLabel.config(width=20, height=1)
                printLabel.grid(columnspan=2, column=0, row=0)
                textLabel.grid(column=0, row=1)
                button_timefor_gatetochangeposition.grid(column=1, row=1)
                gateToChangePositionWindow.mainloop()
            def settimefor_gatetocloseafteropening():
                gateToCloseAfterOpeningWindow = Tk()
                gateToCloseAfterOpeningWindow.title("Kapu automatikus bezárás idejének beállítása")
                gateToCloseAfterOpeningWindow.resizable(False, False)
                printLabel = Label(gateToCloseAfterOpeningWindow, text="Add meg, mennyi idő után záruljon a kapu automatikusan!")
                textLabel = Text(gateToCloseAfterOpeningWindow)
                textLabel.insert("end", "[10-300] másodperc")
                button_timefor_gatetochangeposition = Button(gateToCloseAfterOpeningWindow, text="Küldés", command=lambda: guiFunctions.setGateToChangePosition(2, textLabel.get("1.0", END)))
                textLabel.config(width=20, height=1)
                printLabel.grid(columnspan=2, column=0, row=0)
                textLabel.grid(column=0, row=1)
                button_timefor_gatetochangeposition.grid(column=1, row=1)
                gateToCloseAfterOpeningWindow.mainloop()
            def showOptions():
                optionsWindow = Tk()
                optionsWindow.title("Beállítások")
                optionsWindow.resizable(False, False)
                
                text_optionWindow_isGateOpen = Label(optionsWindow, text=f"Kapu jelenleg nyitva: {isGateOpen}")
                button_optionWindow_isGateOpen = Button(optionsWindow, text="Beállítás", command=setGatePosition)
                text_optionWindow_isGateOpen.grid(column=0, row=0)
                button_optionWindow_isGateOpen.grid(column=1, row=0)
                text_optionWondow_automaticClosing = Label(optionsWindow, text=f"Kapu automatikus beázársa: {automaticClosing}")
                button_optionWindow_automaticClosing = Button(optionsWindow, text="Beállítás", command=setAutomaticClosing)
                text_optionWondow_automaticClosing.grid(column=0, row=1)
                button_optionWindow_automaticClosing.grid(column=1, row=1)
                text_optionWindow_timefor_gatetoChangePosition = Label(optionsWindow, text=f"Kapu nyitása/bezárása: {timefor_gatetochangeposition} másodperc")
                button_optionWindow_timefor_gatetoChangePosition = Button(optionsWindow, text="Beállítás", command=settimefor_gatetoChangePosition)
                text_optionWindow_timefor_gatetoChangePosition.grid(column=0, row=2)
                button_optionWindow_timefor_gatetoChangePosition.grid(column=1, row=2)
                text_optionWindow_timefor_gatetocloseafteropening = Label(optionsWindow, text=f"Kapu automatikus bezárásának ideje: {timefor_gatetocloseafteropening} másodperc")
                button_optionWindow_timefor_gatetocloseafteropening = Button(optionsWindow, text="Beállítás", command=settimefor_gatetocloseafteropening)
                text_optionWindow_timefor_gatetocloseafteropening.grid(column=0, row=3)
                button_optionWindow_timefor_gatetocloseafteropening.grid(column=1, row=3)
                
                optionsWindow.mainloop()

            logoImage = Image.open(Algorithms.resourcePath("icons/guard.png"))
            logoImage = logoImage.resize((200, 200))
            logopnginGUI = ImageTk.PhotoImage(logoImage)
            logoPNGLabel = Label(GUI.root, image = logopnginGUI)
            logoPNGLabel.grid(columnspan=2, column=0, row=0)

            label_numberOfOpenings = Label(GUI.root, text="Kapunyitások száma: \nIsmeretlen")
            label_numberOfOpenings.config(font=("Arial", 18))
            label_numberOfOpenings.grid(column=0, columnspan=3, row=1)

            button_changeGatePosition = Button(GUI.root, command=guiFunctions.changeGatePosition)
            
            button_changeGatePosition.config(width=30, height=2)
            button_changeGatePosition.grid(column=0, row=3)
            button_setDefaultPosition = Button(GUI.root, text="Kapu helyzetének beállítása", command=setGatePosition)
            button_setDefaultPosition.config(width=30, height=2)
            button_setDefaultPosition.grid(column=1, row=3)

            button_authorizedVehicleList = Button(GUI.root, text="Engedélyezett járművek listázása", command=listAuthorizedVehicles)
            button_unauthorizedVehicleList = Button(GUI.root, text="Illetéktelen járművek listázása", command=listunAuthorizedVehicles)
            button_authorizedVehicleList.config(width=30, height=2)
            button_authorizedVehicleList.grid(column=0, row=4)
            button_unauthorizedVehicleList.config(width=30, height=2)
            button_unauthorizedVehicleList.grid(column=1, row=4)

            button_addAuthorizedVehicle = Button(GUI.root, text="Engedélyezett jármű hozzáadása", command=addAuthorizedVehicleWithinGUI)
            button_removeAuthorizedVehicle = Button(GUI.root, text="Engedélyezett jármű letiltása", command=removeAuthorizedVehicleWithinGUI)
            button_addAuthorizedVehicle.config(width=30, height=2)
            button_addAuthorizedVehicle.grid(column=0, row=5)
            button_removeAuthorizedVehicle.config(width=30, height=2)
            button_removeAuthorizedVehicle.grid(column=1, row=5)

            button_getAccessToLog = Button(GUI.root, text="Eseménynapló megtekintése", command=showLogToUser)
            button_getAccessToLog.grid(column=0, columnspan=1, row=6)
            button_getAccessToLog.config(width=30, height=2)

            button_changeSettings = Button(GUI.root, text="Beállítások megtekintése", command=showOptions)
            button_changeSettings.grid(column=1, columnspan=1, row=6)
            button_changeSettings.config(width=30, height=2)
            GUI.imageLabel.grid(column=0, columnspan=2, row=7)
            updateNumberOfOpeningsText()
            GUI.updateImage()
            GUI.updateOpenCloseButtonText()
            GUI.root.mainloop()


if __name__ == "__main__":
    Functions.programStarts()
    if isitWithGUI == False:
        threading.Thread(target=processGate).start()
    else:
        threadTo_ProcessGate = threading.Thread(target=processGate)
        threadTo_ProcessGate.setDaemon(True)
        threadTo_ProcessGate.start()
        GUI.GUIFunc()
