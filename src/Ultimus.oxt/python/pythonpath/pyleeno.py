#!/usr/bin/env python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
########################################################################
# LeenO - Computo Metrico
# Template assistito per la compilazione di Computi Metrici Estimativi
# Copyright (C) Giuseppe Vizziello - supporto@leeno.org
# Licenza LGPL http://www.gnu.org/licenses/lgpl.html
# Il codice contenuto in questo modulo è parte integrante dell'estensione LeenO
# Vi sarò grato se vorrete segnalarmi i malfunzionamenti (veri o presunti)
# Sono inoltre graditi suggerimenti in merito alle gestione della
# Contabilità Lavori e per l'ottimizzazione del codice.
########################################################################

#~ MsgBox('''Per segnalare questo problema,
#~ contatta il canale Telegram
#~ https://t.me/leeno_computometrico''', 'ERRORE!')

#~ documentazione ufficiale: https://api.libreoffice.org/
# ~import pydevd
import locale
import codecs
import configparser
import collections
import subprocess
#~ import psutil
import os, unohelper, pyuno, logging, shutil, base64, sys, uno
import time
import copy
from multiprocessing import Process, freeze_support
import threading
import traceback
import re
# cos'e' il namespace:
# http://www.html.it/articoli/il-misterioso-mondo-dei-namespaces-1/
from com.sun.star.task import XJobExecutor
from datetime import datetime, date
#~ from com.sun.star.lang import Locale
from com.sun.star.beans import PropertyValue
from xml.etree.ElementTree import ElementTree, Element, SubElement, Comment, tostring
#~ from com.sun.star.table.CellContentType import TEXT, EMPTY, VALUE, FORMULA
from com.sun.star.sheet.CellFlags import (VALUE, DATETIME, STRING,
                                          ANNOTATION, FORMULA, HARDATTR,
                                          OBJECTS, EDITATTR, FORMATTED)
from com.sun.star.sheet.GeneralFunction import (SUM, COUNT, AVERAGE, MAX, MIN, PRODUCT, COUNTNUMS)

from com.sun.star.beans.PropertyAttribute import (MAYBEVOID, REMOVEABLE, MAYBEDEFAULT)
########################################################################
# https://forum.openoffice.org/en/forum/viewtopic.php?f=45&t=27805&p=127383
import random
from com.sun.star.script.provider import XScriptProviderFactory
    
from com.sun.star.script.provider import XScriptProvider
def barra_di_stato(testo='', valore=0):
    '''Informa l'utente sullo stato progressivo dell'eleborazione.'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oProgressBar = oDoc.CurrentController.Frame.createStatusIndicator()
    oProgressBar.start('', 100)
    oProgressBar.Value = valore
    oProgressBar.Text = testo
    oProgressBar.reset()
    oProgressBar.end

def basic_LeenO(funcname, *args):
    '''Richiama funzioni definite in Basic'''
    xCompCont = XSCRIPTCONTEXT.getComponentContext()
    sm = xCompCont.ServiceManager
    mspf = sm.createInstance("com.sun.star.script.provider.MasterScriptProviderFactory")
    scriptPro = mspf.createScriptProvider("")
    Xscript = scriptPro.getScript("vnd.sun.star.script:UltimusFree2." + funcname + "?language=Basic&location=application")
    Result = Xscript.invoke(args, None, None)
    return Result[0]
########################################################################
def LeenO_path(arg=None):
    '''Restituisce il percorso di installazione di LeenO.oxt'''
    ctx = XSCRIPTCONTEXT.getComponentContext()
    pir = ctx.getValueByName('/singletons/com.sun.star.deployment.PackageInformationProvider')
    expath = pir.getPackageLocation('org.giuseppe-vizziello.leeno')
    return expath
########################################################################
class New_file:
    def __init__(self):#, computo):
        pass
    def computo(arg=1):
        '''arg  { integer } : 1 mostra il dialogo di salvataggio file'''
        desktop = XSCRIPTCONTEXT.getDesktop()
        opz = PropertyValue()
        opz.Name = 'AsTemplate'
        opz.Value = True
        document = desktop.loadComponentFromURL(LeenO_path()+'/template/leeno/Computo_LeenO.ots', "_blank", 0, (opz,))
        autoexec()
        if arg == 1:
            MsgBox('''Prima di procedere è consigliabile salvare il lavoro.
Provvedi subito a dare un nome al file di computo...''', 'Dai un nome al file...')
            salva_come()
            DlgMain()
        return document
    def usobollo():
        desktop = XSCRIPTCONTEXT.getDesktop()
        opz = PropertyValue()
        opz.Name = 'AsTemplate'
        opz.Value = True
        document = desktop.loadComponentFromURL(LeenO_path()+'/template/offmisc/UsoBollo.ott', "_blank", 0, (opz,))
        return document
########################################################################
def nuovo_computo(arg=None):
    '''Crea un nuovo computo vuoto.'''
    New_file.computo()
########################################################################
def nuovo_usobollo(arg=None):
    '''Crea un nuovo documento in formato uso bollo.'''
    New_file.usobollo()
########################################################################
def invia_voce(arg=None):
# ~def debug(arg=None):
    '''
    Invia le voci di computo, elenco prezzi e analisi, con costi elementari,
    dal documento corrente al Documento Principale.
    '''
    # ~refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    nSheet = oSheet.Name
    fpartenza = uno.fileUrlToSystemPath(oDoc.getURL())
    if fpartenza == sUltimus:
        MsgBox("Questo file coincide con il Documento Principale (DCC).", "Attenzione!")
        return
    elif sUltimus == '':
        MsgBox("E' necessario impostare il Documento Principale (DCC).", "Attenzione!")
        return
    nSheetDCC = getDCCSheet()
    lrow = Range2Cell()[1]
    global cod

    def getAnalisi(oSheet):
        try:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
        except AttributeError:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
        el_y = list()
        try:
            len(oRangeAddress)
            for el in oRangeAddress:
                el_y.append((el.StartRow, el.EndRow))
        except TypeError:
            el_y.append ((oRangeAddress.StartRow, oRangeAddress.EndRow))
        lista = list()
        for y in el_y:
            for el in range (y[0], y[1]+1):
                lista.append(el)
        analisi = list()
        for y in lista:
            if oSheet.getCellByPosition(1, y).Type.value == 'FORMULA':
                analisi.append(oSheet.getCellByPosition(0, y).String)
        return (analisi, lista)
    def Circoscrive_Analisi(lrow):
        #~ oDoc = XSCRIPTCONTEXT.getDocument()
        #~ oSheet = oDoc.CurrentController.ActiveSheet
        if oSheet.getCellByPosition(0, lrow).CellStyle in stili_analisi:
            for el in reversed(range(0, lrow)):
                if oSheet.getCellByPosition(0, el).CellStyle == 'Analisi_Sfondo':
                    SR = el
                    break
            for el in range(lrow, getLastUsedCell(oSheet).EndRow):
                if oSheet.getCellByPosition(0, el).CellStyle == 'An-sfondo-basso Att End':
                    ER = el
                    break
        celle=oSheet.getCellRangeByPosition(0,SR,250,ER)
        return celle
###### partenza
    if oSheet.Name == 'Elenco Prezzi':
        if oSheet.getCellByPosition(0, Range2Cell()[1]).CellStyle not in ('EP-Cs', 'EP-aS'):
            MsgBox('La posizione di PARTENZA non è corretta.','ATTENZIONE!')
            return
        analisi = getAnalisi(oSheet)[0]
        lrow = getAnalisi(oSheet)[1][0]
        cod = oSheet.getCellByPosition(0, lrow).String
        lista = getAnalisi(oSheet)[1]

        selezione = list()
        voci = oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")
        for y in lista:
            rangen = oSheet.getCellRangeByPosition(0, y, 100, y).RangeAddress
            selezione.append(rangen)
        voci.addRangeAddresses(selezione, True)

        coppia = list()

        if analisi:
            _gotoSheet('Analisi di Prezzo')
            oSheet = oDoc.getSheets().getByName('Analisi di Prezzo')

            ranges = oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")
            selezione_analisi = list()
            for el in analisi:
                y = uFindStringCol(el, 0, oSheet)
                sStRange = Circoscrive_Analisi(y)
                SR = sStRange.RangeAddress.StartRow
                ER = sStRange.RangeAddress.EndRow
                coppia.append((SR, ER))
                selezione_analisi.append(sStRange.RangeAddress)
            costi = list()
            for el in coppia:
                for y in range (el[0], el[1]):
                    if oSheet.getCellByPosition(0, y).CellStyle == 'An-lavoraz-Cod-sx' and \
                    oSheet.getCellByPosition(0, y).Type.value != 'EMPTY':
                        costi.append(oSheet.getCellByPosition(0, y).String)
            if len(costi) > 0:
                _gotoSheet('Elenco Prezzi')
                oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
                el_y = list()
                for el in costi:
                    el_y.append(uFindStringCol(el, 0, oSheet))
                for y in el_y:
                    rangen = oSheet.getCellRangeByPosition(0, y, 100, y).RangeAddress
                    selezione.append(rangen)
                voci.addRangeAddresses(selezione, True)
        oDoc.CurrentController.select(voci)
        copy_clip()
        oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
        _gotoDoc(sUltimus)
        ddcDoc = XSCRIPTCONTEXT.getDocument()
        dccSheet = ddcDoc.CurrentController.ActiveSheet
        nome = dccSheet.Name

        if nome in ('Elenco Prezzi'):
            ddcDoc.CurrentController.setActiveSheet(dccSheet)
            _gotoCella(0, 3)
            paste_clip(1)
            #~ doppioni()
        if nome in ('COMPUTO', 'VARIANTE', 'CONTABILITA'):
            dccSheet = ddcDoc.getSheets().getByName('Elenco Prezzi')
            dccSheet.IsVisible = True
            ddcDoc.CurrentController.setActiveSheet(dccSheet)
            _gotoCella(0, 3)
            paste_clip(1)
            #~ doppioni()
            _gotoDoc(sUltimus)
            ddcDoc = XSCRIPTCONTEXT.getDocument()
            _gotoSheet(nome)
            dccSheet = ddcDoc.getSheets().getByName(nome)
            lrow = Range2Cell()[1]
            if dccSheet.getCellByPosition(0, lrow).CellStyle in ('comp Int_colonna'):
                ins_voce_computo_grezza(lrow+1)
                numera_voci(1)
                lrow = Range2Cell()[1]
            if dccSheet.getCellByPosition(0, lrow).CellStyle in (stili_computo + ('comp Int_colonna',)):
                if cod_voce(lrow) in ('', 'Cod. Art.?'):
                    cod_voce(lrow, cod)
                else:
                    ins_voce_computo()
                    _gotoSheet(nome)
                    cod_voce(Range2Cell()[1], cod)
                if Range2Cell()[1] > 20:
                    ddcDoc.CurrentController.setFirstVisibleColumn(0)
                    ddcDoc.CurrentController.setFirstVisibleRow(Range2Cell()[1]-5)
            else:
                return
###### partenza
    if oSheet.Name in ('COMPUTO', 'VARIANTE', 'CONTABILITA'):
        sopra = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
        cod = cod_voce(lrow)
        try:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
        except AttributeError:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
        try:
            SR = oRangeAddress.StartRow
            SR = Circoscrive_Voce_Computo_Att(SR).RangeAddress.StartRow
        except AttributeError:
            MsgBox('La selezione delle voci dal COMPUTO di partenza\ndeve essere contigua.','ATTENZIONE!')
            return
        ER = oRangeAddress.EndRow
        ER = Circoscrive_Voce_Computo_Att(ER).RangeAddress.EndRow
        oDoc.CurrentController.select(oSheet.getCellRangeByPosition(0, SR, 100, ER))
        lista = list()
        for el in range(SR, ER+1):
            if oSheet.getCellByPosition(0, el).CellStyle in ('Comp Start Attributo'):
                lista.append(cod_voce(el))        
        #~ seleziona()
        if nSheetDCC in ('Analisi di Prezzo'):
            MsgBox('Il foglio di destinazione non è corretto.','ATTENZIONE!')
            oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
            return
        if nSheetDCC in ('COMPUTO', 'VARIANTE'):
            copy_clip()
            _gotoDoc(sUltimus)
            ddcDoc = XSCRIPTCONTEXT.getDocument()
            dccSheet = ddcDoc.getSheets().getByName(nSheet)
            lrow = Range2Cell()[1]
            if dccSheet.getCellByPosition(0, lrow).CellStyle in ('comp Int_colonna',):
                lrow = Range2Cell()[1] + 1
            elif dccSheet.getCellByPosition(0, lrow).CellStyle not in stili_computo:
                MsgBox('La posizione di destinazione non è corretta.','ATTENZIONE!')
                oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
                return
            else:
                lrow = next_voice(Range2Cell()[1], 1)
            _gotoCella(0, lrow)
            paste_clip(1)
            numera_voci(1)
            last = lrow+ER-SR+1
            while lrow < last:
                rigenera_voce(lrow)
                lrow = next_voice(lrow, 1)
############ torno su partenza per prendere i prezzi
            _gotoDoc(fpartenza)
            oDoc = XSCRIPTCONTEXT.getDocument()
            _gotoSheet('Elenco Prezzi')
            oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
            selezione = list()
            ranges = oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")
            for el in lista:
                y = uFindStringCol(el, 0, oSheet)
                rangen = oSheet.getCellRangeByPosition(0, y, 100, y).RangeAddress
                selezione.append(rangen)

            ranges.addRangeAddresses(selezione, True)
            oDoc.CurrentController.select(ranges)
            copy_clip()
############
            _gotoDoc(sUltimus)
            ddcDoc = XSCRIPTCONTEXT.getDocument()
            dccSheet = ddcDoc.getSheets().getByName('Elenco Prezzi')
            _gotoSheet('Elenco Prezzi')
            _gotoCella(0, 4)
            #~ chi(('stop', ddcDoc.getURL()) )

            paste_clip(1)
            #~ doppioni()
        if nSheetDCC in ('Elenco Prezzi'):
            MsgBox("Non è possibile inviare voci da un COMPUTO all'Elenco Prezzi.")
            return
        oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    try:
        len (analisi)
 
        selezione = list()
        lista = list()
        _gotoDoc(fpartenza)
        oDoc = XSCRIPTCONTEXT.getDocument()
        _gotoSheet('Analisi di Prezzo')
        ranges = oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")
        ranges.addRangeAddresses(selezione_analisi, True)
        oDoc.CurrentController.select(ranges)

        copy_clip()

        _gotoDoc(sUltimus)
        ddcDoc = XSCRIPTCONTEXT.getDocument()
        inizializza_analisi()
        _gotoCella(0, 0)
        paste_clip(1)
        tante_analisi_in_ep()
    except:
        pass
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    _gotoDoc(fpartenza)
    _gotoSheet(nSheet)
    _gotoDoc(sUltimus)
    doppioni()
    adatta_altezza_riga('Elenco Prezzi')
    _gotoSheet(nSheetDCC)
    # ~refresh(1)
########################################################################
def cod_voce(lrow, cod=None):
    '''
    lrow    { int } : id della riga
    cod  { string } : codice del prezzo
    Se cod è assente, restituisce il codice della voce,
    altrimenti glielo assegna.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    #~ lrow = Range2Cell()[1]
    if oSheet.Name in('COMPUTO', 'VARIANTE', 'CONTABILITA'):
        sopra = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
    elif oSheet.Name in ('Analisi di Prezzo'):
        sopra = Circoscrive_Analisi(lrow).RangeAddress.StartRow+1
    if cod == None:
        return oSheet.getCellByPosition(1, sopra+1).String
    else:
        oSheet.getCellByPosition(1, sopra+1).String = cod

#~ def getVoce(cod=None):
    #~ oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    #~ lrow = Range2Cell()[1]
    #~ sopra = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
    #~ return oSheet.getCellByPosition(1, sopra+1).String
#~ def setVoce(cod):
    #~ oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    #~ lrow = Range2Cell()[1]
    #~ sopra = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
    #~ oSheet.getCellByPosition(1, sopra+1).String = cod
########################################################################
def _gotoDoc(sUrl):
    '''
    sUrl  { string } : nome del file
    porta il focus su di un determinato documento
    '''
    sUrl = uno.systemPathToFileUrl(sUrl)
    if sys.platform == 'linux' or sys.platform == 'darwin':
        target = XSCRIPTCONTEXT.getDesktop().loadComponentFromURL(sUrl, "_default", 0, list())
        target.getCurrentController().Frame.ContainerWindow.toFront()
        target.getCurrentController().Frame.activate()
    elif sys.platform == 'win32':
        desktop = XSCRIPTCONTEXT.getDesktop()
        oFocus = uno.createUnoStruct('com.sun.star.awt.FocusEvent')
        target = desktop.loadComponentFromURL(sUrl, "_default", 0, list())
        target.getCurrentController().getFrame().focusGained(oFocus)
    return target
########################################################################
def getDCCSheet(arg=None):
    '''
    sUrl  { string } : nome del file
    porta il focus su di un determinato documento
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    fpartenza = uno.fileUrlToSystemPath(oDoc.getURL())
    _gotoDoc(sUltimus)
    #~ global sUltimus_sheet
    sUltimus_sheet = XSCRIPTCONTEXT.getDocument().CurrentController.ActiveSheet.Name
    _gotoDoc(fpartenza)
    return sUltimus_sheet

########################################################################
def oggi():
    '''
    restituisce la data di oggi
    '''
    return('/'.join(reversed(str(datetime.now()).split(' ')[0].split('-'))))
import distutils.dir_util
########################################################################
def copia_sorgente_per_git(arg=None):
    '''
    fa una copia della directory del codice nel repository locale ed apre una shell per la commit
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    try:
        if oDoc.getSheets().getByName('S1').getCellByPosition(7,338).String == '':
            src_oxt ='_LeenO'
        else:
            src_oxt = oDoc.getSheets().getByName('S1').getCellByPosition(7,338).String
    except:
        pass
    make_pack(bar=1)
    oxt_path = uno.fileUrlToSystemPath(LeenO_path())
    if sys.platform == 'linux' or sys.platform == 'darwin':
        dest = '/media/giuserpe/PRIVATO/_dwg/ULTIMUSFREE/_SRC/leeno/src/Ultimus.oxt'
        if not os.path.exists(dest):
            try:
                dest = os.getenv("HOME") +'/'+ src_oxt +'/leeno/src/Ultimus.oxt/'
                os.makedirs(dest)
                os.makedirs(os.getenv("HOME") +'/'+ src_oxt +'/leeno/bin/')
                os.makedirs(os.getenv("HOME") +'/'+ src_oxt +'/_SRC/OXT')
            except FileExistsError:
                pass
            comandi = 'cd ' + dest +' && gnome-terminal && gitk &'
        else:
            comandi = 'cd /media/giuserpe/PRIVATO/_dwg/ULTIMUSFREE/_SRC/leeno/src/Ultimus.oxt && gnome-terminal && gitk &'
        if processo('wish') == False:
            subprocess.Popen(comandi, shell=True, stdout=subprocess.PIPE)
    elif sys.platform == 'win32':
        if not os.path.exists('w:/_dwg/ULTIMUSFREE/_SRC/leeno/src/'):
            try:
                os.makedirs(os.getenv("HOMEPATH") +'\\'+ src_oxt +'\\leeno\\src\\Ultimus.oxt\\')
            except FileExistsError:
                pass
            dest = os.getenv("HOMEDRIVE") + os.getenv("HOMEPATH") +'\\'+ src_oxt +'\\leeno\\src\\Ultimus.oxt\\'
        else:
            dest = 'w:/_dwg/ULTIMUSFREE/_SRC/leeno/src/Ultimus.oxt'
        subprocess.Popen('w: && cd w:/_dwg/ULTIMUSFREE/_SRC/leeno/src/Ultimus.oxt && "C:/Program Files/Git/git-bash.exe"', shell=True, stdout=subprocess.PIPE)
    distutils.dir_util.copy_tree(oxt_path, dest)
    return
########################################################################
def avvia_IDE(arg=None):
    '''Avvia la modifica di pyleeno.py con geany'''
    basic_LeenO('file_gest.avvia_IDE')
    oDoc = XSCRIPTCONTEXT.getDocument()
    oLayout = oDoc.CurrentController.getFrame().LayoutManager
    oLayout.showElement("private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_DEV")
    if sys.platform == 'linux' or sys.platform == 'darwin':
        subprocess.Popen('nemo ' + LeenO_path(), shell=True, stdout=subprocess.PIPE)
        subprocess.Popen('geany ' + LeenO_path() + '/python/pythonpath/pyleeno.py', shell=True, stdout=subprocess.PIPE)
    elif sys.platform == 'win32':
        subprocess.Popen('explorer.exe ' + uno.fileUrlToSystemPath(LeenO_path()), shell=True, stdout=subprocess.PIPE)
        subprocess.Popen('"C:/Program Files (x86)/Geany/bin/geany.exe" ' + uno.fileUrlToSystemPath(LeenO_path()) + '/python/pythonpath/pyleeno.py', shell=True, stdout=subprocess.PIPE)
    return
########################################################################
def Inser_SottoCapitolo(arg=None):
    Ins_Categorie(2)

def Inser_SottoCapitolo_arg(lrow, sTesto): #
    '''
    lrow    { double } : id della riga di inerimento
    sTesto  { string } : titolo della sottocategoria
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return

    if oSheet.getCellByPosition(1, lrow).CellStyle == 'Default': lrow -= 2#se oltre la riga rossa
    if oSheet.getCellByPosition(1, lrow).CellStyle == 'Riga_rossa_Chiudi': lrow -= 1#se riga rossa
    insRows(lrow, 1)
    oSheet.getCellByPosition(2, lrow).String = sTesto
# inserisco i valori e le formule
    oSheet.getCellRangeByPosition(0, lrow, 41, lrow).CellStyle = 'livello2 valuta'
    oSheet.getCellRangeByPosition(2, lrow, 17, lrow).CellStyle = 'livello2_'
    oSheet.getCellRangeByPosition(18, lrow, 18, lrow).CellStyle = 'livello2 scritta mini'
    oSheet.getCellRangeByPosition(24, lrow, 24, lrow).CellStyle = 'livello2 valuta mini %'
    oSheet.getCellRangeByPosition(29, lrow, 29, lrow).CellStyle = 'livello2 valuta mini %'
    oSheet.getCellRangeByPosition(30, lrow, 30, lrow).CellStyle = 'livello2 valuta mini'
    oSheet.getCellRangeByPosition(31, lrow, 33, lrow).CellStyle = 'livello2_'
    oSheet.getCellRangeByPosition(2, lrow, 11, lrow).merge(True)
    #~ oSheet.getCellByPosition(1, lrow).Formula = '=AF' + str(lrow+1) + '''&"."&''' + 'AG' + str(lrow+1)
    # rinumero e ricalcolo
    ocellBaseA = oSheet.getCellByPosition(1, lrow)
    ocellBaseR = oSheet.getCellByPosition(31, lrow)

    lrowProvv = lrow-1
    while oSheet.getCellByPosition(32, lrowProvv).CellStyle != 'livello2 valuta':
        if lrowProvv > 4:
            lrowProvv -=1
        else:
            break
    oSheet.getCellByPosition(32, lrow).Value = oSheet.getCellByPosition(1 , lrowProvv).Value + 1
    lrowProvv = lrow-1
    while oSheet.getCellByPosition(31, lrowProvv).CellStyle != 'Livello-1-scritta':
        if lrowProvv > 4:
            lrowProvv -=1
        else:
            break
    oSheet.getCellByPosition(31, lrow).Value = oSheet.getCellByPosition(1 , lrowProvv).Value
    #~ SubSum_Cap(lrow)

########################################################################
def Ins_Categorie(n):
    '''
    n    { int } : livello della categoria
    0 = SuperCategoria
    1 = Categoria
    2 = SubCategoria
    '''
    #~ datarif = datetime.now()

    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    row = Range2Cell()[1]
    if oSheet.getCellByPosition(0, row).CellStyle in stili_computo:
        lrow = next_voice(row, 1)
    elif oSheet.getCellByPosition(0, row).CellStyle in noVoce:
        lrow = row+1
    else:
        return
    sTesto = ''
    if n==0:
        sTesto = 'Inserisci il titolo per la Supercategoria'
    elif n==1:
        sTesto = 'Inserisci il titolo per la Categoria'
    elif n==2:
        sTesto = 'Inserisci il titolo per la Sottocategoria'
    sString = InputBox('', sTesto)
    if sString == None or sString == '':
        return
    zoom = oDoc.CurrentController.ZoomValue
    oDoc.CurrentController.ZoomValue = 400
    if n==0:
        Inser_SuperCapitolo_arg(lrow, sString)
    elif n==1:
        Inser_Capitolo_arg(lrow, sString)
    elif n==2:
        Inser_SottoCapitolo_arg(lrow, sString)

    _gotoCella(2, lrow)
    Rinumera_TUTTI_Capitoli2()
    oDoc.CurrentController.ZoomValue = zoom
    oDoc.CurrentController.setFirstVisibleColumn(0)
    oDoc.CurrentController.setFirstVisibleRow(lrow-5)
    #~ MsgBox('eseguita in ' + str((datetime.now() - datarif).total_seconds()) + ' secondi!','')
    
########################################################################
def Inser_SuperCapitolo(arg=None):
    Ins_Categorie(0)

def Inser_SuperCapitolo_arg(lrow, sTesto='Super Categoria'): #
    '''
    lrow    { double } : id della riga di inerimento
    sTesto  { string } : titolo della categoria
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return
    #~ lrow = Range2Cell()[1]
    if oSheet.getCellByPosition(1, lrow).CellStyle == 'Default': lrow -= 2#se oltre la riga rossa
    if oSheet.getCellByPosition(1, lrow).CellStyle == 'Riga_rossa_Chiudi': lrow -= 1#se riga rossa
    insRows(lrow, 1)
    oSheet.getCellByPosition(2, lrow).String = sTesto
    # inserisco i valori e le formule
    oSheet.getCellRangeByPosition(0, lrow, 41, lrow).CellStyle = 'Livello-0-scritta'
    oSheet.getCellRangeByPosition(2, lrow, 17, lrow).CellStyle = 'Livello-0-scritta mini'
    oSheet.getCellRangeByPosition(18, lrow, 18, lrow).CellStyle = 'Livello-0-scritta mini val'
    oSheet.getCellRangeByPosition(24, lrow, 24, lrow).CellStyle = 'Livello-0-scritta mini %'
    oSheet.getCellRangeByPosition(29, lrow, 29, lrow).CellStyle = 'Livello-0-scritta mini %'
    oSheet.getCellRangeByPosition(30, lrow, 30, lrow).CellStyle = 'Livello-0-scritta mini val'
    oSheet.getCellRangeByPosition(2, lrow, 11, lrow).merge(True)
    # rinumero e ricalcolo
    ocellBaseA = oSheet.getCellByPosition(1, lrow)
    ocellBaseR = oSheet.getCellByPosition(31, lrow)
    lrowProvv = lrow-1
    while oSheet.getCellByPosition(31, lrowProvv).CellStyle != 'Livello-0-scritta':
        if lrowProvv > 4:
            lrowProvv -=1
        else:
            break
    oSheet.getCellByPosition(31, lrow).Value = oSheet.getCellByPosition(1 , lrowProvv).Value + 1
########################################################################
def Inser_Capitolo(arg=None):
    Ins_Categorie(1)

def Inser_Capitolo_arg(lrow, sTesto='Categoria'): #
    '''
    lrow    { double } : id della riga di inerimento
    sTesto  { string } : titolo della categoria
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return
    #~ lrow = Range2Cell()[1]
    if oSheet.getCellByPosition(1, lrow).CellStyle == 'Default': lrow -= 2#se oltre la riga rossa
    if oSheet.getCellByPosition(1, lrow).CellStyle == 'Riga_rossa_Chiudi': lrow -= 1#se riga rossa
    insRows(lrow, 1)
    oSheet.getCellByPosition(2, lrow).String = sTesto
    # inserisco i valori e le formule
    oSheet.getCellRangeByPosition(0, lrow, 41, lrow).CellStyle = 'Livello-1-scritta'
    oSheet.getCellRangeByPosition(2, lrow, 17, lrow).CellStyle = 'Livello-1-scritta mini'
    oSheet.getCellRangeByPosition(18, lrow, 18, lrow).CellStyle = 'Livello-1-scritta mini val'
    oSheet.getCellRangeByPosition(24, lrow, 24, lrow).CellStyle = 'Livello-1-scritta mini %'
    oSheet.getCellRangeByPosition(29, lrow, 29, lrow).CellStyle = 'Livello-1-scritta mini %'
    oSheet.getCellRangeByPosition(30, lrow, 30, lrow).CellStyle = 'Livello-1-scritta mini val'
    oSheet.getCellRangeByPosition(2, lrow, 11, lrow).merge(True)
    # rinumero e ricalcolo
    ocellBaseA = oSheet.getCellByPosition(1, lrow)
    ocellBaseR = oSheet.getCellByPosition(31, lrow)
    lrowProvv = lrow-1
    while oSheet.getCellByPosition(31, lrowProvv).CellStyle != 'Livello-1-scritta':
        if lrowProvv > 4:
            lrowProvv -=1
        else:
            break
    oSheet.getCellByPosition(31, lrow).Value = oSheet.getCellByPosition(1 , lrowProvv).Value + 1
########################################################################
def Rinumera_TUTTI_Capitoli2(arg=None):
    Sincronizza_SottoCap_Tag_Capitolo_Cor()# sistemo gli idcat voce per voce
    Tutti_Subtotali()# ricalcola i totali di categorie e subcategorie

def Tutti_Subtotali(arg=None):
    '''ricalcola i subtotali di categorie e subcategorie'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return
    for n in range(0, ultima_voce(oSheet)+1):
        if oSheet.getCellByPosition(0, n).CellStyle == 'Livello-0-scritta':
            SubSum_SuperCap(n)
        if oSheet.getCellByPosition(0, n).CellStyle == 'Livello-1-scritta':
            SubSum_Cap(n)
        if oSheet.getCellByPosition(0, n).CellStyle == 'livello2 valuta':
            SubSum_SottoCap(n)
# TOTALI GENERALI
    lrow = ultima_voce(oSheet)+1
    for x in (1, lrow):
        oSheet.getCellByPosition(17, x).Formula = '=SUBTOTAL(9;R4:R' + str(lrow+1) + ')'
        oSheet.getCellByPosition(18, x).Formula = '=SUBTOTAL(9;S4:S' + str(lrow+1) + ')'
        oSheet.getCellByPosition(30, x).Formula = '=SUBTOTAL(9;AE4:AE' + str(lrow+1) + ')'
        oSheet.getCellByPosition(36, x).Formula = '=SUBTOTAL(9;AK4:AK' + str(lrow+1) + ')'
########################################################################
def SubSum_SuperCap(lrow):
    '''
    lrow    { double } : id della riga di inerimento
    inserisce i dati nella riga di SuperCategoria
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return
    #~ lrow = Range2Cell()[1]
    lrowE = ultima_voce(oSheet)+2
    nextCap = lrowE
    for n in range(lrow+1, lrowE):
        if oSheet.getCellByPosition(18, n).CellStyle in('Livello-0-scritta mini val', 'Comp TOTALI'):
            #~ MsgBox(oSheet.getCellByPosition(18, n).CellStyle,'')
            nextCap = n + 1
            break
    #~ oDoc.enableAutomaticCalculation(False)
    oSheet.getCellByPosition(18, lrow).Formula = '=SUBTOTAL(9;S' + str(lrow + 1) + ':S' + str(nextCap) + ')'
    oSheet.getCellByPosition(18, lrow).CellStyle = 'Livello-0-scritta mini val'
    oSheet.getCellByPosition(24, lrow).Formula = '=S' + str(lrow + 1) + '/S' + str(lrowE)
    oSheet.getCellByPosition(24, lrow).CellStyle = 'Livello-0-scritta mini %'
    oSheet.getCellByPosition(28, lrow).Formula = '=SUBTOTAL(9;AC' + str(lrow + 1) + ':AC' + str(nextCap) + ')'
    oSheet.getCellByPosition(29, lrow).Formula = '=AE' + str(lrow + 1) + '/S' + str(lrow + 1)
    oSheet.getCellByPosition(29, lrow).CellStyle = 'Livello-0-scritta mini %'
    oSheet.getCellByPosition(30, lrow).Formula = '=SUBTOTAL(9;AE' + str(lrow + 1) + ':AE' + str(nextCap) + ')'
    oSheet.getCellByPosition(30, lrow).CellStyle = 'Livello-0-scritta mini val'
    #~ oDoc.enableAutomaticCalculation(True)
########################################################################
def SubSum_SottoCap(lrow):
    '''
    lrow    { double } : id della riga di inerimento
    inserisce i dati nella riga di subcategoria
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return
    #lrow = 0#Range2Cell()[1]
    lrowE = ultima_voce(oSheet)+2
    nextCap = lrowE
    for n in range(lrow+1, lrowE):
        if oSheet.getCellByPosition(18, n).CellStyle in('livello2 scritta mini', 'Livello-0-scritta mini val', 'Livello-1-scritta mini val', 'Comp TOTALI'):
            nextCap = n + 1
            break
    oSheet.getCellByPosition(18, lrow).Formula = '=SUBTOTAL(9;S' + str(lrow + 1) + ':S' + str(nextCap) + ')'
    oSheet.getCellByPosition(18, lrow).CellStyle = 'livello2 scritta mini'
    oSheet.getCellByPosition(24, lrow).Formula = '=S' + str(lrow + 1) + '/S' + str(lrowE)
    oSheet.getCellByPosition(24, lrow).CellStyle = 'livello2 valuta mini %'
    oSheet.getCellByPosition(28, lrow).Formula = '=SUBTOTAL(9;AC' + str(lrow + 1) + ':AC' + str(nextCap) + ')'
    oSheet.getCellByPosition(28, lrow).CellStyle = 'livello2 scritta mini'
    oSheet.getCellByPosition(29, lrow).Formula = '=AE' + str(lrow + 1) + '/S' + str(lrow +1)
    oSheet.getCellByPosition(29, lrow).CellStyle = 'livello2 valuta mini %'
    oSheet.getCellByPosition(30, lrow).Formula = '=SUBTOTAL(9;AE' + str(lrow + 1) + ':AE' + str(nextCap) + ')'
    oSheet.getCellByPosition(30, lrow).CellStyle = 'livello2 valuta mini'
########################################################################
def SubSum_Cap(lrow):
    '''
    lrow    { double } : id della riga di inerimento
    inserisce i dati nella riga di categoria
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return
    #~ lrow = Range2Cell()[1]
    lrowE = ultima_voce(oSheet)+2
    nextCap = lrowE
    for n in range(lrow+1, lrowE):
        if oSheet.getCellByPosition(18, n).CellStyle in('Livello-1-scritta mini val','Livello-0-scritta mini val',  'Comp TOTALI'):
            #~ MsgBox(oSheet.getCellByPosition(18, n).CellStyle,'')
            nextCap = n + 1
            break
    #~ oDoc.enableAutomaticCalculation(False)
    oSheet.getCellByPosition(18, lrow).Formula = '=SUBTOTAL(9;S' + str(lrow + 1) + ':S' + str(nextCap) + ')'
    oSheet.getCellByPosition(18, lrow).CellStyle = 'Livello-1-scritta mini val'
    oSheet.getCellByPosition(24, lrow).Formula = '=S' + str(lrow + 1) + '/S' + str(lrowE)
    oSheet.getCellByPosition(24, lrow).CellStyle = 'Livello-1-scritta mini %'
    oSheet.getCellByPosition(28, lrow).Formula = '=SUBTOTAL(9;AC' + str(lrow + 1) + ':AC' + str(nextCap) + ')'
    oSheet.getCellByPosition(29, lrow).Formula = '=AE' + str(lrow + 1) + '/S' + str(lrow + 1)
    oSheet.getCellByPosition(29, lrow).CellStyle = 'Livello-1-scritta mini %'
    oSheet.getCellByPosition(30, lrow).Formula = '=SUBTOTAL(9;AE' + str(lrow + 1) + ':AE' + str(nextCap) + ')'
    oSheet.getCellByPosition(30, lrow).CellStyle = 'Livello-1-scritta mini val'
    #~ oDoc.enableAutomaticCalculation(True)

########################################################################
def Sincronizza_SottoCap_Tag_Capitolo_Cor(arg=None):
    '''
    lrow    { double } : id della riga di inerimento
    sincronizza il categoria e sottocategorie
    '''
    datarif = datetime.now()
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return
#    lrow = Range2Cell()[1]
    lastRow = ultima_voce(oSheet)+1

    listasbcat = list()
    listacat = list()
    listaspcat = list()
    for lrow in range(0,lastRow): # 
        if oSheet.getCellByPosition(2, lrow).CellStyle == 'livello2_': #SUB CATEGORIA
            if oSheet.getCellByPosition(2, lrow).String not in listasbcat:
                listasbcat.append((oSheet.getCellByPosition(2, lrow).String))
            try:
                oSheet.getCellByPosition(31, lrow).Value = idspcat
            except:
                pass
            try:
                oSheet.getCellByPosition(32, lrow).Value = idcat
            except:
                pass
            idsbcat = listasbcat.index(oSheet.getCellByPosition(2, lrow).String) +1
            oSheet.getCellByPosition(33, lrow).Value = idsbcat
            oSheet.getCellByPosition(1, lrow).Formula = '=AF' + str(lrow+1) +'&"."&AG' + str(lrow+1) + '&"."&AH' + str(lrow+1)
            
        elif oSheet.getCellByPosition(2, lrow).CellStyle == 'Livello-1-scritta mini': #CATEGORIA
            if oSheet.getCellByPosition(2, lrow).String not in listacat:
                listacat.append((oSheet.getCellByPosition(2, lrow).String))
                
                idsbcat = None
                
            try:
                oSheet.getCellByPosition(31, lrow).Value = idspcat
            except:
                pass
            idcat = listacat.index(oSheet.getCellByPosition(2, lrow).String) +1
            oSheet.getCellByPosition(32, lrow).Value = idcat
            oSheet.getCellByPosition(1, lrow).Formula = '=AF' + str(lrow+1) +'&"."&AG' + str(lrow+1)

        elif oSheet.getCellByPosition(2, lrow).CellStyle == 'Livello-0-scritta mini': #SUPER CATEGORIA
            if oSheet.getCellByPosition(2, lrow).String not in listaspcat:
                listaspcat.append((oSheet.getCellByPosition(2, lrow).String))
                
                idcat = idsbcat = None
                
            idspcat = listaspcat.index(oSheet.getCellByPosition(2, lrow).String) +1
            oSheet.getCellByPosition(31, lrow).Value = idspcat
            oSheet.getCellByPosition(1, lrow).Formula = '=AF' + str(lrow+1)
            
        elif oSheet.getCellByPosition(33, lrow).CellStyle == 'compTagRiservato': #CATEGORIA
            try:
                oSheet.getCellByPosition(33, lrow).Value = idsbcat
            except:
                oSheet.getCellByPosition(33, lrow).Value = 0
            try:
                oSheet.getCellByPosition(32, lrow).Value = idcat
            except:
                oSheet.getCellByPosition(32, lrow).Value = 0
            try:
                oSheet.getCellByPosition(31, lrow).Value = idspcat
            except:
                oSheet.getCellByPosition(31, lrow).Value = 0

    #~ MsgBox('Importazione eseguita con successo\n in ' + str((datetime.now() - datarif).total_seconds()) + ' secondi!','')
    
########################################################################
def insRows(lrow, nrighe): #forse inutile
    '''
    lrow    { double }  : id della riga di inerimento
    lrow    { integer } : numero di nuove righe da inserire

    Inserisce nrighe nella posizione lrow - alternativo a
    oSheet.getRows().insertByIndex(lrow, 1)
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    iSheet = oSheet.RangeAddress.Sheet
    #~ oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    #~ lrow = Range2Cell()[1]
    oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
    oCellRangeAddr.Sheet = iSheet
    oCellRangeAddr.StartColumn = 0
    oCellRangeAddr.EndColumn = 0
    oCellRangeAddr.StartRow = lrow
    oCellRangeAddr.EndRow = lrow + nrighe - 1
    oSheet.insertCells(oCellRangeAddr, 3)   # com.sun.star.sheet.CellInsertMode.ROW
########################################################################
def ultima_voce(oSheet):
    #~ oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    nRow = getLastUsedCell(oSheet).EndRow
    if nRow ==0:
        return 0
    for n in reversed(range(0, nRow)):
        #~ if oSheet.getCellByPosition(0, n).CellStyle in('Comp TOTALI'):
        if oSheet.getCellByPosition(0, n).CellStyle in('EP-aS', 'EP-Cs', 'An-sfondo-basso Att End', 'Comp End Attributo',
                                                        'Comp End Attributo_R', 'comp Int_colonna', 'comp Int_colonna_R_prima',
                                                        'Livello-0-scritta', 'Livello-1-scritta', 'livello2 valuta'):
            break
    return n
########################################################################
def uFindStringCol(sString, nCol, oSheet, start=2):
    '''
    sString { string }  : stringa da cercare
    nCol    { integer } : indice di colonna
    oSheet  { object }  :
    start   { integer } : riga di partenza

    Trova la prima ricorrenza di una stringa(sString) nella
    colonna nCol di un foglio di calcolo(oSheet) e restituisce
    in numero di riga
    '''
    oCell = oSheet.getCellByPosition(0,0)
    oCursor = oSheet.createCursorByRange(oCell)
    oCursor.gotoEndOfUsedArea(True)
    aAddress = oCursor.RangeAddress
    for nRow in range(start, aAddress.EndRow+1):
        if sString in oSheet.getCellByPosition(nCol,nRow).String:
            return nRow
########################################################################
def uFindString(sString, oSheet):
    '''
    sString { string }  : stringa da cercare
    oSheet  { object }  :

    Trova la prima ricorrenza di una stringa(sString) riga
    per riga in un foglio di calcolo(oSheet) e restituisce
    una tupla(IDcolonna, IDriga)
    '''
    oCell = oSheet.getCellByPosition(0,0)
    oCursor = oSheet.createCursorByRange(oCell)
    oCursor.gotoEndOfUsedArea(True)
    aAddress = oCursor.RangeAddress
    for nRow in range(0, aAddress.EndRow+1):
        for nCol in range(0, aAddress.EndColumn+1):
    # ritocco di +Daniele Zambelli:
            if sString in oSheet.getCellByPosition(nCol,nRow).String:
                return(nCol,nRow)
########################################################################
def join_sheets(arg=None):
    '''
    unisci fogli
    serve per unire tanti fogli in un unico foglio
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    lista_fogli = oDoc.Sheets.ElementNames
    if oDoc.getSheets().hasByName('unione_fogli') == False:
        sheet = oDoc.createInstance("com.sun.star.sheet.Spreadsheet")
        unione = oDoc.Sheets.insertByName('unione_fogli', sheet)
        unione = oDoc.getSheets().getByName('unione_fogli')
        for el in lista_fogli:
            oSheet = oDoc.getSheets().getByName(el)
            oRangeAddress = oSheet.getCellRangeByPosition(0,0,(getLastUsedCell(oSheet).EndColumn),(getLastUsedCell(oSheet).EndRow)).getRangeAddress()
            oCellAddress = unione.getCellByPosition(0, getLastUsedCell(unione).EndRow+1).getCellAddress()
            oSheet.copyRange(oCellAddress, oRangeAddress)
        MsgBox('Unione dei fogli eseguita.','Avviso')
    else:
        unione = oDoc.getSheets().getByName('unione_fogli')
        MsgBox('Il foglio "unione_fogli" è già esistente, quindi non procedo.','Avviso!')
    oDoc.CurrentController.setActiveSheet(unione)
########################################################################
def mostra_fogli(arg=None):
    '''Mostra tutti i foglio fogli'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    lista_fogli = oDoc.Sheets.ElementNames
    for el in lista_fogli:
        oDoc.getSheets().getByName(el).IsVisible = True
########################################################################
def mostra_fogli_principali(arg=None):
    '''Mostra tutti i foglio fogli'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    lista_fogli = oDoc.Sheets.ElementNames
    for el in lista_fogli:
        oDoc.getSheets().getByName(el).IsVisible = True
        for nome in ('cP_', 'cT_', 'M1', 'S1', 'S2', 'S5', 'QUADRO ECONOMICO', '_LeenO', 'Scorciatoie'):
            if nome in el:
                oDoc.getSheets().getByName(el).IsVisible = False
########################################################################
def mostra_tabs_contab(arg=None):
    '''Mostra tutti i foglio fogli'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    lista_fogli = oDoc.Sheets.ElementNames
    sproteggi_sheet_TUTTE()
    for el in lista_fogli:
        oDoc.getSheets().getByName(el).IsVisible = True
        for nome in ('cP_', 'M1', 'S1', 'S2', 'S5', 'QUADRO ECONOMICO', '_LeenO', 'Scorciatoie'):
            if nome in el:
                oDoc.getSheets().getByName(el).IsVisible = False
########################################################################
def mostra_tabs_computo(arg=None):
    '''Mostra tutti i foglio fogli'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    lista_fogli = oDoc.Sheets.ElementNames
    sproteggi_sheet_TUTTE()
    for el in lista_fogli:
        oDoc.getSheets().getByName(el).IsVisible = True
        for nome in ('cT_', 'M1', 'S1', 'S2', 'S5', 'QUADRO ECONOMICO', '_LeenO', 'Scorciatoie'):
            if nome in el:
                oDoc.getSheets().getByName(el).IsVisible = False
    
########################################################################
def copia_sheet(nSheet, tag):
    '''
    nSheet   { string } : nome sheet
    tag      { string } : stringa di tag
    duplica copia sheet corrente di fianco a destra
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    #~ nSheet = 'COMPUTO'
    oSheet = oDoc.getSheets().getByName(nSheet)
    idSheet = oSheet.RangeAddress.Sheet + 1
    if oDoc.getSheets().hasByName(nSheet +'_'+ tag) == True:
        MsgBox('La tabella di nome '+ nSheet +'_'+ tag + 'è già presente.', 'ATTENZIONE! Impossibile procedere.')
        return
    else:
        oDoc.Sheets.copyByName(nSheet, nSheet +'_'+ tag, idSheet)
        oSheet = oDoc.getSheets().getByName(nSheet +'_'+ tag)
        oDoc.CurrentController.setActiveSheet(oSheet)
        #~ oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
########################################################################
def Filtra_computo(nSheet, nCol, sString):
    '''
    nSheet   { string } : nome Sheet
    ncol     { integer } : colonna di tag
    sString  { string } : stringa di tag
    crea una nuova sheet contenente le sole voci filtrate
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    copia_sheet(nSheet, sString)
    oSheet = oDoc.CurrentController.ActiveSheet
    for lrow in reversed(range(0, ultima_voce(oSheet))):
        try:
            sStRange = Circoscrive_Voce_Computo_Att(lrow)
            sopra = sStRange.RangeAddress.StartRow
            sotto = sStRange.RangeAddress.EndRow
            if nCol ==1:
                test=sopra+1
            else:
                test=sotto
            if sString != oSheet.getCellByPosition(nCol,test).String:
                oSheet.getRows().removeByIndex(sopra, sotto-sopra+1)
                lrow =next_voice(lrow,0)
        except:
            lrow =next_voice(lrow,0)
    for lrow in range(3, getLastUsedCell(oSheet).EndRow):
        if oSheet.getCellByPosition(18,lrow).CellStyle == 'Livello-1-scritta mini val' and \
        oSheet.getCellByPosition(18,lrow).Value == 0 or \
        oSheet.getCellByPosition(18,lrow).CellStyle == 'livello2 scritta mini' and \
        oSheet.getCellByPosition(18,lrow).Value == 0:

            oSheet.getRows().removeByIndex(lrow, 1)

    #~ iCellAttr =(oDoc.createInstance("com.sun.star.sheet.CellFlags.OBJECTS"))
    flags = OBJECTS
    oSheet.getCellRangeByPosition(0,0,42,0).clearContents(flags) #cancello gli oggetti
    oDoc.CurrentController.select(oSheet.getCellByPosition(0,3))
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
########################################################################
def Filtra_Computo_Cap(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    nSheet = oSheet.getCellByPosition(7,8).String
    sString = oSheet.getCellByPosition(7,10).String
    Filtra_computo(nSheet, 31, sString)
########################################################################
def Filtra_Computo_SottCap(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    nSheet = oSheet.getCellByPosition(7, 8).String
    sString = oSheet.getCellByPosition(7, 12).String
    Filtra_computo(nSheet, 32, sString)
########################################################################
def Filtra_Computo_A(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    nSheet = oSheet.getCellByPosition(7, 8).String
    sString = oSheet.getCellByPosition(7, 14).String
    Filtra_computo(nSheet, 33, sString)
########################################################################
def Filtra_Computo_B(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    nSheet = oSheet.getCellByPosition(7, 8).String
    sString = oSheet.getCellByPosition(7, 16).String
    Filtra_computo(nSheet, 34, sString)
########################################################################
def Filtra_Computo_C(arg=None): #filtra in base al codice di prezzo
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    nSheet = oSheet.getCellByPosition(7, 8).String
    sString = oSheet.getCellByPosition(7, 20).String
    Filtra_computo(nSheet, 1, sString)
########################################################################
def vai_a_M1(arg=None):
    chiudi_dialoghi()
    _gotoSheet('M1', 85)
    _primaCella(0,0)
########################################################################
def vai_a_S2(arg=None):
    chiudi_dialoghi()
    _gotoSheet('S2')
    _primaCella(0,0)
########################################################################
def Vai_a_S1(arg=None):
    chiudi_dialoghi()
    _gotoSheet('S1')
    _primaCella(0,190)
########################################################################
def vai_a_ElencoPrezzi(event=None):
    chiudi_dialoghi()
    _gotoSheet('Elenco Prezzi')
########################################################################
def vai_a_Computo(arg=None):
    chiudi_dialoghi()
    _gotoSheet('COMPUTO')
########################################################################
def vai_a_variabili(arg=None):
    chiudi_dialoghi()
    _gotoSheet('S1', 85)
    _primaCella(6,289)
########################################################################
def vai_a_Scorciatoie(arg=None):
    chiudi_dialoghi()
    _gotoSheet('Scorciatoie')
    _primaCella(0,0)
########################################################################
def _gotoSheet(nSheet, fattore=100):
    '''
    nSheet   { string } : nome Sheet
    attiva e seleziona una sheet
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.Sheets.getByName(nSheet)
    #~ oDoc.getCurrentSelection().getCellAddress().Sheet

    oSheet.IsVisible = True
    oDoc.CurrentController.setActiveSheet(oSheet)
    #~ oDoc.CurrentController.ZoomValue = fattore
    #~ oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
########################################################################
def _primaCella(IDcol=0, IDrow=0):
    '''
    IDcol   { integer } : id colonna
    IDrow   { integer } : id riga
    settaggio prima cella visibile(IDcol, IDrow)
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    oDoc.CurrentController.setFirstVisibleColumn(IDcol)
    oDoc.CurrentController.setFirstVisibleRow(IDrow)
    return
########################################################################
def ordina_col(ncol):
    '''
    ncol   { integer } : id colonna
    ordina i dati secondo la colonna con id ncol
    '''
    #~ oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    oProp = []
    oProp0 = PropertyValue()
    oProp0.Name = 'ByRows'
    oProp0.Value = True
    oProp1 = PropertyValue()
    oProp1.Name = 'HasHeader'
    oProp1.Value = False
    oProp2 = PropertyValue()
    oProp2.Name = 'CaseSensitive'
    oProp2.Value = False
    oProp3 = PropertyValue()
    oProp3.Name = 'NaturalSort'
    oProp3.Value = False
    oProp4 = PropertyValue()
    oProp4.Name = 'IncludeAttribs'
    oProp4.Value = True
    oProp5 = PropertyValue()
    oProp5.Name = 'UserDefIndex'
    oProp5.Value = 0
    oProp6 = PropertyValue()
    oProp6.Name = 'Col1'
    oProp6.Value = ncol
    oProp7 = PropertyValue()
    oProp7.Name = 'Ascending1'
    oProp7.Value = True
    oProp.append(oProp0)
    oProp.append(oProp1)
    oProp.append(oProp2)
    oProp.append(oProp3)
    oProp.append(oProp4)
    oProp.append(oProp5)
    oProp.append(oProp6)
    oProp.append(oProp7)
    properties = tuple(oProp)
    dispatchHelper.executeDispatch(oFrame, '.uno:DataSort', '', 0, properties)
########################################################################
def sproteggi_sheet_TUTTE(arg=None):
    '''
    Sprotegge e riordina tutti fogli del documento.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheets = oDoc.Sheets.ElementNames
    for nome in oSheets:
        oSheet = oDoc.getSheets().getByName(nome)
        oSheet.unprotect('')
    #riordino le sheet
    oDoc.Sheets.moveByName("Elenco Prezzi", 0)
    if oDoc.Sheets.hasByName("Analisi di Prezzo"):
        oDoc.Sheets.moveByName("Analisi di Prezzo", 1)
    oDoc.Sheets.moveByName("COMPUTO", 2)
    if oDoc.Sheets.hasByName("VARIANTE"):
        oDoc.Sheets.moveByName("VARIANTE", 3)
    if oDoc.Sheets.hasByName("CONTABILITA"):
        oDoc.Sheets.moveByName("CONTABILITA", 4)
    if oDoc.Sheets.hasByName("M1"):
        oDoc.Sheets.moveByName("M1", 5)
    oDoc.Sheets.moveByName("S1", 6)
    oDoc.Sheets.moveByName("S2", 7)
    # ~oDoc.Sheets.moveByName("S4", 9)
    if oDoc.Sheets.hasByName("S5"):
        oDoc.Sheets.moveByName("S5", 10)
    if oDoc.Sheets.hasByName("copyright_LeenO"):
        oDoc.Sheets.moveByName("copyright_LeenO", oDoc.Sheets.Count)
########################################################################
def setPreview(arg=0):
    '''
    colore   { integer } : id colore
    attribuisce al foglio corrente un colore a scelta
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet #se questa dà errore, il preview è già attivo
    adatta_altezza_riga(oSheet.Name)
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    oProp = PropertyValue()
    properties =(oProp,)
    dispatchHelper.executeDispatch(oFrame, '.uno:PrintPreview', '', arg, properties)
########################################################################
def setTabColor(colore):
    '''
    colore   { integer } : id colore
    attribuisce al foglio corrente un colore a scelta
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    oProp = PropertyValue()
    oProp.Name = 'TabBgColor'
    oProp.Value = colore
    properties =(oProp,)
    dispatchHelper.executeDispatch(oFrame, '.uno:SetTabBgColor', '', 0, properties)
########################################################################
def txt_Format(stile):
    '''
    Forza la formattazione della cella
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    oProp = PropertyValue()
    oProp.Name = stile
    oProp.Value = True
    properties =(oProp,)
    dispatchHelper.executeDispatch(oFrame, '.uno:' + stile, '', 0, properties)
########################################################################
def show_sheets(x=True):
    '''
    x   { boolean } : True = ON, False = OFF
    
    Mastra/nasconde tutte le tabelle ad escluzione di COMPUTO ed Elenco Prezzi
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheets = list(oDoc.getSheets().getElementNames())
    # ~for nome in ('M1', 'S1', 'S2', 'S4', 'S5', 'Elenco Prezzi', 'COMPUTO'):
    for nome in ('M1', 'S1', 'S2', 'S5', 'Elenco Prezzi', 'COMPUTO'):
        oSheets.remove(nome)
    #~ oSheets.remove('Elenco Prezzi')
    #~ oSheets.remove('COMPUTO')
    for nome in oSheets:
        oSheet = oDoc.getSheets().getByName(nome)
        oSheet.IsVisible = x
    for nome in ('COMPUTO', 'Elenco Prezzi'):
        oSheet = oDoc.getSheets().getByName(nome)
        oSheet.IsVisible = True
    #~ if x == True:
        #~ for nome in ('M1', 'S1', 'S2', 'S4', 'S5'):
            #~ oSheet = oDoc.getSheets().getByName(nome).IsVisible = False
def nascondi_sheets(arg=None):
    show_sheets(False)
########################################################################
def salva_come(nomefile=None):
    '''
    nomefile   { string } : nome del file di destinazione
    Se presente l'argomento nomefile, salva il file corrente in nomefile.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    
    oProp = []
    if nomefile != None:
        nomefile = uno.systemPathToFileUrl(nomefile)
        oProp0 = PropertyValue()
        oProp0.Name = "URL"
        oProp0.Value = nomefile
        oProp.append(oProp0)

    oProp1 = PropertyValue()
    oProp1.Name = "FilterName"
    oProp1.Value = "calc8"
    oProp.append(oProp1)
    
    properties = tuple(oProp)

    dispatchHelper.executeDispatch(oFrame, ".uno:SaveAs", "", 0, properties)
########################################################################
def _gotoCella(IDcol=0, IDrow=0):
    '''
    IDcol   { integer } : id colonna
    IDrow   { integer } : id riga

    muove il cursore nelle cella(IDcol, IDrow)
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    
    oDoc.CurrentController.select(oSheet.getCellByPosition(IDcol, IDrow))
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges"))
    return
########################################################################
def loVersion(arg=None):
    '''
    Legge il numero di versione di LibreOffice.
    '''
    sAccess = createUnoService("com.sun.star.configuration.ConfigurationAccess")
    aConfigProvider = createUnoService("com.sun.star.configuration.ConfigurationProvider")
    arg = uno.createUnoStruct('com.sun.star.beans.PropertyValue')
    arg.Name = "nodepath"
    arg.Value = '/org.openoffice.Setup/Product'
    return aConfigProvider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (arg,)).ooSetupVersionAboutBox
#~ ########################################################################
def adatta_altezza_riga(nSheet=None):
    '''
    Adattal'altezza delle righe al contenuto delle celle.
    
    nSheet   { string } : nSheet della sheet
    imposta l'altezza ottimale delle celle
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oDoc.getSheets().hasByName('S1') == False: return
    nSheet = oSheet.Name
    oDoc.getSheets().hasByName(nSheet)
    oSheet.getCellRangeByPosition(0, 0, getLastUsedCell(oSheet).EndColumn, getLastUsedCell(oSheet).EndRow).Rows.OptimalHeight = True
    #~ se la versione di LibreOffice è maggiore della 5.2, esegue il comando agendo direttamente sullo stile
    lista_stili = ('comp 1-a', 'Comp-Bianche in mezzo Descr_R', 'Comp-Bianche in mezzo Descr', 'EP-a', 'Ultimus_centro_bordi_lati')
    if float(loVersion()[:3]) > 5.2: # and float(loVersion()[:3]) < 6.2: NELLA VERSIONE 6.2 IL PROBLEMA NON è ANCORA RISOLTO
        for stile_cella in lista_stili:
            try:
                oDoc.StyleFamilies.getByName("CellStyles").getByName(stile_cella).IsTextWrapped = True
            except:
                pass
        #~ #if nSheet in('VARIANTE', 'COMPUTO', 'CONTABILITA', 'Richiesta offerta'):
        test = getLastUsedCell(oSheet).EndRow+1
        for y in range(0, test):
            if oSheet.getCellByPosition(2, y).CellStyle in lista_stili:
                oSheet.getCellRangeByPosition(0, y, getLastUsedCell(oSheet).EndColumn, y).Rows.OptimalHeight = True
    if oSheet.Name in('Elenco Prezzi', 'VARIANTE', 'COMPUTO', 'CONTABILITA'):
        oSheet.getCellByPosition(0, 2).Rows.Height = 800
    if nSheet == 'Elenco Prezzi':
        test = getLastUsedCell(oSheet).EndRow+1
        for y in range(0, test):
            oSheet.getCellRangeByPosition(0, y, getLastUsedCell(oSheet).EndColumn, y).Rows.OptimalHeight = True
    return
########################################################################
def voce_breve(arg=None):
    '''
    Cambia il numero di caratteri visualizzati per la descrizione voce in COMPUTO,
    CONTABILITA E VARIANTE.
    '''
    chiudi_dialoghi()
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet.getCellRangeByPosition(0, 0, getLastUsedCell(oSheet).EndColumn, getLastUsedCell(oSheet).EndRow).Rows.OptimalHeight = True
    if oDoc.getSheets().hasByName('S1') == False: return
    if oSheet.Name in ('COMPUTO', 'VARIANTE'):
        oSheet = oDoc.getSheets().getByName('S1')
        if oSheet.getCellRangeByName('S1.H337').Value < 10000:
            conf.write(path_conf, 'Computo', 'inizio_voci_abbreviate', oSheet.getCellRangeByName('S1.H337').String)
            oSheet.getCellRangeByName('S1.H337').Value = 10000
        else:
            oSheet.getCellRangeByName('S1.H337').Value = int(conf.read(path_conf, 'Computo', 'inizio_voci_abbreviate'))
        if oSheet.getCellRangeByName('S1.H338').Value < 10000:
            conf.write(path_conf, 'Computo', 'fine_voci_abbreviate', oSheet.getCellRangeByName('S1.H338').String)
            oSheet.getCellRangeByName('S1.H338').Value = 10000
        else:
            oSheet.getCellRangeByName('S1.H338').Value = int(conf.read(path_conf, 'Computo', 'fine_voci_abbreviate'))
        adatta_altezza_riga()
        
    elif oSheet.Name == 'CONTABILITA':
        oSheet = oDoc.getSheets().getByName('S1')
        if oDoc.NamedRanges.hasByName("#Lib#1") == True:
            MsgBox("Risulta già registrato un SAL. NON E' POSSIBILE PROCEDERE.",'ATTENZIONE!')
            return
        else:
            if oSheet.getCellRangeByName('S1.H335').Value < 10000:
                conf.write(path_conf, 'Contabilità', 'cont_inizio_voci_abbreviate', oSheet.getCellRangeByName('S1.H335').String)
                oSheet.getCellRangeByName('S1.H335').Value = 10000
            else:
                oSheet.getCellRangeByName('S1.H335').Value = int(conf.read(path_conf, 'Contabilità', 'cont_inizio_voci_abbreviate'))
            if oSheet.getCellRangeByName('S1.H336').Value < 10000:
                conf.write(path_conf, 'Contabilità', 'cont_fine_voci_abbreviate', oSheet.getCellRangeByName('S1.H336').String)
                oSheet.getCellRangeByName('S1.H336').Value = 10000
            else:
                oSheet.getCellRangeByName('S1.H336').Value = int(conf.read(path_conf, 'Contabilità', 'cont_fine_voci_abbreviate'))
            adatta_altezza_riga()
########################################################################
def cancella_voci_non_usate(arg=None):
    '''
    Cancella le voci di prezzo non utilizzate.
    '''
    chiudi_dialoghi()
    #~ oDialogo_attesa = dlg_attesa()
    #~ attesa().start() #mostra il dialogo

    if DlgSiNo('''Questo comando ripulisce l'Elenco Prezzi
dalle voci non utilizzate in nessuno degli altri elaborati.

LA PROCEDURA POTREBBE RICHIEDERE DEL TEMPO.

Vuoi procedere comunque?''', 'AVVISO!') == 3:
        #~ oDialogo_attesa.endExecute() #chiude il dialogo
        return
    oDoc = XSCRIPTCONTEXT.getDocument()
    oDoc.enableAutomaticCalculation(False)
    zoom = oDoc.CurrentController.ZoomValue
    oDoc.CurrentController.ZoomValue = 400
    oSheet = oDoc.CurrentController.ActiveSheet

    oRange=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
    SR = oRange.StartRow+1
    ER = oRange.EndRow+1
    lista_prezzi = list()
    for n in range(SR, ER):
        lista_prezzi.append (oSheet.getCellByPosition(0, n).String)
    lista = list()
    for tab in ('COMPUTO','Analisi di Prezzo', 'VARIANTE', 'CONTABILITA'):
        try:
            oSheet = oDoc.getSheets().getByName(tab)
            if tab == 'Analisi di Prezzo':
                col = 0
            else:
                col = 1
            for el in lista_prezzi:
                if uFindStringCol (el, col, oSheet):
                    lista.append(el)
        except:
            pass
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    da_cancellare = set(lista_prezzi).difference(set(lista))
    for n in reversed(range(SR, ER)):
        if oSheet.getCellByPosition(0, n).String in da_cancellare:
            oSheet.Rows.removeByIndex(n, 1)
        if oSheet.getCellByPosition(0, n).String == '' and \
        oSheet.getCellByPosition(1, n).String == '' and \
        oSheet.getCellByPosition(4, n).String == '':
            oSheet.Rows.removeByIndex(n, 1)
    oDoc.enableAutomaticCalculation(True)
    oDoc.CurrentController.ZoomValue = zoom
    _gotoCella(0, 3)
    #~ oDialogo_attesa.endExecute() #chiude il dialogo
########################################################################
    
def voce_breve_ep(arg=None):
    '''
    Ottimizza l'altezza delle celle di Elenco Prezzi o visualizza solo
    tre righe della descrizione.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet

    oRange=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
    SR = oRange.StartRow+1
    ER = oRange.EndRow-1

    if oSheet.getCellByPosition(1, 3).Rows.OptimalHeight == False:
        adatta_altezza_riga()
    else:
        hriga = oSheet.getCellRangeByName('B4').CharHeight * 65 * 2 + 100 #visualizza tre righe
        oSheet.getCellRangeByPosition(0, SR, 0, ER).Rows.Height = hriga

########################################################################
def scelta_viste(arg=None):
    '''
    Gestisce i dialoghi del menù viste nelle tabelle di Analisi di Prezzo,
    Elenco Prezzi, COMPUTO, VARIANTE, CONTABILITA'
    Genera i raffronti tra COMPUTO e VARIANTE e CONTABILITA'
    '''
    #~ refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    psm = uno.getComponentContext().ServiceManager
    dp = psm.createInstance('com.sun.star.awt.DialogProvider')
    if oSheet.Name in('VARIANTE', 'COMPUTO'):
        oDialog1 = dp.createDialog('vnd.sun.star.script:UltimusFree2.DialogViste_A?language=Basic&location=application')
        oDialog1Model = oDialog1.Model
        oDialog1.getControl('Dettaglio').State = conf.read(path_conf, 'Generale', 'dettaglio')
        if oSheet.getColumns().getByIndex(5).Columns.IsVisible  == True: oDialog1.getControl('CBMis').State = 1
        if oSheet.getColumns().getByIndex(17).Columns.IsVisible == True: oDialog1.getControl('CBSic').State = 1
        if oSheet.getColumns().getByIndex(28).Columns.IsVisible == True: oDialog1.getControl('CBMat').State = 1
        if oSheet.getColumns().getByIndex(29).Columns.IsVisible == True: oDialog1.getControl('CBMdo').State = 1
        if oSheet.getColumns().getByIndex(31).Columns.IsVisible == True: oDialog1.getControl('CBCat').State = 1
        if oSheet.getColumns().getByIndex(38).Columns.IsVisible == True: oDialog1.getControl('CBFig').State = 1

        sString = oDialog1.getControl('TextField10')
        sString.Text = oDoc.getSheets().getByName('S1').getCellRangeByName('H337').Value #inizio_voci_abbreviate
        sString = oDialog1.getControl('TextField11')
        sString.Text = oDoc.getSheets().getByName('S1').getCellRangeByName('H338').Value #fine_voci_abbreviate
        
        oDialog1.execute()

    #il salvataggio anche su leeno.conf serve alla funzione voce_breve()
        if oDialog1.getControl('TextField10').getText() != '10000': conf.write(path_conf, 'Computo', 'inizio_voci_abbreviate', oDialog1.getControl('TextField10').getText())
        oDoc.getSheets().getByName('S1').getCellRangeByName('H337').Value = float(oDialog1.getControl('TextField10').getText())

        if oDialog1.getControl('TextField11').getText() != '10000': conf.write(path_conf, 'Computo', 'fine_voci_abbreviate', oDialog1.getControl('TextField11').getText())
        oDoc.getSheets().getByName('S1').getCellRangeByName('H338').Value = float(oDialog1.getControl('TextField11').getText())
        #~ oDialog1.getControl('CBMdo').State = False
        #~ if oSheet.getColumns().getByIndex(29).Columns.IsVisible == True:
            #~ oDialog1.getControl('CBMdo').State = True

        if oDialog1.getControl('OBTerra').State == True:
            computo_terra_terra()
            oDialog1.getControl('CBSic').State = 0
            oDialog1.getControl('CBMdo').State = 0
            oDialog1.getControl('CBMat').State = 0
            oDialog1.getControl('CBCat').State = 0
            oDialog1.getControl('CBFig').State = 0
            oDialog1.getControl('CBMis').State = 1

        if oDialog1.getControl("CBMis").State == 0: #misure
            oSheet.getColumns().getByIndex(5).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(6).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(7).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(8).Columns.IsVisible = False
        else:
            oSheet.getColumns().getByIndex(5).Columns.IsVisible = True
            oSheet.getColumns().getByIndex(6).Columns.IsVisible = True
            oSheet.getColumns().getByIndex(7).Columns.IsVisible = True
            oSheet.getColumns().getByIndex(8).Columns.IsVisible = True   

        if oDialog1.getControl('CBMdo').State == True: #manodopera
            oSheet.getColumns().getByIndex(29).Columns.IsVisible = True
            oSheet.getColumns().getByIndex(30).Columns.IsVisible = True
            oSheet.getColumns().getByIndex(5).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(6).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(7).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(8).Columns.IsVisible = False
            #~ adatta_altezza_riga(oSheet)
            oSheet.clearOutline()
            struct(3)
        else:
            oSheet.getColumns().getByIndex(29).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(30).Columns.IsVisible = False

        if oDialog1.getControl('CBMat').State == 0: #materiali
            oSheet.getColumns().getByIndex(28).Columns.IsVisible = False

        else:
            oSheet.getColumns().getByIndex(28).Columns.IsVisible = True
        
        if oDialog1.getControl('CBCat').State == 0: #categorie
            oSheet.getColumns().getByIndex(31).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(32).Columns.IsVisible = False
            oSheet.getColumns().getByIndex(33).Columns.IsVisible = False
        else:
            oSheet.getColumns().getByIndex(31).Columns.IsVisible = True
            oSheet.getColumns().getByIndex(32).Columns.IsVisible = True
            oSheet.getColumns().getByIndex(33).Columns.IsVisible = True

        if oDialog1.getControl("CBSic").State == 0: #sicurezza
            oSheet.getColumns().getByIndex(17).Columns.IsVisible = False
        else:
            oSheet.getColumns().getByIndex(17).Columns.IsVisible = True

        if oDialog1.getControl("CBFig").State == 0: #figure
            oSheet.getColumns().getByIndex(38).Columns.IsVisible = False
        else:
            oSheet.getColumns().getByIndex(38).Columns.IsVisible = True

        if oDialog1.getControl('Dettaglio').State == 0: #
            conf.write(path_conf, 'Generale', 'dettaglio', '0')
            dettaglio_misure(0)
        else:
            conf.write(path_conf, 'Generale', 'dettaglio', '1')
            dettaglio_misure(0)
            dettaglio_misure(1)
    elif oSheet.Name in('Elenco Prezzi'):
        oCellRangeAddr=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
        oDialog1 = dp.createDialog("vnd.sun.star.script:UltimusFree2.DialogViste_EP?language=Basic&location=application")
        oDialog1Model = oDialog1.Model
        if oSheet.getColumns().getByIndex(3).Columns.IsVisible  == True: oDialog1.getControl('CBSic').State = 1
        if oSheet.getColumns().getByIndex(5).Columns.IsVisible  == True: oDialog1.getControl('CBMdo').State = 1
        if oSheet.getCellByPosition(1, 3).Rows.OptimalHeight == False: oDialog1.getControl('CBDesc').State = 1
        if oSheet.getColumns().getByIndex(7).Columns.IsVisible  == True: oDialog1.getControl('CBOrig').State = 1
        if oDialog1.execute() == 1:
            if oDialog1.getControl("CBSic").State == 0: #sicurezza
                oSheet.getColumns().getByIndex(3).Columns.IsVisible = False
            else:
                oSheet.getColumns().getByIndex(3).Columns.IsVisible = True

            if oDialog1.getControl("CBMdo").State == 0: #manodopera
                oSheet.getColumns().getByIndex(5).Columns.IsVisible = False
                oSheet.getColumns().getByIndex(6).Columns.IsVisible = False
            else:
                oSheet.getColumns().getByIndex(5).Columns.IsVisible = True
                oSheet.getColumns().getByIndex(6).Columns.IsVisible = True

            if oDialog1.getControl("CBDesc").State == 1: #descrizione
                oSheet.getColumns().getByIndex(3).Columns.IsVisible = False
                oSheet.getCellByPosition(1, 3).Rows.OptimalHeight
                voce_breve_ep()
            #~ elif oDialog1.getControl("CBDesc").State == 0: adatta_altezza_riga(oSheet.Name)

            if oDialog1.getControl("CBOrig").State == 0: #origine
                oSheet.getColumns().getByIndex(7).Columns.IsVisible = False
            else:
                oSheet.getColumns().getByIndex(7).Columns.IsVisible = True
            
            if oDialog1.getControl("CBSom").State == 1:
                genera_sommario()

            oRangeAddress=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
            SR = oRangeAddress.StartRow+1
            ER = oRangeAddress.EndRow#-1

            oSheet.getCellRangeByPosition(11, 0, 26, 0).Columns.IsVisible = True
            oSheet.getCellRangeByPosition(23 , SR, 25, ER).CellStyle = 'EP statistiche'
            oSheet.getCellRangeByPosition(26, SR, 26, ER).CellStyle = 'EP-mezzo %'
            oSheet.getCellRangeByName('AA2').CellStyle = 'EP-mezzo %'
            formule = list()
            oSheet.getCellByPosition(11, 0).String = 'COMPUTO'
            oSheet.getCellByPosition(15, 0).String = 'VARIANTE'
            oSheet.getCellByPosition(19, 0).String = "CONTABILITA"
            if oDialog1.getControl("ComVar").State == True: #Computo - Variante
                genera_sommario()
                oRangeAddress.StartColumn = 19
                oRangeAddress.EndColumn = 22

                oSheet.getCellByPosition(23, 0).String = 'COMPUTO - VARIANTE'
                for n in range(4, ultima_voce(oSheet)+2):
                    formule.append(['=IF(Q' + str(n) + '-M' + str(n) + '=0;"--";Q' + str(n) + '-M' + str(n) + ')',
                                    '=IF(R' + str(n) + '-N' + str(n) + '>0;R' + str(n) + '-N' + str(n) + ';"")',
                                    '=IF(R' + str(n) + '-N' + str(n) + '<0;N' + str(n) + '-R' + str(n) + ';"")',
    '=IFERROR(IFS(AND(N' + str(n) + '>R' + str(n) + ';R' + str(n) + '=0);-1;AND(N' + str(n) + '<R' + str(n) + ';N' + str(n) + '=0);1;N' + str(n) + '=R' + str(n) + ';"--";N' + str(n) + '>R' + str(n) + ';-(N' + str(n) + '-R' + str(n) + ')/N' + str(n) + ';N' + str(n) + '<R' + str(n) + ';-(N' + str(n) + '-R' + str(n) + ')/N' + str(n) + ');"--")'])
                n += 1
                oSheet.getCellByPosition(26, 1).Formula ='=IFERROR(IFS(AND(N2>R2;R2=0);-1;AND(N2<R2;N2=0);1;N2=R2;"--";N2>R2;-(N2-R2)/N2;N2<R2;-(N2-R2)/N2);"--")'
                oSheet.getCellByPosition(26, ER).Formula = '=IFERROR(IFS(AND(N' + str(n) + '>R' + str(n) + ';R' + str(n) + '=0);-1;AND(N' + str(n) + '<R' + str(n) + ';N' + str(n) + '=0);1;N' + str(n) + '=R' + str(n) + ';"--";N' + str(n) + '>R' + str(n) + ';-(N' + str(n) + '-R' + str(n) + ')/N' + str(n) + ';N' + str(n) + '<R' + str(n) + ';-(N' + str(n) + '-R' + str(n) + ')/N' + str(n) + ');"--")'
                oRange = oSheet.getCellRangeByPosition(23, 3, 26, ultima_voce(oSheet))
                formule = tuple(formule)
                oRange.setFormulaArray(formule)
                ###
                if oRangeAddress.StartColumn != 0:
                    oCellRangeAddr.StartColumn = 18
                    oCellRangeAddr.EndColumn = 21
                    oSheet.group(oCellRangeAddr, 0)
                    oSheet.getCellRangeByPosition(18, 0, 21, 0).Columns.IsVisible = False
                    
                    oCellRangeAddr.StartColumn = 15
                    oCellRangeAddr.EndColumn = 15
                    oSheet.group(oCellRangeAddr, 0)
                    oSheet.getCellRangeByPosition(15, 0, 15, 0).Columns.IsVisible = False
                ###

            if oDialog1.getControl("ComCon").State == True: #Computo - Contabilità
                genera_sommario()
                oRangeAddress.StartColumn = 15
                oRangeAddress.EndColumn = 18

                oSheet.getCellByPosition(23, 0).String = 'COMPUTO - CONTABILITÀ'
                for n in range(4, ultima_voce(oSheet)+2):
                    formule.append(['=IF(U' + str(n) + '-M' + str(n) + '=0;"--";U' + str(n) + '-M' + str(n) + ')',
                                    '=IF(V' + str(n) + '-N' + str(n) + '>0;V' + str(n) + '-N' + str(n) + ';"")',
                                    '=IF(V' + str(n) + '-N' + str(n) + '<0;N' + str(n) + '-V' + str(n) + ';"")',
    '=IFERROR(IFS(AND(N' + str(n) + '>V' + str(n) + ';V' + str(n) + '=0);-1;AND(N' + str(n) + '<V' + str(n) + ';N' + str(n) + '=0);1;N' + str(n) + '=V' + str(n) + ';"--";N' + str(n) + '>V' + str(n) + ';-(N' + str(n) + '-V' + str(n) + ')/N' + str(n) + ';N' + str(n) + '<V' + str(n) + ';-(N' + str(n) + '-V' + str(n) + ')/N' + str(n) + ');"--")'])
                n += 1
                #~ for el in(1, ER+1):
                oSheet.getCellByPosition(26, 1).Formula ='=IFERROR(IFS(AND(N2>V2;V2=0);-1;AND(N2<V2;N2=0);1;N2=V2;"--";N2>V2;-(N2-V2)/N2;N2<V2;-(N2-V2)/N2);"--")'
                oSheet.getCellByPosition(26, ER).Formula = '=IFERROR(IFS(AND(N' + str(n) + '>V' + str(n) + ';V' + str(n) + '=0);-1;AND(N' + str(n) + '<V' + str(n) + ';N' + str(n) + '=0);1;N' + str(n) + '=V' + str(n) + ';"--";N' + str(n) + '>V' + str(n) + ';-(N' + str(n) + '-V' + str(n) + ')/N' + str(n) + ';N' + str(n) + '<V' + str(n) + ';-(N' + str(n) + '-V' + str(n) + ')/N' + str(n) + ');"--")'
                oRange = oSheet.getCellRangeByPosition(23, 3, 26, ultima_voce(oSheet))
                formule = tuple(formule)
                oRange.setFormulaArray(formule)
                ###
                if oRangeAddress.StartColumn != 0:
                # evidenzia le quantità eccedenti il VI/I
                    for el in range (3, getLastUsedCell(oSheet).EndRow):
                        if oSheet.getCellByPosition(26, el).Value >= 0.2 or oSheet.getCellByPosition(26, el).String == '20,00%':
                            oSheet.getCellRangeByPosition(0, el, 25, el).CellBackColor = 16777062
                    #~ oCellRangeAddr=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
                    if DlgSiNo("Nascondo eventuali voci non ancora contabilizzate?") == 2:
                        struttura_off()
                        for el in range(3, getLastUsedCell(oSheet).EndRow):
                            if oSheet.getCellByPosition(20, el).Value == 0:
                                oCellRangeAddr.StartRow = el
                                oCellRangeAddr.EndRow = el
                                oSheet.group(oCellRangeAddr, 1)
                                oSheet.getCellRangeByPosition(0, el, 1, el).Rows.IsVisible = False

                    oCellRangeAddr.StartColumn = 5
                    oCellRangeAddr.EndColumn = 11
                    oSheet.group(oCellRangeAddr, 0)
                    oSheet.getCellRangeByPosition(5, 0, 11, 0).Columns.IsVisible = False
                    oCellRangeAddr.StartColumn = 15
                    oCellRangeAddr.EndColumn = 19
                    oSheet.group(oCellRangeAddr, 0)
                    oSheet.getCellRangeByPosition(15, 0, 19, 0).Columns.IsVisible = False
                ###

            if oDialog1.getControl("VarCon").State == True: #Variante - Contabilità
                genera_sommario()

                oRangeAddress.StartColumn = 11
                oRangeAddress.EndColumn = 14
                
                oSheet.getCellByPosition(23, 0).String = 'VARIANTE - CONTABILITÀ'
                for n in range(4, ultima_voce(oSheet)+2):
                    formule.append(['=IF(U' + str(n) + '-Q' + str(n) + '=0;"--";U' + str(n) + '-Q' + str(n) + ')',
                                    '=IF(V' + str(n) + '-R' + str(n) + '>0;V' + str(n) + '-R' + str(n) + ';"")',
                                    '=IF(V' + str(n) + '-R' + str(n) + '<0;R' + str(n) + '-V' + str(n) + ';"")',
    '=IFERROR(IFS(AND(R' + str(n) + '>V' + str(n) + ';V' + str(n) + '=0);-1;AND(R' + str(n) + '<V' + str(n) + ';R' + str(n) + '=0);1;R' + str(n) + '=V' + str(n) + ';"--";R' + str(n) + '>V' + str(n) + ';-(R' + str(n) + '-V' + str(n) + ')/R' + str(n) + ';R' + str(n) + '<V' + str(n) + ';-(R' + str(n) + '-V' + str(n) + ')/R' + str(n) + ');"--")'])
                n += 1
                #~ for el in(1, ER+1):
                oSheet.getCellByPosition(26, 1).Formula ='=IFERROR(IFS(AND(R2>V2;V2=0);-1;AND(R2<V2;R2=0);1;R2=V2;"--";R2>V2;-(R2-V2)/R2;R2<V2;-(R2-V2)/R2);"--")'
                oSheet.getCellByPosition(26, ER).Formula = '=IFERROR(IFS(AND(R' + str(n) + '>V' + str(n) + ';V' + str(n) + '=0);-1;AND(R' + str(n) + '<V' + str(n) + ';R' + str(n) + '=0);1;R' + str(n) + '=V' + str(n) + ';"--";R' + str(n) + '>V' + str(n) + ';-(R' + str(n) + '-V' + str(n) + ')/R' + str(n) + ';R' + str(n) + '<V' + str(n) + ';-(R' + str(n) + '-V' + str(n) + ')/R' + str(n) + ');"--")'
                oRange = oSheet.getCellRangeByPosition(23, 3, 26, ultima_voce(oSheet))
                formule = tuple(formule)
                oRange.setFormulaArray(formule)
            # operazioni comuni
            for el in(11, 15, 19, 26):
                oSheet.getCellRangeByPosition(el, 3, el, ultima_voce(oSheet)).CellStyle = 'EP-mezzo %'
            for el in(12, 16, 20, 23):
                oSheet.getCellRangeByPosition(el, 3, el, ultima_voce(oSheet)).CellStyle = 'EP statistiche_q'
            for el in(13, 17, 21, 24, 25):
                oSheet.getCellRangeByPosition(el, 3, el, ultima_voce(oSheet)).CellStyle = 'EP statistiche'
            oCellRangeAddr.StartColumn = 3
            oCellRangeAddr.EndColumn = 3
            oSheet.group(oCellRangeAddr, 0)
            oSheet.getCellRangeByPosition(3, 0, 3, 0).Columns.IsVisible = False
            oCellRangeAddr.StartColumn = 5
            oCellRangeAddr.EndColumn = 11
            oSheet.group(oCellRangeAddr, 0)
            oSheet.getCellRangeByPosition(5, 0, 11, 0).Columns.IsVisible = False
            
            oDoc.CurrentController.select(oSheet.getCellRangeByName('AA2'))
            #~ oDoc.CurrentController.select(oDoc.getSheets().getByName('S5').getCellRangeByName('B30'))
            copy_clip()
            oDoc.CurrentController.select(oSheet.getCellRangeByPosition(26, 3, 26, ER))
            paste_format()
            
            if oDialog1.getControl("ComVar").State == True or \
            oDialog1.getControl("ComCon").State == True or \
            oDialog1.getControl("VarCon").State == True:
                if DlgSiNo("Nascondo eventuali righe con scostamento nullo?") == 2:
                    errori =('#DIV/0!', '--')
                    hide_error(errori, 26)
                    oSheet.group(oRangeAddress, 0)
                    oSheet.getCellRangeByPosition(oRangeAddress.StartColumn, 0, oRangeAddress.EndColumn, 1).Columns.IsVisible = False
            _primaCella()
        else:
            return
    elif oSheet.Name in('Analisi di Prezzo'):
        oDialog1 = dp.createDialog("vnd.sun.star.script:UltimusFree2.DialogViste_AN?language=Basic&location=application")
        oDialog1Model = oDialog1.Model
        if  oSheet.getCellByPosition(1, 2).Rows.OptimalHeight == False: oDialog1.getControl("CBDesc").State = 1 #descrizione breve

        oS1 = oDoc.getSheets().getByName('S1')
        sString = oDialog1.getControl('TextField5')
        sString.Text =oS1.getCellRangeByName('S1.H319').Value * 100 #sicurezza
        sString = oDialog1.getControl('TextField6')
        sString.Text =oS1.getCellRangeByName('S1.H320').Value * 100 #spese_generali
        sString = oDialog1.getControl('TextField7')
        sString.Text =oS1.getCellRangeByName('S1.H321').Value * 100 #utile_impresa
        
        #accorpa_spese_utili
        if oS1.getCellRangeByName('S1.H323').Value == 1: oDialog1.getControl('CheckBox4').State = 1
        sString = oDialog1.getControl('TextField8')
        sString.Text =oS1.getCellRangeByName('S1.H324').Value * 100 #sconto
        sString = oDialog1.getControl('TextField9')
        sString.Text =oS1.getCellRangeByName('S1.H326').Value * 100 #maggiorazione

        oDialog1.execute() #mostra il dialogo
        
        if  oSheet.getCellByPosition(1, 2).Rows.OptimalHeight == True and oDialog1.getControl("CBDesc").State == 1: #descrizione breve
            basic_LeenO('Strutture.Tronca_Altezza_Analisi')
        #~ elif oDialog1.getControl("CBDesc").State == 0: adatta_altezza_riga(oSheet.Name)

        #~ sString.Text =oSheet.getCellRangeByName('S1.H321').Value * 100 #utile_impresa
        oS1.getCellRangeByName('S1.H319').Value = float(oDialog1.getControl('TextField5').getText().replace(',','.')) / 100  ##sicurezza
        oS1.getCellRangeByName('S1.H320').Value = float(oDialog1.getControl('TextField6').getText().replace(',','.')) / 100  #spese generali
        oS1.getCellRangeByName('S1.H321').Value = float(oDialog1.getControl('TextField7').getText().replace(',','.')) / 100  #utile_impresa
        oS1.getCellRangeByName('S1.H323').Value = oDialog1.getControl('CheckBox4').State
        oS1.getCellRangeByName('S1.H324').Value = float(oDialog1.getControl('TextField8').getText().replace(',','.')) / 100  #sconto
        oS1.getCellRangeByName('S1.H326').Value = float(oDialog1.getControl('TextField9').getText().replace(',','.')) / 100  #maggiorazione

        #accorpa_spese_utili
        if oS1.getCellRangeByName('S1.H323').Value == 1: oDialog1.getControl('CheckBox4').State = 1
        sString = oDialog1.getControl('TextField8')
        sString.Text =oS1.getCellRangeByName('S1.H324').Value * 100 #sconto
        sString = oDialog1.getControl('TextField9')
        sString.Text =oS1.getCellRangeByName('S1.H326').Value * 100 #maggiorazione
        
    elif oSheet.Name in('CONTABILITA', 'Registro', 'SAL'):
        oDialog1 = dp.createDialog("vnd.sun.star.script:UltimusFree2.Dialogviste_N?language=Basic&location=application")
        oDialog1Model = oDialog1.Model
        oDialog1.getControl('Dettaglio').State = conf.read(path_conf, 'Generale', 'dettaglio')
        oDialog1.execute()
        if oDialog1.getControl('Dettaglio').State == 0: #
            conf.write(path_conf, 'Generale', 'dettaglio', '0')
            dettaglio_misure(0)
        else:
            conf.write(path_conf, 'Generale', 'dettaglio', '1')
            dettaglio_misure(0)
            dettaglio_misure(1)
    #~ adatta_altezza_riga(oSheet.Name)
    refresh(1)
    #~ MsgBox('Operazione eseguita con successo!','')
########################################################################
def genera_variante(arg=None):
    '''Genera il foglio di VARIANTE a partire dal COMPUTO'''
    chiudi_dialoghi()
    oDoc = XSCRIPTCONTEXT.getDocument()
    if oDoc.getSheets().hasByName('VARIANTE') == False:
        if oDoc.NamedRanges.hasByName("AA") == True:
            oDoc.NamedRanges.removeByName("AA")
            oDoc.NamedRanges.removeByName("BB")
        oDoc.Sheets.copyByName('COMPUTO','VARIANTE', 4)
        oSheet = oDoc.getSheets().getByName('COMPUTO')
        lrow = getLastUsedCell(oSheet).EndRow
        rifa_nomearea('COMPUTO', '$AJ$3:$AJ$' + str(lrow), 'AA')
        rifa_nomearea('COMPUTO', '$N$3:$N$'  + str(lrow), "BB")
        rifa_nomearea('COMPUTO', '$AK$3:$AK$' + str(lrow), "cEuro")
        oSheet = oDoc.getSheets().getByName('VARIANTE')
        _gotoSheet('VARIANTE')
        setTabColor(16777062)
        oSheet.getCellByPosition(2,0).String  = "VARIANTE"
        oSheet.getCellByPosition(2,0).CellStyle = "comp Int_colonna"
        oSheet.getCellRangeByName("C1").CellBackColor = 16777062
        oSheet.getCellRangeByPosition(0,2,42,2).CellBackColor = 16777062
        if DlgSiNo("""Vuoi svuotare la VARIANTE appena generata?

Se decidi di continuare, cancellerai tutte le voci di
misurazione già presenti in questo elaborato.
Cancello le voci di misurazione?
 """,'ATTENZIONE!') ==2:
            lrow = uFindStringCol('TOTALI COMPUTO', 2, oSheet) -3
            oSheet.Rows.removeByIndex(3, lrow)
            _gotoCella(0,2)
            ins_voce_computo()
            adatta_altezza_riga('VARIANTE')
    else:
        _gotoSheet('VARIANTE')
########################################################################
def genera_sommario(arg=None):
    '''
    Genera i sommari in Elenco Prezzi
    '''
    #~ oDialogo_attesa = dlg_attesa()
    #~ attesa().start() #mostra il dialogo
    refresh(0)
    struttura_off()

    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.getSheets().getByName('COMPUTO')
    lrow = getLastUsedCell(oSheet).EndRow
    rifa_nomearea('COMPUTO', '$AJ$3:$AJ$' + str(lrow), 'AA')
    rifa_nomearea('COMPUTO', '$N$3:$N$'  + str(lrow), "BB")
    rifa_nomearea('COMPUTO', '$AK$3:$AK$' + str(lrow), "cEuro")

    if oDoc.getSheets().hasByName('VARIANTE') == True:
        oSheet = oDoc.getSheets().getByName('VARIANTE')
        lrow = getLastUsedCell(oSheet).EndRow
        rifa_nomearea('VARIANTE', '$AJ$3:$AJ$' + str(lrow), 'varAA')
        rifa_nomearea('VARIANTE', '$N$3:$N$'  + str(lrow), "varBB")
        rifa_nomearea('VARIANTE', '$AK$3:$AK$' + str(lrow), "varEuro")

    if oDoc.getSheets().hasByName('CONTABILITA') == True:
        oSheet = oDoc.getSheets().getByName('CONTABILITA')
        lrow = getLastUsedCell(oSheet).EndRow
        lrow = getLastUsedCell(oDoc.getSheets().getByName('CONTABILITA')).EndRow
        rifa_nomearea('CONTABILITA', '$AJ$3:$AJ$' + str(lrow), 'GG')
        rifa_nomearea('CONTABILITA', '$S$3:$S$'  + str(lrow), "G1G1")
        rifa_nomearea('CONTABILITA', '$AK$3:$AK$' + str(lrow), "conEuro")
        
    formule = list()
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    for n in range(4, ultima_voce(oSheet)+2):
        stringa =(['=N' + str(n) + '/$N$2',
                        '=SUMIF(AA;A' + str(n) + ';BB)',
                        '=SUMIF(AA;A' + str(n) + ';cEuro)',
                        '', '', '', '', '', '', '', ''])
        if oDoc.getSheets().hasByName('VARIANTE') == True:
            stringa =(['=N' + str(n) + '/$N$2',
                        '=SUMIF(AA;A' + str(n) + ';BB)',
                        '=SUMIF(AA;A' + str(n) + ';cEuro)',
                        '',
                        '=R' + str(n) + '/$R$2',
                        '=SUMIF(varAA;A' + str(n) + ';varBB)',
                        '=SUMIF(varAA;A' + str(n) + ';varEuro)',
                        '', '', '',
                        ''])
            if oDoc.getSheets().hasByName('CONTABILITA') == True:
                stringa =(['=N' + str(n) + '/$N$2',
                            '=SUMIF(AA;A' + str(n) + ';BB)',
                            '=SUMIF(AA;A' + str(n) + ';cEuro)',
                            '',
                            '=R' + str(n) + '/$R$2',
                            '=SUMIF(varAA;A' + str(n) + ';varBB)',
                            '=SUMIF(varAA;A' + str(n) + ';varEuro)',
                            '',
                            '=V' + str(n) + '/$V$2',
                            '=SUMIF(GG;A' + str(n) + ';G1G1)',
                            '=SUMIF(GG;A' + str(n) + ';conEuro)'])
        elif oDoc.getSheets().hasByName('CONTABILITA') == True:
            stringa =(['=N' + str(n) + '/$N$2',
                        '=SUMIF(AA;A' + str(n) + ';BB)',
                        '=SUMIF(AA;A' + str(n) + ';cEuro)',
                        '',
                        '', '', '',
                        '',
                        '=V' + str(n) + '/$V$2',
                        '=SUMIF(GG;A' + str(n) + ';G1G1)',
                        '=SUMIF(GG;A' + str(n) + ';conEuro)'])
        formule.append(stringa)
    oRange = oSheet.getCellRangeByPosition(11, 3, 21, ultima_voce(oSheet))
    formule = tuple(formule)
    oRange.setFormulaArray(formule)
    refresh(1)
    adatta_altezza_riga(oSheet.Name)
    #~ oDialogo_attesa.endExecute() #chiude il dialogo
########################################################################
def riordina_ElencoPrezzi(arg=None):
    '''Riordina l'Elenco Prezzi secondo l'ordine alfabetico dei codici di prezzo'''
    chiudi_dialoghi()
    refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    zoom = oDoc.CurrentController.ZoomValue
    oDoc.CurrentController.ZoomValue = 400
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    if uFindStringCol('Fine elenco', 0, oSheet) == None:
        inserisci_Riga_rossa()
    test = str(uFindStringCol('Fine elenco', 0, oSheet))
    rifa_nomearea('Elenco Prezzi', "$A$3:$AF$" + test, 'elenco_prezzi')
    rifa_nomearea('Elenco Prezzi', "$A$3:$A$" + test, 'Lista')
    oRangeAddress=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
    SC = oRangeAddress.StartColumn
    EC = oRangeAddress.EndColumn
    SR = oRangeAddress.StartRow+1
    ER = oRangeAddress.EndRow
    if SR == ER: return
    oRange = oSheet.getCellRangeByPosition(SC, SR, EC, ER)
    oDoc.CurrentController.select(oRange)
    ordina_col(1)
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    refresh(1)
    oDoc.CurrentController.ZoomValue = zoom
########################################################################
def doppioni(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    '''
    Cancella eventuali voci che si ripetono in Elenco Prezzi
    '''
    zoom = oDoc.CurrentController.ZoomValue
    refresh(0)
    if oDoc.getSheets().hasByName('Analisi di Prezzo') == True:
        lista_tariffe_analisi = list()
        oSheet = oDoc.getSheets().getByName('Analisi di Prezzo')
        for n in range(0, ultima_voce(oSheet)+1):
            if oSheet.getCellByPosition(0, n).CellStyle == 'An-1_sigla':
                lista_tariffe_analisi.append(oSheet.getCellByPosition(0, n).String)
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')

    SR = 0
    ER = getLastUsedCell(oSheet).EndRow

    try:
        lista_tariffe_analisi
        for i in reversed(range(SR, ER)):
            if oSheet.getCellByPosition(0, i).String in lista_tariffe_analisi:
                oSheet.getRows().removeByIndex(i, 1)
    except:
        pass
    oRangeAddress=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
    SR = oRangeAddress.StartRow+1
    ER = oRangeAddress.EndRow-1
    oRange = oSheet.getCellRangeByPosition(0, SR, 7, ER)
    lista_come_array = tuple(set(oRange.getDataArray()))
    # ~chi ([len(lista_come_array),(lista_come_array)])
    # ~return
    oSheet.getRows().removeByIndex(SR, ER-SR+1)
    lista_tar = list()
    oSheet.getRows().insertByIndex(SR, len(set(lista_come_array)))
    for el in set(lista_come_array):
        lista_tar.append(el[0])
    colonne_lista = len(lista_come_array[0]) # numero di colonne necessarie per ospitare i dati
    righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati
    oRange = oSheet.getCellRangeByPosition( 0,
                                            3,
                                            colonne_lista + 0 - 1, # l'indice parte da 0
                                            righe_lista + 3 - 1)
    oRange.setDataArray(lista_come_array)
    oSheet.getCellRangeByPosition(0, 3, 0, righe_lista + 3 - 1).CellStyle = "EP-aS"
    oSheet.getCellRangeByPosition(1, 3, 1, righe_lista + 3 - 1).CellStyle = "EP-a"
    oSheet.getCellRangeByPosition(2, 3, 7, righe_lista + 3 - 1).CellStyle = "EP-mezzo"
    oSheet.getCellRangeByPosition(5, 3, 5, righe_lista + 3 - 1).CellStyle = "EP-mezzo %"
    oSheet.getCellRangeByPosition(8, 3, 9, righe_lista + 3 - 1).CellStyle = "EP-sfondo"

    oSheet.getCellRangeByPosition(11, 3, 11, righe_lista + 3 - 1).CellStyle = 'EP-mezzo %'
    oSheet.getCellRangeByPosition(12, 3, 12, righe_lista + 3 - 1).CellStyle = 'EP statistiche_q'
    oSheet.getCellRangeByPosition(13, 3, 13, righe_lista + 3 - 1).CellStyle = 'EP statistiche_Contab_q'
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    if oDoc.getSheets().hasByName('Analisi di Prezzo') == True:
        tante_analisi_in_ep()
    refresh(1)
    oDoc.CurrentController.ZoomValue = zoom
    adatta_altezza_riga(oSheet.Name)
    riordina_ElencoPrezzi()
    if len(set(lista_tar)) != len(set(lista_come_array)):
        MsgBox('Ci sono ancora 2 o più voci che hanno lo stesso Codice Articolo pur essendo diverse.', 'C o n t r o l l a!')
########################################################################
# Scrive un file.
def XPWE_out(elaborato, out_file):
    '''
    esporta il documento in formato XPWE

    elaborato { string } : nome del foglio da esportare
    out_file  { string } : nome base del file

    il nome file risulterà out_file-elaborato.xpwe
    '''
    refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    oDialogo_attesa = dlg_attesa('Esportazione di ' + elaborato + ' in corso...')
    attesa().start() #mostra il dialogo
    if conf.read(path_conf, 'Generale', 'dettaglio') == '1':
        dettaglio_misure(0)
    numera_voci(1)
    top = Element('PweDocumento')
#~ intestazioni
    CopyRight = SubElement(top,'CopyRight')
    CopyRight.text = 'Copyright ACCA software S.p.A.'
    TipoDocumento = SubElement(top,'TipoDocumento')
    TipoDocumento.text = '1'
    TipoFormato = SubElement(top,'TipoFormato')
    TipoFormato.text = 'XMLPwe'
    Versione = SubElement(top,'Versione')
    Versione.text = ''
    SourceVersione = SubElement(top,'SourceVersione')
    release = str(Lmajor) +'.'+ str(Lminor) +'.'+ Lsubv
    SourceVersione.text = release
    SourceNome = SubElement(top,'SourceNome')
    SourceNome.text = 'LeenO.org'
    FileNameDocumento = SubElement(top,'FileNameDocumento')
#~ dati generali
    PweDatiGenerali = SubElement(top,'PweDatiGenerali')
    PweMisurazioni = SubElement(top,'PweMisurazioni')
    PweDGProgetto = SubElement(PweDatiGenerali,'PweDGProgetto')
    PweDGDatiGenerali = SubElement(PweDGProgetto,'PweDGDatiGenerali')
    PercPrezzi = SubElement(PweDGDatiGenerali,'PercPrezzi')
    PercPrezzi.text = '0'

    Comune = SubElement(PweDGDatiGenerali,'Comune')
    Provincia = SubElement(PweDGDatiGenerali,'Provincia')
    Oggetto = SubElement(PweDGDatiGenerali,'Oggetto')
    Committente = SubElement(PweDGDatiGenerali,'Committente')
    Impresa = SubElement(PweDGDatiGenerali,'Impresa')
    ParteOpera = SubElement(PweDGDatiGenerali,'ParteOpera')
#~  leggo i dati generali
    oSheet = oDoc.getSheets().getByName('S2')
    Comune.text = oSheet.getCellByPosition(2, 3).String
    Provincia.text = ''
    Oggetto.text = oSheet.getCellByPosition(2, 2).String
    Committente.text = oSheet.getCellByPosition(2, 5).String
    Impresa.text = oSheet.getCellByPosition(2, 16).String
    ParteOpera.text = ''
#~ Capitoli e Categorie
    PweDGCapitoliCategorie = SubElement(PweDatiGenerali,'PweDGCapitoliCategorie')
#~ SuperCategorie
    oSheet = oDoc.getSheets().getByName(elaborato)
    lastRow = ultima_voce(oSheet)+1
    # evito di esportare in SuperCategorie perché inutile, almeno per ora
    listaspcat = list()
    PweDGSuperCategorie = SubElement(PweDGCapitoliCategorie,'PweDGSuperCategorie')
    for n in range(0, lastRow):
        if oSheet.getCellByPosition(1, n).CellStyle == 'Livello-0-scritta':
            desc = oSheet.getCellByPosition(2, n).String
            if desc not in listaspcat:
                listaspcat.append(desc)
                idID = str(listaspcat.index(desc) +1)

            #~ PweDGSuperCategorie = SubElement(PweDGCapitoliCategorie,'PweDGSuperCategorie')
                DGSuperCategorieItem = SubElement(PweDGSuperCategorie,'DGSuperCategorieItem')
                DesSintetica = SubElement(DGSuperCategorieItem,'DesSintetica')
            
                DesEstesa = SubElement(DGSuperCategorieItem,'DesEstesa')
                DataInit = SubElement(DGSuperCategorieItem,'DataInit')
                Durata = SubElement(DGSuperCategorieItem,'Durata')
                CodFase = SubElement(DGSuperCategorieItem,'CodFase')
                Percentuale = SubElement(DGSuperCategorieItem,'Percentuale')
                Codice = SubElement(DGSuperCategorieItem,'Codice')

                DGSuperCategorieItem.set('ID', idID)
                DesSintetica.text = desc
                DataInit.text = oggi()
                Durata.text = '0'
                Percentuale.text = '0'

#~ Categorie
    listaCat = list()
    PweDGCategorie = SubElement(PweDGCapitoliCategorie,'PweDGCategorie')
    for n in range(0,lastRow):
        if oSheet.getCellByPosition(2, n).CellStyle == 'Livello-1-scritta mini':
            desc = oSheet.getCellByPosition(2, n).String
            if desc not in listaCat:
                listaCat.append(desc)
                idID = str(listaCat.index(desc) +1)

                #~ PweDGCategorie = SubElement(PweDGCapitoliCategorie,'PweDGCategorie')
                DGCategorieItem = SubElement(PweDGCategorie,'DGCategorieItem')
                DesSintetica = SubElement(DGCategorieItem,'DesSintetica')
                
                DesEstesa = SubElement(DGCategorieItem,'DesEstesa')
                DataInit = SubElement(DGCategorieItem,'DataInit')
                Durata = SubElement(DGCategorieItem,'Durata')
                CodFase = SubElement(DGCategorieItem,'CodFase')
                Percentuale = SubElement(DGCategorieItem,'Percentuale')
                Codice = SubElement(DGCategorieItem,'Codice')

                DGCategorieItem.set('ID', idID)
                DesSintetica.text = desc
                DataInit.text = oggi()
                Durata.text = '0'
                Percentuale.text = '0'

#~ SubCategorie
    listasbCat = list()
    PweDGSubCategorie = SubElement(PweDGCapitoliCategorie,'PweDGSubCategorie')
    for n in range(0,lastRow):
        if oSheet.getCellByPosition(2, n).CellStyle == 'livello2_':
            desc = oSheet.getCellByPosition(2, n).String
            if desc not in listasbCat:
                listasbCat.append(desc)
                idID = str(listasbCat.index(desc) +1)

                #~ PweDGSubCategorie = SubElement(PweDGCapitoliCategorie,'PweDGSubCategorie')
                DGSubCategorieItem = SubElement(PweDGSubCategorie,'DGSubCategorieItem')
                DesSintetica = SubElement(DGSubCategorieItem,'DesSintetica')

                DesEstesa = SubElement(DGSubCategorieItem,'DesEstesa')
                DataInit = SubElement(DGSubCategorieItem,'DataInit')
                Durata = SubElement(DGSubCategorieItem,'Durata')
                CodFase = SubElement(DGSubCategorieItem,'CodFase')
                Percentuale = SubElement(DGSubCategorieItem,'Percentuale')
                Codice = SubElement(DGSubCategorieItem,'Codice')

                DGSubCategorieItem.set('ID', idID)
                DesSintetica.text = desc
                DataInit.text = oggi()
                Durata.text = '0'
                Percentuale.text = '0'

#~ Moduli
    PweDGModuli = SubElement(PweDatiGenerali,'PweDGModuli')
    PweDGAnalisi = SubElement(PweDGModuli,'PweDGAnalisi')
    SpeseUtili = SubElement(PweDGAnalisi,'SpeseUtili')
    SpeseGenerali = SubElement(PweDGAnalisi,'SpeseGenerali')
    UtiliImpresa = SubElement(PweDGAnalisi,'UtiliImpresa')
    OneriAccessoriSc = SubElement(PweDGAnalisi,'OneriAccessoriSc')
    ConfQuantita = SubElement(PweDGAnalisi,'ConfQuantita')

    oSheet = oDoc.getSheets().getByName('S1')
    if oSheet.getCellByPosition(7,322).Value ==0: # se 0: Spese e Utili Accorpati
        SpeseUtili.text = '1'
    else:
        SpeseUtili.text = '-1'
        
    UtiliImpresa.text = oSheet.getCellByPosition(7,320).String[:-1].replace(',','.')
    OneriAccessoriSc.text = oSheet.getCellByPosition(7,318).String[:-1].replace(',','.')
    SpeseGenerali.text = oSheet.getCellByPosition(7,319).String[:-1].replace(',','.')

#~ Configurazioni
    PU  = str(len(getFormatString('comp 1-a PU').split(',')[-1]))
    LUN = str(len(getFormatString('comp 1-a LUNG').split(',')[-1]))
    LAR = str(len(getFormatString('comp 1-a LARG').split(',')[-1]))
    PES = str(len(getFormatString('comp 1-a peso').split(',')[-1]))
    QUA = str(len(getFormatString('Blu').split(',')[-1]))
    PR = str(len(getFormatString('comp sotto Unitario').split(',')[-1]))
    TOT = str(len(getFormatString('An-1v-dx').split(',')[-1]))
    PweDGConfigurazione = SubElement(PweDatiGenerali,'PweDGConfigurazione')
    PweDGConfigNumeri = SubElement(PweDGConfigurazione,'PweDGConfigNumeri')
    Divisa = SubElement(PweDGConfigNumeri,'Divisa')
    Divisa.text = 'euro'
    ConversioniIN = SubElement(PweDGConfigNumeri,'ConversioniIN')
    ConversioniIN.text = 'lire'
    FattoreConversione = SubElement(PweDGConfigNumeri,'FattoreConversione')
    FattoreConversione.text = '1936.27'
    Cambio = SubElement(PweDGConfigNumeri,'Cambio')
    Cambio.text = '1'
    PartiUguali = SubElement(PweDGConfigNumeri,'PartiUguali')
    PartiUguali.text = '9.' + PU + '|0'
    Lunghezza = SubElement(PweDGConfigNumeri,'Lunghezza')
    Lunghezza.text = '9.'+ LUN + '|0'
    Larghezza = SubElement(PweDGConfigNumeri,'Larghezza')
    Larghezza.text = '9.'+ LAR + '|0'
    HPeso = SubElement(PweDGConfigNumeri,'HPeso')
    HPeso.text = '9.' + PES + '|0'
    Quantita = SubElement(PweDGConfigNumeri,'Quantita')
    Quantita.text = '10.'+ QUA + '|1'
    Prezzi = SubElement(PweDGConfigNumeri,'Prezzi')
    Prezzi.text = '10.' + PR + '|1'
    PrezziTotale = SubElement(PweDGConfigNumeri,'PrezziTotale')
    PrezziTotale.text = '14.'+ TOT +'|1'
    ConvPrezzi = SubElement(PweDGConfigNumeri,'ConvPrezzi')
    ConvPrezzi.text = '11.0|1'
    ConvPrezziTotale = SubElement(PweDGConfigNumeri,'ConvPrezziTotale')
    ConvPrezziTotale.text = '15.0|1'
    IncidenzaPercentuale = SubElement(PweDGConfigNumeri,'IncidenzaPercentuale')
    IncidenzaPercentuale.text = '7.3|0'
    Aliquote = SubElement(PweDGConfigNumeri,'Aliquote')
    Aliquote.text = '7.3|0'

#~ Elenco Prezzi
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    PweElencoPrezzi = SubElement(PweMisurazioni,'PweElencoPrezzi')
    diz_ep = dict()
    lista_AP = list()
    for n in range(3, getLastUsedCell(oSheet).EndRow):
        if oSheet.getCellByPosition(1, n).Type.value == 'FORMULA' and \
        oSheet.getCellByPosition(2, n).Type.value == 'FORMULA':
            lista_AP.append(oSheet.getCellByPosition(0, n).String)
        elif oSheet.getCellByPosition(1, n).Type.value == 'TEXT' and \
        oSheet.getCellByPosition(2, n).Type.value == 'TEXT':
            EPItem = SubElement(PweElencoPrezzi,'EPItem')
            EPItem.set('ID', str(n))
            TipoEP = SubElement(EPItem,'TipoEP')
            TipoEP.text = '0'
            Tariffa = SubElement(EPItem,'Tariffa')
            id_tar = str(n)
            Tariffa.text = oSheet.getCellByPosition(0, n).String
            diz_ep[oSheet.getCellByPosition(0, n).String] = id_tar
            Articolo = SubElement(EPItem,'Articolo')
            Articolo.text = ''
            DesEstesa = SubElement(EPItem,'DesEstesa')
            DesEstesa.text = oSheet.getCellByPosition(1, n).String
            DesRidotta = SubElement(EPItem,'DesRidotta')
            if len(DesEstesa.text) > 120:
                DesRidotta.text = DesEstesa.text[:60] + ' ... ' + DesEstesa.text[-60:]
            else:
                DesRidotta.text = DesEstesa.text
            DesBreve = SubElement(EPItem,'DesBreve')
            if len(DesEstesa.text) > 60:
                DesBreve.text = DesEstesa.text[:30] + ' ... ' + DesEstesa.text[-30:]
            else:
                DesBreve.text = DesEstesa.text
            UnMisura = SubElement(EPItem,'UnMisura')
            UnMisura.text = oSheet.getCellByPosition(2, n).String
            Prezzo1 = SubElement(EPItem,'Prezzo1')
            Prezzo1.text = str(oSheet.getCellByPosition(4, n).Value)
            Prezzo2 = SubElement(EPItem,'Prezzo2')
            Prezzo2.text = '0'
            Prezzo3 = SubElement(EPItem,'Prezzo3')
            Prezzo3.text = '0'
            Prezzo4 = SubElement(EPItem,'Prezzo4')
            Prezzo4.text = '0'
            Prezzo5 = SubElement(EPItem,'Prezzo5')
            Prezzo5.text = '0'
            IDSpCap = SubElement(EPItem,'IDSpCap')
            IDSpCap.text = '0'
            IDCap = SubElement(EPItem,'IDCap')
            IDCap.text = '0'
            IDSbCap = SubElement(EPItem,'IDSbCap')
            IDSbCap.text = '0'
            Flags = SubElement(EPItem,'Flags')
            if oSheet.getCellByPosition(8, n).String  == '(AP)':
                Flags.text = '131072'
            else:
                Flags.text = '0'
            Data = SubElement(EPItem,'Data')
            Data.text = '30/12/1899'
            AdrInternet = SubElement(EPItem,'AdrInternet')
            AdrInternet.text = ''
            PweEPAnalisi = SubElement(EPItem,'PweEPAnalisi')
            
            IncSIC = SubElement(EPItem,'IncSIC')
            if oSheet.getCellByPosition(3, n).Value == 0.0:
                IncSIC.text = ''
            else:
                IncSIC.text = str(oSheet.getCellByPosition(3, n).Value * 100)
                
            IncMDO = SubElement(EPItem,'IncMDO')
            if oSheet.getCellByPosition(5, n).Value == 0.0:
                IncMDO.text = ''
            else:
                IncMDO.text = str(oSheet.getCellByPosition(5, n).Value * 100)
                
            IncMAT = SubElement(EPItem,'IncMAT')
            if oSheet.getCellByPosition(6, n).Value == 0.0:
                IncMAT.text = ''
            else:
                IncMAT.text = str(oSheet.getCellByPosition(6, n).Value * 100)
            
            IncATTR = SubElement(EPItem,'IncATTR')
            if oSheet.getCellByPosition(7, n).Value == 0.0:
                IncATTR.text = ''
            else:
                IncATTR.text = str(oSheet.getCellByPosition(7, n).Value * 100)

#Analisi di prezzo
    if len(lista_AP) != 0:
        oSheet = oDoc.getSheets().getByName('Analisi di Prezzo')
        k = n+1
        for el in lista_AP:
            try:
                m = uFindStringCol(el, 0, oSheet)
                EPItem = SubElement(PweElencoPrezzi,'EPItem')
                EPItem.set('ID', str(k))
                TipoEP = SubElement(EPItem,'TipoEP')
                TipoEP.text = '0'
                Tariffa = SubElement(EPItem,'Tariffa')
                id_tar = str(k)
                Tariffa.text = oSheet.getCellByPosition(0, m).String
                diz_ep[oSheet.getCellByPosition(0, m).String] = id_tar
                Articolo = SubElement(EPItem,'Articolo')
                Articolo.text = ''
                DesEstesa = SubElement(EPItem,'DesEstesa')
                DesEstesa.text = oSheet.getCellByPosition(1, m).String
                DesRidotta = SubElement(EPItem,'DesRidotta')
                if len(DesEstesa.text) > 120:
                    DesRidotta.text = DesEstesa.text[:60] + ' ... ' + DesEstesa.text[-60:]
                else:
                    DesRidotta.text = DesEstesa.text
                DesBreve = SubElement(EPItem,'DesBreve')
                if len(DesEstesa.text) > 60:
                    DesBreve.text = DesEstesa.text[:30] + ' ... ' + DesEstesa.text[-30:]
                else:
                    DesBreve.text = DesEstesa.text
                UnMisura = SubElement(EPItem,'UnMisura')
                UnMisura.text = oSheet.getCellByPosition(2, m).String
                Prezzo1 = SubElement(EPItem,'Prezzo1')
                Prezzo1.text = str(oSheet.getCellByPosition(6, m).Value)
                Prezzo2 = SubElement(EPItem,'Prezzo2')
                Prezzo2.text = '0'
                Prezzo3 = SubElement(EPItem,'Prezzo3')
                Prezzo3.text = '0'
                Prezzo4 = SubElement(EPItem,'Prezzo4')
                Prezzo4.text = '0'
                Prezzo5 = SubElement(EPItem,'Prezzo5')
                Prezzo5.text = '0'
                IDSpCap = SubElement(EPItem,'IDSpCap')
                IDSpCap.text = '0'
                IDCap = SubElement(EPItem,'IDCap')
                IDCap.text = '0'
                IDSbCap = SubElement(EPItem,'IDSbCap')
                IDSbCap.text = '0'
                Flags = SubElement(EPItem,'Flags')
                Flags.text = '131072'
                Data = SubElement(EPItem,'Data')
                Data.text = '30/12/1899'
                AdrInternet = SubElement(EPItem,'AdrInternet')
                AdrInternet.text = ''
                PweEPAnalisi = SubElement(EPItem,'PweEPAnalisi')
                PweEPAR = SubElement(PweEPAnalisi,'PweEPAR')
                nEPARItem = 2
                for x in range(m, m+100):
                    if oSheet.getCellByPosition(0, x).CellStyle == 'An-lavoraz-desc':
                        EPARItem = SubElement(PweEPAR,'EPARItem')
                        EPARItem.set('ID', str(nEPARItem))
                        nEPARItem += 1
                        Tipo = SubElement(EPARItem,'Tipo')
                        Tipo.text = '0'
                        IDEP = SubElement(EPARItem,'IDEP')
                        IDEP.text = diz_ep.get(oSheet.getCellByPosition(0, x).String)
                        if IDEP.text == None:
                            IDEP.text ='-2'
                        Descrizione = SubElement(EPARItem,'Descrizione')
                        if '=IF(' in oSheet.getCellByPosition(1, x).String:
                            Descrizione.text = ''
                        else:
                            Descrizione.text = oSheet.getCellByPosition(1, x).String
                        Misura = SubElement(EPARItem,'Misura')
                        Misura.text = ''
                        Qt = SubElement(EPARItem,'Qt')
                        Qt.text = ''
                        Prezzo = SubElement(EPARItem,'Prezzo')
                        Prezzo.text = ''
                        FieldCTL = SubElement(EPARItem,'FieldCTL')
                        FieldCTL.text = '0'
                    if oSheet.getCellByPosition(0, x).CellStyle == 'An-lavoraz-Cod-sx' and \
                    oSheet.getCellByPosition(1, x).String != '':
                        EPARItem = SubElement(PweEPAR,'EPARItem')
                        EPARItem.set('ID', str(nEPARItem))
                        nEPARItem += 1
                        Tipo = SubElement(EPARItem,'Tipo')
                        Tipo.text = '1'
                        IDEP = SubElement(EPARItem,'IDEP')
                        IDEP.text = diz_ep.get(oSheet.getCellByPosition(0, x).String)
                        if IDEP.text == None:
                            IDEP.text ='-2'
                        Descrizione = SubElement(EPARItem,'Descrizione')
                        if '=IF(' in oSheet.getCellByPosition(1, x).String:
                            Descrizione.text = ''
                        else:
                            Descrizione.text = oSheet.getCellByPosition(1, x).String
                        Misura = SubElement(EPARItem,'Misura')
                        Misura.text = oSheet.getCellByPosition(2, x).String
                        Qt = SubElement(EPARItem,'Qt')
                        Qt.text = oSheet.getCellByPosition(3, x).String.replace(',','.')
                        Prezzo = SubElement(EPARItem,'Prezzo')
                        Prezzo.text = str(oSheet.getCellByPosition(4, x).Value).replace(',','.')
                        FieldCTL = SubElement(EPARItem,'FieldCTL')
                        FieldCTL.text = '0'
                    elif oSheet.getCellByPosition(0, x).CellStyle == 'An-sfondo-basso Att End':
                        break

                IncSIC = SubElement(EPItem,'IncSIC')
                if oSheet.getCellByPosition(10, n).Value == 0.0:
                    IncSIC.text = ''
                else:
                    IncSIC.text = str(oSheet.getCellByPosition(10, n).Value)
                    
                IncMDO = SubElement(EPItem,'IncMDO')
                if oSheet.getCellByPosition(8, n).Value == 0.0:
                    IncMDO.text = ''
                else:
                    IncMDO.text = str(oSheet.getCellByPosition(5, n).Value * 100)
                k += 1
            except:
                pass

#COMPUTO/VARIANTE/CONTABILITA
    oSheet = oDoc.getSheets().getByName(elaborato)
    PweVociComputo = SubElement(PweMisurazioni,'PweVociComputo')
    oDoc.CurrentController.setActiveSheet(oSheet)
    nVCItem = 2
    for n in range(0, ultima_voce(oSheet)):
        if oSheet.getCellByPosition(0, n).CellStyle in ('Comp Start Attributo', 'Comp Start Attributo_R'):
            sStRange = Circoscrive_Voce_Computo_Att(n)
            sStRange.RangeAddress
            sopra = sStRange.RangeAddress.StartRow
            sotto = sStRange.RangeAddress.EndRow
            if elaborato == 'CONTABILITA': sotto -=1
            VCItem = SubElement(PweVociComputo,'VCItem')
            VCItem.set('ID', str(nVCItem))
            nVCItem += 1

            IDEP = SubElement(VCItem,'IDEP')
            IDEP.text = diz_ep.get(oSheet.getCellByPosition(1, sopra+1).String)
##########################
            Quantita = SubElement(VCItem,'Quantita')
            Quantita.text = oSheet.getCellByPosition(9, sotto).String
##########################
            DataMis = SubElement(VCItem,'DataMis')
            if elaborato == 'CONTABILITA':
                DataMis.text = oSheet.getCellByPosition(1, sopra+2).String
            else:
                DataMis.text = oggi() #'26/12/1952'#'28/09/2013'###
            vFlags = SubElement(VCItem,'Flags')
            vFlags.text = '0'
##########################
            IDSpCat = SubElement(VCItem,'IDSpCat')
            IDSpCat.text = str(oSheet.getCellByPosition(31, sotto).String)
            if IDSpCat.text == '':
                IDSpCat.text = '0'
##########################
            IDCat = SubElement(VCItem,'IDCat')
            IDCat.text = str(oSheet.getCellByPosition(32, sotto).String)
            if IDCat.text == '':
                IDCat.text = '0'
##########################
            IDSbCat = SubElement(VCItem,'IDSbCat')
            IDSbCat.text = str(oSheet.getCellByPosition(33, sotto).String)
            if IDSbCat.text == '':
                IDSbCat.text = '0'
##########################
            PweVCMisure = SubElement(VCItem,'PweVCMisure')
            for m in range(sopra+2, sotto):
                RGItem = SubElement(PweVCMisure,'RGItem')
                x = 2
                RGItem.set('ID', str(x))
                x += 1
##########################
                IDVV = SubElement(RGItem,'IDVV')
                IDVV.text = '-2'
##########################
                Descrizione = SubElement(RGItem,'Descrizione')
                Descrizione.text = oSheet.getCellByPosition(2, m).String
##########################
                PartiUguali = SubElement(RGItem,'PartiUguali')
                PartiUguali.text = valuta_cella(oSheet.getCellByPosition(5, m))
##########################
                Lunghezza = SubElement(RGItem,'Lunghezza')
                Lunghezza.text = valuta_cella(oSheet.getCellByPosition(6, m))
##########################
                Larghezza = SubElement(RGItem,'Larghezza')
                Larghezza.text = valuta_cella(oSheet.getCellByPosition(7, m))
##########################
                HPeso = SubElement(RGItem,'HPeso')
                HPeso.text = valuta_cella(oSheet.getCellByPosition(8, m))
##########################
                Quantita = SubElement(RGItem,'Quantita')
                Quantita.text = str(oSheet.getCellByPosition(9, m).Value)
                # se negativa in CONTABILITA:
                if oSheet.getCellByPosition(11, m).Value != 0:
                    Quantita.text = '-' + oSheet.getCellByPosition(11, m).String
##########################
                Flags = SubElement(RGItem,'Flags')
                if '*** VOCE AZZERATA ***' in Descrizione.text:
                    PartiUguali.text = str(abs(float(valuta_cella(oSheet.getCellByPosition(5, m)))))
                    Flags.text = '1'
                elif '-' in Quantita.text or oSheet.getCellByPosition(11, m).Value !=0:
                    Flags.text = '1'
                elif "Parziale [" in oSheet.getCellByPosition(8, m).String:
                    Flags.text = '2'
                    HPeso.text = ''
                elif 'PARTITA IN CONTO PROVVISORIO' in Descrizione.text:
                    Flags.text = '16'
                else:
                    Flags.text = '0'
##########################
                if 'DETRAE LA PARTITA IN CONTO PROVVISORIO' in Descrizione.text:
                    Flags.text = '32'
                if '- vedi voce n.' in Descrizione.text:
                    IDVV.text = str(int(Descrizione.text.split('- vedi voce n.')[1].split(' ')[0])+1)
                    Flags.text = '32768'
                    #~ PartiUguali.text =''
                    if '-' in Quantita.text or oSheet.getCellByPosition(11, m).Value !=0:
                        Flags.text = '32769'
            n = sotto+1
##########################
    oDialogo_attesa.endExecute()
    # ~out_file = filedia('Salva con nome...', '*.xpwe', 1)
    # ~out_file = uno.fileUrlToSystemPath(oDoc.getURL())
    # ~mri (uno.fileUrlToSystemPath(oDoc.getURL()))
    # ~chi(out_file)
    if conf.read(path_conf, 'Generale', 'dettaglio') == '1':
        dettaglio_misure(1)
    try:
        if out_file.split('.')[-1].upper() != 'XPWE':
            out_file = out_file + '-'+ elaborato + '.xpwe'
        FileNameDocumento.text = out_file
    except AttributeError:
        return
    riga = str(tostring(top, encoding="unicode"))
    #~ if len(lista_AP) != 0:
        #~ riga = riga.replace('<PweDatiGenerali>','<Fgs>131072</Fgs><PweDatiGenerali>')
    try:
        of = codecs.open(out_file,'w','utf-8')
        of.write(riga)
        # ~MsgBox('Esportazione in formato XPWE eseguita con successo\nsul file ' + out_file + '!','Avviso.')
    except:
        MsgBox('Esportazione non eseguita!\n\nVerifica che il file di destinazione non sia già in uso!','E R R O R E !')
    refresh(1)
########################################################################
#~ def firme_in_calce_run(arg=None):
def firme_in_calce(arg=None):
    oDialogo_attesa = dlg_attesa()# avvia il diaolgo di attesa che viene chiuso alla fine con 
    '''
    Inserisce(in COMPUTO o VARIANTE) un riepilogo delle categorie
    ed i dati necessari alle firme
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()

    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name in('Analisi di Prezzo', 'Elenco Prezzi'):
        lrowF = ultima_voce(oSheet)+1
        oDoc.CurrentController.setFirstVisibleRow(lrowF-1)
        lrowE = getLastUsedCell(oSheet).EndRow
        for i in range(lrowF, getLastUsedCell(oSheet).EndRow+1):
            if oSheet.getCellByPosition(0, i).CellStyle == "Riga_rossa_Chiudi":
                lrowE = i
                break
        if lrowE > lrowF+1:
            oSheet.getRows().removeByIndex(lrowF, lrowE-lrowF)
        riga_corrente = lrowF+1
        oSheet.getRows().insertByIndex(lrowF, 15)
        oSheet.getCellRangeByPosition(0,lrowF,100,lrowF+15-1).CellStyle = "Ultimus_centro"
    #~ raggruppo i righi di mirura
        iSheet = oSheet.RangeAddress.Sheet
        oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
        oCellRangeAddr.Sheet = iSheet
        oCellRangeAddr.StartColumn = 0
        oCellRangeAddr.EndColumn = 0
        oCellRangeAddr.StartRow = lrowF
        oCellRangeAddr.EndRow = lrowF+15-1
        oSheet.group(oCellRangeAddr, 1)
        
#~ INSERISCI LA DATA E IL PROGETTISTA
        oSheet.getCellByPosition(1 , riga_corrente+3).Formula = '=CONCATENATE("Data, ";TEXT(NOW();"GG/MM/AAAA"))'
    #~ consolido il risultato
        oRange = oSheet.getCellByPosition(1 , riga_corrente+3)
        flags =(oDoc.createInstance('com.sun.star.sheet.CellFlags.FORMULA'))
        aSaveData = oRange.getDataArray()
        oRange.setDataArray(aSaveData)
        oSheet.getCellRangeByPosition(1,riga_corrente+3,1,riga_corrente+3).CellStyle = 'ULTIMUS'
        oSheet.getCellByPosition(1 , riga_corrente+5).Formula = 'Il Progettista'
        oSheet.getCellByPosition(1 , riga_corrente+6).Formula = '=CONCATENATE($S2.$C$13)' #senza concatenate, se la cella di origine è vuota il risultato è '0,00'

    if oSheet.Name in('COMPUTO', 'VARIANTE', 'CompuM_NoP'):
        zoom = oDoc.CurrentController.ZoomValue
        oDoc.CurrentController.ZoomValue = 400

        attesa().start()
        lrowF = ultima_voce(oSheet)+2

        oDoc.CurrentController.setFirstVisibleRow(lrowF-2)
        lrowE = getLastUsedCell(oSheet).EndRow
        for i in range(lrowF, getLastUsedCell(oSheet).EndRow+1):
            if oSheet.getCellByPosition(0, i).CellStyle == "Riga_rossa_Chiudi":
                lrowE = i
                break
        if lrowE > lrowF+1:
            oSheet.getRows().removeByIndex(lrowF, lrowE-lrowF)
        riga_corrente = lrowF+2
        if oDoc.getSheets().hasByName('S2') == True:
            ii = 11
            vv = 18
            ac = 28
            ad = 29
            ae = 30
            ss = 41
            col ='S'
        else:
            ii = 8
            vv = 9
            ss = 9
            col ='J'
        oSheet.getRows().insertByIndex(lrowF, 17)
        oSheet.getCellRangeByPosition(0, lrowF, ss, lrowF+17-1).CellStyle = 'ULTIMUS'
        # raggruppo i righi di mirura
        iSheet = oSheet.RangeAddress.Sheet
        oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
        oCellRangeAddr.Sheet = iSheet
        oCellRangeAddr.StartColumn = 0
        oCellRangeAddr.EndColumn = 0
        oCellRangeAddr.StartRow = lrowF
        oCellRangeAddr.EndRow = lrowF+17-1
        oSheet.group(oCellRangeAddr, 1)

    #~ INSERIMENTO TITOLO
        oSheet.getCellByPosition(2 , riga_corrente).String = 'Riepilogo strutturale delle Categorie'
        oSheet.getCellByPosition(ii , riga_corrente).String = 'Incidenze %'
        oSheet.getCellByPosition(vv , riga_corrente).String = 'Importi €'
        oSheet.getCellByPosition(ac , riga_corrente).String = 'Materiali\ne Noli €'
        oSheet.getCellByPosition(ad , riga_corrente).String = 'Incidenza\nMDO %'
        oSheet.getCellByPosition(ae , riga_corrente).String = 'Importo\nMDO €'
        inizio_gruppo = riga_corrente
        riga_corrente += 1
        for i in range(0, lrowF):
            if oSheet.getCellByPosition(1 , i).CellStyle == 'Livello-0-scritta':
                oSheet.getRows().insertByIndex(riga_corrente,1)
                oSheet.getCellRangeByPosition(0, riga_corrente, 30, riga_corrente).CellStyle = 'ULTIMUS_1'
                oSheet.getCellByPosition(1 , riga_corrente).Formula = '=B' + str(i+1) 
                oSheet.getCellByPosition(1 , riga_corrente).CellStyle = 'Ultimus_destra_1'
                oSheet.getCellByPosition(2 , riga_corrente).Formula = '=C' + str(i+1)
                oSheet.getCellByPosition(ii , riga_corrente).Formula = '=' + col + str(riga_corrente+1) + '/' + col + str(lrowF) + '*100'
                oSheet.getCellByPosition(ii, riga_corrente).CellStyle = 'Ultimus %_1'
                oSheet.getCellByPosition(vv , riga_corrente).Formula = '='+ col + str(i+1) 
                oSheet.getCellRangeByPosition(vv , riga_corrente, ae , riga_corrente).CellStyle = 'Ultimus_totali_1'
                oSheet.getCellByPosition(ac , riga_corrente).Formula = '=AC'+ str(i+1)
                oSheet.getCellByPosition(ad , riga_corrente).Formula = '=AD'+ str(i+1) + '*100'
                oSheet.getCellByPosition(ad, riga_corrente).CellStyle = 'Ultimus %_1'
                oSheet.getCellByPosition(ae , riga_corrente).Formula = '=AE'+ str(i+1)
                riga_corrente += 1
            elif oSheet.getCellByPosition(1 , i).CellStyle == 'Livello-1-scritta':
                oSheet.getRows().insertByIndex(riga_corrente,1)
                oSheet.getCellRangeByPosition(0, riga_corrente, 30, riga_corrente).CellStyle = 'ULTIMUS_2'
                oSheet.getCellByPosition(1 , riga_corrente).Formula = '=B' + str(i+1) 
                oSheet.getCellByPosition(1 , riga_corrente).CellStyle = 'Ultimus_destra'
                oSheet.getCellByPosition(2 , riga_corrente).Formula = '=C' + str(i+1)
                oSheet.getCellByPosition(ii , riga_corrente).Formula = '=' + col + str(riga_corrente+1) + '/' + col + str(lrowF) + '*100'
                oSheet.getCellByPosition(ii, riga_corrente).CellStyle = 'Ultimus %'
                oSheet.getCellByPosition(vv , riga_corrente).Formula = '='+ col + str(i+1) 
                oSheet.getCellByPosition(vv , riga_corrente).CellStyle = 'Ultimus_bordo'
                oSheet.getCellByPosition(ac , riga_corrente).Formula = '=AC'+ str(i+1)
                oSheet.getCellByPosition(ad , riga_corrente).Formula = '=AD'+ str(i+1) + '*100'
                oSheet.getCellByPosition(ad, riga_corrente).CellStyle = 'Ultimus %'
                oSheet.getCellByPosition(ae , riga_corrente).Formula = '=AE'+ str(i+1)
                riga_corrente += 1
            elif oSheet.getCellByPosition(1 , i).CellStyle == 'livello2 valuta':
                oSheet.getRows().insertByIndex(riga_corrente,1)
                oSheet.getCellRangeByPosition(0, riga_corrente, 30, riga_corrente).CellStyle = 'ULTIMUS_3'
                oSheet.getCellByPosition(1 , riga_corrente).Formula = '=B' + str(i+1) 
                oSheet.getCellByPosition(1 , riga_corrente).CellStyle = 'Ultimus_destra_3'
                oSheet.getCellByPosition(2 , riga_corrente).Formula = '=C' + str(i+1)
                oSheet.getCellByPosition(ii , riga_corrente).Formula = '=' + col + str(riga_corrente+1) + '/' + col + str(lrowF) + '*100'
                oSheet.getCellByPosition(ii, riga_corrente).CellStyle = 'Ultimus %_3'
                oSheet.getCellByPosition(vv , riga_corrente).Formula = '='+ col + str(i+1) 
                oSheet.getCellByPosition(vv , riga_corrente).CellStyle = 'ULTIMUS_3'
                oSheet.getCellByPosition(ac , riga_corrente).Formula = '=AC'+ str(i+1)
                oSheet.getCellByPosition(ad , riga_corrente).Formula = '=AD'+ str(i+1) + '*100'
                oSheet.getCellByPosition(ad, riga_corrente).CellStyle = 'Ultimus %_3'
                oSheet.getCellByPosition(ae , riga_corrente).Formula = '=AE'+ str(i+1)
                riga_corrente += 1
        oSheet.getCellRangeByPosition(2,inizio_gruppo,ae,inizio_gruppo).CellStyle = "Ultimus_centro"
        oSheet.getCellByPosition(ii, riga_corrente).Value = 100
        oSheet.getCellByPosition(2 , riga_corrente).CellStyle = 'Ultimus_destra'
        oSheet.getCellByPosition(ii , riga_corrente).CellStyle = 'Ultimus %_1'
        oSheet.getCellByPosition(vv , riga_corrente).Formula = '=' + col + str(lrowF) 
        oSheet.getCellByPosition(vv , riga_corrente).CellStyle = 'Ultimus_Bordo_sotto'
        oSheet.getCellByPosition(ac , riga_corrente).Formula = '=AC' + str(lrowF)
        oSheet.getCellByPosition(ac , riga_corrente).CellStyle = 'Ultimus_Bordo_sotto'
        oSheet.getCellByPosition(ae , riga_corrente).Formula = '=AE' + str(lrowF)
        oSheet.getCellByPosition(ae , riga_corrente).CellStyle = 'Ultimus_Bordo_sotto'
        oSheet.getCellByPosition(ad , riga_corrente).Formula = '=AD' + str(lrowF) + '*100'
        oSheet.getCellByPosition(2 , riga_corrente).String= '          T O T A L E   €'
        oSheet.getCellByPosition(2 , riga_corrente).CellStyle = 'ULTIMUS_1'
        fine_gruppo = riga_corrente
    #~ DATA
        oSheet.getCellByPosition(2 , riga_corrente+3).Formula = '=CONCATENATE("Data, ";TEXT(NOW();"GG/MM/AAAA"))'
    #~ consolido il risultato
        oRange = oSheet.getCellByPosition(2 , riga_corrente+3)
        flags =(oDoc.createInstance('com.sun.star.sheet.CellFlags.FORMULA'))
        aSaveData = oRange.getDataArray()
        oRange.setDataArray(aSaveData)
        
        oSheet.getCellByPosition(2 , riga_corrente+5).Formula = 'Il Progettista'
        oSheet.getCellByPosition(2 , riga_corrente+6).Formula = '=CONCATENATE($S2.$C$13)' #senza concatenate, se la cella di origine è vuota il risultato è '0,00'
        oSheet.getCellRangeByPosition(2 , riga_corrente+5, 2 , riga_corrente+6).CellStyle = 'Ultimus_centro'

        ###  inserisco il salto pagina in cima al riepilogo
        oDoc.CurrentController.select(oSheet.getCellByPosition(0, lrowF))
        ctx = XSCRIPTCONTEXT.getComponentContext()
        desktop = XSCRIPTCONTEXT.getDesktop()
        oFrame = desktop.getCurrentFrame()
        dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
        dispatchHelper.executeDispatch(oFrame, ".uno:InsertRowBreak", "", 0, list())
        oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges"))
        ###
        #~ oSheet.getCellByPosition(lrowF,0).Rows.IsManualPageBreak = True
    oDialogo_attesa.endExecute()
    oDoc.CurrentController.ZoomValue = zoom
########################################################################
def next_voice(lrow, n=1):
# ~def debug (arg=None, n=1):
    '''
    lrow { double }   : riga di riferimento
    n    { integer }  : se 0 sposta prima della voce corrente
                        se 1 sposta dopo della voce corrente
    sposta il cursore prima o dopo la voce corrente restituento un idrow
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    # ~lrow = Range2Cell()[1]
    if lrow==0:
        while oSheet.getCellByPosition(0, lrow).CellStyle not in stili_computo + stili_contab:
            lrow +=1
        return lrow
    fine = ultima_voce(oSheet)+1
    # la parte che segue sposta il focus dopo della voce corrente (ad esempio sul titolo di categoria)
    if lrow >= fine:
        return lrow
    if oSheet.getCellByPosition(0, lrow).CellStyle in stili_computo + stili_contab:
        if n==0:
            sopra = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
            lrow = sopra
        elif n==1:
            sotto = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.EndRow
            lrow = sotto+1
    elif oSheet.getCellByPosition(0, lrow).CellStyle in ('Ultimus_centro_bordi_lati',):
        for y in range(lrow, getLastUsedCell(oSheet).EndRow+1):
            if oSheet.getCellByPosition(0, y).CellStyle != 'Ultimus_centro_bordi_lati':
                lrow = y
                break
    elif oSheet.getCellByPosition(0, lrow).CellStyle in noVoce:
        # ~while oSheet.getCellByPosition(0, lrow).CellStyle in noVoce:
        lrow +=1
    else:
        return
    return lrow
    # la parte che segue sposta il focus all'effettivo inizio della voce successiva
    # ~fine = ultima_voce(oSheet)+1
    # ~if lrow <= 1: lrow = 2
    # ~if lrow >= fine or oSheet.getCellByPosition(0, lrow).CellStyle in('Comp TOTALI'): return lrow
    # ~if oSheet.getCellByPosition(0, lrow).CellStyle in stili_computo + stili_contab:
        # ~if n==0:
            # ~sopra = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
            # ~lrow = sopra
        # ~elif n==1:
            # ~sotto = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.EndRow
            # ~lrow = sotto+1
    # ~elif oSheet.getCellByPosition(0, lrow).CellStyle in ('Ultimus_centro_bordi_lati',):
        # ~for y in range(lrow, getLastUsedCell(oSheet).EndRow+1):
            # ~if oSheet.getCellByPosition(0, y).CellStyle != 'Ultimus_centro_bordi_lati':
                # ~lrow = y
                # ~break
    # ~while oSheet.getCellByPosition(0, lrow).CellStyle in noVoce:
        # ~lrow +=1
    # ~return lrow
########################################################################
def cancella_analisi_da_ep(arg=None):
    '''
    cancella le voci in Elenco Prezzi che derivano da analisi
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet = oDoc.Sheets.getByName('Analisi di Prezzo')
    lista_an = list()
    for i in range(0, getLastUsedCell(oSheet).EndRow):
        if oSheet.getCellByPosition(0, i).CellStyle == 'An-1_sigla':
            codice = oSheet.getCellByPosition(0, i).String
            lista_an.append(oSheet.getCellByPosition(0, i).String)
    oSheet = oDoc.Sheets.getByName('Elenco Prezzi')
    for i in reversed(range(0, getLastUsedCell(oSheet).EndRow)):
        if oSheet.getCellByPosition(0, i).String in lista_an:
            oSheet.getRows().removeByIndex(i, 1)
###
def analisi_in_ElencoPrezzi(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    try:
        oSheet = oDoc.CurrentController.ActiveSheet
        if oSheet.Name != 'Analisi di Prezzo':
            return
        oDoc.enableAutomaticCalculation(False) # blocco il calcolo automatico
        sStRange = Circoscrive_Analisi(Range2Cell()[1])
        riga = sStRange.RangeAddress.StartRow + 2
        
        codice = oSheet.getCellByPosition(0, riga).String
        
        oSheet = oDoc.Sheets.getByName('Elenco Prezzi')
        oDoc.CurrentController.setActiveSheet(oSheet)
        
        oSheet.getRows().insertByIndex(3,1)

        oSheet.getCellByPosition(0,3).CellStyle = 'EP-aS'
        oSheet.getCellByPosition(1,3).CellStyle = 'EP-a'
        oSheet.getCellRangeByPosition(2,3,8,3).CellStyle = 'EP-mezzo'
        oSheet.getCellByPosition(5,3).CellStyle = 'EP-mezzo %'
        oSheet.getCellByPosition(9,3).CellStyle = 'EP-sfondo'
        oSheet.getCellByPosition(10,3).CellStyle = 'Default'
        oSheet.getCellByPosition(11,3).CellStyle = 'EP-mezzo %'
        oSheet.getCellByPosition(12,3).CellStyle = 'EP statistiche_q'
        oSheet.getCellByPosition(13,3).CellStyle = 'EP statistiche_Contab_q'

        oSheet.getCellByPosition(0,3).String = codice

        oSheet.getCellByPosition(1,3).Formula = "=$'Analisi di Prezzo'.B" + str(riga+1)
        oSheet.getCellByPosition(2,3).Formula = "=$'Analisi di Prezzo'.C" + str(riga+1)
        oSheet.getCellByPosition(3,3).Formula = "=$'Analisi di Prezzo'.K" + str(riga+1)
        oSheet.getCellByPosition(4,3).Formula = "=$'Analisi di Prezzo'.G" + str(riga+1)
        oSheet.getCellByPosition(5,3).Formula = "=$'Analisi di Prezzo'.I" + str(riga+1)
        oSheet.getCellByPosition(6,3).Formula = "=$'Analisi di Prezzo'.J" + str(riga+1)
        oSheet.getCellByPosition(7,3).Formula = "=$'Analisi di Prezzo'.A" + str(riga+1)
        oSheet.getCellByPosition(8,3).String = "(AP)"
        oSheet.getCellByPosition(11,3).Formula = "=N4/$N$2"
        oSheet.getCellByPosition(12,3).Formula = "=SUMIF(AA;A4;BB)"
        oSheet.getCellByPosition(13,3).Formula = "=SUMIF(AA;A4;cEuro)"
        oDoc.enableAutomaticCalculation(True)  # sblocco il calcolo automatico
        _gotoCella(1, 3)
    except:
        oDoc.enableAutomaticCalculation(True)
########################################################################
def tante_analisi_in_ep(arg=None):
    '''
    Trsferisce le analisi all'Elenco Prezzi.
    '''
    chiudi_dialoghi()
    refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    lista_analisi = list()
    oSheet = oDoc.getSheets().getByName('Analisi di prezzo')
    rifa_nomearea('Analisi di Prezzo', '$A$3:$K$' + str(getLastUsedCell(oSheet).EndRow), 'analisi')
    voce = list()
    idx = 4
    for n in range(0, ultima_voce(oSheet)+1):
        if oSheet.getCellByPosition(0, n).CellStyle == 'An-1_sigla' and oSheet.getCellByPosition(1, n).String != '<<<Scrivi la descrizione della nuova voce da analizzare   ':
            voce =(oSheet.getCellByPosition(0, n).String,
                '=VLOOKUP(A' + str(idx) + ';analisi;2;FALSE())',
                '=VLOOKUP(A' + str(idx) + ';analisi;3;FALSE())',
                '=VLOOKUP(A' + str(idx) + ';analisi;11;FALSE())',
                '=VLOOKUP(A' + str(idx) + ';analisi;7;FALSE())',
                '=VLOOKUP(A' + str(idx) + ';analisi;9;FALSE())',
                '=VLOOKUP(A' + str(idx) + ';analisi;10;FALSE())',
            )
            lista_analisi.append(voce)
            idx += 1
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    if len(lista_analisi) !=0:
        oSheet.getRows().insertByIndex(3,len(lista_analisi))
    else:
        return
    oRange = oSheet.getCellRangeByPosition(0, 3, 6, 3+len(lista_analisi)-1)
    lista_come_array = tuple(lista_analisi)
    
    oSheet.getCellRangeByPosition(11, 3, 11, 3+len(lista_analisi)-1).CellStyle = 'EP-mezzo %'
    oSheet.getCellRangeByPosition(12, 3, 12, 3+len(lista_analisi)-1).CellStyle = 'EP statistiche_q'
    oSheet.getCellRangeByPosition(13, 3, 13, 3+len(lista_analisi)-1).CellStyle = 'EP statistiche_Contab_q'
    # ~chi(lista_come_array)
    oRange.setDataArray(lista_come_array) #setFrmulaArray() sarebbe meglio, ma mi fa storie sul codice articolo
    for y in range(3, 3+len(lista_analisi)):
        for x in range(1, 8): #evito il codice articolo, altrimenti me lo converte in numero
            oSheet.getCellByPosition(x, y).Formula = oSheet.getCellByPosition(x, y).String
    oSheet.getCellRangeByPosition(0, 3, 7, 3+len(lista_analisi)-1).CellStyle = 'EP-C mezzo'
    oSheet.getCellRangeByPosition(0, 3, 0, 3+len(lista_analisi)-1).CellStyle = 'EP-aS'
    oSheet.getCellRangeByPosition(1, 3, 1, 3+len(lista_analisi)-1).CellStyle = 'EP-a'
    oSheet.getCellRangeByPosition(5, 3, 5, 3+len(lista_analisi)-1).CellStyle = 'EP-mezzo %'
    refresh(1)
    _gotoSheet('Elenco Prezzi')
    #~ MsgBox('Trasferite ' + str(len(lista_analisi)) + ' analisi di prezzo in Elenco Prezzi.', 'Avviso')
########################################################################
def Circoscrive_Analisi(lrow):
    '''
    lrow    { int }  : riga di riferimento per
                        la selezione dell'intera voce
    Circoscrive una voce di analisi
    partendo dalla posizione corrente del cursore
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.getCellByPosition(0, lrow).CellStyle in stili_analisi:
        for el in reversed(range(0, lrow)):
            #~ chi(oSheet.getCellByPosition(0, el).CellStyle)
            if oSheet.getCellByPosition(0, el).CellStyle == 'Analisi_Sfondo':
                SR = el
                break
        for el in range(lrow, getLastUsedCell(oSheet).EndRow):
            if oSheet.getCellByPosition(0, el).CellStyle == 'An-sfondo-basso Att End':
                ER = el
                break
    celle=oSheet.getCellRangeByPosition(0,SR,250,ER)
    return celle
def Circoscrive_Voce_Computo_Att(lrow):
    '''
    lrow    { int }  : riga di riferimento per
                        la selezione dell'intera voce

    Circoscrive una voce di COMPUTO, VARIANTE o CONTABILITÀ
    partendo dalla posizione corrente del cursore
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    #~ lrow = Range2Cell()[1]
    #~ if oSheet.Name in('VARIANTE', 'COMPUTO','CONTABILITA'):
    if oSheet.getCellByPosition(0, lrow).CellStyle in('comp progress', 'comp 10 s', 'Comp Start Attributo',
    'Comp End Attributo', 'Comp Start Attributo_R', 'comp 10 s_R', 'Comp End Attributo_R', 'Livello-0-scritta', 'Livello-1-scritta', 'livello2 valuta'):
        y = lrow
        while oSheet.getCellByPosition(0, y).CellStyle not in('Comp End Attributo', 'Comp End Attributo_R'):
            y +=1
        lrowE=y
        y = lrow
        while oSheet.getCellByPosition(0, y).CellStyle not in('Comp Start Attributo', 'Comp Start Attributo_R'):
            y -=1
        lrowS=y
    celle=oSheet.getCellRangeByPosition(0,lrowS,250,lrowE)
    return celle
########################################################################
def ColumnNumberToName(oSheet,cColumnNumb):
    '''Trasforma IDcolonna in Nome'''
    #~ oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    oColumns = oSheet.getColumns()
    oColumn = oColumns.getByIndex(cColumnNumb).Name
    return oColumn
########################################################################
def ColumnNameToNumber(oSheet,cColumnName):
    '''Trasforma il nome colonna in IDcolonna'''
    #~ oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    oColumns = oSheet.getColumns()
    oColumn = oColumns.getByName(cColumnName)
    oRangeAddress = oColumn.getRangeAddress()
    nColumn = oRangeAddress.StartColumn
    return nColumn
########################################################################
def azzera_voce(arg=None):
    '''
    Azzera la quantità di una voce e ne raggruppa le relative righe
    '''
    refresh(0)
    try:
        oDoc = XSCRIPTCONTEXT.getDocument()
        oSheet = oDoc.CurrentController.ActiveSheet
        if oSheet.Name in('COMPUTO', 'VARIANTE', 'CONTABILITA'):
            try:
                sRow = oDoc.getCurrentSelection().getRangeAddresses()[0].StartRow
                eRow = oDoc.getCurrentSelection().getRangeAddresses()[0].EndRow

            except:
                sRow = oDoc.getCurrentSelection().getRangeAddress().StartRow
                eRow = oDoc.getCurrentSelection().getRangeAddress().EndRow
            sStRange = Circoscrive_Voce_Computo_Att(sRow)
            sStRange.RangeAddress
            sRow = sStRange.RangeAddress.StartRow
            sStRange = Circoscrive_Voce_Computo_Att(eRow)
            try:
                sStRange.RangeAddress
            except:
                return
            inizio = sStRange.RangeAddress.StartRow
            eRow = sStRange.RangeAddress.EndRow+1
            
            lrow = sRow
            fini = list()
            for x in range(sRow, eRow):
                if oSheet.getCellByPosition(0, x).CellStyle == 'Comp End Attributo':
                    fini.append(x)
                elif oSheet.getCellByPosition(0, x).CellStyle == 'Comp End Attributo_R':
                    fini.append(x-2)
        idx = 0
        for lrow in fini:
            lrow += idx
            try:
                sStRange = Circoscrive_Voce_Computo_Att(lrow)
                sStRange.RangeAddress
                inizio = sStRange.RangeAddress.StartRow
                fine = sStRange.RangeAddress.EndRow
                if oSheet.Name == 'CONTABILITA':
                    fine -=1
                _gotoCella(2, fine-1)
                if oSheet.getCellByPosition(2, fine-1).String == '*** VOCE AZZERATA ***':
                    ### elimino il colore di sfondo
                    if oSheet.Name == 'CONTABILITA':
                        oSheet.getCellRangeByPosition(0, inizio, 250, fine+1).clearContents(HARDATTR)
                    else:
                        oSheet.getCellRangeByPosition(0, inizio, 250, fine).clearContents(HARDATTR)
                    raggruppa_righe_voce(lrow, 0)
                    oSheet.getRows().removeByIndex(fine-1, 1)
                    fine -=1
                    _gotoCella(2, fine-1)
                    idx -= 1
                else:
                    Copia_riga_Ent()
                    oSheet.getCellByPosition(2, fine).String = '*** VOCE AZZERATA ***'
                    if oSheet.Name == 'CONTABILITA':
                        oSheet.getCellByPosition(5, fine).Formula = '=SUBTOTAL(9;J' + str(inizio+1) + ':J' + str(fine+1) + ')-SUBTOTAL(9;L' + str(inizio) + ':L' + str(fine) + ')'
                        inverti_segno()
                        # ~oSheet.getCellByPosition(9, fine).Formula = '=-SUM(J' + str(inizio+1) + ':J' + str(fine) + ')'
                        # ~oSheet.getCellByPosition(11, fine).Formula = '=-SUM(L' + str(inizio+1) + ':L' + str(fine) + ')'
                    else:
                        oSheet.getCellByPosition(5, fine).Formula = '=-SUBTOTAL(9;J' + str(inizio+1) + ':J' + str(fine) + ')'
                    ### cambio il colore di sfondo
                    oDoc.CurrentController.select(sStRange)
                    raggruppa_righe_voce (lrow, 1)
                    ctx = XSCRIPTCONTEXT.getComponentContext()
                    desktop = XSCRIPTCONTEXT.getDesktop()
                    oFrame = desktop.getCurrentFrame()
                    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
                    oProp = PropertyValue()
                    oProp.Name = 'BackgroundColor'
                    oProp.Value = 15066597
                    properties =(oProp,)
                    dispatchHelper.executeDispatch(oFrame, '.uno:BackgroundColor', '', 0, properties)
                    _gotoCella(2, fine)
                    ###   
                lrow = Range2Cell()[1]
                lrow = next_voice(lrow, 1)
            except:
                pass
        # ~numera_voci(1)
    except:
        pass
    refresh(1)
    return
########################################################################
def elimina_voci_azzerate(arg=None):
    '''
    Elimina le voci in cui compare la dicitura '*** VOCE AZZERATA ***'
    in COMPUTO o in VARIANTE, senza chiedere conferma
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    try:
        if oSheet.Name in('COMPUTO', 'VARIANTE', 'CONTABILITA'):
            ER = getLastUsedCell(oSheet).EndRow
            for lrow in reversed(range(0, ER)):
                if oSheet.getCellByPosition(2, lrow).String == '*** VOCE AZZERATA ***':
                    elimina_voce(lrow=lrow, msg=0)
            numera_voci(1)
    except:
        return
########################################################################
def raggruppa_righe_voce (lrow, flag=1):
    '''
    Raggruppa le righe che compongono una singola voce.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    #~ lrow = Range2Cell()[1]
    if oSheet.Name in('COMPUTO', 'VARIANTE'):
        sStRange = Circoscrive_Voce_Computo_Att (lrow)
        sStRange.RangeAddress

        iSheet = oSheet.RangeAddress.Sheet
        oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
        oCellRangeAddr.Sheet = iSheet
        oCellRangeAddr.StartColumn = sStRange.RangeAddress.StartColumn
        oCellRangeAddr.EndColumn = sStRange.RangeAddress.EndColumn
        oCellRangeAddr.StartRow = sStRange.RangeAddress.StartRow
        oCellRangeAddr.EndRow = sStRange.RangeAddress.EndRow
        if flag == 1:
            oSheet.group(oCellRangeAddr, 1)
        else:
            oSheet.ungroup(oCellRangeAddr, 1)
########################################################################
def nasconde_voci_azzerate(arg=None):
    '''
    Nasconde le voci in cui compare la dicitura '*** VOCE AZZERATA ***'
    in COMPUTO o in VARIANTE.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    try:
        if oSheet.Name in('COMPUTO', 'VARIANTE'):
            oSheet.clearOutline()
            ER = getLastUsedCell(oSheet).EndRow
            for lrow in reversed(range(0, ER)):
                if oSheet.getCellByPosition(2, lrow).String == '*** VOCE AZZERATA ***':
                    raggruppa_righe_voce(lrow, 1)
    except:
        return
########################################################################
def seleziona(lrow=None):
#~ def debug(lrow=None):
    '''
    Seleziona voci intere
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name in('Elenco Prezzi'): return
    if oSheet.Name in('COMPUTO', 'VARIANTE'):
        try:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
        except AttributeError:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
        try:
            if lrow != None:
                SR = oRangeAddress.StartRow
                SR = Circoscrive_Voce_Computo_Att(SR).RangeAddress.StartRow
            else:
                SR = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
        except AttributeError:
            MsgBox('La selezione deve essere contigua.','ATTENZIONE!')
            return 0
        if lrow != None:
            ER = oRangeAddress.EndRow
            ER = Circoscrive_Voce_Computo_Att(ER).RangeAddress.EndRow
        else:
            ER = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.EndRow
    if oSheet.Name == 'Analisi di Prezzo':
        try:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
        except AttributeError:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
        try:
            if lrow != None:
                SR = oRangeAddress.StartRow
                SR = Circoscrive_Voce_Computo_Att(SR).RangeAddress.StartRow
            else:
                SR = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
        except AttributeError:
            MsgBox('La selezione deve essere contigua.','ATTENZIONE!')
            return 0
        if lrow != None:
            ER = oRangeAddress.EndRow
            ER = Circoscrive_Voce_Computo_Att(ER).RangeAddress.EndRow
        else:
            ER = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.EndRow
    if oSheet.Name =='CONTABILITA':
        cerca_partenza()
        if partenza[2] == '#reg':
            sblocca_cont()
            if sblocca_computo == 0:
                return
            pass
        else:
            pass
        try:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
        except AttributeError:
            oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
        try:
            if lrow != None:
                SR = oRangeAddress.StartRow
                SR = Circoscrive_Voce_Computo_Att(SR).RangeAddress.StartRow
            else:
                SR = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.StartRow
        except AttributeError:
            MsgBox('La selezione deve essere contigua.','ATTENZIONE!')
            return 0
        if lrow != None:
            ER = oRangeAddress.EndRow
            ER = Circoscrive_Voce_Computo_Att(ER).RangeAddress.EndRow
        else:
            ER = Circoscrive_Voce_Computo_Att(lrow).RangeAddress.EndRow
    return oDoc.CurrentController.select(oSheet.getCellRangeByPosition(0, SR, 50, ER))
########################################################################
def elimina_voce(lrow=None, msg=1):
    '''
    Elimina una voce in COMPUTO, VARIANTE, CONTABILITA o Analisi di Prezzo
    lrow { long }  : numero riga
    msg  { bit }   : 1 chiedi conferma con messaggio
                     0 egegui senza conferma
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if lrow == None or lrow == 0:
        lrow = Range2Cell()[1]
    if oSheet.Name in('Elenco Prezzi'): return
    try:
        if oSheet.Name in('COMPUTO', 'VARIANTE'):
            sStRange = Circoscrive_Voce_Computo_Att(lrow)
        elif oSheet.Name == 'Analisi di Prezzo':
            sStRange = Circoscrive_Analisi(lrow)
        ###
        if oSheet.Name =='CONTABILITA':
            cerca_partenza()
            if partenza[2] == '#reg':
                sblocca_cont()
                if sblocca_computo == 0:
                    return
                pass
            else:
                pass
            sStRange = Circoscrive_Voce_Computo_Att(lrow)
        ###
    except:
        return
    sStRange.RangeAddress
    SR = sStRange.RangeAddress.StartRow
    ER = sStRange.RangeAddress.EndRow
    oDoc.CurrentController.select(oSheet.getCellRangeByPosition(0, SR, 250, ER))
    #~ return
    if msg==1:
        if DlgSiNo("""OPERAZIONE NON ANNULLABILE!
        
Stai per eliminare la voce selezionata.
Vuoi Procedere?
 """,'AVVISO!') ==2:
            oSheet.getRows().removeByIndex(SR, ER-SR+1)
            numera_voci(0)
        else:
            return
    elif msg==0:
        oSheet.getRows().removeByIndex(SR, ER-SR+1)
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges"))
########################################################################
def copia_riga_computo(lrow):
# ~def debug(lrow):
    '''
    Inserisce una nuova riga di misurazione nel computo
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    # ~lrow = Range2Cell()[1]
    stile = oSheet.getCellByPosition(1, lrow).CellStyle
    if stile in('comp Art-EP', 'comp Art-EP_R', 'Comp-Bianche in mezzo'):#'Comp-Bianche in mezzo Descr', 'comp 1-a', 'comp sotto centro'):# <stili computo
        lrow = lrow+1 # PER INSERIMENTO SOTTO RIGA CORRENTE
        oSheet.getRows().insertByIndex(lrow,1)
# imposto gli stili
        oSheet.getCellRangeByPosition(5, lrow, 7, lrow,).CellStyle = 'comp 1-a'
        oSheet.getCellByPosition(0, lrow).CellStyle = 'comp 10 s'
        oSheet.getCellByPosition(1, lrow).CellStyle = 'Comp-Bianche in mezzo'
        oSheet.getCellByPosition(2, lrow).CellStyle = 'comp 1-a'
        oSheet.getCellRangeByPosition(3, lrow, 4, lrow).CellStyle = 'Comp-Bianche in mezzo bordate_R'
        oSheet.getCellByPosition(5, lrow).CellStyle = 'comp 1-a PU'
        oSheet.getCellByPosition(6, lrow).CellStyle = 'comp 1-a LUNG'
        oSheet.getCellByPosition(7, lrow).CellStyle = 'comp 1-a LARG'
        oSheet.getCellByPosition(8, lrow).CellStyle = 'comp 1-a peso'
        oSheet.getCellByPosition(9, lrow).CellStyle = 'Blu'
# ci metto le formule
        oSheet.getCellByPosition(9, lrow).Formula = '=IF(PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + '))'
        _gotoCella(2, lrow)
        # ~oDoc.CurrentController.select(oSheet.getCellByPosition(2, lrow))
        # ~oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges"))
def copia_riga_contab(lrow):
    '''
    Inserisce una nuova riga di misurazione in contabilità
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    #~ lrow = Range2Cell()[1]
    stile = oSheet.getCellByPosition(1, lrow).CellStyle
    if  oSheet.getCellByPosition(1, lrow+1).CellStyle == 'comp sotto Bianche_R':
        return
    if stile in('comp Art-EP_R', 'Data_bianca', 'Comp-Bianche in mezzo_R'):
        lrow = lrow+1 # PER INSERIMENTO SOTTO RIGA CORRENTE
        oSheet.getRows().insertByIndex(lrow,1)
    # imposto gli stili
        oSheet.getCellByPosition(1, lrow).CellStyle = 'Comp-Bianche in mezzo_R'
        oSheet.getCellByPosition(2, lrow).CellStyle = 'comp 1-a'
        oSheet.getCellByPosition(5, lrow).CellStyle = 'comp 1-a PU'
        oSheet.getCellByPosition(6, lrow).CellStyle = 'comp 1-a LUNG'
        oSheet.getCellByPosition(7, lrow).CellStyle = 'comp 1-a LARG'
        oSheet.getCellByPosition(8, lrow).CellStyle = 'comp 1-a peso'
        oSheet.getCellRangeByPosition(11, lrow, 23, lrow).CellStyle = 'Comp-Bianche in mezzo_R'
        oSheet.getCellByPosition(8, lrow).CellStyle = 'comp 1-a peso'
        oSheet.getCellRangeByPosition(9, lrow, 11, lrow).CellStyle = 'Blu'
    # ci metto le formule
        oSheet.getCellByPosition(9, lrow).Formula = '=IF(PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + ')<=0;"";PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + '))'
        # ~oSheet.getCellByPosition(11, lrow).Formula = '=IF(PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + ')>=0;"";PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + ')*-1)'
    # preserva la data di misura
        if oSheet.getCellByPosition(1, lrow+1).CellStyle == 'Data_bianca':
            oRangeAddress = oSheet.getCellByPosition(1, lrow+1).getRangeAddress()
            oCellAddress = oSheet.getCellByPosition(1,lrow).getCellAddress()
            oSheet.copyRange(oCellAddress, oRangeAddress)
            oSheet.getCellByPosition(1, lrow+1).String = ""
            oSheet.getCellByPosition(1, lrow+1).CellStyle = 'Comp-Bianche in mezzo_R'
        _gotoCella(2, lrow)
def copia_riga_analisi(lrow):
    '''
    Inserisce una nuova riga di misurazione in analisi di prezzo
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    stile = oSheet.getCellByPosition(0, lrow).CellStyle
    if stile in('An-lavoraz-desc', 'An-lavoraz-Cod-sx'):
        lrow=lrow+1
        oSheet.getRows().insertByIndex(lrow,1)
    # imposto gli stili
        oSheet.getCellByPosition(0, lrow).CellStyle = 'An-lavoraz-Cod-sx'
        oSheet.getCellRangeByPosition(1, lrow, 5, lrow).CellStyle = 'An-lavoraz-generica'
        oSheet.getCellByPosition(3, lrow).CellStyle = 'An-lavoraz-input'
        oSheet.getCellByPosition(6, lrow).CellStyle = 'An-senza'
        oSheet.getCellByPosition(7, lrow).CellStyle = 'An-senza-DX'
    # ci metto le formule
        #~ oDoc.enableAutomaticCalculation(False)
        oSheet.getCellByPosition(1, lrow).Formula = '=IF(A' + str(lrow+1) + '="";"";CONCATENATE("  ";VLOOKUP(A' + str(lrow+1) + ';elenco_prezzi;2;FALSE());' '))'
        oSheet.getCellByPosition(2, lrow).Formula = '=IF(A' + str(lrow+1) + '="";"";VLOOKUP(A' + str(lrow+1) + ';elenco_prezzi;3;FALSE()))'
        oSheet.getCellByPosition(3, lrow).Value = 0
        oSheet.getCellByPosition(4, lrow).Formula = '=IF(A' + str(lrow+1) + '="";0;VLOOKUP(A' + str(lrow+1) + ';elenco_prezzi;5;FALSE()))'
        oSheet.getCellByPosition(5, lrow).Formula = '=D' + str(lrow+1) + '*E' + str(lrow+1)
        oSheet.getCellByPosition(8, lrow).Formula = '=IF(A' + str(lrow+1) + '="";"";IF(VLOOKUP(A' + str(lrow+1) + ';elenco_prezzi;6;FALSE())="";"";(VLOOKUP(A' + str(lrow+1) + ';elenco_prezzi;6;FALSE()))))'
        oSheet.getCellByPosition(9, lrow).Formula = '=IF(I' + str(lrow+1) + '="";"";I' + str(lrow+1) + '*F' + str(lrow+1) + ')'
        #~ oDoc.enableAutomaticCalculation(True)
    # preserva il Pesca
        if oSheet.getCellByPosition(1, lrow-1).CellStyle == 'An-lavoraz-dx-senza-bordi':
            oRangeAddress = oSheet.getCellByPosition(0, lrow+1).getRangeAddress()
            oCellAddress = oSheet.getCellByPosition(0,lrow).getCellAddress()
            oSheet.copyRange(oCellAddress, oRangeAddress)
        oSheet.getCellByPosition(0, lrow).String = 'Cod. Art.?'
    _gotoCella(1, lrow)
########################################################################
def Copia_riga_Ent(arg=None): #Aggiungi Componente - capisce su quale tipologia di tabelle è
    # ~datarif = datetime.now()
    #~ refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    nome_sheet = oSheet.Name
    if nome_sheet in('COMPUTO', 'VARIANTE'):
        if conf.read(path_conf, 'Generale', 'dettaglio') == '1':
            dettaglio_misura_rigo()
        copia_riga_computo(lrow)
    elif nome_sheet == 'CONTABILITA':
        if conf.read(path_conf, 'Generale', 'dettaglio') == '1':
            dettaglio_misura_rigo()
        copia_riga_contab(lrow)
    elif nome_sheet == 'Analisi di Prezzo':
        copia_riga_analisi(lrow)
    #~ refresh(1)
    # ~MsgBox('eseguita in ' + str((datetime.now() - datarif).total_seconds()) + ' secondi!','')

########################################################################
def cerca_partenza(arg=None):
    '''
    Conserva, nella variabile globale 'partenza', il nome del foglio [0] e l'id
    della riga di codice prezzo componente [1], il flag '#reg' solo per la contbailità.
    partenza = (nome_foglio, id_rcodice, flag_contabilità)
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    global partenza

    if oSheet.getCellByPosition(0, lrow).CellStyle in stili_computo: #COMPUTO, VARIANTE
        sStRange = Circoscrive_Voce_Computo_Att(lrow)
        partenza =(oSheet.Name, sStRange.RangeAddress.StartRow+1)
    elif oSheet.getCellByPosition(0, lrow).CellStyle in stili_contab: #CONTABILITA
        sStRange = Circoscrive_Voce_Computo_Att(lrow)
        partenza =(oSheet.Name, sStRange.RangeAddress.StartRow+1, oSheet.getCellByPosition(22, sStRange.RangeAddress.StartRow+1).String)
    elif oSheet.getCellByPosition(0, lrow).CellStyle in ('An-lavoraz-Cod-sx', 'Comp TOTALI'): #ANALISI o riga totale
        partenza =(oSheet.Name, lrow)
    return partenza
########################################################################
sblocca_computo = 0
def sblocca_cont():
    '''
    Controlla che non ci siano atti contabili registrati e dà il consenso a procedere.
    '''
    global sblocca_computo
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name in('CONTABILITA'):
        cerca_partenza()
        chi(partenza[2])
        chi(sblocca_computo)
        if sblocca_computo == 1:
            pass
        else:
            if partenza[2] == '':
                pass
            if partenza[2] == '#reg':
                if DlgSiNo("""Lavorando in questo punto del foglio,
comprometterai la validità degli atti contabili già emessi.

Vuoi procedere?

SCEGLIENDO SI' SARAI COSTRETTO A RIGENERARLI!""", 'Voce già registrata!') ==3:
                    pass
                else:
                    sblocca_computo = 1
        chi(sblocca_computo)
########################################################################
def cerca_in_elenco(arg=None):
    '''Evidenzia il codice di elenco prezzi della voce corrente.'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    if oSheet.Name in ('COMPUTO', 'CONTABILITA', 'VARIANTE', 'Analisi di Prezzo'):
        if oSheet.Name == 'Analisi di Prezzo':
            if oSheet.getCellByPosition(0, lrow).CellStyle in ('An-lavoraz-Cod-sx', 'An-1_sigla'):
                codice_da_cercare = oSheet.getCellByPosition(0, lrow).String
            else:
                return
        else:
            sStRange = Circoscrive_Voce_Computo_Att (lrow)
            sopra = sStRange.RangeAddress.StartRow
            codice_da_cercare = oSheet.getCellByPosition(1,sopra+1).String
        oSheet = oDoc.getSheets().getByName("Elenco Prezzi")
        oSheet.IsVisible = True
        _gotoSheet('Elenco Prezzi')
    elif oSheet.Name in ('Elenco Prezzi'):
        if oSheet.getCellByPosition(1, lrow).Type.value == 'FORMULA':
            codice_da_cercare = oSheet.getCellByPosition(0, lrow).String
        else:
            return
        oSheet = oDoc.getSheets().getByName("Analisi di Prezzo")
        oSheet.IsVisible = True
        _gotoSheet('Analisi di Prezzo')

    if codice_da_cercare == "Cod. Art.?":
        return
    if codice_da_cercare != '':
        oCell=uFindString (codice_da_cercare, oSheet)
        # ~_gotoCella(oCell[0], oCell[1])
        oDoc.CurrentController.select(oSheet.getCellRangeByPosition(oCell[0], oCell[1], 30, oCell[1]))
########################################################################
def pesca_cod(arg=None):
#~ def debug(arg=None):
    '''
    Permette di scegliere il codice per la voce di COMPUTO o VARIANTE o CONTABILITA dall'Elenco Prezzi.
    Capisce quando la voce nel libretto delle misure è già registrata o nel documento ci sono già atti contabili emessi.
    '''
    global sblocca_computo
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    if oSheet.getCellByPosition(0, lrow).CellStyle not in stili_computo + stili_contab + stili_analisi + stili_elenco:
        return
    if oSheet.Name in('Analisi di Prezzo'):
        cerca_partenza()
        cerca_in_elenco()
        _gotoSheet('Elenco Prezzi')
###

    if oSheet.Name in('CONTABILITA'):
        ### controllo che non ci siano atti registrati
        cerca_partenza()
        if partenza[2] == '#reg':
            sblocca_cont()
            if sblocca_computo == 0:
                return
            pass
        else:
            pass
        ###
###
    if oSheet.Name in('COMPUTO', 'VARIANTE'):
        if oDoc.NamedRanges.hasByName("#Lib#1") == True:
            if sblocca_computo == 0:
                if DlgSiNo("Risulta già registrato un SAL. VUOI PROCEDERE COMUQUE?",'ATTENZIONE!') ==3:
                    return
                else:
                    sblocca_computo = 1
        cerca_partenza()
    if oSheet.getCellByPosition(1, partenza[1]).String != 'Cod. Art.?':
        cerca_in_elenco()
    _gotoSheet('Elenco Prezzi')
###
    if oSheet.Name in('Elenco Prezzi'):
        try:
            lrow = Range2Cell()[1]
            codice = oSheet.getCellByPosition(0, lrow).String
            _gotoSheet(partenza[0])
            oSheet = oDoc.CurrentController.ActiveSheet
            if partenza[0] == 'Analisi di Prezzo':
                oSheet.getCellByPosition(0, partenza[1]).String = codice
                _gotoCella(3, partenza[1])
            else:
                oSheet.getCellByPosition(1, partenza[1]).String = codice
                _gotoCella(2, partenza[1]+1)
        except NameError:
            return
########################################################################
def ricicla_misure(arg=None):
    '''
    In CONTABILITA consente l'inserimento di nuove voci di misurazione
    partendo da voci già inserite in COMPUTO o VARIANTE.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name =='CONTABILITA':
        try:
            ### controllo che non ci siano atti registrati
            cerca_partenza()
            if partenza[2] == '#reg':
                sblocca_cont()
                if sblocca_computo == 0:
                    return
                pass
            else:
                pass
            ###
        except:
            pass

        lrow = Range2Cell()[1]
        if oSheet.getCellByPosition(0, lrow).CellStyle not in stili_contab + ('comp Int_colonna_R_prima',): return
        ins_voce_contab(arg = 0)
        cerca_partenza()
        _gotoSheet(conf.read(path_conf, 'Contabilità', 'ricicla_da'))

    if oSheet.Name in ('COMPUTO', 'VARIANTE'):
        lrow = Range2Cell()[1]
        sStRange = Circoscrive_Voce_Computo_Att(lrow)
        sopra = sStRange.RangeAddress.StartRow+2
        sotto = sStRange.RangeAddress.EndRow-1

        oSrc = oSheet.getCellRangeByPosition(2, sopra, 8, sotto).getRangeAddress()
        try:
            oDest = oDoc.getSheets().getByName('CONTABILITA')
        except:
            return
        oCellAddress = oDest.getCellByPosition(2, partenza[1]+1).getCellAddress()
        _gotoSheet('CONTABILITA')
        for n in range (sopra, sotto):
            copia_riga_contab(partenza[1])
        oDest.copyRange(oCellAddress, oSrc)
        
        oDest.getCellByPosition(1, partenza[1]).String = oSheet.getCellByPosition(1, sopra-1).String
        parziale_verifica()
        _gotoCella(2, partenza[1]+1)
########################################################################
def inverti_un_segno(lrow):
    '''
    Inverte il segno delle formule di quantità nel rigo di misurazione lrow.
    lrow    { int }  : riga di riferimento
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    # ~lrow = Range2Cell()[1]
    if oSheet.Name in('COMPUTO', 'VARIANTE'):
        if 'comp 1-a' in oSheet.getCellByPosition(2, lrow).CellStyle:
            if 'ROSSO' in oSheet.getCellByPosition(2, lrow).CellStyle:
                if oSheet.getCellByPosition(4, lrow).Type.value != 'EMPTY':
                    oSheet.getCellByPosition(9, lrow).Formula='=IF(PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + '))' # se VediVoce
                else:
                    oSheet.getCellByPosition(9, lrow).Formula='=IF(PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + '))'
                for x in range (2, 9):
                    oSheet.getCellByPosition(x, lrow).CellStyle = oSheet.getCellByPosition(x, lrow).CellStyle.split(' ROSSO')[0]
            else:
                if oSheet.getCellByPosition(4, lrow).Type.value != 'EMPTY':
                    oSheet.getCellByPosition(9, lrow).Formula = '=IF(PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";-PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + '))' # se VediVoce
                else:
                    oSheet.getCellByPosition(9, lrow).Formula = '=IF(PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";-PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + '))'
                for x in range (2, 9):
                    oSheet.getCellByPosition(x, lrow).CellStyle = oSheet.getCellByPosition(x, lrow).CellStyle + ' ROSSO'
    if oSheet.Name in('CONTABILITA'):
        if 'comp 1-a' in oSheet.getCellByPosition(2, lrow).CellStyle:
            formula1 = oSheet.getCellByPosition(9, lrow).Formula
            formula2 = oSheet.getCellByPosition(11, lrow).Formula
            oSheet.getCellByPosition(11, lrow).Formula = formula1
            oSheet.getCellByPosition(9, lrow).Formula = formula2
            if oSheet.getCellByPosition(11, lrow).Value > 0:
                for x in range (2, 12):
                    oSheet.getCellByPosition(x, lrow).CellStyle = oSheet.getCellByPosition(x, lrow).CellStyle + ' ROSSO'
            else:
                for x in range (2, 12):
                    oSheet.getCellByPosition(x, lrow).CellStyle = oSheet.getCellByPosition(x, lrow).CellStyle.split(' ROSSO')[0]
########################################################################
def inverti_segno(arg=None):
    '''
    Inverte il segno delle formule di quantità nei righi di misurazione selezionati.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lista = list()
    try:
        oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
    except AttributeError:
        oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
    el_y = list()
    try:
        len(oRangeAddress)
        for el in oRangeAddress:
            el_y.append((el.StartRow, el.EndRow))
    except TypeError:
        el_y.append ((oRangeAddress.StartRow, oRangeAddress.EndRow))
    for y in el_y:
        for el in range (y[0], y[1]+1):
            lista.append(el)
    # ~for lrow in lista:
        # ~inverti_segno_core(lrow)
    # ~return
    if oSheet.Name in('COMPUTO', 'VARIANTE'):
        for lrow in lista:
            if 'comp 1-a' in oSheet.getCellByPosition(2, lrow).CellStyle:
                if 'ROSSO' in oSheet.getCellByPosition(2, lrow).CellStyle:

                    if oSheet.getCellByPosition(4, lrow).Type.value != 'EMPTY':
                        oSheet.getCellByPosition(9, lrow).Formula='=IF(PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + '))' # se VediVoce
                    else:
                        oSheet.getCellByPosition(9, lrow).Formula='=IF(PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + '))'
                    for x in range (2, 9):
                        oSheet.getCellByPosition(x, lrow).CellStyle = oSheet.getCellByPosition(x, lrow).CellStyle.split(' ROSSO')[0]
                else:
                    if oSheet.getCellByPosition(4, lrow).Type.value != 'EMPTY':
                        oSheet.getCellByPosition(9, lrow).Formula = '=IF(PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";-PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + '))' # se VediVoce
                    else:
                        oSheet.getCellByPosition(9, lrow).Formula = '=IF(PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";-PRODUCT(F' + str(lrow+1) + ':I' + str(lrow+1) + '))'
                    for x in range (2, 9):
                        oSheet.getCellByPosition(x, lrow).CellStyle = oSheet.getCellByPosition(x, lrow).CellStyle + ' ROSSO'
    if oSheet.Name in('CONTABILITA'):
        for lrow in lista:
            if 'comp 1-a' in oSheet.getCellByPosition(2, lrow).CellStyle:
                formula1 = oSheet.getCellByPosition(9, lrow).Formula
                formula2 = oSheet.getCellByPosition(11, lrow).Formula
                oSheet.getCellByPosition(11, lrow).Formula = formula1
                oSheet.getCellByPosition(9, lrow).Formula = formula2
                if oSheet.getCellByPosition(11, lrow).Value > 0:
                    for x in range (2, 12):
                        oSheet.getCellByPosition(x, lrow).CellStyle = oSheet.getCellByPosition(x, lrow).CellStyle + ' ROSSO'
                else:
                    for x in range (2, 12):
                        oSheet.getCellByPosition(x, lrow).CellStyle = oSheet.getCellByPosition(x, lrow).CellStyle.split(' ROSSO')[0]
########################################################################
def valuta_cella(oCell):
    '''
    Estrae qualsiasi valore da una cella, restituendo una strigna, indipendentemente dal tipo originario.
    oCell       { object }  : cella da validare
    '''
    if oCell.Type.value == 'FORMULA':
        if re.search('[a-zA-Z]', oCell.Formula):
            valore = str(oCell.Value)
        else:
            valore = oCell.Formula.split('=')[-1]
    elif oCell.Type.value == 'VALUE':
        valore = str(oCell.Value)
    elif oCell.Type.value == 'TEXT':
        valore = str(oCell.String)
    elif oCell.Type.value == 'EMPTY':
        valore = ''
    if valore == ' ': valore = ''
    return valore
########################################################################
def dettaglio_misura_rigo(arg=None):
# ~def debug(arg=None):
    '''
    Indica il dettaglio delle misure nel rigo di descrizione quando
    incontra delle formule nei valori immessi.
    bit { integer }  : 1 inserisce i dettagli
                       0 cancella i dettagli
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    if ' >(' in oSheet.getCellByPosition(2, lrow).String:
        oSheet.getCellByPosition(2, lrow).String = oSheet.getCellByPosition(2, lrow).String.split(' >(')[0]
    if oSheet.getCellByPosition(2, lrow).CellStyle in ('comp 1-a') and "*** VOCE AZZERATA ***" not in oSheet.getCellByPosition(2, lrow).String:
        for el in range(5, 9):
            if oSheet.getCellByPosition(el, lrow).Type.value == 'FORMULA':
                stringa =''
                break
            else:
                stringa = None

        if stringa == '':
            for el in range(5, 9):
                test = '>('
                if oSheet.getCellByPosition(el, lrow).Type.value == 'FORMULA':
                    if '$' not in oSheet.getCellByPosition(el, lrow).Formula:
                        try:
                            eval(oSheet.getCellByPosition(el, lrow).Formula.split('=')[1].replace('^','**'))
                            # ~eval(oSheet.getCellByPosition(el, lrow).Formula.split('=')[1])
                            stringa = stringa + '(' + oSheet.getCellByPosition(el, lrow).Formula.split('=')[-1] + ')*'
                        except:
                            stringa = stringa + '(' + oSheet.getCellByPosition(el, lrow).String.split('=')[-1] + ')*'
                            pass
                else:
                    stringa = stringa + '*' + str(oSheet.getCellByPosition(el, lrow).String) + '*'
            while '**' in stringa:
                stringa=stringa.replace('**','*')
            if stringa[0] == '*':
                stringa = stringa[1:-1]
            else:
                stringa = stringa[0:-1]
            stringa = ' >(' + stringa + ')'
            if oSheet.getCellByPosition(2, lrow).Type.value != 'FORMULA':
                oSheet.getCellByPosition(2, lrow).String = oSheet.getCellByPosition(2, lrow).String + stringa.replace('.',',')
########################################################################
def dettaglio_misure(bit):
    '''
    Indica il dettaglio delle misure nel rigo di descrizione quando
    incontra delle formule nei valori immessi.
    bit { integer }  : 1 inserisce i dettagli
                       0 cancella i dettagli
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    try:
        oSheet = oDoc.CurrentController.ActiveSheet
    except:
        return
    ER = getLastUsedCell(oSheet).EndRow
    if bit == 1:
        for lrow in range(0, ER):
            if oSheet.getCellByPosition(2, lrow).CellStyle in ('comp 1-a') and "*** VOCE AZZERATA ***" not in oSheet.getCellByPosition(2, lrow).String:
                for el in range(5, 9):
                    if oSheet.getCellByPosition(el, lrow).Type.value == 'FORMULA':
                        stringa =''
                        break
                    else:
                        stringa = None
                if stringa == '':
                    for el in range(5, 9):
                        test = '>('
                        if oSheet.getCellByPosition(el, lrow).Type.value == 'FORMULA':
                            if '$' not in oSheet.getCellByPosition(el, lrow).Formula:
                                try:
                                    eval(oSheet.getCellByPosition(el, lrow).Formula.split('=')[1].replace('^','**'))
                                    # ~eval(oSheet.getCellByPosition(el, lrow).Formula.split('=')[1])
                                    stringa = stringa + '(' + oSheet.getCellByPosition(el, lrow).Formula.split('=')[-1] + ')*'
                                except:
                                    stringa = stringa + '(' + oSheet.getCellByPosition(el, lrow).String.split('=')[-1] + ')*'
                                    pass
                        else:
                            stringa = stringa + '*' + str(oSheet.getCellByPosition(el, lrow).String) + '*'
                    while '**' in stringa:
                        stringa=stringa.replace('**','*')
                    if stringa[0] == '*':
                        stringa = stringa[1:-1]
                    else:
                        stringa = stringa[0:-1]
                    stringa = ' >(' + stringa + ')'
                    if oSheet.getCellByPosition(2, lrow).Type.value != 'FORMULA':
                        oSheet.getCellByPosition(2, lrow).String = oSheet.getCellByPosition(2, lrow).String + stringa.replace('.',',')
    else:
        for lrow in range(0, ER):
            if ' >(' in oSheet.getCellByPosition(2, lrow).String:
                oSheet.getCellByPosition(2, lrow).String = oSheet.getCellByPosition(2, lrow).String.split(' >(')[0]
    return
########################################################################
def debug_validation(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    #~ mri(oDoc.CurrentSelection.Validation)
    
    oSheet.getCellRangeByName('L1').String = 'Ricicla da:'
    oSheet.getCellRangeByName('L1').CellStyle = 'Reg_prog'
    oCell= oSheet.getCellRangeByName('N1')
    if oCell.String not in("COMPUTO", "VARIANTE", 'Scegli origine'):
        oCell.CellStyle = 'Menu_sfondo _input_grasBig'
        valida_cella(oCell, '"COMPUTO";"VARIANTE"',titoloInput='Scegli...', msgInput='COMPUTO o VARIANTE', err=True)
        oCell.String ='Scegli...'
    
def valida_cella(oCell, lista_val, titoloInput='', msgInput='', err= False ):
    '''
    Validità lista valori
    Imposta un elenco di valori a cascata, da cui scegliere.
    oCell       { object }  : cella da validare
    lista_val   { string }  : lista dei valori in questa forma: '"UNO";"DUE";"TRE"'
    titoloInput { string }  : titolo del suggerimento che compare passando il cursore sulla cella
    msgInput    { string }  : suggerimento che compare passando il cursore sulla cella
    err         { boolean } : permette di abilitare il messaggio di errore per input non validi
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet

    oTabVal = oCell.getPropertyValue("Validation")
    oTabVal.setPropertyValue('ConditionOperator', 1)

    oTabVal.setPropertyValue("ShowInputMessage", True) 
    oTabVal.setPropertyValue("InputTitle", titoloInput)
    oTabVal.setPropertyValue("InputMessage", msgInput) 
    oTabVal.setPropertyValue("ErrorMessage", "ERRORE: Questo valore non è consentito.")
    oTabVal.setPropertyValue("ShowErrorMessage", err)
    oTabVal.ErrorAlertStyle = uno.Enum("com.sun.star.sheet.ValidationAlertStyle", "STOP")
    oTabVal.Type = uno.Enum("com.sun.star.sheet.ValidationType", "LIST")
    oTabVal.Operator = uno.Enum("com.sun.star.sheet.ConditionOperator", "EQUAL")
    oTabVal.setFormula1(lista_val)
    oCell.setPropertyValue("Validation", oTabVal)

def debug_ConditionalFormat(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oCell= oDoc.CurrentSelection
    oSheet = oDoc.CurrentController.ActiveSheet

    i =oCell.RangeAddress.StartRow
    n =oCell.Rows.Count
    oSheet.getRows().removeByIndex(i, n)
########################################################################
def debugclip(arg=None):
    import pyperclip
    #~ mri(XSCRIPTCONTEXT.getComponentContext())
    sText = 'sticazzi'
    #create SystemClipboard instance
    oClip = createUnoService("com.sun.star.datatransfer.clipboard.SystemClipboard")
    oClipContents = oClip.getContents()
    flavors = oClipContents.getTransferDataFlavors()
    mri(oClip)
    #~ for i in flavors:
        #~ aDataFlavor = flavors(i)
        #~ chi(aDataFlavor)
        
    return
    #~ createUnoService =(XSCRIPTCONTEXT.getComponentContext().getServiceManager().createInstance)
    #~ oTR = createUnoListener("Tr_", "com.sun.star.datatransfer.XTransferable")
    oClip.setContents( oTR, None )
    sTxtCString = sText
    oClip.flushClipboard()
########################################################################
def rimuovi_area_di_stampa (arg=None):
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    dispatchHelper.executeDispatch(oFrame, ".uno:DeletePrintArea", "", 0, list())
########################################################################
def visualizza_PageBreak (arg=None):
    '''

    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    oProp = PropertyValue()
    oProp.Name = 'PagebreakMode'
    oProp.Value = True
    properties =(oProp,)

    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    dispatchHelper.executeDispatch(oFrame, ".uno:PagebreakMode", "", 0, properties)
########################################################################
def delete (arg=None):
    '''
    Elimina righe o colonne.
    arg       { string }  : 'R' per righe
                            'C' per colonne
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    oProp = PropertyValue()
    oProp.Name = 'Flags'
    oProp.Value = arg
    properties =(oProp,)

    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    dispatchHelper.executeDispatch(oFrame, ".uno:DeleteCell", "", 0, properties)
########################################################################
def copy_clip(arg=None):
    #~ oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()

    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    dispatchHelper.executeDispatch(oFrame, ".uno:Copy", "", 0, list())
########################################################################
def paste_clip(arg=None, insCells = 0):
    oDoc = XSCRIPTCONTEXT.getDocument()
    #~ oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    oProp = []
    oProp0 = PropertyValue()
    oProp0.Name = 'Flags'
    oProp0.Value = 'A'
    oProp1 = PropertyValue()
    oProp1.Name = 'FormulaCommand'
    oProp1.Value = 0
    oProp2 = PropertyValue()
    oProp2.Name = 'SkipEmptyCells'
    oProp2.Value = False
    oProp3 = PropertyValue()
    oProp3.Name = 'Transpose'
    oProp3.Value = False
    oProp4 = PropertyValue()
    oProp4.Name = 'AsLink'
    oProp4.Value = False
    oProp.append(oProp0)
    oProp.append(oProp1)
    oProp.append(oProp2)
    oProp.append(oProp3)
    oProp.append(oProp4)
    # insert mode ON
    if insCells == 1:
        oProp5 = PropertyValue()
        oProp5.Name = 'MoveMode'
        oProp5.Value = 0
        oProp.append(oProp5)
    properties = tuple(oProp)

    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    dispatchHelper.executeDispatch(oFrame, '.uno:InsertContents', '', 0, properties)
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
########################################################################
def paste_format(arg=None):
    '''
    Incolla solo il formato cella
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    oProp = []
    oProp0 = PropertyValue()
    oProp0.Name = 'Flags'
    oProp0.Value = 'T'
    oProp1 = PropertyValue()
    oProp1.Name = 'FormulaCommand'
    oProp1.Value = 0
    oProp2 = PropertyValue()
    oProp2.Name = 'SkipEmptyCells'
    oProp2.Value = False
    oProp3 = PropertyValue()
    oProp3.Name = 'Transpose'
    oProp3.Value = False
    oProp4 = PropertyValue()
    oProp4.Name = 'AsLink'
    oProp4.Value = False
    oProp.append(oProp0)
    oProp.append(oProp1)
    oProp.append(oProp2)
    oProp.append(oProp3)
    oProp.append(oProp4)
    properties = tuple(oProp)
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    dispatchHelper.executeDispatch(oFrame, '.uno:InsertContents', '', 0, properties)
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
########################################################################
def copia_celle_visibili(arg=None):
    '''
    A partire dalla selezione di un range di celle in cui alcune righe e/o
    colonne sono nascoste, mette in clipboard solo il contenuto delle celle
    visibili.
    Liberamente ispirato a "Copy only visible cells" http://bit.ly/2j3bfq2
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    try:
        oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
    except AttributeError:
        oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
    IS = oRangeAddress.Sheet
    SC = oRangeAddress.StartColumn
    EC = oRangeAddress.EndColumn
    SR = oRangeAddress.StartRow
    ER = oRangeAddress.EndRow
    if EC == 1023:
        EC = getLastUsedCell(oSheet).EndColumn
    if ER == 1048575:
        ER = getLastUsedCell(oSheet).EndRow
    righe = list()
    colonne = list()
    i = 0
    for nRow in range(SR, ER+1):
        if oSheet.getCellByPosition(SR, nRow).Rows.IsVisible == False:
            righe.append(i)
        i += 1
    i = 0
    for nCol in range(SC, EC+1):
        if oSheet.getCellByPosition(nCol, nRow).Columns.IsVisible == False:
            colonne.append(i)
        i += 1

    if oDoc.getSheets().hasByName('tmp_clip') == False:
        sheet = oDoc.createInstance("com.sun.star.sheet.Spreadsheet")
        tmp = oDoc.Sheets.insertByName('tmp_clip', sheet)
    tmp = oDoc.getSheets().getByName('tmp_clip')    

    oCellAddress = tmp.getCellByPosition(0,0).getCellAddress()
    tmp.copyRange(oCellAddress, oRangeAddress)
    
    for i in reversed(righe):
        tmp.getRows().removeByIndex(i, 1)
    for i in reversed(colonne):
        tmp.getColumns().removeByIndex(i, 1)

    oRange = tmp.getCellRangeByPosition(0,0, EC-SC-len(colonne), ER-SR-len(righe))
    oDoc.CurrentController.select(oRange)

    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    dispatchHelper.executeDispatch(oFrame, ".uno:Copy", "", 0, list())
    oDoc.Sheets.removeByName('tmp_clip')
    oDoc.CurrentController.setActiveSheet(oSheet)
    oDoc.CurrentController.select(oSheet.getCellRangeByPosition(SC, SR, EC, ER))
# Range2Cell ###########################################################
def Range2Cell(arg=None):
    '''
    Restituisce la tupla (IDcolonna, IDriga, NameSheet) della posizione corrente
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    try:
        if oDoc.getCurrentSelection().getRangeAddresses()[0]:
            nRow = oDoc.getCurrentSelection().getRangeAddresses()[0].StartRow
            nCol = oDoc.getCurrentSelection().getRangeAddresses()[0].StartColumn
    except AttributeError:
        nRow = oDoc.getCurrentSelection().getRangeAddress().StartRow
        nCol = oDoc.getCurrentSelection().getRangeAddress().StartColumn
    return(nCol, nRow, oSheet.Name)
########################################################################
# restituisce l'ID dell'ultima riga usata
def getLastUsedCell(oSheet):
    '''
    Restitusce l'indirizzo dell'ultima cella usata
    in forma di oggetto
    '''
    oCell = oSheet.getCellByPosition(0, 0)
    oCursor = oSheet.createCursorByRange(oCell)
    oCursor.gotoEndOfUsedArea(True)
    aAddress = oCursor.RangeAddress
    return aAddress#.EndColumn, aAddress.EndRow)
########################################################################
# numera le voci di computo o contabilità
def numera_voci(bit=1):#
    '''
    bit { integer }  : 1 rinumera tutto
                       0 rinumera dalla voce corrente in giù
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lastRow = getLastUsedCell(oSheet).EndRow+1
    lrow = Range2Cell()[1]
    n = 1
    
    if bit==0:
        for x in reversed(range(0, lrow)):
            if oSheet.getCellByPosition(1,x).CellStyle in('comp Art-EP', 'comp Art-EP_R') and oSheet.getCellByPosition(1,x).CellBackColor != 15066597:
                n = oSheet.getCellByPosition(0,x).Value +1
                break
        for row in range(lrow,lastRow):
            if oSheet.getCellByPosition(1,row).CellBackColor == 15066597:
                oSheet.getCellByPosition(0,row).String = ''
            elif oSheet.getCellByPosition(1,row).CellStyle in('comp Art-EP', 'comp Art-EP_R'):
                oSheet.getCellByPosition(0,row).Value = n
                n +=1
    if bit==1:
        for row in range(0,lastRow):
            # ~if oSheet.getCellByPosition(1,row).CellBackColor == 15066597:
                # ~oSheet.getCellByPosition(0,row).String = ''
            # ~elif oSheet.getCellByPosition(1,row).CellStyle in('comp Art-EP', 'comp Art-EP_R'):
                # ~oSheet.getCellByPosition(0,row).Value = n
                # ~n = n+1
            if oSheet.getCellByPosition(1,row).CellStyle in('comp Art-EP', 'comp Art-EP_R'):
                oSheet.getCellByPosition(0,row).Value = n
                n = n+1
            # ~oSheet.getCellByPosition(0,row).Value = n
            # ~n = n+1
########################################################################
def refresh(arg=1):
    '''
    Abilita / disabilita il refresh per accelerare le procedure
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    if arg == 0:
        #~ oDoc.CurrentController.ZoomValue = 400
        oDoc.enableAutomaticCalculation(False) # blocco il calcolo automatico
        #~ oDoc.addActionLock()
        #~ oDoc.removeActionLock()
        #~ oDoc.lockControllers #disattiva l'eco a schermo
    elif arg == 1:
        #~ oDoc.CurrentController.ZoomValue = 100
        oDoc.enableAutomaticCalculation(True) # sblocco il calcolo automatico
        #~ oDoc.removeActionLock()
        #~ oDoc.unlockControllers #attiva l'eco a schermo
########################################################################
def richiesta_offerta(arg=None):
#~ def debug(arg=None):
    '''Crea la Lista Lavorazioni e Forniture dall'Elenco Prezzi,
per la formulazione dell'offerta'''
    chiudi_dialoghi()
    oDoc = XSCRIPTCONTEXT.getDocument()
    _gotoSheet('Elenco Prezzi')
    genera_sommario()
    oSheet = oDoc.CurrentController.ActiveSheet
    try:
        oDoc.Sheets.copyByName(oSheet.Name,'Elenco Prezzi', 5)
    except:
        pass
    nSheet = oDoc.getSheets().getByIndex(5).Name
    _gotoSheet(nSheet)
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet.Name = 'Richiesta offerta'
    setTabColor(10079487)
    oSheet = oDoc.CurrentController.ActiveSheet
    fine = getLastUsedCell(oSheet).EndRow+1
    oRange = oSheet.getCellRangeByPosition (12,3,12, fine)
    aSaveData = oRange.getDataArray()
    oRange = oSheet.getCellRangeByPosition (3,3,3, fine)
    oRange.CellStyle = 'EP statistiche_q'
    oRange.setDataArray(aSaveData)
    oSheet.getCellByPosition(3 , 2).String = 'Quantità\na Computo'
    oSheet.getCellByPosition(5 , 2).String = 'Prezzo Unitario\nin lettere'
    oSheet.getCellByPosition(6 , 2).String = 'Importo'
    oSheet.Columns.removeByIndex(7, 100)
    oSheet.getColumns().getByName("D").IsVisible = True
    oSheet.getColumns().getByName("F").IsVisible = True
    oSheet.getColumns().getByName("G").IsVisible = True
    oSheet.getColumns().getByName("A").Columns.Width = 1600
    oSheet.getColumns().getByName("B").Columns.Width = 8000
    oSheet.getColumns().getByName("C").Columns.Width = 1200
    oSheet.getColumns().getByName("D").Columns.Width = 1600
    oSheet.getColumns().getByName("E").Columns.Width = 1500
    oSheet.getColumns().getByName("F").Columns.Width = 4000
    oSheet.getColumns().getByName("G").Columns.Width = 1800
    oDoc.CurrentController.freezeAtPosition(0, 1)
    
    formule = list()
    for x in range(3,getLastUsedCell(oSheet).EndRow-1):
        formule.append(['=IF(E' + str(x+1) + '<>"";D' + str(x+1) + '*E' + str(x+1) + ';""'])
    oSheet.getCellRangeByPosition (6,3,6,len(formule)+2).CellBackColor = 15757935
    oRange = oSheet.getCellRangeByPosition (6,3,6,len(formule)+2)
    formule = tuple(formule)
    oRange.setFormulaArray(formule)

    oSheet.getCellRangeByPosition(5, 3, 5, fine).clearContents(VALUE + DATETIME + STRING +
                                          ANNOTATION + FORMULA + HARDATTR +
                                          OBJECTS + EDITATTR + FORMATTED)
    
    oSheet.getCellRangeByPosition(4, 3, 4, fine+1).clearContents(VALUE + FORMULA + STRING) #cancella prezzi unitari
    oSheet.getCellRangeByPosition(0, fine-1, 100, fine+1).clearContents(VALUE + FORMULA + STRING)
    oSheet.Columns.insertByIndex(0, 1)

    oSrc = oSheet.getCellRangeByPosition(1,0,1, fine).RangeAddress
    oDest = oSheet.getCellByPosition(0,0).CellAddress
    oSheet.copyRange(oDest, oSrc)
    oSheet.getCellByPosition(0,2).String="N."
    for x in range(3, fine-1):
        oSheet.getCellByPosition(0,x).Value = x-2
    oSheet.getCellRangeByPosition(0, 1, 0, fine).CellStyle="EP-aS"
    for y in (2, 3):
        for x in range(3, fine-1):
            if oSheet.getCellByPosition(y,x).Type.value == 'FORMULA':
                oSheet.getCellByPosition(y,x).String = oSheet.getCellByPosition(y,x).String
    for x in range(3, fine-1):
        if oSheet.getCellByPosition(5,x).Type.value == 'FORMULA':
            oSheet.getCellByPosition(5,x).Value = oSheet.getCellByPosition(5,x).Value
    oSheet.getColumns().getByName("A").Columns.Width = 650

    oSheet.getCellByPosition(7,fine).Formula="=SUBTOTAL(9;H2:H"+ str(fine+1) +")"
    oSheet.getCellByPosition(2,fine).String="TOTALE COMPUTO"
    oSheet.getCellRangeByPosition(0,fine,7,fine).CellStyle="Comp TOTALI"
    oSheet.Rows.removeByIndex(fine-1, 1)
    oSheet.Rows.removeByIndex(0, 2)
    oSheet.getCellByPosition(2,fine+3).String="(diconsi euro - in lettere)"
    oSheet.getCellRangeByPosition (2,fine+3,6,fine+3).CellStyle="List-intest_med_c"
    oSheet.getCellByPosition(2,fine+5).String="Pari a Ribasso del ___________%"
    oSheet.getCellByPosition(2,fine+8).String="(ribasso in lettere)"
    oSheet.getCellRangeByPosition (2,fine+8,6,fine+8).CellStyle="List-intest_med_c"
    # INSERISCI LA DATA E L'OFFERENTE
    oSheet.getCellByPosition(2, fine+10).Formula = '=CONCATENATE("Data, ";TEXT(NOW();"GG/MM/AAAA"))'
    oSheet.getCellRangeByPosition (2,fine+10,2,fine+10).CellStyle = "Ultimus"
    oSheet.getCellByPosition(2, fine+12).String = "L'OFFERENTE"
    oSheet.getCellByPosition(2, fine+12).CellStyle = 'centro_grassetto'
    oSheet.getCellByPosition(2, fine+13).String= '(timbro e firma)'
    oSheet.getCellByPosition(2, fine+13).CellStyle = 'centro_corsivo'
    
    # CONSOLIDA LA DATA    
    oRange = oSheet.getCellRangeByPosition (2,fine+10,2,fine+10)
    #~ Flags = com.sun.star.sheet.CellFlags.FORMULA
    aSaveData = oRange.getDataArray()
    oRange.setDataArray(aSaveData)
    oSheet.getCellRangeByPosition(0, 0, getLastUsedCell(oSheet).EndColumn, getLastUsedCell(oSheet).EndRow).CellBackColor = -1
# imposta stile pagina ed intestazioni
    oSheet.PageStyle = 'PageStyle_COMPUTO_A4'
    pagestyle = oDoc.StyleFamilies.getByName('PageStyles').getByName('PageStyle_COMPUTO_A4')
    pagestyle.HeaderIsOn =  True
    left = pagestyle.RightPageHeaderContent.LeftText.Text
    
    pagestyle.HeaderIsOn= True
    oHContent=pagestyle.RightPageHeaderContent
    filename = '' #uno.fileUrlToSystemPath(oDoc.getURL())
    if len(filename) > 50:
        filename = filename[:20] + ' ... ' + filename[-20:]
    oHContent.LeftText.String = filename
    oHContent.CenterText.String=''
    oHContent.RightText.String = tempo = ''.join(''.join(''.join(str(datetime.now()).split('.')[0].split(' ')).split('-')).split(':'))
    adatta_altezza_riga(nSheet)
    pagestyle.RightPageHeaderContent=oHContent
    _gotoCella(0, 1)
    return
########################################################################
def ins_voce_elenco(arg=None):
    '''
    Inserisce una nuova riga voce in Elenco Prezzi
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    refresh(0) 
    oSheet = oDoc.CurrentController.ActiveSheet
    _gotoCella(0,3)
    oSheet.getRows().insertByIndex(3,1)
    
    oSheet.getCellByPosition(0, 3).CellStyle = "EP-aS"
    oSheet.getCellByPosition(1, 3).CellStyle = "EP-a"
    oSheet.getCellRangeByPosition(2, 3, 7, 3).CellStyle = "EP-mezzo"
    oSheet.getCellRangeByPosition(8, 3, 9, 3).CellStyle = "EP-sfondo"
    for el in(5, 11, 15, 19, 26):
        oSheet.getCellByPosition(el, 3).CellStyle = "EP-mezzo %"

    for el in(12, 16, 20, 21):#(12, 16, 20):
        oSheet.getCellByPosition(el, 3).CellStyle = 'EP statistiche_q'

    for el in(13, 17, 23, 24, 25):#(12, 16, 20):
        oSheet.getCellByPosition(el, 3).CellStyle = 'EP statistiche'

    oSheet.getCellRangeByPosition(0, 3, 26, 3).clearContents(HARDATTR)
    oSheet.getCellByPosition(11, 3).Formula = '=IF(ISERROR(N4/$N$2);"--";N4/$N$2)'
    #~ oSheet.getCellByPosition(11, 3).Formula = '=N4/$N$2'
    oSheet.getCellByPosition(12, 3).Formula = '=SUMIF(AA;A4;BB)'
    oSheet.getCellByPosition(13, 3).Formula = '=SUMIF(AA;A4;cEuro)'

    #copio le formule dalla riga sotto
    oRangeAddress = oSheet.getCellRangeByPosition(15, 4, 26, 4).getRangeAddress()
    oCellAddress = oSheet.getCellByPosition(15,3).getCellAddress()
    oSheet.copyRange(oCellAddress, oRangeAddress)
    oCell = oSheet.getCellByPosition(2, 3)
    valida_cella(oCell, '"cad";"corpo";"dm";"dm²";"dm³";"kg";"lt";"m";"m²";"m³";"q";"t";"',titoloInput='Scegli...', msgInput='Unità di misura')
    refresh(1)
########################################################################
# nuova_voce ###########################################################
def ins_voce_computo_grezza(lrow):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    #lrow = Range2Cell()[1]
########################################################################
# questo sistema eviterebbe l'uso della sheet S5 da cui copiare i range campione
# potrei svuotare la S5 ma allungando di molto il codice per la generazione della voce
# per ora lascio perdere

    #~ insRows(lrow,4) #inserisco le righe
    #~ oSheet.getCellByPosition(0,lrow).CellStyle = 'Comp Start Attributo'
    #~ oSheet.getCellRangeByPosition(0,lrow,30,lrow).CellStyle = 'Comp-Bianche sopra'
    #~ oSheet.getCellByPosition(2,lrow).CellStyle = 'Comp-Bianche sopraS'
    #~
    #~ oSheet.getCellByPosition(0,lrow+1).CellStyle = 'comp progress'
    #~ oSheet.getCellByPosition(1,lrow+1).CellStyle = 'comp Art-EP'
    #~ oSheet.getCellRangeByPosition(2,lrow+1,8,lrow+1).CellStyle = 'Comp-Bianche in mezzo Descr'
    #~ oSheet.getCellRangeByPosition(2,lrow+1,8,lrow+1).merge(True)
########################################################################
## vado alla vecchia maniera ## copio il range di righe computo da S5 ##
    oSheetto = oDoc.getSheets().getByName('S5')
    #~ oRangeAddress = oSheetto.getCellRangeByName('$A$9:$AR$12').getRangeAddress()
    oRangeAddress = oSheetto.getCellRangeByPosition(0, 8, 42, 11).getRangeAddress()
    oCellAddress = oSheet.getCellByPosition(0,lrow).getCellAddress()
    oSheet.getRows().insertByIndex(lrow, 4)#~ insRows(lrow,4) #inserisco le righe
    oSheet.copyRange(oCellAddress, oRangeAddress)
########################################################################
    #~ sformula = '=IF(LEN(VLOOKUP(B' + str(lrow+2) + ';elenco_prezzi;2;FALSE()))<($S1.$H$337+$S1.H338);VLOOKUP(B' + str(lrow+2) + ';elenco_prezzi;2;FALSE());CONCATENATE(LEFT(VLOOKUP(B' + str(lrow+2) + ';elenco_prezzi;2;FALSE());$S1.$H$337);" [...] ";RIGHT(VLOOKUP(B' + str(lrow+2) + ';elenco_prezzi;2;FALSE());$S1.$H$338)))'
    #~ oSheet.getCellByPosition(2, lrow+1).Formula = sformula
########################################################################
# raggruppo i righi di mirura
    iSheet = oSheet.RangeAddress.Sheet
    oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
    oCellRangeAddr.Sheet = iSheet
    oCellRangeAddr.StartColumn = 0
    oCellRangeAddr.EndColumn = 0
    oCellRangeAddr.StartRow = lrow+2
    oCellRangeAddr.EndRow = lrow+2
    oSheet.group(oCellRangeAddr, 1)
########################################################################
# correggo alcune formule
    oSheet.getCellByPosition(13,lrow+3).Formula ='=J'+str(lrow+4)
    oSheet.getCellByPosition(35,lrow+3).Formula ='=B'+str(lrow+2)

    if oSheet.getCellByPosition(31, lrow-1).CellStyle in('livello2 valuta', 'Livello-0-scritta', 'Livello-1-scritta', 'compTagRiservato'):
        oSheet.getCellByPosition(31, lrow+3).Value = oSheet.getCellByPosition(31, lrow-1).Value
        oSheet.getCellByPosition(32, lrow+3).Value = oSheet.getCellByPosition(32, lrow-1).Value
        oSheet.getCellByPosition(33, lrow+3).Value = oSheet.getCellByPosition(33, lrow-1).Value
########################################################################
    _gotoCella(1,lrow+1)
########################################################################
# ins_voce_computo #####################################################
def ins_voce_computo(arg=None): #TROPPO LENTA
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    if oSheet.getCellByPosition(0, lrow).CellStyle in(noVoce + stili_computo):
        lrow = next_voice(lrow, 1)
    else:
        return
    ins_voce_computo_grezza(lrow)
    numera_voci(0)
    if conf.read(path_conf, 'Generale', 'pesca_auto') == '1':
        pesca_cod()
########################################################################
def rigenera_voce(lrow=None):
    '''
    Ripristina/ricalcola le formule di descrizione e somma di una voce.
    in CPMPUTO e VARIANTE
    '''
    lrow = Range2Cell()[1]
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    sStRange = Circoscrive_Voce_Computo_Att(lrow)
    sopra = sStRange.RangeAddress.StartRow
    sotto = sStRange.RangeAddress.EndRow
    for r in range(sopra+2, sotto):
        if 'comp 1-a' in (oSheet.getCellByPosition(2, r).CellStyle) and oSheet.getCellByPosition(9, r).Type.value != 'FORMULA':
            if oSheet.Name in('COMPUTO', 'VARIANTE'):
                if oSheet.getCellByPosition(4, r).Type.value != 'EMPTY':
                    oSheet.getCellByPosition(9, r).Formula = '=IF(PRODUCT(E' + str(r+1) + ':I' + str(r+1) + ')=0;"";PRODUCT(E' + str(r+1) + ':I' + str(r+1) + '))'
                else:
                    oSheet.getCellByPosition(9, r).Formula = '=IF(PRODUCT(F' + str(r+1) + ':I' + str(r+1) + ')=0;"";PRODUCT(F' + str(r+1) + ':I' + str(r+1) + '))'
            if oSheet.Name in('CONTABILITA'):
                pass #in questo caso la formula dei negativi deve essere condizionata da uno specifico stile di cella (ROSSO)
    oSheet.getCellByPosition(2, sopra+1).Formula = '=IF(LEN(VLOOKUP(B'+ str(sopra+2) + ';elenco_prezzi;2;FALSE()))<($S1.$H$337+$S1.$H$338);VLOOKUP(B'+ str(sopra+2) + ';elenco_prezzi;2;FALSE());CONCATENATE(LEFT(VLOOKUP(B'+ str(sopra+2) + ';elenco_prezzi;2;FALSE());$S1.$H$337);" [...] ";RIGHT(VLOOKUP(B'+ str(sopra+2) + ';elenco_prezzi;2;FALSE());$S1.$H$338)))'
    oSheet.getCellByPosition(8, sotto).Formula = '=CONCATENATE("SOMMANO [";VLOOKUP(B'+ str(sopra+2) + ';elenco_prezzi;3;FALSE());"]")'
    oSheet.getCellByPosition(9, sotto).Formula = '=SUBTOTAL(9;J'+ str(sopra+2) + ':J'+ str(sotto+1) + ')'
    oSheet.getCellByPosition(11, sotto).Formula = '=VLOOKUP(B'+ str(sopra+2) + ';elenco_prezzi;5;FALSE())'
    oSheet.getCellByPosition(13, sotto).Formula = '=J'+ str(sotto+1)
    oSheet.getCellByPosition(17, sotto).Formula = '=AB'+ str(sotto+1) +'*J'+ str(sotto+1)
    #~ oSheet.getCellByPosition(18, sotto).Formula = '=J'+ str(sotto+1) +'*L'+ str(sotto+1)
    oSheet.getCellByPosition(18, sotto).Formula = '=IF(VLOOKUP(B' + str(sopra+2) + ';elenco_prezzi;3;FALSE())="%";J'+ str(sotto+1) +'*L'+ str(sotto+1) +'/100;J'+ str(sotto+1) +'*L'+ str(sotto+1) +')'
    oSheet.getCellByPosition(27, sotto).Formula = '=VLOOKUP(B'+ str(sopra+2) + ';elenco_prezzi;4;FALSE())'
    oSheet.getCellByPosition(28, sotto).Formula = '=S'+ str(sotto+1) +'-AE'+ str(sotto+1)
    oSheet.getCellByPosition(29, sotto).Formula = '=VLOOKUP(B'+ str(sopra+2) + ';elenco_prezzi;6;FALSE())'
    oSheet.getCellByPosition(30, sotto).Formula = '=IF(AD'+ str(sotto+1) +'<>""; PRODUCT(AD'+ str(sotto+1) +'*S'+ str(sotto+1) +'))'
    oSheet.getCellByPosition(35, sotto).Formula = '=B'+ str(sopra+2)
    oSheet.getCellByPosition(36, sotto).Formula = '=IF(ISERROR(S'+ str(sotto+1) +');"";IF(S'+ str(sotto+1) +'<>"";S'+ str(sotto+1) +';""))'
########################################################################
def rigenera_tutte(arg=None,):
    '''
    Ripristina le formule in tutto il foglio
    '''
    chiudi_dialoghi()
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    refresh(0)
    zoom = oDoc.CurrentController.ZoomValue
    oDoc.CurrentController.ZoomValue = 400
    nome = oSheet.Name
    #~ oDialogo_attesa = dlg_attesa('Rigenerazione delle formule in ' + oSheet.Name + '...')
    #~ attesa().start() #mostra il dialogo
    # ~oDoc.CurrentController.select(oSheet.getCellRangeByPosition(0, 0, 30, 0))
    if nome in ('COMPUTO', 'VARIANTE'):
        try:
            oSheet = oDoc.Sheets.getByName(nome)
            row = next_voice(0, 1)
            last = ultima_voce(oSheet)
            while row < last:
                oDoc.CurrentController.select(oSheet.getCellRangeByPosition(0, row, 30, row))
                rigenera_voce(row)
                row = next_voice(row, 1)
            Rinumera_TUTTI_Capitoli2()
        except:
            pass
    oDoc.CurrentController.ZoomValue = zoom
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    #~ oDialogo_attesa.endExecute()
    refresh(1)
    return
########################################################################
# leeno.conf  ##########################################################
def leeno_conf(arg=None):
    '''
    Visualizza il menù di configurazione
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    if not oDoc.getSheets().hasByName('S1'):
        for bar in GetmyToolBarNames:
            toolbar_on(bar, 0)
        return
    psm = uno.getComponentContext().ServiceManager
    dp = psm.createInstance("com.sun.star.awt.DialogProvider")
    oDlg_config = dp.createDialog("vnd.sun.star.script:UltimusFree2.Dlg_config?language=Basic&location=application")
    oDialog1Model = oDlg_config.Model

    oSheets = list(oDoc.getSheets().getElementNames())
    # ~for nome in ('M1', 'S1', 'S2', 'S4', 'S5', 'Elenco Prezzi', 'COMPUTO'):
    for nome in ('M1', 'S1', 'S2', 'S5', 'Elenco Prezzi', 'COMPUTO'):
        oSheets.remove(nome)
    for nome in oSheets:
        oSheet = oDoc.getSheets().getByName(nome)
        if oSheet.IsVisible == False:
            oDlg_config.getControl('CheckBox2').State = 0
            test = 0
            break
        else:
            oDlg_config.getControl('CheckBox2').State = 1
            test = 1
    if oDoc.getSheets().getByName("copyright_LeenO").IsVisible == True: oDlg_config.getControl('CheckBox2').State = 1
    if conf.read(path_conf, 'Generale', 'pesca_auto') == '1': oDlg_config.getControl('CheckBox1').State = 1 #pesca codice automatico
    if conf.read(path_conf, 'Generale', 'toolbar_contestuali') == '1': oDlg_config.getControl('CheckBox6').State = 1
    
    oSheet = oDoc.getSheets().getByName('S5')
    # descrizione_in_una_colonna
    if oSheet.getCellRangeByName('C9').IsMerged == False:
        oDlg_config.getControl('CheckBox5').State = 1
    else:
        oDlg_config.getControl('CheckBox5').State = 0
    
    #~ if conf.read(path_conf, 'Generale', 'descrizione_in_una_colonna') == '1': oDlg_config.getControl('CheckBox5').State = 1
    
    sString = oDlg_config.getControl('TextField1')
    sString.Text = conf.read(path_conf, 'Generale', 'altezza_celle')

    #~ sString = oDlg_config.getControl("ComboBox1")
    #~ sString.Text = conf.read(path_conf, 'Generale', 'visualizza') #visualizza all'avvio
    
    sString = oDlg_config.getControl("ComboBox2") #spostamento ad INVIO
    if conf.read(path_conf, 'Generale', 'movedirection')== '1':
        sString.Text = 'A DESTRA' 
    elif conf.read(path_conf, 'Generale', 'movedirection')== '0':
        sString.Text = 'IN BASSO' 
    oSheet = oDoc.getSheets().getByName('S1')
    
    # fullscreen
    oLayout = oDoc.CurrentController.getFrame().LayoutManager
    if oLayout.isElementVisible('private:resource/toolbar/standardbar') == False:
        oDlg_config.getControl('CheckBox3').State = 1
    
    sString = oDlg_config.getControl('TextField14')
    sString.Text =oSheet.getCellRangeByName('S1.H334').String #vedi_voce_breve
    sString = oDlg_config.getControl('TextField4')
    sString.Text =oSheet.getCellRangeByName('S1.H335').String #cont_inizio_voci_abbreviate
    if oDoc.NamedRanges.hasByName("#Lib#1") == True:
        sString.setEnable(False)
    sString = oDlg_config.getControl('TextField12')
    sString.Text =oSheet.getCellRangeByName('S1.H336').String #cont_fine_voci_abbreviate
    if oDoc.NamedRanges.hasByName("#Lib#1") == True:
        sString.setEnable(False)

    if conf.read(path_conf, 'Generale', 'torna_a_ep') == '1': oDlg_config.getControl('CheckBox8').State = 1

    # Contabilità abilita
    if oSheet.getCellRangeByName('S1.H328').Value == 1: oDlg_config.getControl('CheckBox7').State = 1
    sString = oDlg_config.getControl('TextField13')
    if conf.read(path_conf, 'Contabilità', 'idxsal') == '&273.Dlg_config.TextField13.Text':
        sString.Text = '20'
    else:
        sString.Text = conf.read(path_conf, 'Contabilità', 'idxsal')
        if sString.Text == '':
            sString.Text = '20'
    sString = oDlg_config.getControl('ComboBox3')
    sString.Text = conf.read(path_conf, 'Contabilità', 'ricicla_da')
    
    sString = oDlg_config.getControl('ComboBox4')
    sString.Text = conf.read(path_conf, 'Generale', 'copie_backup')
    sString = oDlg_config.getControl('TextField5')
    sString.Text = conf.read(path_conf, 'Generale', 'pausa_backup')

### MOSTRA IL DIALOGO
    oDlg_config.execute()

    if oDlg_config.getControl('CheckBox2').State != test:
        if oDlg_config.getControl('CheckBox2').State == 1:
            show_sheets(True)
        else:
            show_sheets(False)

    if oDlg_config.getControl('CheckBox3').State == 1:
        toolbar_switch(0)
    else:
        toolbar_switch(1)
 
    #~ conf.write(path_conf, 'Generale', 'visualizza', oDlg_config.getControl('ComboBox1').getText())
    
    ctx = XSCRIPTCONTEXT.getComponentContext()
    oGSheetSettings = ctx.ServiceManager.createInstanceWithContext("com.sun.star.sheet.GlobalSheetSettings", ctx)
    if oDlg_config.getControl('ComboBox2').getText() == 'IN BASSO':
        conf.write(path_conf, 'Generale', 'movedirection', '0')
        oGSheetSettings.MoveDirection = 0
    else:
        conf.write(path_conf, 'Generale', 'movedirection', '1')
        oGSheetSettings.MoveDirection = 1
    conf.write(path_conf, 'Generale', 'altezza_celle', oDlg_config.getControl('TextField1').getText())
  
    conf.write(path_conf, 'Generale', 'pesca_auto', str(oDlg_config.getControl('CheckBox1').State))
    conf.write(path_conf, 'Generale', 'descrizione_in_una_colonna', str(oDlg_config.getControl('CheckBox5').State))
    conf.write(path_conf, 'Generale', 'toolbar_contestuali', str(oDlg_config.getControl('CheckBox6').State))
    toolbar_vedi()
    if oDlg_config.getControl('CheckBox5').State == 1:
        descrizione_in_una_colonna(False)
    else:
        descrizione_in_una_colonna(True)
    conf.write(path_conf, 'Generale', 'torna_a_ep', str(oDlg_config.getControl('CheckBox8').State)) #torna su prezzario
    
#il salvataggio anche su leeno.conf serve alla funzione voce_breve()

    if oDlg_config.getControl('TextField14').getText() != '10000': conf.write(path_conf, 'Generale', 'vedi_voce_breve', oDlg_config.getControl('TextField14').getText())
    oSheet.getCellRangeByName('S1.H334').Value = float(oDlg_config.getControl('TextField14').getText())

    if oDlg_config.getControl('TextField4').getText() != '10000': conf.write(path_conf, 'Contabilità', 'cont_inizio_voci_abbreviate', oDlg_config.getControl('TextField4').getText())
    oSheet.getCellRangeByName('S1.H335').Value = float(oDlg_config.getControl('TextField4').getText())

    if oDlg_config.getControl('TextField12').getText() != '10000': conf.write(path_conf, 'Contabilità', 'cont_fine_voci_abbreviate', oDlg_config.getControl('TextField12').getText())
    oSheet.getCellRangeByName('S1.H336').Value = float(oDlg_config.getControl('TextField12').getText())
    adatta_altezza_riga()

    conf.write(path_conf, 'Contabilità', 'abilita', str(oDlg_config.getControl('CheckBox7').State))
    conf.write(path_conf, 'Contabilità', 'idxsal', oDlg_config.getControl('TextField13').getText())
    if oDlg_config.getControl('ComboBox3').getText() in ('COMPUTO', '&305.Dlg_config.ComboBox3.Text'):
        conf.write(path_conf, 'Contabilità', 'ricicla_da', 'COMPUTO')
    else:
        conf.write(path_conf, 'Contabilità', 'ricicla_da', 'VARIANTE')
    conf.write(path_conf, 'Generale', 'copie_backup', oDlg_config.getControl('ComboBox4').getText())
    conf.write(path_conf, 'Generale', 'pausa_backup', oDlg_config.getControl('TextField5').getText())
    autorun()
########################################################################
#percorso di ricerca di leeno.conf
if sys.platform == 'win32':
    path_conf = os.getenv("APPDATA") + '/.config/leeno/leeno.conf'
else:
    path_conf = os.getenv("HOME") + '/.config/leeno/leeno.conf'
class conf:
    '''
    path    { string }: indirizzo del file di configurazione
    section { string }: sezione
    option  { string }: opzione
    value   { string }: valore
    '''
    def __init__(self, path=path_conf):
        #~ config = configparser.SafeConfigParser()
        #~ config.read(path) 
        #~ self.path = path
        pass
    def write(path, section, option, value):
        """
        Scrive i dati nel file di configurazione.
        http://www.programcreek.com/python/example/1033/ConfigParser.SafeConfigParser
        Write the specified Section.Option to the config file specified by path.
        Replace any previous value.  If the path doesn't exist, create it.
        Also add the option the the in-memory config.
        """
        config = configparser.SafeConfigParser()
        config.read(path)

        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, value)
        
        fp = open(path, 'w')
        config.write(fp)
        fp.close()
        
    def read(path, section, option):
        '''
        https://pymotw.com/2/ConfigParser/
        Legge i dati dal file di configurazione.
        '''
        config = configparser.SafeConfigParser()
        config.read(path)
        return config.get(section, option)
        
    def diz(path):
        '''
        Legge tutto il file di configurazione e restituisce un dizionario.
        '''
        my_config_parser_dict = {s:dict(config.items(s)) for s in config.sections()}
        return my_config_parser_dict
    
def config_default(arg=None):
    '''
    Imposta i parametri di default in leeno.conf
    '''
    parametri = (
    ('Zoom', 'fattore', '100'),
    ('Zoom', 'fattore_ottimale', '81'),
    ('Zoom', 'fullscreen', '0'),
    ('Generale', 'dialogo', '1'),
    #~ ('Generale', 'visualizza', 'Menù Principale'),
    ('Generale', 'altezza_celle', '1.25'),
    ('Generale', 'pesca_auto', '1'),
    ('Generale', 'movedirection', '1'),
    ('Generale', 'descrizione_in_una_colonna', '0'),
    ('Generale', 'toolbar_contestuali', '1'),
    ('Generale', 'vedi_voce_breve', '50'),
    ('Generale', 'dettaglio', '1'),
    ('Generale', 'torna_a_ep', '1'),
    ('Generale', 'copie_backup', '5'),
    ('Generale', 'pausa_backup', '15'),
    
    #~ ('Computo', 'riga_bianca_categorie', '1'),
    #~ ('Computo', 'voci_senza_numerazione', '0'),
    ('Computo', 'inizio_voci_abbreviate', '100'),
    ('Computo', 'fine_voci_abbreviate', '120'),
    ('Contabilità', 'cont_inizio_voci_abbreviate', '100'),
    ('Contabilità', 'cont_fine_voci_abbreviate', '120'),
    ('Contabilità', 'abilita', '0'),
    ('Contabilità', 'idxsal', '20'),
    ('Contabilità', 'ricicla_da', 'COMPUTO')
    )
    for el in parametri:
        try:
            conf.read(path_conf, el[0], el[1])
        except:
            conf.write(path_conf, el[0], el[1], el[2])
########################################################################
def nuova_voce_scelta(arg=None): #assegnato a ctrl-shift-n
    '''
    Contestualizza in ogni tabella l'inserimento delle voci.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name in('COMPUTO', 'VARIANTE'):
        ins_voce_computo()
    elif oSheet.Name =='Analisi di Prezzo':
        inizializza_analisi()
    elif oSheet.Name =='CONTABILITA':
        ins_voce_contab()
    elif oSheet.Name =='Elenco Prezzi':
        ins_voce_elenco()
    
# nuova_voce_contab  ##################################################
def ins_voce_contab(lrow=0, arg=1):
    '''
    Inserisce una nuova voce in CONTABILITA.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if lrow == 0:
        lrow = Range2Cell()[1]
    nome = oSheet.Name
    try:
        ### controllo che non ci siano atti registrati
        cerca_partenza()
        if partenza[2] == '#reg':
            sblocca_cont()
            if sblocca_computo == 0:
                return
            pass
        else:
            pass
        ###
    except:
        pass
    stile = oSheet.getCellByPosition( 0, lrow).CellStyle
    nSal = 0
    if stile == 'comp Int_colonna_R_prima':
        lrow += 1
    elif stile =='Ultimus_centro_bordi_lati':
        i = lrow
        while i != 0:
            if oSheet.getCellByPosition(23, i).Value != 0:
                nSal = int(oSheet.getCellByPosition(23, i).Value)
                break
            i -= 1
        while oSheet.getCellByPosition( 0, lrow).CellStyle == stile:
            lrow += 1
        if oSheet.getCellByPosition( 0, lrow).CellStyle == 'uuuuu':
            lrow += 1
            #~ nSal += 1
        #~ else
    elif stile == 'Comp TOTALI':
        pass
    elif stile in stili_contab:
        sStRange = Circoscrive_Voce_Computo_Att(lrow)
        nSal = int(oSheet.getCellByPosition(23, sStRange.RangeAddress.StartRow + 1).Value)
        lrow = next_voice(lrow)
    else:
        return
    oSheetto = oDoc.getSheets().getByName('S5')
    oRangeAddress = oSheetto.getCellRangeByPosition(0, 22, 48, 26).getRangeAddress()
    oCellAddress = oSheet.getCellByPosition(0,lrow).getCellAddress()
    oSheet.getRows().insertByIndex(lrow, 5) #inserisco le righe
    oSheet.copyRange(oCellAddress, oRangeAddress)
    oSheet.getCellRangeByPosition(0, lrow, 48, lrow+5).Rows.OptimalHeight = True
    _gotoCella(1, lrow+1)

    #~ if(oSheet.getCellByPosition(0,lrow).queryIntersection(oSheet.getCellRangeByName('#Lib#'+str(nSal)).getRangeAddress())):
        #~ chi('appartiene')
    #~ else:
        #~ chi('nooooo')
    #~ return

    sStRange = Circoscrive_Voce_Computo_Att(lrow)
    sopra = sStRange.RangeAddress.StartRow
    for n in reversed(range(0, sopra)):
        if oSheet.getCellByPosition(1, n).CellStyle == 'Ultimus_centro_bordi_lati':
            break
        if oSheet.getCellByPosition(1, n).CellStyle == 'Data_bianca':
            data = oSheet.getCellByPosition(1, n).Value
            break
    try:
        oSheet.getCellByPosition(1, sopra+2).Value = data
    except:
        oSheet.getCellByPosition(1, sopra+2).Value = date.today().toordinal()-693594
########################################################################
    #~ sformula = '=IF(LEN(VLOOKUP(B' + str(lrow+2) + ';elenco_prezzi;2;FALSE()))<($S1.$H$337+$S1.H338);VLOOKUP(B' + str(lrow+2) + ';elenco_prezzi;2;FALSE());CONCATENATE(LEFT(VLOOKUP(B' + str(lrow+2) + ';elenco_prezzi;2;FALSE());$S1.$H$337);" [...] ";RIGHT(VLOOKUP(B' + str(lrow+2) + ';elenco_prezzi;2;FALSE());$S1.$H$338)))'
    #~ oSheet.getCellByPosition(2, lrow+1).Formula = sformula
########################################################################
# raggruppo i righi di mirura
    iSheet = oSheet.RangeAddress.Sheet
    oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
    oCellRangeAddr.Sheet = iSheet
    oCellRangeAddr.StartColumn = 0
    oCellRangeAddr.EndColumn = 0
    oCellRangeAddr.StartRow = lrow+2
    oCellRangeAddr.EndRow = lrow+2
    oSheet.group(oCellRangeAddr, 1)
########################################################################

    if oDoc.NamedRanges.hasByName('#Lib#'+str(nSal)):
        if lrow -1 == oSheet.getCellRangeByName('#Lib#'+str(nSal)).getRangeAddress().EndRow:
            nSal += 1
    
    oSheet.getCellByPosition(23, sopra + 1).Value = nSal
    oSheet.getCellByPosition(23, sopra + 1).CellStyle = 'Sal'
    
    oSheet.getCellByPosition(35, sopra+4).Formula = '=B'+ str(sopra+2)
    oSheet.getCellByPosition(36, sopra+4).Formula = '=IF(ISERROR(P'+ str(sopra +5) +');"";IF(P' + str(sopra+5) +'<>"";P' + str(sopra +5) + ';""))'
    oSheet.getCellByPosition(36, sopra+4).CellStyle = "comp -controolo"
    numera_voci(0)
    if conf.read(path_conf, 'Generale', 'pesca_auto') == '1':
        if arg == 0 : return
        pesca_cod()
########################################################################
# CONTABILITA ## CONTABILITA ## CONTABILITA ## CONTABILITA ## CONTABILITA #
def attiva_contabilita(arg=None):
    '''Se presenti, attiva e visualizza le tabelle di contabilità'''
    chiudi_dialoghi()
    oDoc = XSCRIPTCONTEXT.getDocument()
    if oDoc.Sheets.hasByName('S1'):
        oDoc.Sheets.getByName('S1').getCellByPosition(7,327).Value = 1
        if oDoc.Sheets.hasByName('CONTABILITA'):
            for el in('Registro', 'SAL','CONTABILITA'):
                if oDoc.Sheets.hasByName(el):_gotoSheet(el)
        else:
            oDoc.Sheets.insertNewByName('CONTABILITA',4)
            _gotoSheet('CONTABILITA')
            svuota_contabilita()
            ins_voce_contab()
            #~ set_larghezza_colonne()
        _gotoSheet('CONTABILITA')
########################################################################
def svuota_contabilita(arg=None):
    '''Ricrea il foglio di contabilità partendo da zero.'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    for n in range(1 ,20):
        if oDoc.NamedRanges.hasByName('#Lib#'+str(n)) == True:
            oDoc.NamedRanges.removeByName('#Lib#'+str(n))
            oDoc.NamedRanges.removeByName('#SAL#'+str(n))
            oDoc.NamedRanges.removeByName('#Reg#'+str(n))
    for el in('Registro', 'SAL', 'CONTABILITA'):
        if oDoc.Sheets.hasByName(el):
            oDoc.Sheets.removeByName(el)
    
    oDoc.Sheets.insertNewByName('CONTABILITA',3)
    oSheet = oDoc.Sheets.getByName('CONTABILITA')

    _gotoSheet('CONTABILITA')
    setTabColor(16757935)
    oSheet.getCellRangeByName('C1').String = 'CONTABILITA'
    oSheet.getCellRangeByName('C1').CellStyle = 'comp Int_colonna'
    oSheet.getCellRangeByName('C1').CellBackColor = 16757935
    oSheet.getCellByPosition(0,2).String = 'N.'
    oSheet.getCellByPosition(1,2).String = 'Articolo\nData'
    oSheet.getCellByPosition(2,2).String = 'LAVORAZIONI\nO PROVVISTE'
    oSheet.getCellByPosition(5,2).String = 'P.U.\nCoeff.'
    oSheet.getCellByPosition(6,2).String = 'Lung.'
    oSheet.getCellByPosition(7,2).String = 'Larg.'
    oSheet.getCellByPosition(8,2).String = 'Alt.\nPeso'
    oSheet.getCellByPosition(9,2).String = 'Quantità\nPositive'
    oSheet.getCellByPosition(11,2).String = 'Quantità\nNegative'
    oSheet.getCellByPosition(13,2).String = 'Prezzo\nunitario'
    oSheet.getCellByPosition(15,2).String = 'Importi'
    oSheet.getCellByPosition(17,2).String = 'Sicurezza\ninclusa'
    oSheet.getCellByPosition(18,2).String = 'Serve per avere le quantità\nrealizzate "pulite" e sommabili'
    oSheet.getCellByPosition(19,2).String = 'Lib.\nN.'
    oSheet.getCellByPosition(20,2).String = 'Lib.\nP.'
    oSheet.getCellByPosition(22,2).String = 'flag'
    oSheet.getCellByPosition(23,2).String = 'SAL\nN.'
    oSheet.getCellByPosition(25,2).String = 'Importi\nSAL parziali'
    oSheet.getCellByPosition(27,2).String = 'Sicurezza\nunitaria'
    oSheet.getCellByPosition(28,2).String = 'Materiali\ne Noli €'
    oSheet.getCellByPosition(29,2).String = 'Incidenza\nMdO %'
    oSheet.getCellByPosition(30,2).String = 'Importo\nMdO'
    oSheet.getCellByPosition(31,2).String = 'Super Cat'
    oSheet.getCellByPosition(32,2).String = 'Cat'
    oSheet.getCellByPosition(33,2).String = 'Sub Cat'
    #~ oSheet.getCellByPosition(34,2).String = 'tag B'sub Scrivi_header_moduli
    #~ oSheet.getCellByPosition(35,2).String = 'tag C'
    oSheet.getCellByPosition(36,2).String = 'Importi\nsenza errori'
    oSheet.getCellByPosition(0,2).Rows.Height = 800
    #~ colore colonne riga di intestazione
    oSheet.getCellRangeByPosition(0, 2, 36 , 2).CellStyle = 'comp Int_colonna_R'
    oSheet.getCellByPosition(0, 2).CellStyle = 'comp Int_colonna_R_prima'
    oSheet.getCellByPosition(18, 2).CellStyle = 'COnt_noP'
    oSheet.getCellRangeByPosition(0,0,0,3).Rows.OptimalHeight = True
    #~ riga di controllo importo
    oSheet.getCellRangeByPosition(0, 1, 36 , 1).CellStyle = 'comp In testa'
    oSheet.getCellByPosition(2,1).String = 'QUESTA RIGA NON VIENE STAMPATA'
    oSheet.getCellRangeByPosition(0, 1, 1, 1).merge(True)
    oSheet.getCellByPosition(13,1).String = 'TOTALE:'
    oSheet.getCellByPosition(20,1).String = 'SAL SUCCESSIVO:'

    oSheet.getCellByPosition(25, 1).Formula = '=$P$2-SUBTOTAL(9;$P$2:$P$2)'

    oSheet.getCellByPosition(15,1).Formula='=SUBTOTAL(9;P3:P4)' #importo lavori
    oSheet.getCellByPosition(0,1).Formula='=AK2' #importo lavori
    oSheet.getCellByPosition(17,1).Formula='=SUBTOTAL(9;R3:R4)' #importo sicurezza
    
    oSheet.getCellByPosition(28,1).Formula='=SUBTOTAL(9;AC3:AC4)' #importo materiali
    oSheet.getCellByPosition(29,1).Formula='=AE2/Z2'  #Incidenza manodopera %
    oSheet.getCellByPosition(29, 1).CellStyle = 'Comp TOTALI %'
    oSheet.getCellByPosition(30,1).Formula='=SUBTOTAL(9;AE3:AE4)' #importo manodopera
    oSheet.getCellByPosition(36,1).Formula='=SUBTOTAL(9;AK3:AK4)' #importo certo

    #~ rem riga del totale
    oSheet.getCellByPosition(2,3).String = 'T O T A L E'
    oSheet.getCellByPosition(15,3).Formula='=SUBTOTAL(9;P3:P4)' #importo lavori
    oSheet.getCellByPosition(17,3).Formula='=SUBTOTAL(9;R3:R4)' #importo sicurezza
    oSheet.getCellByPosition(30,3).Formula='=SUBTOTAL(9;AE3:AE4)' #importo manodopera
    oSheet.getCellRangeByPosition(0, 3, 36 , 3).CellStyle = 'Comp TOTALI'
    #~ rem riga rossa
    oSheet.getCellByPosition(0,4).String = 'Fine Computo'
    oSheet.getCellRangeByPosition(0, 4, 36 , 4).CellStyle = 'Riga_rossa_Chiudi'
    _gotoCella(0, 2)
    set_larghezza_colonne()
########################################################################
def partita (testo):
    '''
    Aggiunge/dedrae rigo di PARTITA PROVVISORIA
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name != "CONTABILITA": return
    x = Range2Cell()[1]
    if oSheet.getCellByPosition(0, x).CellStyle == 'comp 10 s_R':
        if oSheet.getCellByPosition(2, x).Type.value != 'EMPTY':
            Copia_riga_Ent()
            x +=1
        oSheet.getCellByPosition(2, x).String = testo
        oSheet.getCellRangeByPosition(2, x, 8, x).CellBackColor = 16777113
        _gotoCella(5, x)
def partita_aggiungi(arg=None):
    partita('PARTITA PROVVISORIA')
def partita_detrai(arg=None):
    partita('SI DETRAE PARTITA PROVVISORIA')

########################################################################
#~ def genera_libretto():
def debug (arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    mri(oDoc.StyleFamilies.getByName("CellStyles").getByName('comp 1-a PU'))
    return
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name != 'CONTABILITA': return
    numera_voci()
    oRanges = oDoc.NamedRanges
    nSal=1
    if oRanges.hasByName("#Lib#1") == True:
        nSal=20
    else:
        try:
            nSal = int(conf.read(path_conf, 'Contabilità', 'idxsal'))
        except ValueError:
            nSal = 20
    while nSal > 0:
        if oRanges.hasByName("#Lib#" + str(nSal)):
            break
        nSal = nSal-1
    #~ Recupero la prima riga non registrata
    oSheetCont = oDoc.Sheets.getByName('CONTABILITA')
    if nSal >= 1:
        oNamedRange = oRanges.getByName("#Lib#" + str(nSal)).ReferredCells.RangeAddress
        frow = oNamedRange.StartRow
        lrow = oNamedRange.EndRow
        daVoce = oNamedRange.EndRow+2
    #~ recupero l'ultimo numero di pagina usato (serve in caso di libretto unico)
        #~ oSheetCont = oDoc.Sheets.getByName('CONTABILITA')
        old_nPage = int(oSheetCont.getCellByPosition(20,lrow).Value)
        daVoce = int(oSheetCont.getCellByPosition(0,daVoce).Value)
        if daVoce == 0:
            MsgBox('Non ci sono voci di misurazione da registrare.','ATTENZIONE!')
            return
        oCell = oSheetCont.getCellRangeByPosition(0,frow,25,lrow)
#~ 'Raggruppa_righe
        oCell.Rows.IsVisible=False
    else:
        daVoce=1
#############
# PRIMA RIGA
    daVoce = InputBox (str(daVoce), "Registra voci Libretto da n.")
    try:
        lrow = int(uFindStringCol(daVoce, 0, oSheet))
    except TypeError:
        return
    sStRange = Circoscrive_Voce_Computo_Att (lrow)
    primariga = sStRange.RangeAddress.StartRow
#############
#  ULTIMA RIGA
    oCellRange = oSheetCont.getCellRangeByPosition(0,3,0,getLastUsedCell(oSheetCont).EndRow -2)
    aVoce = int(oCellRange.computeFunction(MAX))
    aVoce = InputBox (str(aVoce), "A voce n.:")
    try:
        lrow = int(uFindStringCol(aVoce, 0, oSheet))
    except TypeError:
        return 
    sStRange = Circoscrive_Voce_Computo_Att (lrow)
    ultimariga = sStRange.RangeAddress.EndRow

    lrowDown =uFindStringCol("T O T A L E", 2, oSheetCont)
    oCell = oSheetCont.getCellRangeByPosition(19,primariga,25,lrowDown)
    oDoc.CurrentController.select(oCell)
    rimuovi_area_di_stampa()
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    oSheetCont.removeAllManualPageBreaks()
    visualizza_PageBreak()

    
    #~ nomearea="#Lib#"+nsal
    #~ rem annota importo parziale SAL
#~ 'Print ultimariga & " - " & "SAL n." & nSal
    #~ oSheetCont.getCellByPosition(25, ultimariga-1).string = "SAL n." & nSal
    #~ oSheetCont.getCellByPosition(25, ultimariga).formula = "=SUBTOTAL(9;P" & primariga+1 & ":P" & ultimariga+1 & ")"
    #~ oSheetCont.getCellByPosition(25, ultimariga).cellstyle = "comp sotto Euro 3_R"
    #~ rem immetti le firme
    #~ inizioFirme = ultimariga+1
    #~ firme (ultimariga+1)' riga di inserimento
    #~ fineFirme = ultimariga+10 rem 10 è un numero deciso nella sub FIRME
#~ '    Print finefirme
    #~ rem definisci il range del #Lib#
    #~ area="$A$" & primariga+1 & ":$AJ$"&fineFirme+1
#~ 'Print area 
    #~ ScriptPy("pyleeno.py","rifa_nomearea", "CONTABILITA", area , nomearea)
    
    #~ oSheetCont.getCellRangeByPosition (0,inizioFirme,32,finefirme).CellStyle = "Ultimus_centro_bordi_lati"
    #~ oNamedRange=oRanges.getByName("#Lib#" & nSal).referredCells
#~ '    ThisComponent.CurrentController.Select(oNamedRange)
    #~ rem ----------------------------------------------------------------------
    #~ With oNamedRange.RangeAddress
        #~ daRiga = .StartRow
        #~ aRiga = .EndRow
        #~ daColonna = .StartColumn
        #~ aColonna = .EndColumn
    #~ End With
    #~ rem set area di stampa
    #~ Dim selLib(0) as new com.sun.star.table.CellRangeAddress
    #~ selLib(0).StartColumn = daColonna
    #~ selLib(0).StartRow = daRiga
    #~ selLib(0).EndColumn = 11
    #~ selLib(0).EndRow = aRiga
    #~ rem set intestazione area di stampa
    #~ oTitles = createUnoStruct("com.sun.star.table.CellRangeAddress")
    #~ oTitles.startRow = 2' headstart - 1
    #~ oTitles.EndRow = 2 'headend - 1
    #~ oTitles.startColumn = 0
    #~ oTitles.EndColumn = 11
    #~ oSheetCont.setTitleRows(oTitles)
    #~ oSheetCont.setPrintareas(selLib())
    #~ oSheetCont.setPrintTitleRows(true)
    #~ rem ----------------------------------------------------------------------
    #~ rem sbianco i dati e l'intestazione
    #~ ThisComponent.CurrentController.Select(oSheetCont.getCellRangeByPosition(0, daRiga, 11, fineFirme))
    #~ ScriptPy("pyleeno.py","adatta_altezza_riga")
    #~ Sbianca_celle
    #~ ThisComponent.CurrentController.Select(oSheetCont.getCellRangeByPosition(0, 2, 11, 2))
    #~ Sbianca_celle
    #~ ThisComponent.currentController.removeRangeSelectionListener(oRangeSelectionListener) 'deseleziona
    #~ rem ----------------------------------------------------------------------
    #~ ThisComponent.CurrentController.setFirstVisibleRow (fineFirme-3) 'solo debug
    #~ i=1
    #~ Do While oSheetCont.getCellByPosition(1,fineFirme).rows.IsStartOfNewPage = False
#~ '    oSheetCont.getCellByPosition(2 ,fineFirme).setstring("Sto sistemando il Libretto...")
        #~ insRows (fineFirme,1) 'insertByIndex non funziona
        #~ If i=3 Then
            #~ oSheetCont.getCellByPosition(2, fineFirme).setstring("====================")
            #~ daqui=fineFirme
        #~ End If 
        #~ fineFirme = fineFirme+1
        #~ i=i+1
    #~ Loop
    #~ oSheetCont.rows.removeByIndex (fineFirme-1, 1)
    
    #~ rem ----------------------------------------------------------------------
    #~ rem cancella l'ultima riga
    #~ fineFirme = fineFirme-1
    #~ If daqui<>0 then
        #~ ThisComponent.CurrentController.Select(oSheetCont.getCellByPosition(2, daqui))
        #~ copy_clip
        #~ ThisComponent.CurrentController.Select(oSheetCont.getCellRangeByPosition(2, daqui, 2, finefirme-1))
#~ 'Print finefirme-1
        #~ paste_clip
    #~ End If
    
    #~ rem ----------------------------------------------------------------------
    #~ rem definisci il range del #Lib#
    #~ area="$A$" & primariga+1 & ":$AJ$"&fineFirme+1
    #~ ScriptPy("pyleeno.py","rifa_nomearea", "CONTABILITA", area , nomearea)
    
    #~ rem raggruppo
    #~ oCell = oSheetCont.getCellRangeByPosition(0,primariga,25,finefirme)
    #~ oSheetCont.getCellRangeByPosition (0,inizioFirme,25,finefirme).CellStyle = "Ultimus_centro_bordi_lati"
    #~ oCell = oSheetCont.getCellRangeByPosition (0,finefirme,35,finefirme)
    #~ oSheetCont.getCellByPosition(2 , inizioFirme+1).CellStyle = "ULTIMUS" 'stile data
    #~ rem recupero la data
    #~ datafirma = Right (oSheetCont.getCellByPosition(2 , inizioFirme+1).value, 10)
    #~ ThisComponent.CurrentController.Select(oCell)
    #~ bordo_sotto
    #~ ThisComponent.currentController.removeRangeSelectionListener(oRangeSelectionListener)
    #~ rem ----------------------------------------------------------------------
    #~ rem QUESTA DEVE DIVENTARE UN'OPZIONE A SCELTA DELL'UTENTE
    #~ rem in caso di libretto unico questo If è da attivare
    #~ rem in modo che la numerazione delle pagine non ricominci da capo
#~ '+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#~ '        If nSal > 1 Then
#~ '            nLib = 1
#~ '            inumPag = 1 + old_nPage 'SE IL LIBRETTO è UNICO
#~ '        End If
#~ '+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #~ rem ----------------------------------------------------------------------
    #~ nLib = nSal
#~ 'End If
#~ '#########################################################################
    #~ rem COMPILO LA SITUAZIONE CONTABILE IN "S2" 1di2
    #~ oS2 = ThisComponent.Sheets.getByName("S2")
    #~ rem TROVO LA POSIZIONE DEL TITOLO
    #~ oEnd=uFindString("SITUAZIONE CONTABILE", oS2)
    #~ xS2=oEnd.RangeAddress.EndRow        'riga
    #~ yS2=oEnd.RangeAddress.EndColumn    'colonna
    
    #~ oS2.getCellByPosition(yS2+nSal,xS2+1).value = nSal 'numero sal
#~ '    Print "datafirma " & datafirma
    #~ oS2.getCellByPosition(yS2+nSal,xS2+2).value = datafirma 'data
    #~ oS2.getCellByPosition(yS2+nSal,xS2+24).value = aVoce ' ultima voce libretto
    #~ oS2.getCellByPosition(yS2+nSal,xS2+25).value = inumPag ' ultima pagina libretto
    #~ ThisComponent.currentController.removeRangeSelectionListener(oRangeSelectionListener)
#~ '#########################################################################
    
#~ 'BARRA_chiudi
    #~ Barra_Apri_Chiudi_5("                         Sto elaborando il Libetto delle Misure...", 75)
    
    #~ Dim IntPag()
    #~ IntPag() = oSheetCont.RowPageBreaks
#~ 'GoTo togo:
    #~ rem ----------------------------------------------------------------------
    #~ rem col seguente ciclo FOR inserisco i dati ma non il numero di pagina
    #~ For i = primariga to fineFirme
        #~ IF     oSheetCont.getCellByPosition( 1 , i).cellstyle = "comp Art-EP_R" then
            #~ if primariga=0 then
                #~ sStRange = Circoscrive_Voce_Computo_Att (i)
                #~ With sStRange.RangeAddress
                    #~ primariga =.StartRow
                #~ End With
            #~ end If
            #~ oSheetCont.getCellByPosition(19, i).value= nLib '1 ' numero libretto
            #~ oSheetCont.getCellByPosition(22, i).string= "#reg" ' flag registrato
            #~ oSheetCont.getCellByPosition(23, i).value= nSal ' numero SAL
            #~ oSheetCont.getCellByPosition(23, i).cellstyle = "Sal"
#~ '        else
#~ '        oSheetCont.getCellByPosition( 1 , i).Rows.Height = 500 'altezza riga
        #~ end if
    #~ Next
    #~ inumPag = 0'+ old_nPage 'SE IL LIBRETTO è UNICO
    #~ rem ----------------------------------------------------------------------
    #~ rem il ciclo For che segue è preso da https://forum.openoffice.org/it/forum/viewtopic.php?f=26&t=6014
#~ '    Dim IntPag()
#~ '    IntPag() = oSheetCont.RowPageBreaks
    #~ rem ----------------------------------------------------------------------
    #~ togo:
    #~ rem ----------------------------------------------------------------------
    #~ rem col seguente ciclo FOR inserisco solo il numero di pagina
    #~ rem inserendo qui anche il resto dei dati ho numeri di pagina un po' ballerini
    #~ For i = primariga to fineFirme
        #~ For n = LBound(IntPag) To UBound(IntPag)
            #~ if i < IntPag(n).Position Then
                #~ if oSheetCont.getCellByPosition( 1 , i).cellstyle = "comp Art-EP_R" then
                    #~ inumPag = n ' + old_nPage 'SE IL LIBRETTO è UNICO
                    #~ oSheetCont.getCellByPosition(20, i).value = inumPag 'numero Pagina
#~ '    oSheetCont.getCellByPosition(19, i).value= nLib '1 ' numero libretto
#~ '    oSheetCont.getCellByPosition(22, i).string= "#reg" ' flag registrato
#~ '    oSheetCont.getCellByPosition(23, i).value= nSal ' numero SAL
#~ '    oSheetCont.getCellByPosition(23, i).cellstyle = "Sal"
                    #~ Exit For
                #~ end If
            #~ end if
            #~ Next n
            #~ Next i
            #~ rem ----------------------------------------------------------------------
            #~ rem annoto ultimo numero di pagina 
            #~ oSheetCont.getCellByPosition(20 , fineFirme).value = UBound(IntPag)'inumPag
            #~ oSheetCont.getCellByPosition(20 , fineFirme).CellStyle = "num centro"
            #~ rem ----------------------------------------------------------------------
#~ 'fissa (0,idxrow+1)
            
            #~ ThisComponent.currentController.removeRangeSelectionListener(oRangeSelectionListener)
            #~ rem ----------------------------------------------------------------------
            #~ rem inserisco la prima riga GIALLA del LIBRETTO
            #~ oNamedRange=oRanges.getByName(nomearea).referredCells
            #~ ins = oNamedRange.RangeAddress.StartRow
            #~ insRows (ins, 1) 'insertByIndex non funziona
            #~ oSheetCont.getCellRangeByPosition (0,ins,25,ins).CellStyle = "uuuuu" '"Ultimus_Bordo_sotto"
            #~ fissa (0, ins + 1)
            #~ rem ----------------------------------------------------------------------
            #~ rem ci metto un po' di informazioni
            #~ oSheetCont.getCellByPosition(2,ins).string = "segue Libretto delle Misure n." & nSal & " - " & davoce & "÷" & avoce
            #~ oSheetCont.getCellByPosition(20,ins).value =  UBound(IntPag) 'ultimo numero pagina
            #~ oSheetCont.getCellByPosition(19, ins).value= nLib '1 ' numero libretto
            #~ oSheetCont.getCellByPosition(23, ins).value= nSal ' numero SAL
            #~ oSheetCont.getCellByPosition(25, ins).formula = "=SUBTOTAL(9;$P$" & primariga+1 & ":$P$" & ultimariga+2 & ")"
            #~ oSheetCont.getCellByPosition(25, ins).cellstyle = "comp sotto Euro 3_R"
            #~ rem ----------------------------------------------------------------------
            #~ rem annoto il sal corrente sulla riga di intestazione
            #~ ins =uFindString("LAVORAZIONI"+ chr(10) + "O PROVVISTE", oSheetCont).RangeAddress.EndRow
            #~ oSheetCont.getCellByPosition(25,ins).value = nSal
            #~ oSheetCont.getCellByPosition(25, ins).cellstyle = "Menu_sfondo _input_grasBig"
#~ '    oSheetCont.getCellByPosition(25, ins-1).formula = "=SUBTOTAL(9;$P$" & primariga+1 & ":$P$" & ultimariga+2 & ")"
            #~ oSheetCont.getCellByPosition(25, ins-1).formula = "=$P$2-SUBTOTAL(9;$P$" & IdxRow & ":$P$" & ultimariga+2 & ")"
            #~ rem ----------------------------------------------------------------------
            #~ rem fisso la riga alla prima voce
            #~ For i= 2 To 100
                #~ If oSheetCont.getCellByPosition(1,i).CellStyle = "Comp-Bianche sopra_R" Then
                    #~ Exit For
                    #~ EndIf
                    
                #~ Next
#~ 'fissa (0,idxRow)
                #~ ThisComponent.CurrentController().freezeAtPosition(0,idxRow+1)
                #~ Ripristina_statusLine 'Barra_chiudi_sempre_4
                #~ Protezione_area ("CONTABILITA",nomearea)
                #~ Struttura_Contab ("#Lib#")
                #~ RiDefinisci_Area_Elenco_prezzi ' non capisco come mai l'area di elenco_prezzi viene cambiata
                #~ Genera_REGISTRO
            #~ end Sub

########################################################################
def genera_atti_contabili(arg=None):
# ~def debug(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name != "CONTABILITA": return
    if DlgSiNo('''Prima di procedere è consigliabile salvare il lavoro.
Puoi continuare, ma a tuo rischio!
Se decidi di continuare, devi attendere il messaggio di procedura completata senza interferire con mouse e/o tastiera.
Procedo senza salvare?''', 'Avviso') == 3:
        return
    else:
        #~ genera_libretto()
        MsgBox('''La generazione degli allegati contabili è stata completata.
Grazie per l'attesa.''','Voci registrate!')


# FINE_CONTABILITA ## FINE_CONTABILITA ## FINE_CONTABILITA ## FINE_CONTABILITA
########################################################################
def inizializza_elenco(arg=None):
    '''
    Riscrive le intestazioni di colonna e le formule dei totali in Elenco Prezzi.
    '''
    chiudi_dialoghi()
    refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.Sheets.getByName('Elenco Prezzi')
    
    zoom = oDoc.CurrentController.ZoomValue
    oDoc.CurrentController.ZoomValue = 400
    #~ oDialogo_attesa = dlg_attesa()
    #~ attesa().start() #mostra il dialogo
    
    struttura_off()
    oCellRangeAddr=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
    SR = oCellRangeAddr.StartRow
    ER = oCellRangeAddr.EndRow
    SC = oCellRangeAddr.StartColumn
    EC = oCellRangeAddr.EndColumn
    oSheet.getCellRangeByPosition(11, 3, EC, ER - 1).clearContents(STRING + VALUE + FORMULA)

    oDoc.CurrentController.freezeAtPosition(0, 3)
    oSheet.getCellRangeByPosition(0, 0, 100 , 0).CellStyle = "Default"
#~ riscrivo le intestazioni di colonna
    set_larghezza_colonne()
    oSheet.getCellRangeByName('L1').String ='COMPUTO'
    oSheet.getCellRangeByName('P1').String ='VARIANTE'
    oSheet.getCellRangeByName('T1').String ='CONTABILITA'
    oSheet.getCellRangeByName('B2').String ='QUESTA RIGA NON VIENE STAMPATA'
    oSheet.getCellRangeByName("'Elenco Prezzi'.A2:AA2").CellStyle = "comp In testa"
    oSheet.getCellRangeByName("'Elenco Prezzi'.AA2").CellStyle = 'EP-mezzo %'

    oSheet.getCellRangeByName("'Elenco Prezzi'.A3:AA3").CellStyle = "EP-a -Top"
    oSheet.getCellRangeByName('A3').String ='Codice\nArticolo'
    oSheet.getCellRangeByName('B3').String ='DESCRIZIONE DEI LAVORI\nE DELLE SOMMINISTRAZIONI'
    oSheet.getCellRangeByName('C3').String ='Unità\ndi misura'
    oSheet.getCellRangeByName('D3').String ='Sicurezza\ninclusa'
    oSheet.getCellRangeByName('E3').String ='Prezzo\nunitario'
    oSheet.getCellRangeByName('F3').String ='Incidenza\nMdO'
    oSheet.getCellRangeByName('G3').String ='Importo\nMdO'
    oSheet.getCellRangeByName('H3').String ='Codice di origine'
    oSheet.getCellRangeByName('L3').String ='Inc. % \nComputo'
    oSheet.getCellRangeByName('M3').String ='Quantità\nComputo'
    oSheet.getCellRangeByName('N3').String ='Importi\nComputo'
    oSheet.getCellRangeByName('L3:N3').CellBackColor = 16762855
    oSheet.getCellRangeByName('P3').String ='Inc. % \nVariante'
    oSheet.getCellRangeByName('Q3').String ='Quantità\nVariante'
    oSheet.getCellRangeByName('R3').String ='Importi\nVariante'
    oSheet.getCellRangeByName('P3:R3').CellBackColor = 16777062
    oSheet.getCellRangeByName('T3').String ='Inc. % \nContabilità'
    oSheet.getCellRangeByName('U3').String ='Quantità\nContabilità'
    oSheet.getCellRangeByName('V3').String ='Importi\nContabilità'
    oSheet.getCellRangeByName('T3:V3').CellBackColor = 16757935
    oSheet.getCellRangeByName('X3').String ='Quantità\nvariaz.'
    oSheet.getCellRangeByName('Y3').String ='IMPORTI\nin più'
    oSheet.getCellRangeByName('Z3').String ='IMPORTI\nin meno'
    oSheet.getCellRangeByName('AA3').String ='VAR. %'
    oSheet.getCellRangeByName('I1:J1').Columns.IsVisible = False

    y = uFindStringCol('Fine elenco', 0, oSheet) + 1
    oSheet.getCellRangeByName('N2').Formula='=SUBTOTAL(9;N3:N' + str(y) +')'
    oSheet.getCellRangeByName('R2').Formula='=SUBTOTAL(9;R3:R' + str(y) +')'
    oSheet.getCellRangeByName('V2').Formula='=SUBTOTAL(9;V3:V' + str(y) +')'
    oSheet.getCellRangeByName('Y2').Formula='=SUBTOTAL(9;Y3:Y' + str(y) +')'
    oSheet.getCellRangeByName('Z2').Formula='=SUBTOTAL(9;Z3:Z' + str(y) +')'
#~  riga di totale importo COMPUTO
    y -=1
    oSheet.getCellByPosition(12, y).String='TOTALE'
    oSheet.getCellByPosition(13, y).Formula='=SUBTOTAL(9;N3:N' + str(y) +')'
#~ riga di totale importo CONTABILITA'
    oSheet.getCellByPosition(16, y).String='TOTALE'
    oSheet.getCellByPosition(17, y).Formula='=SUBTOTAL(9;R3:R' + str(y) +')'
#~ rem	riga di totale importo VARIANTE
    oSheet.getCellByPosition(20, y).String='TOTALE'
    oSheet.getCellByPosition(21, y).Formula='=SUBTOTAL(9;V3:V' + str(y) +')'
#~ rem	riga di totale importo PARALLELO
    oSheet.getCellByPosition(23, y).String='TOTALE'
    oSheet.getCellByPosition(24, y).Formula='=SUBTOTAL(9;Y3:Y' + str(y) +')'
    oSheet.getCellByPosition(25, y).Formula='=SUBTOTAL(9;Z3:Z' + str(y) +')'
    oSheet.getCellRangeByPosition(10, y, 26 , y).CellStyle = 'EP statistiche_Contab'

    y +=1
    #~ oSheet.getCellRangeByName('C2').String = 'prezzi'
    #~ oSheet.getCellRangeByName('E2').Formula = '=COUNT(E3:E' + str(y) +')'
    oSheet.getCellRangeByName('K2:K' + str(y)).CellStyle = 'Default'
    oSheet.getCellRangeByName('O2:O' + str(y)).CellStyle = 'Default'
    oSheet.getCellRangeByName('S2:S' + str(y)).CellStyle = 'Default'
    oSheet.getCellRangeByName('W2:W' + str(y)).CellStyle = 'Default'
    oSheet.getCellRangeByPosition(3, 3, 250, y +10).clearContents(HARDATTR)
    #~ riga_rossa()
    #~ oDialogo_attesa.endExecute()
    oDoc.CurrentController.ZoomValue = zoom
    refresh(1)
    #~ MsgBox('Rigenerazione del foglio eseguita!','')
########################################################################
def inizializza_computo(arg=None):
    '''
    Riscrive le intestazioni di colonna e le formule dei totali in COMPUTO.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.Sheets.getByName('COMPUTO')
    oDoc.CurrentController.setActiveSheet(oSheet)
    oDoc.CurrentController.freezeAtPosition(0, 3)

    lRow = ultima_voce(oSheet)+1
    #~ arg = "cancella"
    #~ if arg == "cancella":
        #~ oSheet.Rows.removeByIndex(0, getLastUsedCell(oSheet).EndRow+1)

    if ultima_voce(oSheet) == 0:
        oRow=uFindString("TOTALI COMPUTO", oSheet)
        try:
            lRowE=oRow.CellAddress.Row
        except:
            lRowE = 3
    else:
        lRowE = lRow
    
    Flags = STRING + VALUE + FORMULA
    oSheet.getCellRangeByPosition(0, 0, 100, 2).clearContents(Flags)
    oSheet.getCellRangeByPosition(12, 0, 16, lRowE).clearContents(Flags)
    oSheet.getCellRangeByPosition(22, 0, 23, lRowE).clearContents(Flags)
    oSheet.getCellRangeByPosition(0, 0, 100 , 0).CellStyle = "Default"
    oSheet.getCellRangeByPosition(0, 0, 100 , 0).clearContents(HARDATTR)
    oSheet.getCellRangeByPosition(44, 0, 100 , lRowE+10).CellStyle = "Default"
    #~ oSheet.getCellRangeByName('C1').CellStyle = 'comp Int_colonna'
    #~ oSheet.getCellRangeByName('C1').CellBackColor = 16762855
    #~ oSheet.getCellRangeByName('C1').String = 'COMPUTO'

    oSheet.getCellByPosition(2,1).String = 'QUESTA RIGA NON VIENE STAMPATA'
    oSheet.getCellByPosition(17,1).Formula = '=SUBTOTAL(9;R3:R' + str(lRowE+1) + ')' #sicurezza
    oSheet.getCellByPosition(18,1).Formula = '=SUBTOTAL(9;S3:S' + str(lRowE+1) + ')' #importo lavori
    oSheet.getCellByPosition(0,1).Formula = '=AK2'

    oSheet.getCellByPosition(28,1).Formula= '=SUBTOTAL(9;AC3:AC' + str(lRowE+1) + ')' #importo materiali

    oSheet.getCellByPosition(29,1).Formula= '=AE2/S2'  #Incidenza manodopera %
    oSheet.getCellByPosition(29, 1).CellStyle = "Comp TOTALI %"
    oSheet.getCellByPosition(30,1).Formula= '=SUBTOTAL(9;AE3:AE' + str(lRowE+1) + ')' #importo manodopera
    oSheet.getCellByPosition(36,1).Formula= '=SUBTOTAL(9;AK3:AK' + str(lRowE+1) + ')' #totale computo sole voci senza errori

    oSheet.getCellRangeByPosition(0, 1, 43, 1).CellStyle = "comp In testa"
    oSheet.getCellRangeByPosition(0, 0, 43, 2).merge(False)
    oSheet.getCellRangeByPosition(0, 1, 1, 1).merge(True)

#~ rem riga di intestazione
    oSheet.getCellByPosition(0,2).String = 'N.'
    oSheet.getCellByPosition(1,2).String = 'Articolo\nData'
    oSheet.getCellByPosition(2,2).String = 'DESIGNAZIONE DEI LAVORI\nE DELLE SOMMINISTRAZIONI'
    oSheet.getCellByPosition(5,2).String = 'P.U.\nCoeff.'
    oSheet.getCellByPosition(6,2).String = 'Lung.'
    oSheet.getCellByPosition(7,2).String = 'Larg.'
    oSheet.getCellByPosition(8,2).String = 'Alt.\nPeso'
    oSheet.getCellByPosition(9,2).String = 'Quantità'
    oSheet.getCellByPosition(11,2).String = 'Prezzo\nunitario'
    oSheet.getCellByPosition(13,2).String = 'Serve per avere le quantità\nrealizzate "pulite" e sommabili'
    oSheet.getCellByPosition(17,2).String = 'di cui\nsicurezza'
    oSheet.getCellByPosition(18,2).String = 'Importo €'
    oSheet.getCellByPosition(24,2).String = 'Incidenza\nsul totale' # POTREBBE SERVIRE PER INDICARE L'INCIDENZA DI OGNI SINGOLA VOCE
    oSheet.getCellByPosition(27,2).String = 'Sicurezza\nunitaria'
    oSheet.getCellByPosition(28,2).String = 'Materiali\ne Noli €'
    oSheet.getCellByPosition(29,2).String = 'Incidenza\nMdO %'
    oSheet.getCellByPosition(30,2).String = 'Importo\nMdO'
    oSheet.getCellByPosition(31,2).String = 'Super Cat'
    oSheet.getCellByPosition(32,2).String = 'Cat'
    oSheet.getCellByPosition(33,2).String = 'Sub Cat'
    oSheet.getCellByPosition(34,2).String = 'tag B'
    oSheet.getCellByPosition(35,2).String = 'tag C'
    oSheet.getCellByPosition(36,2).String = 'importo totale computo\nsole voci senza errori'
    oSheet.getCellByPosition(38,2).String = 'Figure e\nannotazioni'
    oSheet.getCellByPosition(43,2).String = 'riservato per annotare\nil numero della voce'
    oSheet.getCellRangeByPosition(0, 2, 43 , 2).CellStyle = 'comp Int_colonna'
    oSheet.getCellByPosition(13,2).CellStyle = 'COnt_noP'
    oSheet.getCellByPosition(19,2).CellStyle = 'COnt_noP'
    oSheet.getCellByPosition(36,2).CellStyle = 'COnt_noP'
    oSheet.getCellByPosition(43,2).CellStyle = 'COnt_noP'
    oCell=oSheet.getCellRangeByPosition(0, 0, 43, 2)

#~ rem riga del totale
    oSheet.getCellByPosition(2,lRowE).String = "TOTALI COMPUTO"
    oSheet.getCellByPosition(17,lRowE).Formula="=SUBTOTAL(9;R3:R" + str(lRowE+1) + ")" #importo sicurezza
    oSheet.getCellByPosition(18,lRowE).Formula="=SUBTOTAL(9;S3:S" + str(lRowE+1) + ")" #importo lavori
    oSheet.getCellByPosition(29,lRowE).Formula="=AE" + str(lRowE+1) + "/S" + str(lRowE+1) + ""  #Incidenza manodopera %
    oSheet.getCellByPosition(30,lRowE).Formula="=SUBTOTAL(9;AE3:AE" + str(lRowE+1) + ")" #importo manodopera
    oSheet.getCellByPosition(36,lRowE).Formula="=SUBTOTAL(9;AK3:AK" + str(lRowE+1) + ")" #totale computo sole voci senza errori
    oSheet.getCellRangeByPosition(0, lRowE, 36 , lRowE).CellStyle = "Comp TOTALI"
    oSheet.getCellByPosition(24,lRowE).CellStyle = "Comp TOTALI %"
    oSheet.getCellByPosition(29,lRowE).CellStyle = "Comp TOTALI %"

    inserisci_Riga_rossa()

    oSheet = oDoc.Sheets.getByName('S1')
    oSheet.getCellByPosition(9, 190).Formula="=$COMPUTO.$S$2"
    oSheet = oDoc.Sheets.getByName('M1')
    oSheet.getCellByPosition(3, 0).Formula="=$COMPUTO.$S$2"
    oSheet = oDoc.Sheets.getByName('S2')
    oSheet.getCellByPosition(4, 0).Formula="=$COMPUTO.$S$2"
    set_larghezza_colonne()
    setTabColor(16762855)
########################################################################
def inizializza_analisi(arg=None):
    '''
    Se non presente, crea il foglio 'Analisi di Prezzo' ed inserisce la prima scheda
    '''
    chiudi_dialoghi()
    oDoc = XSCRIPTCONTEXT.getDocument()
    rifa_nomearea('S5', '$B$108:$P$133', 'blocco_analisi')
    if oDoc.getSheets().hasByName('Analisi di Prezzo') == False:
        oDoc.getSheets().insertNewByName('Analisi di Prezzo',1)
        oSheet = oDoc.Sheets.getByName('Analisi di Prezzo')
        oSheet.getCellRangeByPosition(0,0,15,0).CellStyle = 'Analisi_Sfondo'
        oSheet.getCellByPosition(0, 1).Value = 0
        oSheet = oDoc.Sheets.getByName('Analisi di Prezzo')
        oDoc.CurrentController.setActiveSheet(oSheet)
        setTabColor(12189608)
        oRangeAddress=oDoc.NamedRanges.blocco_analisi.ReferredCells.RangeAddress
        oCellAddress = oSheet.getCellByPosition(0, getLastUsedCell(oSheet).EndRow).getCellAddress()
        oDoc.CurrentController.select(oSheet.getCellByPosition(0,2))
        oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
        set_larghezza_colonne()
    else: 
        _gotoSheet('Analisi di Prezzo')
        oSheet = oDoc.Sheets.getByName('Analisi di Prezzo')
        oDoc.CurrentController.setActiveSheet(oSheet)
        lrow = Range2Cell()[1]
        urow = getLastUsedCell(oSheet).EndRow
        if lrow >= urow:
            lrow = ultima_voce(oSheet)-5
        for n in range(lrow ,getLastUsedCell(oSheet).EndRow):
            if oSheet.getCellByPosition(0, n).CellStyle == 'An-sfondo-basso Att End':
                break 
        oRangeAddress=oDoc.NamedRanges.blocco_analisi.ReferredCells.RangeAddress
        oSheet.getRows().insertByIndex(n+2,26)
        oCellAddress = oSheet.getCellByPosition(0,n+2).getCellAddress()
        oDoc.CurrentController.select(oSheet.getCellByPosition(0,n+2+1))
        oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    oSheet.copyRange(oCellAddress, oRangeAddress)
    inserisci_Riga_rossa()
    return
########################################################################
def inserisci_Riga_rossa(arg=None):
    '''
    Inserisce la riga rossa di chiusura degli elaborati
    Questa riga è un riferimento per varie operazioni
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    nome = oSheet.Name
    if nome in('COMPUTO', 'VARIANTE', 'CONTABILITA'):
        lrow = ultima_voce(oSheet) + 2
        for n in range(lrow, getLastUsedCell(oSheet).EndRow+2):
            if oSheet.getCellByPosition(0,n).CellStyle == 'Riga_rossa_Chiudi':
                return
        oSheet.getRows().insertByIndex(lrow,1)
        oSheet.getCellByPosition(0, lrow).String = 'Fine Computo'
        oSheet.getCellRangeByPosition(0,lrow,34,lrow).CellStyle='Riga_rossa_Chiudi'
    elif nome == 'Analisi di Prezzo':
        lrow = ultima_voce(oSheet) + 2
        oSheet.getCellByPosition( 0, lrow).String = 'Fine ANALISI'
        oSheet.getCellRangeByPosition(0,lrow,10,lrow).CellStyle='Riga_rossa_Chiudi' 
    elif nome == 'Elenco Prezzi':
        lrow = ultima_voce(oSheet) + 1
        oSheet.getCellByPosition( 0, lrow).String = 'Fine elenco'
        oSheet.getCellRangeByPosition(0,lrow,7,lrow).CellStyle='Riga_rossa_Chiudi' 
    oSheet.getCellByPosition(2, lrow).String = 'Questa riga NON deve essere cancellata, MAI!!!(ma può rimanere tranquillamente NASCOSTA!)'
########################################################################
def rifa_nomearea(sSheet, sRange, sName):
    '''
    Definisce o ridefinisce un'area di dati a cui far riferimento
    sSheet = nome del foglio, es.: 'S5'
    sRange = individuazione del range di celle, es.:'$B$89:$L$89'
    sName = nome da attribuire all'area scelta, es.: "manodopera"
    '''
    sPath = "$'" + sSheet + "'." + sRange
    oDoc = XSCRIPTCONTEXT.getDocument()
    oRanges = oDoc.NamedRanges
    oCellAddress = oDoc.Sheets.getByName(sSheet).getCellRangeByName('A1').getCellAddress()
    if oRanges.hasByName(sName):
        oRanges.removeByName(sName)
    oRanges.addNewByName(sName,sPath,oCellAddress,0)
########################################################################
def struct_colore(l):
    '''
    Mette in vista struttura secondo il colore
    l { integer } : specifica il livello di categoria
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    zoom = oDoc.CurrentController.ZoomValue
    oDoc.CurrentController.ZoomValue = 400
    oSheet = oDoc.CurrentController.ActiveSheet
    iSheet = oSheet.RangeAddress.Sheet
    oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
    oCellRangeAddr.Sheet = iSheet
    hriga = oSheet.getCellRangeByName('B4').CharHeight * 65
    #~ giallo(16777072,16777120,16777168)
    #~ verde(9502608,13696976,15794160)
    #~ viola(12632319,13684991,15790335)
    col0 = 16724787 #riga_rossa
    col1 = 16777072
    col2 = 16777120
    col3 = 16777168
# attribuisce i colori
    for y in range(3, getLastUsedCell(oSheet).EndRow):
        if oSheet.getCellByPosition(0, y).String == '':
            oSheet.getCellByPosition(0, y).CellBackColor = col3
        elif len(oSheet.getCellByPosition(0, y).String.split('.')) == 2:
            oSheet.getCellByPosition(0, y).CellBackColor = col2
        elif len(oSheet.getCellByPosition(0, y).String.split('.')) == 1:
            oSheet.getCellByPosition(0, y).CellBackColor = col1
    if l == 0:
        colore = col1
        myrange =(col1, col0)
    elif l == 1:
        colore = col2
        myrange =(col1, col2, col0)
    elif l == 2:
        colore = col3
        myrange =(col1, col2, col3, col0)
   
        for n in(3, 7):
            oCellRangeAddr.StartColumn = n
            oCellRangeAddr.EndColumn = n
            oSheet.group(oCellRangeAddr,0)
            oSheet.getCellRangeByPosition(n, 0, n, 0).Columns.IsVisible=False
    test = ultima_voce(oSheet)+2
    lista = list()
    for n in range(0, test):
        if oSheet.getCellByPosition(0, n).CellBackColor == colore:
            oSheet.getCellByPosition(0,n).Rows.Height = hriga
            sopra = n+1
            for n in range(sopra+1, test):
                if oSheet.getCellByPosition(0, n).CellBackColor in myrange:
                    sotto = n-1
                    lista.append((sopra, sotto))
                    break
    for el in lista:
        oCellRangeAddr.StartRow = el[0]
        oCellRangeAddr.EndRow = el[1]
        oSheet.group(oCellRangeAddr,1)
        oSheet.getCellRangeByPosition(0, el[0], 0, el[1]).Rows.IsVisible=False
    oDoc.CurrentController.ZoomValue = zoom
    return
########################################################################
def struttura_Elenco(arg=None):
    '''
    Dà una tonalità di colore, diverso dal colore dello stile cella, alle righe
    che non hanno il prezzo, come i titoli di capitolo e sottocapitolo.
    '''
    chiudi_dialoghi()
    if DlgSiNo('''Adesso puoi dare ai titoli di capitolo e sottocapitolo
una tonalità di colore che ne facilita la leggibilità, ma
il risultato finale dipende dalla struttura dei codici di voce.

QUESTA OPERAZIONE RICHIEDE DEL TEMPO E
LibreOffice POTREBBE SEMBRARE BLOCCATO!

Vuoi procedere con la creazione della struttura dei capitoli?''', 'Avviso') == 3:
            return
    riordina_ElencoPrezzi()
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet.clearOutline()
    struct_colore(0) #attribuisce i colori
    struct_colore(1)
    struct_colore(2)
    return
########################################################################
def XML_toscana_import(arg=None):
    '''
    Importazione di un prezzario XML della regione Toscana 
    in tabella Elenco Prezzi del template COMPUTO.
    '''
    MsgBox('Questa operazione potrebbe richiedere del tempo.','Avviso')

    try:
        filename = filedia('Scegli il file XML Toscana da importare', '*.xml')
        if filename == None: return
    except:
        return
    New_file.computo(0)
    # effettua il parsing del file XML
    tree = ElementTree()
    # ~tree.parse(filename)
    try:
        tree.parse(filename)
    except Exception as e:
        MsgBox ("Eccezione " + str(type(e)) +
                "\nMessaggio: " + str(e.args) + '\n' +
                traceback.format_exc());
        return
    root = tree.getroot()
    iter = tree.getiterator()

    PRT = '{' + str(iter[0].getchildren()[0]).split('}')[0].split('{')[-1] + '}' # xmlns
    # nome del prezzario
    intestazione = root.find(PRT+'intestazione')
    titolo = 'Prezzario '+ intestazione.get('autore') + ' - ' + intestazione[0].get('area') +' '+ intestazione[0].get('anno')
    licenza = intestazione[1].get('descrizione').split(':')[0] +' '+ intestazione[1].get('tipo')
    titolo = titolo + '\nCopyright: ' + licenza  + '\nhttp://prezzariollpp.regione.toscana.it'

    Contenuto = root.find(PRT+'Contenuto')

    voci = root.getchildren()[1]

    tipo_lista = list()
    cap_lista = list()
    lista_articoli = list()
    lista_cap = list()
    lista_subcap = list()
    for el in voci:
        if el.tag == PRT+'Articolo':
            codice = el.get('codice')
            codicesp = codice.split('.')
        
        voce = el.getchildren()[2].text
        articolo = el.getchildren()[3].text
        if articolo == None:
            desc_voce = voce
        else:
            desc_voce = voce + ' ' + articolo
        udm = el.getchildren()[4].text

        try:
            sic = float(el.getchildren()[-1][-4].get('valore'))
        except IndexError:
            sic =''
        try:
            prezzo = float(el.getchildren()[5].text)
        except:
            prezzo = float(el.getchildren()[5].text.split('.')[0]+el.getchildren()[5].text.split('.')[1]+'.'+el.getchildren()[5].text.split('.')[2])
        try:
            mdo = float(el.getchildren()[-1][-1].get('percentuale'))/100
            mdoE = mdo * prezzo
        except IndexError:
            mdo =''
            mdoE = ''
        if codicesp[0] not in tipo_lista:
            tipo_lista.append(codicesp[0])
            cap =(codicesp[0], el.getchildren()[0].text, '', '', '', '', '')
            lista_cap.append(cap)
        if codicesp[0]+'.'+codicesp[1] not in cap_lista:
            cap_lista.append(codicesp[0]+'.'+codicesp[1])
            cap =(codicesp[0]+'.'+codicesp[1], el.getchildren()[1].text, '', '', '', '', '', '')
            lista_subcap.append(cap)
        voceel =(codice, desc_voce, udm, sic, prezzo, mdo, mdoE)
        lista_articoli.append(voceel)
# compilo ##############################################################
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.getSheets().getByName('S2')
    oSheet.getCellByPosition(2, 2).String = titolo
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    oSheet.getCellByPosition(1, 0).String = titolo
    oSheet.getCellByPosition(2, 0).String = '''ATTENZIONE!
1. Lo staff di LeenO non si assume alcuna responsabilità riguardo al contenuto del prezzario.
2. L’utente finale è tenuto a verificare il contenuto dei prezzari sulla base di documenti ufficiali.
3. L’utente finale è il solo responsabile degli elaborati ottenuti con l'uso di questo prezzario.

Si consiglia una attenta lettura delle note informative disponibili sul sito istituzionale ufficiale di riferimento prima di accedere al prezzario.'''
    oSheet.getCellByPosition(1, 0).CellStyle = 'EP-mezzo'
    n = 0

    for el in (lista_articoli, lista_cap, lista_subcap):
        oSheet.getRows().insertByIndex(4, len(el))
        lista_come_array = tuple(el)
        # Parametrizzo il range di celle a seconda della dimensione della lista
        scarto_colonne = 0 # numero colonne da saltare a partire da sinistra
        scarto_righe = 4 # numero righe da saltare a partire dall'alto
        colonne_lista = len(lista_come_array[1]) # numero di colonne necessarie per ospitare i dati
        righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati
        oRange = oSheet.getCellRangeByPosition( 0, 4, colonne_lista + 0 - 1, righe_lista + 4 - 1)
        oRange.setDataArray(lista_come_array)
        #~ oSheet.getRows().removeByIndex(3, 1)
        oDoc.CurrentController.setActiveSheet(oSheet)

        oSheet.getCellRangeByPosition(0, 3, 0, righe_lista + 3 - 1).CellStyle = "EP-aS"
        oSheet.getCellRangeByPosition(1, 3, 1, righe_lista + 3 - 1).CellStyle = "EP-a"
        oSheet.getCellRangeByPosition(2, 3, 7, righe_lista + 3 - 1).CellStyle = "EP-mezzo"
        oSheet.getCellRangeByPosition(5, 3, 5, righe_lista + 3 - 1).CellStyle = "EP-mezzo %"
        oSheet.getCellRangeByPosition(8, 3, 9, righe_lista + 3 - 1).CellStyle = "EP-sfondo"
        oSheet.getCellRangeByPosition(11, 3, 11, righe_lista + 3 - 1).CellStyle = 'EP-mezzo %'
        oSheet.getCellRangeByPosition(12, 3, 12, righe_lista + 3 - 1).CellStyle = 'EP statistiche_q'
        oSheet.getCellRangeByPosition(13, 3, 13, righe_lista + 3 - 1).CellStyle = 'EP statistiche'
        if n == 1: 
            oSheet.getCellRangeByPosition(0, 3, 0, righe_lista + 3 - 1).CellBackColor = 16777120
        elif n == 2:
            oSheet.getCellRangeByPosition(0, 3, 0, righe_lista + 3 - 1).CellBackColor = 16777168
        n += 1
    #~ set_larghezza_colonne()
    toolbar_vedi()
    adatta_altezza_riga('Elenco Prezzi')
    riordina_ElencoPrezzi()
    #~ struttura_Elenco()
    
    dest = filename[0:-4]+ '.ods'
    salva_come(dest)
    MsgBox('''
Importazione eseguita con successo!

ATTENZIONE:
1. Lo staff di LeenO non si assume alcuna responsabilità riguardo al contenuto del prezzario.
2. L’utente finale è tenuto a verificare il contenuto dei prezzari sulla base di documenti ufficiali.
3. L’utente finale è il solo responsabile degli elaborati ottenuti con l'uso di questo prezzario.

N.B.: Si consiglia una attenta lettura delle note informative disponibili sul sito istituzionale ufficiale prima di accedere al Prezzario.

    ''','ATTENZIONE!')
#~ ########################################################################
def fuf(arg=None):
    '''
    Traduce un particolare formato DAT usato in falegnameria - non c'entra un tubo con LeenO.
    E' solo una cortesia per un amico.
    '''
    filename = filedia('Scegli il file XML-SIX da importare', '*.dat')
    riga = list()
    try:
        f = open(filename, 'r')
    except TypeError:
        return
    ordini = list()
    riga =('Codice', 'Descrizione articolo', 'Quantità', 'Data consegna','Conto lavoro', 'Prezzo(€)')
    ordini.append(riga)
    
    for row in f:
        art =row[:15]
        if art[0:4] not in('HEAD', 'FEET'):
            art = art[4:]
            des =row[22:62]
            num = 1 #row[72:78].replace(' ','')
            car =row[78:87]
            dataC =row[96:104]
            dataC = '=DATE('+ dataC[:4]+';'+dataC[4:6]+';'+dataC[6:] + ')'
            clav =row[120:130]
            prz =row[142:-1]
            riga =(art, des, num, dataC, clav, float(prz.strip()))
            ordini.append(riga)

    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lista_come_array = tuple(ordini)
    colonne_lista = len(lista_come_array[0]) # numero di colonne necessarie per ospitare i dati
    righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati

    oRange = oSheet.getCellRangeByPosition( 0,
                                            0,
                                            colonne_lista -1, # l'indice parte da 0
                                            righe_lista -1)
    oRange.setFormulaArray(lista_come_array)
    
    oSheet.getCellRangeByPosition(0, 0, getLastUsedCell(oSheet).EndColumn, getLastUsedCell(oSheet).EndRow).Columns.OptimalWidth = True

    return
    copy_clip()

    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()
    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    oProp = []
    oProp0 = PropertyValue()
    oProp0.Name = 'Flags'
    oProp0.Value = 'D'
    oProp1 = PropertyValue()
    oProp1.Name = 'FormulaCommand'
    oProp1.Value = 0
    oProp2 = PropertyValue()
    oProp2.Name = 'SkipEmptyCells'
    oProp2.Value = False
    oProp3 = PropertyValue()
    oProp3.Name = 'Transpose'
    oProp3.Value = False
    oProp4 = PropertyValue()
    oProp4.Name = 'AsLink'
    oProp4.Value = False
    oProp5 = PropertyValue()
    oProp5.Name = 'MoveMode'
    oProp5.Value = 4
    oProp.append(oProp0)
    oProp.append(oProp1)
    oProp.append(oProp2)
    oProp.append(oProp3)
    oProp.append(oProp4)
    oProp.append(oProp5)
    properties = tuple(oProp)
    #~ _gotoCella(6,1)

    dispatchHelper.executeDispatch(oFrame, '.uno:InsertContents', '', 0, properties)
    oDoc.CurrentController.select(oSheet.getCellRangeByPosition(0, 1, 5, getLastUsedCell(oSheet).EndRow+1))

    ordina_col(3)
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    
#~ ########################################################################
def XML_import_ep(arg=None):
    '''
    Routine di importazione di un prezzario XML-SIX in tabella Elenco Prezzi
    del template COMPUTO.
    '''
    MsgBox('Questa operazione potrebbe richiedere del tempo.','Avviso')
    New_file.computo(0)
    try:
        filename = filedia('Scegli il file XML-SIX da importare', '*.xml')
        if filename == None:
            return
        oDialogo_attesa = dlg_attesa()
        attesa().start() #mostra il dialogo
    except:
        return

    datarif = datetime.now()
    # inizializzazioe delle variabili
    lista_articoli = list() # lista in cui memorizzare gli articoli da importare
    diz_um = dict() # array per le unità di misura
    # stringhe per descrizioni articoli
    desc_breve = str()
    desc_estesa = str()
    # effettua il parsing del file XML
    tree = ElementTree()
    if filename == None:
        return
    #~ f = open(filename, 'r')
    f = codecs.open(filename,'r','utf-8')
    out_file = '.'.join(filename.split('.')[:-1]) + '.bak'
    of = codecs.open(out_file,'w','utf-8')
    
    #~ rows = list()
    for row in f:
        nrow = row.replace('&#x13;','').replace('&#xD;&#xA;',' ').replace('&#xA;','').replace('   <','<').replace('  <','<').replace(' <','<').replace('\r','').replace('\n','')
        #~ re.search('[a-zA-Z]', oCell.Formula):
        of.write(nrow)

    from yattag import indent
    
    #~ tree.parse(filename)
    tree.parse(out_file)
    # ottieni l'item root
    root = tree.getroot()
    logging.debug(list(root))
    # effettua il parsing di tutti gli elemnti dell'albero
    iter = tree.getiterator()
    listaSOA = []
    articolo = []
    articolo_modificato =()
    lingua_scelta = 'it'
########################################################################
    # nome del prezzario
    prezzario = root.find('{six.xsd}prezzario')
    if len(prezzario.findall('{six.xsd}przDescrizione')) == 2:
        if prezzario.findall('{six.xsd}przDescrizione')[0].get('lingua') == lingua_scelta:
            nome = prezzario.findall('{six.xsd}przDescrizione')[0].get('breve')
        else:
            nome = prezzario.findall('{six.xsd}przDescrizione')[1].get('breve')
    else:
        nome = prezzario.findall('{six.xsd}przDescrizione')[0].get('breve')
########################################################################
    madre = ''
    for elem in iter:
        # esegui le verifiche sulla root dell'XML
        if elem.tag == '{six.xsd}intestazione':
            intestazioneId= elem.get('intestazioneId')
            lingua= elem.get('lingua')
            separatore= elem.get('separatore')
            separatoreParametri= elem.get('separatoreParametri')
            valuta= elem.get('valuta')
            autore= elem.get('autore')
            versione= elem.get('versione')
            # inserisci i dati generali
            #~ self.update_dati_generali(nome=None, cliente=None,
                                       #~ redattore=autore,
                                       #~ ricarico=1,
                                       #~ manodopera=None,
                                       #~ sicurezza=None,
                                       #~ indirizzo=None,
                                       #~ comune=None, provincia=None,
                                       #~ valuta=valuta)
        elif elem.tag == '{six.xsd}categoriaSOA':
            soaId = elem.get('soaId')
            soaCategoria = elem.get('soaCategoria')
            soaDescrizione = elem.find('{six.xsd}soaDescrizione')
            if soaDescrizione != None:
                breveSOA = soaDescrizione.get('breve')
            voceSOA =(soaCategoria, soaId, breveSOA)
            listaSOA.append(voceSOA)
        elif elem.tag == '{six.xsd}prezzario':
            prezzarioId = elem.get('prezzarioId')
            przId= elem.get('przId')
            try:
                livelli_struttura = len(elem.get('prdStruttura').split('.'))
            except:
                pass
            categoriaPrezzario= elem.get('categoriaPrezzario')
########################################################################
        elif elem.tag == '{six.xsd}unitaDiMisura':
            um_id= elem.get('unitaDiMisuraId')
            um_sim= elem.get('simbolo')
            um_dec= elem.get('decimali')
            # crea il dizionario dell'unita di misura
########################################################################
            #~ unità di misura
            unita_misura = ''
            try:
                if len(elem.findall('{six.xsd}udmDescrizione')) == 1:
                    unita_misura = elem.findall('{six.xsd}udmDescrizione')[0].get('breve')
                else:
                    if elem.findall('{six.xsd}udmDescrizione')[1].get('lingua') == lingua_scelta:
                        idx = 1 #ITALIANO
                    else:
                        idx = 0 #TEDESCO
                    unita_misura = elem.findall('{six.xsd}udmDescrizione')[idx].get('breve')
            except IndexError:
                pass
            diz_um[um_id] = unita_misura
########################################################################
        # se il tag è un prodotto fa parte degli articoli da analizzare
        elif elem.tag == '{six.xsd}prodotto':
            prod_id = elem.get('prodottoId')
            if prod_id is not None:
                prod_id = int(prod_id)
            tariffa= elem.get('prdId')
            voce = elem.get('voce')

            sic = elem.get('onereSicurezza')
            if sic != None:
                sicurezza = float(sic)
            else:
                sicurezza = ''
########################################################################
            if diz_um.get(elem.get('unitaDiMisuraId')) != None:
                unita_misura = diz_um.get(elem.get('unitaDiMisuraId'))
            else:
                unita_misura = ''
########################################################################
            # verifica e ricava le sottosezioni
            sub_mdo = elem.find('{six.xsd}incidenzaManodopera')
            if sub_mdo != None:
                mdo = float(sub_mdo.text)
            else:
                mdo =''
########################################################################
            #~ chi(elem.findall('{six.xsd}prdDescrizione')[0].get('breve'))
            #~ return
            try:
                if len(elem.findall('{six.xsd}prdDescrizione')) == 1:
                    desc_breve = elem.findall('{six.xsd}prdDescrizione')[0].get('breve')
                    desc_estesa = elem.findall('{six.xsd}prdDescrizione')[0].get('estesa')
                else:
                #descrizione voce
                    if elem.findall('{six.xsd}prdDescrizione')[0].get('lingua') == lingua_scelta:
                        idx = 0 #ITALIANO
                    else:
                        idx = 1 #TEDESCO
                        idx = 0 #ITALIANO
                    desc_breve = elem.findall('{six.xsd}prdDescrizione')[idx].get('breve')
                    desc_estesa = elem.findall('{six.xsd}prdDescrizione')[idx].get('estesa')
            except:
                pass
            if desc_breve == None: desc_breve = ''
            if desc_estesa == None: desc_estesa = ''
            if len(desc_breve) > len(desc_estesa): desc_voce = desc_breve
            else: desc_voce = desc_estesa
########################################################################
            sub_quot = elem.find('{six.xsd}prdQuotazione')
            if sub_quot != None:
                list_nr = sub_quot.get('listaQuotazioneId')
                if sub_quot.get('valore') != None:
                    valore = float(sub_quot.get('valore'))
                if valore == 0: valore = ''
                if sub_quot.get('quantita') is not None: quantita = float(sub_quot.get('quantita')) #SERVE DAVVERO???
                if desc_voce[:2] == '- ': desc_voce=desc_voce[2:]
                desc_voce = madre + '\n- ' + desc_voce
            else:
                madre = desc_voce
                valore = ''
                quantita = ''
            elem_7 = ''
            elem_11 = ''
            if mdo != '' and mdo != 0: elem_7 = mdo/100
            if sicurezza != '' and valore != '': elem_11 = valore*sicurezza/100
            # Nota che ora articolo_modificato non è più una lista ma una tupla,
            # riguardo al motivo, vedi commenti in basso
            articolo_modificato = (tariffa,          #2  colonna
                                    desc_voce,        #4  colonna
                                    unita_misura,     #6  colonna
                                    '',
                                    valore,           #7  prezzo
                                    elem_7,           #8  mdo %
                                    elem_11)          #11 sicurezza %
            lista_articoli.append(articolo_modificato)
# compilo ##############################################################
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.getSheets().getByName('S2')
    oSheet.getCellByPosition(2, 2).String = nome
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    oSheet.getCellByPosition(1, 1).String = nome
    oSheet.getRows().insertByIndex(4, len(lista_articoli))

    lista_come_array = tuple(lista_articoli)
    # Parametrizzo il range di celle a seconda della dimensione della lista
    scarto_colonne = 0 # numero colonne da saltare a partire da sinistra
    scarto_righe = 4 # numero righe da saltare a partire dall'alto
    colonne_lista = len(lista_come_array[1]) # numero di colonne necessarie per ospitare i dati
    righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati
    oRange = oSheet.getCellRangeByPosition( scarto_colonne,
                                            scarto_righe,
                                            colonne_lista + scarto_colonne - 1, # l'indice parte da 0
                                            righe_lista + scarto_righe - 1)
    oRange.setDataArray(lista_come_array)
    oSheet.getRows().removeByIndex(3, 1)
    oDoc.CurrentController.setActiveSheet(oSheet)
    #~ struttura_Elenco()
    oDialogo_attesa.endExecute()
    MsgBox('Importazione eseguita con successo!','')
    autoexec()
# XML_import ###########################################################
########################################################################
def XML_import_multi(arg=None):
    '''
    Routine di importazione di un prezzario XML-SIX in tabella Elenco Prezzi
    del template COMPUTO.
    Tratta da PreventARES https://launchpad.net/preventares
    di <Davide Vescovini> <davide.vescovini@gmail.com>
    *Versione bilingue*
    '''
    MsgBox("L'importazione dati dal formato XML-SIX potrebbe richiedere del tempo.", 'Avviso')
    New_file.computo(0)
    try:
        filename = filedia('Scegli il file XML-SIX da importare', '*.xml')
        if filename == None:
            return
        oDialogo_attesa = dlg_attesa()
        attesa().start() #mostra il dialogo
    except:
        return
        
    datarif = datetime.now()
    # inizializzazioe delle variabili
    lista_articoli = list() # lista in cui memorizzare gli articoli da importare
    diz_um = dict() # array per le unità di misura
    # stringhe per descrizioni articoli
    desc_breve = str()
    desc_estesa = str()
    # effettua il parsing del file XML
    tree = ElementTree()
    if filename == None:
        return
    tree.parse(filename)
    # ottieni l'item root
    root = tree.getroot()
    logging.debug(list(root))
    # effettua il parsing di tutti gli elemnti dell'albero XML
    iter = tree.getiterator()
    listaSOA = []
    articolo = []
    lingua_scelta = 'it'
########################################################################
    # nome del prezzario
    prezzario = root.find('{six.xsd}prezzario')
    if len(prezzario.findall('{six.xsd}przDescrizione')) == 2:
        if prezzario.findall('{six.xsd}przDescrizione')[0].get('lingua') == lingua_scelta:
            nome1 = prezzario.findall('{six.xsd}przDescrizione')[0].get('breve')
            nome2 = prezzario.findall('{six.xsd}przDescrizione')[1].get('breve')
        else:
            nome1 = prezzario.findall('{six.xsd}przDescrizione')[1].get('breve')
            nome2 = prezzario.findall('{six.xsd}przDescrizione')[0].get('breve')
        nome=nome1+'\n§\n'+nome2
    else:
        nome = prezzario.findall('{six.xsd}przDescrizione')[0].get('breve')
########################################################################
    suffB_IT, suffE_IT, suffB_DE, suffE_DE = '', '', '', ''
    test = True
    madre = ''
    for elem in iter:
        # esegui le verifiche sulla root dell'XML
        if elem.tag == '{six.xsd}intestazione':
            intestazioneId= elem.get('intestazioneId')
            lingua= elem.get('lingua')
            separatore= elem.get('separatore')
            separatoreParametri= elem.get('separatoreParametri')
            valuta= elem.get('valuta')
            autore= elem.get('autore')
            versione= elem.get('versione')
        elif elem.tag == '{six.xsd}categoriaSOA':
            soaId = elem.get('soaId')
            soaCategoria = elem.get('soaCategoria')
            soaDescrizione = elem.find('{six.xsd}soaDescrizione')
            if soaDescrizione != None:
                breveSOA = soaDescrizione.get('breve')
            voceSOA =(soaCategoria, soaId, breveSOA)
            listaSOA.append(voceSOA)
        elif elem.tag == '{six.xsd}prezzario':
            prezzarioId = elem.get('prezzarioId')
            przId= elem.get('przId')
            try:
                livelli_struttura = len(elem.get('prdStruttura').split('.'))
            except:
                pass
            categoriaPrezzario= elem.get('categoriaPrezzario')
########################################################################
        elif elem.tag == '{six.xsd}unitaDiMisura':
            um_id= elem.get('unitaDiMisuraId')
            um_sim= elem.get('simbolo')
            um_dec= elem.get('decimali')
            # crea il dizionario dell'unita di misura
########################################################################
            #~ unità di misura
            unita_misura = ''
            try:
                if len(elem.findall('{six.xsd}udmDescrizione')) == 1:
                    unita_misura = elem.findall('{six.xsd}udmDescrizione')[0].get('breve')
                else:
                    if elem.findall('{six.xsd}udmDescrizione')[1].get('lingua') == lingua_scelta:
                        unita_misura1 = elem.findall('{six.xsd}udmDescrizione')[1].get('breve')
                        unita_misura2 = elem.findall('{six.xsd}udmDescrizione')[0].get('breve')
                    else:
                        unita_misura1 = elem.findall('{six.xsd}udmDescrizione')[0].get('breve')
                        unita_misura2 = elem.findall('{six.xsd}udmDescrizione')[1].get('breve')
                if unita_misura != None:
                    unita_misura = unita_misura1 +' § '+ unita_misura2
            except IndexError:
                pass
            diz_um[um_id] = unita_misura
########################################################################
        # se il tag è un prodotto fa parte degli articoli da analizzare
        elif elem.tag == '{six.xsd}prodotto':

            prod_id = elem.get('prodottoId')
            if prod_id is not None:
                prod_id = int(prod_id)
            tariffa= elem.get('prdId')
            sic = elem.get('onereSicurezza')
            if sic != None:
                sicurezza = float(sic)
            else:
                sicurezza = ''
########################################################################
            if diz_um.get(elem.get('unitaDiMisuraId')) != None:
                unita_misura = diz_um.get(elem.get('unitaDiMisuraId'))
            else:
                unita_misura = ''
########################################################################
            # verifica e ricava le sottosezioni
            sub_mdo = elem.find('{six.xsd}incidenzaManodopera')
            if sub_mdo != None:
                mdo = float(sub_mdo.text)
            else:
                mdo =''
########################################################################
            # descrizione voci
            desc_estesa1, desc_estesa2 = '', ''
            if test == 0:
                test = 1
                suffB_IT = suffB_IT + ' '
                suffE_IT = suffE_IT + ' '
                suffB_DE = suffB_DE + ' '
                suffE_DE = suffE_DE + ' '
            #~ try:
            if len(elem.findall('{six.xsd}prdDescrizione')) == 1:
                desc_breve = elem.findall('{six.xsd}prdDescrizione')[0].get('breve')
                desc_estesa = elem.findall('{six.xsd}prdDescrizione')[0].get('estesa')
            else:
        #descrizione voce
                if elem.findall('{six.xsd}prdDescrizione')[0].get('lingua') == lingua_scelta:
                    desc_breve1  = elem.findall('{six.xsd}prdDescrizione')[0].get('breve')
                    desc_breve2  = elem.findall('{six.xsd}prdDescrizione')[1].get('breve')
                    desc_estesa1 = elem.findall('{six.xsd}prdDescrizione')[0].get('estesa')
                    desc_estesa2 = elem.findall('{six.xsd}prdDescrizione')[1].get('estesa')
                else:
                    desc_breve1  = elem.findall('{six.xsd}prdDescrizione')[1].get('breve')
                    desc_breve2  = elem.findall('{six.xsd}prdDescrizione')[0].get('breve')
                    desc_estesa1 = elem.findall('{six.xsd}prdDescrizione')[1].get('estesa')
                    desc_estesa2 = elem.findall('{six.xsd}prdDescrizione')[0].get('estesa')
                if desc_breve1 == None:
                    desc_breve1 = ''
                if desc_breve2 == None:
                    desc_breve2 = ''
                if desc_estesa1 == None:
                    desc_estesa1 = ''
                if desc_estesa2 == None:
                    desc_estesa2 = ''
                desc_breve = suffB_IT + desc_breve1.strip() +'\n§\n'+ suffB_DE + desc_breve2.strip()
                desc_estesa = suffE_IT + desc_estesa1.strip() +'\n§\n'+ suffE_DE + desc_estesa2.strip()
            if len(desc_breve) > len(desc_estesa):
                desc_voce = desc_breve
            else:
                desc_voce = desc_estesa
            #~ except IndexError:
                #~ pass
########################################################################
            sub_quot = elem.find('{six.xsd}prdQuotazione')
            if sub_quot != None:
                list_nr = sub_quot.get('listaQuotazioneId')
                if sub_quot.get('valore') != None:
                    valore = float(sub_quot.get('valore'))
                if valore == 0:
                    valore = ''
                if sub_quot.get('quantita') is not None: #SERVE DAVVERO???
                    quantita = float(sub_quot.get('quantita'))
            else:
                test = 0
                suffB_IT, suffB_DE, suffE_IT, suffE_DE = desc_breve1, desc_breve2, desc_estesa1, desc_estesa2
                valore = ''
                quantita = ''
            vuoto = ''
            elem_7 = ''
            elem_11 = ''
            articolo_modificato = (tariffa,          #2  colonna
                                    desc_voce,        #4  colonna
                                    unita_misura,     #6  colonna
                                    vuoto,
                                    valore,           #7  prezzo
                                    elem_7,           #8  mdo %
                                    elem_11)          #11 sicurezza %
            lista_articoli.append(articolo_modificato)
# compilo la tabella ###################################################
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.getSheets().getByName('S2')
    oSheet.getCellByPosition(2, 2).String = nome
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    oSheet.getCellByPosition(1, 1).String = nome
    oSheet.getRows().insertByIndex(4, len(lista_articoli))

    lista_come_array = tuple(lista_articoli)
    # Parametrizzo il range di celle a seconda della dimensione della lista
    scarto_colonne = 0 # numero colonne da saltare a partire da sinistra
    scarto_righe = 4 # numero righe da saltare a partire dall'alto
    colonne_lista = len(lista_come_array[1]) # numero di colonne necessarie per ospitare i dati
    righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati
    oRange = oSheet.getCellRangeByPosition( scarto_colonne,
                                            scarto_righe,
                                            colonne_lista + scarto_colonne - 1, # l'indice parte da 0
                                            righe_lista + scarto_righe - 1)
    oRange.setDataArray(lista_come_array)
    oSheet.getRows().removeByIndex(3, 1)
    oDoc.CurrentController.setActiveSheet(oSheet)
    #~ struttura_Elenco()
    oDialogo_attesa.endExecute()
    MsgBox('Importazione eseguita con successo!','')
    autoexec()
# XML_import_multi ###################################################
########################################################################
class importa_listino_leeno_th(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        importa_listino_leeno_run()
def importa_listino_leeno(arg=None):
    importa_listino_leeno_th().start()
###
def importa_listino_leeno_run(arg=None):
    '''
    Esegue la conversione di un listino (formato LeenO) in template Computo
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    #~ giallo(16777072,16777120,16777168)
    #~ verde(9502608,13696976,15794160)
    #~ viola(12632319,13684991,15790335)
    lista_articoli = list()
    nome = oSheet.getCellByPosition(2, 0).String
    test = uFindStringCol('ATTENZIONE!', 5, oSheet)+1
    assembla = DlgSiNo('''Il riconoscimento di descrizioni e sottodescrizioni
dipende dalla colorazione di sfondo delle righe.

Nel caso in cui questa fosse alterata, il risultato finale
della conversione potrebbe essere inatteso.

Considera anche la possibilità di recuperare il formato XML(SIX)
di questo prezzario dal sito ufficiale dell'ente che lo rilascia.        

Vuoi assemblare descrizioni e sottodescrizioni?''', 'Richiesta')

    orig = oDoc.getURL()
    dest0 = orig[0:-4]+ '_new.ods'

    orig = uno.fileUrlToSystemPath(LeenO_path()+'/template/leeno/Computo_LeenO.ots')
    dest = uno.fileUrlToSystemPath(dest0)

    shutil.copyfile(orig, dest)
    oDialogo_attesa = dlg_attesa()
    attesa().start() #mostra il dialogo
    madre = ''
    for el in range(test, getLastUsedCell(oSheet).EndRow+1):
        tariffa = oSheet.getCellByPosition(2, el).String
        descrizione = oSheet.getCellByPosition(4, el).String
        um = oSheet.getCellByPosition(6, el).String
        sic = oSheet.getCellByPosition(11, el).String
        prezzo = oSheet.getCellByPosition(7, el).String
        mdo_p = oSheet.getCellByPosition(8, el).String
        mdo = oSheet.getCellByPosition(9, el).String
        if oSheet.getCellByPosition(2, el).CellBackColor in(16777072,16777120,9502608,13696976,12632319,13684991):
            articolo =(tariffa,
                        descrizione,
                        um,
                        sic,
                        prezzo,
                        mdo_p,
                        mdo,)
        elif oSheet.getCellByPosition(2, el).CellBackColor in(16777168,15794160,15790335):
            if assembla ==2: madre = descrizione
            articolo =(tariffa,
                        descrizione,
                        um,
                        sic,
                        prezzo,
                        mdo_p,
                        mdo,)
        else:
            if madre == '':
                descrizione = oSheet.getCellByPosition(4, el).String
            else:
                descrizione = madre + ' \n- ' + oSheet.getCellByPosition(4, el).String
            articolo =(tariffa,
                        descrizione,
                        um,
                        sic,
                        prezzo,
                        mdo_p,
                        mdo,)
        lista_articoli.append(articolo)
    oDialogo_attesa.endExecute()
    _gotoDoc(dest) #vado sul nuovo file
# compilo la tabella ###################################################
    oDoc = XSCRIPTCONTEXT.getDocument()
    oDialogo_attesa = dlg_attesa()
    attesa().start() #mostra il dialogo
    
    oSheet = oDoc.getSheets().getByName('S2')
    oSheet.getCellByPosition(2, 2).String = nome
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    oSheet.getCellByPosition(1, 1).String = nome

    oSheet.getRows().insertByIndex(4, len(lista_articoli))
    lista_come_array = tuple(lista_articoli)
    # Parametrizzo il range di celle a seconda della dimensione della lista
    colonne_lista = len(lista_come_array[1]) # numero di colonne necessarie per ospitare i dati
    righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati
    oRange = oSheet.getCellRangeByPosition( 0,
                                            4,
                                            colonne_lista - 1, # l'indice parte da 0
                                            righe_lista + 4 - 1)
    oRange.setDataArray(lista_come_array)
    oSheet.getRows().removeByIndex(3, 1)
    oDoc.CurrentController.setActiveSheet(oSheet)
    oDialogo_attesa.endExecute()
    procedo = DlgSiNo('''Vuoi mettere in ordine la visualizzazione del prezzario?     

Le righe senza prezzo avranno una tonalità di sfondo
diversa dalle altre e potranno essere facilmente nascoste.

Questa operazione potrebbe richiedere del tempo.''', 'Richiesta...')
    if procedo ==2:
        attesa().start() #mostra il dialogo
        #~ struttura_Elenco()
        oDialogo_attesa.endExecute()
    MsgBox('Conversione eseguita con successo!','')
    autoexec()
   
########################################################################
def importa_stili(filename=None):
    '''
    Importa tutti gli stili da un documento di riferimento. Se non è
    selezionato, il file di rifetimento è il template di leenO.
    '''
    if DlgSiNo('''Questa operazione sovrascriverà gli stili
del documento attivo, se già presenti!

Se non scegli un file di riferimento, saranno
importati gli stili di default di LeenO.

Vuoi continuare?''', 'Importa Stili in blocco?') == 3: return
    filename = filedia('Scegli il file di riferimento...', '*.ods')
    if filename == None:
        #~ desktop = XSCRIPTCONTEXT.getDesktop()
        filename = LeenO_path()+'/template/leeno/Computo_LeenO.ots'
    else:
        filename = uno.systemPathToFileUrl(filename)
    oDoc = XSCRIPTCONTEXT.getDocument()
    oDoc.getStyleFamilies().loadStylesFromURL(filename,list())
    for el in oDoc.Sheets.ElementNames:
        oDoc.CurrentController.setActiveSheet(oDoc.getSheets().getByName(el))
        adatta_altezza_riga(el)
    try:
        _gotoSheet('Elenco Prezzi')
    except:
        pass
########################################################################
def parziale(arg=None):
    '''
    Inserisce una riga con l'indicazione della somma parziale.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    if oSheet.Name in('COMPUTO','VARIANTE', 'CONTABILITA'):
        parziale_core(lrow)
        parziale_verifica()
###
def parziale_core(lrow):
    '''
    lrow    { double } : id della riga di inerimento
    '''

    if lrow == 0: return
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    sStRange = Circoscrive_Voce_Computo_Att(lrow)
    sopra = sStRange.RangeAddress.StartRow
    sotto = sStRange.RangeAddress.EndRow
    if oSheet.Name in('COMPUTO','VARIANTE'):
        if oSheet.getCellByPosition(0, lrow).CellStyle == 'comp 10 s' and \
        oSheet.getCellByPosition(1, lrow).CellStyle == 'Comp-Bianche in mezzo' and \
        oSheet.getCellByPosition(2, lrow).CellStyle == 'comp 1-a' or \
        oSheet.getCellByPosition(0, lrow).CellStyle == 'Comp End Attributo':
            oSheet.getRows().insertByIndex(lrow, 1)

        oSheet.getCellByPosition(1, lrow).CellStyle = 'Comp-Bianche in mezzo'
        oSheet.getCellRangeByPosition(2, lrow, 7, lrow).CellStyle = 'comp sotto centro'
        oSheet.getCellByPosition(8, lrow).CellStyle = 'comp sotto BiancheS'
        oSheet.getCellByPosition(9, lrow).CellStyle = 'Comp-Variante num sotto'
        oSheet.getCellByPosition(8, lrow).Formula = '''=CONCATENATE("Parziale [";VLOOKUP(B'''+ str(sopra+2) + ''';elenco_prezzi;3;FALSE());"]")'''
        for i in reversed(range(0, lrow)):
            if oSheet.getCellByPosition(9, i-1).CellStyle in('vuote2', 'Comp-Variante num sotto'):
                i
                break
        oSheet.getCellByPosition(9, lrow).Formula = "=SUBTOTAL(9;J" + str(i) + ":J" + str(lrow+1) + ")"

    if oSheet.Name in('CONTABILITA'):
        
        if oSheet.getCellByPosition (0, lrow).CellStyle == "comp 10 s_R" and \
        oSheet.getCellByPosition (1, lrow).CellStyle == "Comp-Bianche in mezzo_R" and \
        oSheet.getCellByPosition (2, lrow).CellStyle == "comp 1-a" or \
        'Somma positivi e negativi [' in oSheet.getCellByPosition (8, lrow).String:
            oSheet.getRows().insertByIndex(lrow, 1)
        elif oSheet.getCellByPosition (0, lrow).CellStyle == "Comp End Attributo_R" or \
        oSheet.getCellByPosition (1, lrow).CellStyle == "Data_bianca" or \
        oSheet.getCellByPosition (1, lrow).CellStyle == "comp Art-EP_R":
            return

        oSheet.getCellByPosition(2, lrow).CellStyle = "comp sotto centro"
        oSheet.getCellRangeByPosition(5, lrow, 7, lrow).CellStyle = "comp sotto centro"
        oSheet.getCellByPosition(8, lrow).CellStyle = "comp sotto BiancheS"
        oSheet.getCellByPosition(9, lrow).CellStyle = "Comp-Variante num sotto"
        oSheet.getCellByPosition(8, lrow).Formula ='=CONCATENATE("Parziale [";VLOOKUP(B' + str(sopra+2) + ';elenco_prezzi;3;FALSE());"]")'

        i = lrow
        while i > 0:
            if oSheet.getCellByPosition (9, i-1).CellStyle in ('vuote2', 'Comp-Variante num sotto'):
                da=i
                break
            i -= 1
        oSheet.getCellByPosition(9, lrow).Formula = '=SUBTOTAL(9;J' + str(da) + ':J' + str(lrow+1) + ')-SUBTOTAL(9;L' + str(da) + ':L' + str(lrow+1) + ')'

    
###
def parziale_verifica(arg=None):
    '''
    Controlla l'esattezza del calcolo del parziale quanto le righe di
    misura vengono aggiunte o cancellate.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    #~ if oSheet.Name in('COMPUTO','VARIANTE', 'CONTABILITA'):
    sStRange = Circoscrive_Voce_Computo_Att(lrow)
    sopra = sStRange.RangeAddress.StartRow+2
    sotto = sStRange.RangeAddress.EndRow
    for n in range(sopra, sotto):
        if 'Parziale [' in(oSheet.getCellByPosition(8, n).String):
            parziale_core(n)
########################################################################
def vedi_voce_xpwe(lrow,vRif,flags=''):
    """(riga d'inserimento, riga di riferimento)"""
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    sStRange = Circoscrive_Voce_Computo_Att(vRif)
    sStRange.RangeAddress
    idv = sStRange.RangeAddress.StartRow +1
    sotto = sStRange.RangeAddress.EndRow
    art = 'B$' + str(idv+1)
    idvoce = 'A$' + str(idv+1)
    des = 'C$' + str(idv+1)
    quantity = 'J$' + str(sotto+1)
    um = 'VLOOKUP(' + art + ';elenco_prezzi;3;FALSE())'
    
    #~ if oSheet.Name == 'CONTABILITA':
        #~ sformula = '=CONCATENATE("";"- vedi voce n.";TEXT(' + idvoce +';"@");" - art. ";' + art + ';" [";' + um + ';"]"'
    #~ else:
    sformula = '=CONCATENATE("";"- vedi voce n.";TEXT(' + idvoce +';"@");" - art. ";' + art +';" - ";LEFT(' + des + ';$S1.$H$334);"... [";' + um + ';" ";TEXT('+ quantity +';"0,00");"]";)'
    oSheet.getCellByPosition(2, lrow).Formula= sformula
    oSheet.getCellByPosition(4, lrow).Formula='=' + quantity
    oSheet.getCellByPosition(9, lrow).Formula='=IF(PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + ')=0;"";PRODUCT(E' + str(lrow+1) + ':I' + str(lrow+1) + '))'
    if flags in('32769', '32801'): # 32768
        inverti_segno()
        oSheet.getCellRangeByPosition(2, lrow, 10, lrow).CharColor = 16724787
########################################################################
def vedi_voce(arg=None):
    '''
    Inserisce un riferimento a voce precedente sulla riga corrente.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    if oSheet.getCellByPosition(2, lrow).Type.value != 'EMPTY':
        if oSheet.Name in ('COMPUTO', 'VARIANTE'):
            copia_riga_computo(lrow)
        elif oSheet.Name in ('CONTABILITA'):
            copia_riga_contab(lrow)
        lrow += 1   
    if oSheet.getCellByPosition(2, lrow).CellStyle == 'comp 1-a':
        to = basic_LeenO('ListenersSelectRange.getRange', "Seleziona voce di riferimento o indica n. d'ordine")
        if not oSheet.Name in to:
            to ='$' + oSheet.Name + '.$C$' + str(uFindStringCol(to, 0, oSheet))
        try:
            to = int(to.split('$')[-1])-1
        except ValueError:
            return
        _gotoCella(2, lrow)
        focus = oDoc.CurrentController.getFirstVisibleRow
        if to < lrow:
            vedi_voce_xpwe(lrow, to,)

def strall(el, n=3, pos=0):
    '''
    Allunga una stringa fino a n.
    el  { string }   : stringa di partenza
    n   { int }      : numero di caratteri da aggiungere
    pos { int }      : 0 = prefisso; 1 = suffisso

    '''
    #~ el ='o'
    if pos == 0:
        el = n * '0' + el
    else:
        el = el + n * '0'
    return el

########################################################################
def converti_stringhe(arg=None):
    '''
    Converte in numeri le stinghe o viceversa.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    try:
        sRow = oDoc.getCurrentSelection().getRangeAddresses()[0].StartRow
        sCol = oDoc.getCurrentSelection().getRangeAddresses()[0].StartColumn
        eRow = oDoc.getCurrentSelection().getRangeAddresses()[0].EndRow
        eCol = oDoc.getCurrentSelection().getRangeAddresses()[0].EndColumn
    except AttributeError:
        sRow = oDoc.getCurrentSelection().getRangeAddress().StartRow
        sCol = oDoc.getCurrentSelection().getRangeAddress().StartColumn
        eRow = oDoc.getCurrentSelection().getRangeAddress().EndRow
        eCol = oDoc.getCurrentSelection().getRangeAddress().EndColumn
    oRange = oSheet.getCellRangeByPosition(sCol, sRow, eCol, eRow)
    for y in range(sCol, eCol+1):
        for x in range(sRow, eRow+1):
            try:
                if oSheet.getCellByPosition(y, x).Type.value == 'TEXT':
                    oSheet.getCellByPosition(y, x).Value = float(oSheet.getCellByPosition(y, x).String.replace(',','.'))
                else:
                    oSheet.getCellByPosition(y, x).String = oSheet.getCellByPosition(y, x).String
            except:
                pass
    return
########################################################################
def getNumFormat (FormatString):
    '''
    Restituisce il numero identificativo del formato sulla base di una
    stringa di rifetrimento.
    FormatString { string } : codifica letterale del numero; es.: "#.##0,00"
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet

    LocalSettings = uno.createUnoStruct("com.sun.star.lang.Locale")
    LocalSettings.Language = "it"
    LocalSettings.Country = "IT"
    NumberFormats = oDoc.NumberFormats
    #~ FormatString # = "#.##0,00"
    NumberFormatId = NumberFormats.queryKey(FormatString, LocalSettings, True)

    if NumberFormatId == -1:
       NumberFormatId = NumberFormats.addNew(FormatString, LocalSettings)
    return NumberFormatId
########################################################################
def getFormatString (stile_cella):
    '''
    Recupera la stringa di riferimento dal nome dello stile di cella.
    stile_cella { string } : nome dello stile di cella
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    num = oDoc.StyleFamilies.getByName("CellStyles").getByName(stile_cella).NumberFormat
    return oDoc.getNumberFormats().getByKey(num).FormatString
########################################################################
def dec_pl (nome_stile, n):
    '''
    Cambia il numero dei decimali dello stile di cella.
    stile_cella { string } : nome stile di cella
    n { int } : nuovo numero decimali
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    stringa = getFormatString(nome_stile).split(';')
    new = list()
    for el in stringa:
        new.append (el.split(',')[0] + ',' + '0'* n)
    #~ oDoc.StyleFamilies.getByName('CellStyles').getByName(nome_stile).NumberFormat = getNumFormat(strall("#.##0,", 6+int(PartiUguali), 1))
    oDoc.StyleFamilies.getByName('CellStyles').getByName(nome_stile).NumberFormat = getNumFormat(';'.join(new))
    return 
########################################################################
# ~class XPWE_import_th(threading.Thread):
    # ~def __init__(self):
        # ~threading.Thread.__init__(self)
    # ~def run(self):
        # ~XPWE_import_run()
def XPWE_import(arg=None):
    '''
    Viasualizza il menù Esporta XPWE
    '''
    try:
        XPWE_in(scegli_elaborato('Importa dal formato XPWE'))
    except:
        return
########################################################################
# ~def XPWE_import_run(elaborato):
    # ~'''
    # ~Viasualizza il menù export/import XPWE
    # ~'''
    # ~chi(888)
    # ~XPWE_menu()
    # ~XPWE_in(elaborato)
########################################################################
def XPWE_in(arg):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    refresh(0)
    oDialogo_attesa = dlg_attesa('Caricamento dei dati...')
    if oDoc.getSheets().hasByName('S2') == False:
        MsgBox('Puoi usare questo comando da un file di computo nuovo o già esistente.','ATTENZIONE!')
        return
    else:
        MsgBox("Il contenuto dell'archivio XPWE sarà aggiunto a questo file come " + arg + ".",'Avviso!')
    _gotoSheet('COMPUTO')
    oDoc.CurrentController.select(oDoc.getSheets().hasByName('COMPUTO')) # per evitare che lo script parta da un altro documento
    filename = filedia('Scegli il file XPWE da importare...','*.xpwe')#'*.xpwe')
    '''xml auto indent: http://www.freeformatter.com/xml-formatter.html'''
    # inizializzazione delle variabili
    datarif = datetime.now()
    lista_articoli = list() # lista in cui memorizzare gli articoli da importare
    diz_ep = dict() # array per le voci di elenco prezzi
    # effettua il parsing del file XML
    tree = ElementTree()
    if filename == 'Cancel' or filename == '':
        return
    try:
        tree.parse(filename)
    except TypeError:
        return
    except PermissionError:
        MsgBox('Accertati che il nome del file sia corretto.', 'ATTENZIONE! Impossibile procedere.')
        return
    # ottieni l'item root
    root = tree.getroot()
    logging.debug(list(root))
    # effettua il parsing di tutti gli elementi dell'albero XML
    iter = tree.getiterator()
    if root.find('FileNameDocumento'):
        nome_file = root.find('FileNameDocumento').text
    else:
        nome_file = "nome_file"
###
    dati = root.find('PweDatiGenerali')
    DatiGenerali = dati.getchildren()[0][0]
    percprezzi = DatiGenerali[0].text
    comune = DatiGenerali[1].text
    provincia = DatiGenerali[2].text
    oggetto = DatiGenerali[3].text
    committente = DatiGenerali[4].text
    impresa = DatiGenerali[5].text
    parteopera = DatiGenerali[6].text

### PweDGCapitoliCategorie
    try:
        CapCat = dati.find('PweDGCapitoliCategorie')
### PweDGSuperCapitoli
        lista_supcap = list()
        if CapCat.find('PweDGSuperCapitoli'):
            PweDGSuperCapitoli = CapCat.find('PweDGSuperCapitoli').getchildren()
            for elem in PweDGSuperCapitoli:
                id_sc = elem.get('ID')
                codice = elem.find('Codice').text
                try:
                    codice = elem.find('Codice').text
                except AttributeError:
                    codice = ''
                dessintetica = elem.find('DesSintetica').text
                percentuale = elem.find('Percentuale').text
                diz = dict()
                diz['id_sc'] = id_sc
                diz['codice'] = codice
                diz['dessintetica'] = dessintetica
                diz['percentuale'] = percentuale
                lista_supcap.append(diz)
### PweDGCapitoli
        lista_cap = list()
        if CapCat.find('PweDGCapitoli'):
            PweDGCapitoli = CapCat.find('PweDGCapitoli').getchildren()
            for elem in PweDGCapitoli:
                id_sc = elem.get('ID')
                codice = elem.find('Codice').text
                try:
                    codice = elem.find('Codice').text
                except AttributeError:
                    codice = ''
                dessintetica = elem.find('DesSintetica').text
                percentuale = elem.find('Percentuale').text
                diz = dict()
                diz['id_sc'] = id_sc
                diz['codice'] = codice
                diz['dessintetica'] = dessintetica
                diz['percentuale'] = percentuale
                lista_cap.append(diz)
### PweDGSubCapitoli
        lista_subcap = list()
        if CapCat.find('PweDGSubCapitoli'):
            PweDGSubCapitoli = CapCat.find('PweDGSubCapitoli').getchildren()
            for elem in PweDGSubCapitoli:
                id_sc = elem.get('ID')
                codice = elem.find('Codice').text
                try:
                    codice = elem.find('Codice').text
                except AttributeError:
                    codice = ''
                dessintetica = elem.find('DesSintetica').text
                percentuale = elem.find('Percentuale').text
                diz = dict()
                diz['id_sc'] = id_sc
                diz['codice'] = codice
                diz['dessintetica'] = dessintetica
                diz['percentuale'] = percentuale
                lista_subcap.append(diz)
### PweDGSuperCategorie
        lista_supcat = list()
        if CapCat.find('PweDGSuperCategorie'):
            PweDGSuperCategorie = CapCat.find('PweDGSuperCategorie').getchildren()
            for elem in PweDGSuperCategorie:
                id_sc = elem.get('ID')
                dessintetica = elem.find('DesSintetica').text
                try:
                    percentuale = elem.find('Percentuale').text
                except AttributeError:
                    percentuale = '0'
                supcat =(id_sc, dessintetica, percentuale)
                lista_supcat.append(supcat)
### PweDGCategorie
        lista_cat = list()
        if CapCat.find('PweDGCategorie'):
            PweDGCategorie = CapCat.find('PweDGCategorie').getchildren()
            for elem in PweDGCategorie:
                id_sc = elem.get('ID')
                dessintetica = elem.find('DesSintetica').text
                try:
                    percentuale = elem.find('Percentuale').text
                except AttributeError:
                    percentuale = '0'
                cat =(id_sc, dessintetica, percentuale)
                lista_cat.append(cat)
### PweDGSubCategorie
        lista_subcat = list()
        if CapCat.find('PweDGSubCategorie'):
            PweDGSubCategorie = CapCat.find('PweDGSubCategorie').getchildren()
            for elem in PweDGSubCategorie:
                id_sc = elem.get('ID')
                dessintetica = elem.find('DesSintetica').text
                try:
                    percentuale = elem.find('Percentuale').text
                except AttributeError:
                    percentuale = '0'
                subcat =(id_sc, dessintetica, percentuale)
                lista_subcat.append(subcat)
    except AttributeError:
        pass
### PweDGWBS
    try:
        PweDGWBS = dati.find('PweDGWBS')
        pass
    except AttributeError:
        pass
### PweDGAnalisi
    PweDGAnalisi = dati.find('PweDGModuli').getchildren()[0]
    speseutili = PweDGAnalisi.find('SpeseUtili').text
    spesegenerali = PweDGAnalisi.find('SpeseGenerali').text
    utiliimpresa = PweDGAnalisi.find('UtiliImpresa').text
    oneriaccessorisc = PweDGAnalisi.find('OneriAccessoriSc').text
    confquantita = PweDGAnalisi.find('ConfQuantita').text
    oSheet = oDoc.getSheets().getByName('S1')
    
    try:
        oSheet.getCellByPosition(7,318).Value = float(oneriaccessorisc)/100
    except:
        pass
    try:
        oSheet.getCellByPosition(7,319).Value = float(spesegenerali)/100
    except:
        pass
    try:
        oSheet.getCellByPosition(7,320).Value = float(utiliimpresa)/100
    except:
        pass
### imposto le approssimazioni
    try:
        PweDGConfigNumeri = dati.find('PweDGConfigurazione').getchildren()[0]
        Divisa = PweDGConfigNumeri.find('Divisa').text
        ConversioniIN = PweDGConfigNumeri.find('ConversioniIN').text
        FattoreConversione = PweDGConfigNumeri.find('FattoreConversione').text
        Cambio = PweDGConfigNumeri.find('Cambio').text
        PartiUguali = PweDGConfigNumeri.find('PartiUguali').text.split('.')[-1].split('|')[0]
        Larghezza = PweDGConfigNumeri.find('Larghezza').text.split('.')[-1].split('|')[0]
        Lunghezza = PweDGConfigNumeri.find('Lunghezza').text.split('.')[-1].split('|')[0]
        HPeso = PweDGConfigNumeri.find('HPeso').text.split('.')[-1].split('|')[0]
        Quantita = PweDGConfigNumeri.find('Quantita').text.split('.')[-1].split('|')[0]
        Prezzi = PweDGConfigNumeri.find('Prezzi').text.split('.')[-1].split('|')[0]
        PrezziTotale = PweDGConfigNumeri.find('PrezziTotale').text.split('.')[-1].split('|')[0]
        ConvPrezzi = PweDGConfigNumeri.find('ConvPrezzi').text.split('.')[-1].split('|')[0]
        ConvPrezziTotale = PweDGConfigNumeri.find('ConvPrezziTotale').text.split('.')[-1].split('|')[0]
        IncidenzaPercentuale = PweDGConfigNumeri.find('IncidenzaPercentuale').text.split('.')[-1].split('|')[0]
        Aliquote = PweDGConfigNumeri.find('Aliquote').text.split('.')[-1].split('|')[0]
        dec_pl('comp 1-a PU', int(PartiUguali))
        dec_pl('comp 1-a LUNG', int(Lunghezza))
        dec_pl('comp 1-a LARG', int(Larghezza))
        dec_pl('comp 1-a peso', int(HPeso))
        for el in ('Comp-Variante num sotto', 'An-lavoraz-input', 'Blu'):
            dec_pl(el, int(Quantita))
        for el in ('comp sotto Unitario', 'An-lavoraz-generica'):
            dec_pl(el, int(Prezzi))
        for el in ('comp sotto Euro Originale', 'Livello-0-scritta mini val',
        'Livello-1-scritta mini val', 'livello2 scritta mini', 'Comp TOTALI',
        'Ultimus_totali_1', 'Ultimus_bordo', 'ULTIMUS_3', 'Ultimus_Bordo_sotto',
        'Comp-Variante num sotto','An-valuta-dx', 'An-1v-dx', 'An-lavoraz-generica',
        'An-lavoraz-Utili-num sin'):
            dec_pl(el, int(PrezziTotale))
    except IndexError:
        pass
###
    misurazioni = root.find('PweMisurazioni')
    PweElencoPrezzi = misurazioni.getchildren()[0]

### leggo l'elenco prezzi ##############################################
    epitems = PweElencoPrezzi.findall('EPItem')
    dict_articoli = dict()
    lista_articoli = list()
    lista_analisi = list()
    lista_tariffe_analisi = list()
    for elem in epitems:
        id_ep = elem.get('ID')
        diz_ep = dict()
        tipoep = elem.find('TipoEP').text
        if elem.find('Tariffa').text != None:
            tariffa = elem.find('Tariffa').text
        else:
            tariffa = ''
        articolo = elem.find('Articolo').text
        desridotta = elem.find('DesRidotta').text
        destestesa = elem.find('DesEstesa').text#.strip()
        try:
            desridotta = elem.find('DesBreve').text
        except AttributeError:
            pass
        try:
            desbreve = elem.find('DesBreve').text
        except AttributeError:
            desbreve = ''

        if elem.find('UnMisura').text != None:
            unmisura = elem.find('UnMisura').text
        else:
            unmisura = ''
        # ~prezzo1 = elem.find('Prezzo1').text
        if elem.find('Prezzo1').text == '0' :
            prezzo1 = ''
        else:
            prezzo1 = float(elem.find('Prezzo1').text)
        prezzo2 = elem.find('Prezzo2').text
        prezzo3 = elem.find('Prezzo3').text
        prezzo4 = elem.find('Prezzo4').text
        prezzo5 = elem.find('Prezzo5').text
        
        try:
            idspcap = elem.find('IDSpCap').text
        except AttributeError:
            idspcap = ''
        try:
            idcap = elem.find('IDCap').text
        except AttributeError:
            idcap = ''
        try:
            idsbcap = elem.find('IDSbCap').text
        except AttributeError:
            idsbcap = ''
        try:
            flags = elem.find('Flags').text
        except AttributeError:
            flags = ''
        try:
            data = elem.find('Data').text
        except AttributeError:
            data = ''
            
        IncSIC = ''
        IncMDO = ''
        IncMAT = ''
        IncATTR= ''

        try:
            if float(elem.find('IncSIC').text) != 0 : IncSIC = float(elem.find('IncSIC').text) / 100
        except: # AttributeError TypeError:
            pass
        try:
            if float(elem.find('IncMDO').text) != 0 : IncMDO = float(elem.find('IncMDO').text) / 100
        except: # AttributeError TypeError:
            pass
        try:
            if float(elem.find('IncMAT').text) != 0 : IncMAT = float(elem.find('IncMAT').text) / 100
        except: # AttributeError TypeError:
            pass
        try:
            if float(elem.find('IncATTR').text) != 0 : IncATTR = float(elem.find('IncATTR').text) / 100
        except: # AttributeError TypeError:
            pass
        try:
            adrinternet = elem.find('AdrInternet').text
        except AttributeError:
            adrinternet = ''
        if elem.find('PweEPAnalisi').text == None:
            pweepanalisi = ''
        else:
            pweepanalisi = elem.find('PweEPAnalisi').text
        #~ chi(pweepanalisi)
        diz_ep['tipoep'] = tipoep
        diz_ep['tariffa'] = tariffa
        diz_ep['articolo'] = articolo
        diz_ep['desridotta'] = desridotta
        diz_ep['destestesa'] = destestesa
        diz_ep['desridotta'] = desridotta
        diz_ep['desbreve'] = desbreve
        diz_ep['unmisura'] = unmisura
        diz_ep['prezzo1'] = prezzo1
        diz_ep['prezzo2'] = prezzo2
        diz_ep['prezzo3'] = prezzo3
        diz_ep['prezzo4'] = prezzo4
        diz_ep['prezzo5'] = prezzo5
        diz_ep['idspcap'] = idspcap
        diz_ep['idcap'] = idcap
        diz_ep['flags'] = flags
        diz_ep['data'] = data
        diz_ep['adrinternet'] = adrinternet
        #~ diz_ep['pweepanalisi'] = pweepanalisi
        diz_ep['IncSIC'] = IncSIC
        diz_ep['IncMDO'] = IncMDO
        diz_ep['IncMAT'] = IncMDO
        diz_ep['IncATTR'] = IncMDO
        
        dict_articoli[id_ep] = diz_ep
        articolo_modificato = (tariffa,
                                    destestesa,
                                    unmisura,
                                    IncSIC,
                                    # ~float(prezzo1),
                                    prezzo1,
                                    IncMDO,
                                    IncMAT,
                                    IncATTR)
        lista_articoli.append(articolo_modificato)
### leggo analisi di prezzo
        pweepanalisi = elem.find('PweEPAnalisi')
        PweEPAR = pweepanalisi.find('PweEPAR')
        if PweEPAR != None:
            EPARItem = PweEPAR.findall('EPARItem')
            analisi = list()
            for el in EPARItem:
                id_an = el.get('ID')
                an_tipo = el.find('Tipo').text
                id_ep = el.find('IDEP').text
                an_des = el.find('Descrizione').text
                an_um = el.find('Misura').text
                if an_um == None: an_um = ''
                try:
                    an_qt = el.find('Qt').text.replace(' ','')
                except:
                    an_qt = ''
                try:
                    an_pr = el.find('Prezzo').text.replace(' ','')
                except:
                    an_pr = ''
                an_fld = el.find('FieldCTL').text
                an_rigo =(id_ep, an_des, an_um, an_qt, an_pr)
                analisi.append(an_rigo)
            lista_analisi.append([tariffa, destestesa, unmisura, analisi, prezzo1])
            lista_tariffe_analisi.append(tariffa)
# leggo voci di misurazione e righe ####################################
    lista_misure = list()
    try:
        PweVociComputo = misurazioni.getchildren()[1]
        vcitems = PweVociComputo.findall('VCItem')
        prova_l = list()
        for elem in vcitems:
            diz_misura = dict()
            id_vc = elem.get('ID')
            id_ep = elem.find('IDEP').text
            quantita = elem.find('Quantita').text
            try:
                datamis = elem.find('DataMis').text
            except AttributeError:
                datamis = ''
            try:
                flags = elem.find('Flags').text
            except AttributeError:
                flags = ''
            try:
                idspcat = elem.find('IDSpCat').text
            except AttributeError:
                idspcat = ''
            try:
                idcat = elem.find('IDCat').text
            except AttributeError:
                idcat = ''
            try:
                idsbcat = elem.find('IDSbCat').text
            except AttributeError:
                idsbcat = ''
            try:
                CodiceWBS = elem.find('CodiceWBS').text
            except AttributeError:
                CodiceWBS = ''
            righi_mis = elem.getchildren()[-1].findall('RGItem')
            lista_rig = list()
            riga_misura =()
            lista_righe = list()#[]
            new_id_l = list()

            for el in righi_mis:
                rgitem = el.get('ID')
                idvv = el.find('IDVV').text
                if el.find('Descrizione').text != None:
                    descrizione = el.find('Descrizione').text
                else:
                    descrizione = ''
                partiuguali = el.find('PartiUguali').text
                lunghezza = el.find('Lunghezza').text
                larghezza = el.find('Larghezza').text
                hpeso = el.find('HPeso').text
                quantita = el.find('Quantita').text
                flags = el.find('Flags').text
                riga_misura = (descrizione,
                                '',
                                '',
                                partiuguali,
                                lunghezza,
                                larghezza,
                                hpeso,
                                quantita,
                                flags,
                                idvv,
                                )
                mia = []
                mia.append(riga_misura[0])
                for el in riga_misura[1:]:
                    if el == None:
                        el = ''
                    else:
                        try:
                            el = float(el)
                        except ValueError:
                            if el != '':
                                el = '=' + el.replace('.',',')
                    mia.append(el)
                lista_righe.append(riga_misura)
            diz_misura['id_vc'] = id_vc
            diz_misura['id_ep'] = id_ep
            diz_misura['quantita'] = quantita
            diz_misura['datamis'] = datamis
            diz_misura['flags'] = flags
            diz_misura['idspcat'] = idspcat
            diz_misura['idcat'] = idcat
            diz_misura['idsbcat'] = idsbcat
            diz_misura['lista_rig'] = lista_righe

            new_id = strall(idspcat) +'.'+ strall(idcat) +'.'+ strall(idsbcat)
            new_id_l =(new_id, diz_misura)
            prova_l.append(new_id_l)
            lista_misure.append(diz_misura)
    except IndexError:
        MsgBox("""Nel file scelto non risultano esserci voci di misurazione,
perciò saranno importate le sole voci di Elenco Prezzi.

Si tenga conto che:
- sarà importato solo il "Prezzo 1" dell'elenco;
- a seconda della versione, il formato XPWE potrebbe
  non conservare alcuni dati come le incidenze di
  sicurezza e di manodopera!""",'ATTENZIONE!')
        pass
    if len(lista_misure) != 0 and arg not in ('Elenco', 'CONTABILITA'):
        if DlgSiNo("""Vuoi tentare un riordino delle voci secondo la stuttura delle Categorie?

    Scegliendo Sì, nel caso in cui il file di origine risulti particolarmente disordinato, riceverai un messaggio che ti indica come intervenire.

    Se il risultato finale non dovesse andar bene, puoi ripetere l'importazione senza il riordino delle voci rispondendo No a questa domanda.""", "Richiesta") ==2:
            riordine = sorted(prova_l, key=lambda el: el[0])
            lista_misure = list()
            for el in riordine:
                lista_misure.append(el[1])
    attesa().start()
###
# compilo Anagrafica generale ##########################################
    #~ New_file.computo()
# compilo Anagrafica generale ##########################################
    oSheet = oDoc.getSheets().getByName('S2')
    if oggetto != None:
        oSheet.getCellByPosition(2,2).String = oggetto
    if comune != None:
        oSheet.getCellByPosition(2,3).String = comune
    if committente != None:
        oSheet.getCellByPosition(2,5).String = committente
    if impresa != None:
        oSheet.getCellByPosition(3,16).String = impresa
###
    zoom = oDoc.CurrentController.ZoomValue
    oDoc.CurrentController.ZoomValue = 400

# compilo Elenco Prezzi ################################################
    oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
    # Siccome setDataArray pretende una tupla(array 1D) o una tupla di tuple(array 2D)
    # trasformo la lista_articoli da una lista di tuple a una tupla di tuple
    lista_come_array = tuple(lista_articoli)
    # Parametrizzo il range di celle a seconda della dimensione della lista
    colonne_lista = len(lista_come_array[0]) # numero di colonne necessarie per ospitare i dati
    righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati

    oSheet.getRows().insertByIndex(3, righe_lista)
    oRange = oSheet.getCellRangeByPosition( 0,
                                            3,
                                            colonne_lista -1, # l'indice parte da 0
                                            righe_lista +3-1)
    oRange.setDataArray(lista_come_array)
    lrow = getLastUsedCell(oSheet).EndRow -1 
    oSheet.getCellRangeByPosition(0, 3, 0, lrow).CellStyle = "EP-aS"
    oSheet.getCellRangeByPosition(1, 3, 1, lrow).CellStyle = "EP-a"
    oSheet.getCellRangeByPosition(2, 3, 7, lrow).CellStyle = "EP-mezzo"
    oSheet.getCellRangeByPosition(5, 3, 5, lrow).CellStyle = "EP-mezzo %"
    oSheet.getCellRangeByPosition(8, 3, 9, lrow).CellStyle = "EP-sfondo"

    oSheet.getCellRangeByPosition(11, 3, 11, lrow).CellStyle = 'EP-mezzo %'
    oSheet.getCellRangeByPosition(12, 3, 12, lrow).CellStyle = 'EP statistiche_q'
    oSheet.getCellRangeByPosition(13, 3, 13, lrow).CellStyle = 'EP statistiche_Contab_q'
# aggiungo i capitoli alla lista delle voci ############################
    #~ giallo(16777072,16777120,16777168)
    #~ verde(9502608,13696976,15794160)
    #~ viola(12632319,13684991,15790335)
    #~ col1 = 16777072
    #~ col2 = 16777120
    #~ col3 = 16777168
    #~ capitoli = list()
# SUPERCAPITOLI
    try:
        for el in lista_supcap:
            tariffa = el.get('codice')
            if tariffa != None:
                destestesa = el.get('dessintetica')
                titolo = (tariffa,
                                        destestesa,
                                        '',
                                        '',
                                        '',
                                        '',
                                        '')
                capitoli.append(titolo)
        lista_come_array = tuple(capitoli)
        colonne_lista = len(lista_come_array[0]) # numero di colonne necessarie per ospitare i dati
        righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati

        oSheet.getRows().insertByIndex(3, righe_lista)
        oRange = oSheet.getCellRangeByPosition( 0,
                                                3,
                                                colonne_lista -1, # l'indice parte da 0
                                                righe_lista +3-1)
        oRange.setDataArray(lista_come_array)
        oSheet.getCellRangeByPosition(0, 3, 0, righe_lista +3-1).CellStyle = "EP-aS"
        oSheet.getCellRangeByPosition(1, 3, 1, righe_lista +3-1).CellStyle = "EP-a"
        oSheet.getCellRangeByPosition(2, 3, 7, righe_lista +3-1).CellStyle = "EP-mezzo"
        oSheet.getCellRangeByPosition(5, 3, 5, righe_lista +3-1).CellStyle = "EP-mezzo %"
        oSheet.getCellRangeByPosition(8, 3, 9, righe_lista +3-1).CellStyle = "EP-sfondo"

        oSheet.getCellRangeByPosition(11, 3, 11, righe_lista +3-1).CellStyle = 'EP-mezzo %'
        oSheet.getCellRangeByPosition(12, 3, 12, righe_lista +3-1).CellStyle = 'EP statistiche_q'
        oSheet.getCellRangeByPosition(13, 3, 13, righe_lista +3-1).CellStyle = 'EP statistiche_Contab_q'
        oSheet.getCellRangeByPosition(0, 3, 0, righe_lista + 3 - 1).CellBackColor = col1
    except:
        pass
# CAPITOLI
    capitoli = list()
    try:
        for el in lista_cap: # + lista_subcap:
            tariffa = el.get('codice')
            if tariffa != None:
                destestesa = el.get('dessintetica')
                titolo = (tariffa,
                                        destestesa,
                                        '',
                                        '',
                                        '',
                                        '',
                                        '')
                capitoli.append(titolo)
        lista_come_array = tuple(capitoli)
        colonne_lista = len(lista_come_array[0]) # numero di colonne necessarie per ospitare i dati
        righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati

        oSheet.getRows().insertByIndex(3, righe_lista)
        oRange = oSheet.getCellRangeByPosition( 0,
                                                3,
                                                colonne_lista -1, # l'indice parte da 0
                                                righe_lista +3-1)
        oRange.setDataArray(lista_come_array)
        oSheet.getCellRangeByPosition(0, 3, 0, righe_lista +3-1).CellStyle = "EP-aS"
        oSheet.getCellRangeByPosition(1, 3, 1, righe_lista +3-1).CellStyle = "EP-a"
        oSheet.getCellRangeByPosition(2, 3, 7, righe_lista +3-1).CellStyle = "EP-mezzo"
        oSheet.getCellRangeByPosition(5, 3, 5, righe_lista +3-1).CellStyle = "EP-mezzo %"
        oSheet.getCellRangeByPosition(8, 3, 9, righe_lista +3-1).CellStyle = "EP-sfondo"

        oSheet.getCellRangeByPosition(11, 3, 11, righe_lista +3-1).CellStyle = 'EP-mezzo %'
        oSheet.getCellRangeByPosition(12, 3, 12, righe_lista +3-1).CellStyle = 'EP statistiche_q'
        oSheet.getCellRangeByPosition(13, 3, 13, righe_lista +3-1).CellStyle = 'EP statistiche_Contab_q'
        oSheet.getCellRangeByPosition(0, 3, 0, righe_lista + 3 - 1).CellBackColor = col2
    except:
        pass
# SUBCAPITOLI
    capitoli = list()
    try:
        for el in lista_subcap:
            tariffa = el.get('codice')
            if tariffa != None:
                destestesa = el.get('dessintetica')
                titolo = (tariffa,
                                        destestesa,
                                        '',
                                        '',
                                        '',
                                        '',
                                        '')
                capitoli.append(titolo)
        lista_come_array = tuple(capitoli)
        colonne_lista = len(lista_come_array[0]) # numero di colonne necessarie per ospitare i dati
        righe_lista = len(lista_come_array) # numero di righe necessarie per ospitare i dati

        oSheet.getRows().insertByIndex(4, righe_lista)
        oRange = oSheet.getCellRangeByPosition( 0,
                                                3,
                                                colonne_lista -1, # l'indice parte da 0
                                                righe_lista +3-1)
        oRange.setDataArray(lista_come_array)
        oSheet.getCellRangeByPosition(0, 3, 0, righe_lista +3-1).CellStyle = "EP-aS"
        oSheet.getCellRangeByPosition(1, 3, 1, righe_lista +3-1).CellStyle = "EP-a"
        oSheet.getCellRangeByPosition(2, 3, 7, righe_lista +3-1).CellStyle = "EP-mezzo"
        oSheet.getCellRangeByPosition(5, 3, 5, righe_lista +3-1).CellStyle = "EP-mezzo %"
        oSheet.getCellRangeByPosition(8, 3, 9, righe_lista +3-1).CellStyle = "EP-sfondo"

        oSheet.getCellRangeByPosition(11, 3, 11, righe_lista +3-1).CellStyle = 'EP-mezzo %'
        oSheet.getCellRangeByPosition(12, 3, 12, righe_lista +3-1).CellStyle = 'EP statistiche_q'
        oSheet.getCellRangeByPosition(13, 3, 13, righe_lista +3-1).CellStyle = 'EP statistiche_Contab_q'
        oSheet.getCellRangeByPosition(0, 3, 0, righe_lista + 3 - 1).CellBackColor = col3
    except:
        pass
    for el in(11, 15, 19, 26):
        oSheet.getCellRangeByPosition(el, 3, el, ultima_voce(oSheet)).CellStyle = 'EP-mezzo %'
    for el in(12, 16, 20, 23):
        oSheet.getCellRangeByPosition(el, 3, el, ultima_voce(oSheet)).CellStyle = 'EP statistiche_q'
    for el in(13, 17, 21, 24, 25):
        oSheet.getCellRangeByPosition(el, 3, el, ultima_voce(oSheet)).CellStyle = 'EP statistiche'
    #~ adatta_altezza_riga('Elenco Prezzi')
    riordina_ElencoPrezzi()
    #~ struttura_Elenco()

### elimino le voci che hanno analisi
    for i in reversed(range(3, getLastUsedCell(oSheet).EndRow)):
        if oSheet.getCellByPosition(0, i).String in lista_tariffe_analisi:
            oSheet.getRows().removeByIndex(i, 1)
###
# Compilo Analisi di prezzo ############################################
    if len(lista_analisi) !=0:
        inizializza_analisi()
        oSheet = oDoc.getSheets().getByName('Analisi di Prezzo')
        for el in lista_analisi:
            prezzo_finale = el[-1]
            sStRange = Circoscrive_Analisi(Range2Cell()[1])
            lrow = sStRange.RangeAddress.StartRow + 2
            oSheet.getCellByPosition(0, lrow).String = el[0]
            oSheet.getCellByPosition(1, lrow).String = el[1]
            oSheet.getCellByPosition(2, lrow).String = el[2]
            y = 0
            n = lrow + 2
            for x in el[3]:
                if el[3][y][1] not in ('MANODOPERA', 'MATERIALI', 'NOLI', 'TRASPORTI', 'ALTRE FORNITURE E PRESTAZIONI'):
                    copia_riga_analisi(n)
                if dict_articoli.get(el[3][y][0]) != None:
                    oSheet.getCellByPosition(0, n).String = dict_articoli.get(el[3][y][0]).get('tariffa')
                else:
                    oSheet.getCellByPosition(0, n).String = ''
                    oSheet.getCellByPosition(1, n).String = x[1]
                    oSheet.getCellByPosition(2, n).String = x[2]
                    oSheet.getCellByPosition(3, n).Value = float(x[3].replace(',','.'))
                    oSheet.getCellByPosition(4, n).Value = float(x[4].replace(',','.'))
                if el[3][y][1] not in ('MANODOPERA', 'MATERIALI', 'NOLI', 'TRASPORTI', 'ALTRE FORNITURE E PRESTAZIONI'):
                    try:
                        float (el[3][y][3])
                        oSheet.getCellByPosition(3, n).Value = el[3][y][3]
                    except:
                        #~ pass
                        oSheet.getCellByPosition(3, n).Formula = '=' + el[3][y][3]
                y += 1
                n += 1
            if oSheet.getCellByPosition(6, sStRange.RangeAddress.StartRow + 2).Value != prezzo_finale:
                oSheet.getCellByPosition(6, sStRange.RangeAddress.StartRow + 2).Value = prezzo_finale
            inizializza_analisi()
        elimina_voce (ultima_voce(oSheet), 0)
        tante_analisi_in_ep()
        fine = getLastUsedCell(oSheet).EndRow
        for n in reversed(range(0, fine)):
            if oSheet.getCellByPosition(0, n).String == 'Cod. Art.?' and oSheet.getCellByPosition(0, n-1).CellStyle == 'An-lavoraz-Cod-sx':
                oSheet.getRows().removeByIndex(n, 1)
            if oSheet.getCellByPosition(0, n).String == 'Cod. Art.?':
                oSheet.getCellByPosition(0, n).String = ''
    if len(lista_misure) == 0:
        #~ MsgBox('Importazione eseguita con successo in ' + str((datetime.now() - datarif).total_seconds()) + ' secondi!        \n\nImporto € ' + oSheet.getCellByPosition(0, 1).String ,'')
        MsgBox("Importate n."+ str(len(lista_articoli)) +" voci dall'elenco prezzi\ndel file: " + filename, 'Avviso')
        oSheet = oDoc.getSheets().getByName('Elenco Prezzi')
        oDoc.CurrentController.setActiveSheet(oSheet)
        oDoc.CurrentController.ZoomValue = zoom
        refresh(1)
        oDialogo_attesa.endExecute()
        return
    refresh(0)
    doppioni()
    if arg == 'Elenco':
        oDoc.CurrentController.ZoomValue = zoom
        refresh(1)
        oDialogo_attesa.endExecute()
        return
# Inserisco i dati nel COMPUTO #########################################
    if arg == 'VARIANTE':
        genera_variante()
    elif arg == 'CONTABILITA':
        attiva_contabilita()
    oSheet = oDoc.getSheets().getByName(arg)
    if oSheet.getCellByPosition(1, 4).String == 'Cod. Art.?':
        if arg == 'CONTABILITA':
            oSheet.getRows().removeByIndex(3, 5)
        else:
            oSheet.getRows().removeByIndex(3, 4)
    oDoc.CurrentController.select(oSheet)
    iSheet_num = oSheet.RangeAddress.Sheet
###
    oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
    oCellRangeAddr.Sheet = oSheet.RangeAddress.Sheet # recupero l'index del foglio
    diz_vv = dict()

    testspcat = '0'
    testcat = '0'
    testsbcat = '0'
    x = 1
    for el in lista_misure:
        datamis = el.get('datamis')
        idspcat = el.get('idspcat')
        idcat = el.get('idcat')
        idsbcat = el.get('idsbcat')

        lrow = ultima_voce(oSheet) + 1
#~ inserisco le categorie
        try:
            if idspcat != testspcat:
                testspcat = idspcat
                testcat = '0'
                Inser_SuperCapitolo_arg(lrow, lista_supcat[eval(idspcat)-1][1])
                lrow +=1
        except UnboundLocalError:
            pass
        try:
            if idcat != testcat:
                testcat = idcat
                testsbcat = '0'
                Inser_Capitolo_arg(lrow, lista_cat[eval(idcat)-1][1])
                lrow +=1
        except UnboundLocalError:
            pass
        try:
            if idsbcat != testsbcat:
                testsbcat = idsbcat
                Inser_SottoCapitolo_arg(lrow, lista_subcat[eval(idsbcat)-1][1])
        except UnboundLocalError:
            pass
        lrow = ultima_voce(oSheet) + 1
        if arg == 'CONTABILITA':
            ins_voce_contab(lrow = ultima_voce(oSheet) + 1, arg=0)
        else:
            ins_voce_computo_grezza(lrow)
        ID = el.get('id_ep')
        id_vc = el.get('id_vc')

        try:
            oSheet.getCellByPosition(1, lrow+1).String = dict_articoli.get(ID).get('tariffa')
        except:
            pass
        diz_vv[id_vc] = lrow+1
        oSheet.getCellByPosition(0, lrow+1).String = str(x)
        x = x+1
        SC = 2
        SR = lrow + 2 + 1
        nrighe = len(el.get('lista_rig')) - 1

        if nrighe > -1:
            EC = SC + len(el.get('lista_rig')[0])
            ER = SR + nrighe

            if nrighe > 0:
                oSheet.getRows().insertByIndex(SR, nrighe)

            oRangeAddress = oSheet.getCellRangeByPosition(0, SR-1, 250, SR-1).getRangeAddress()

            for n in range(SR, SR+nrighe):
                oCellAddress = oSheet.getCellByPosition(0, n).getCellAddress()
                oSheet.copyRange(oCellAddress, oRangeAddress)
                if arg == 'CONTABILITA':
                    oSheet.getCellByPosition(1, n).String = ''
                    oSheet.getCellByPosition(1, n).CellStyle  = 'Comp-Bianche in mezzo_R'

            oCellRangeAddr.StartColumn = SC
            oCellRangeAddr.StartRow = SR
            oCellRangeAddr.EndColumn = EC
            oCellRangeAddr.EndRow = ER

        ###
        # INSERISCO PRIMA SOLO LE RIGHE SE NO MI FA CASINO
            SR = SR - 1
            if arg == 'CONTABILITA':
                oSheet.getCellByPosition(1, SR).Formula = '=DATE(' + datamis.split('/')[2] +';' + datamis.split('/')[1] +';' + datamis.split('/')[0] + ')'
                oSheet.getCellByPosition(1, SR).Value = oSheet.getCellByPosition(1, SR).Value
            for mis in el.get('lista_rig'):
                if mis[0] != None: #descrizione
                    descrizione = mis[0].strip()
                    oSheet.getCellByPosition(2, SR).String = descrizione
                else:
                    descrizione =''

                if mis[3] != None: #parti uguali
                    try:
                        oSheet.getCellByPosition(5, SR).Value = float(mis[3].replace(',','.'))
                    except ValueError:
                        oSheet.getCellByPosition(5, SR).Formula = '=' + str(mis[3]).split('=')[-1] # tolgo evenutali '=' in eccesso
                if mis[4] != None: #lunghezza
                    try:
                        oSheet.getCellByPosition(6, SR).Value = float(mis[4].replace(',','.'))
                    except ValueError:
                        oSheet.getCellByPosition(6, SR).Formula = '=' + str(mis[4]).split('=')[-1] # tolgo evenutali '=' in eccesso
                if mis[5] != None: #larghezza
                    try:
                        oSheet.getCellByPosition(7, SR).Value = float(mis[5].replace(',','.'))
                    except ValueError:
                        oSheet.getCellByPosition(7, SR).Formula = '=' + str(mis[5]).split('=')[-1] # tolgo evenutali '=' in eccesso
                if mis[6] != None: #HPESO
                    try:
                        oSheet.getCellByPosition(8, SR).Value = float(mis[6].replace(',','.'))
                        
                    except:
                        oSheet.getCellByPosition(8, SR).Formula = '=' + str(mis[6]).split('=')[-1] # tolgo evenutali '=' in eccesso
                if mis[8] == '2':
                    parziale_core(SR)
                    oSheet.getRows().removeByIndex(SR+1, 1)
                    descrizione =''

                if mis[9] != '-2':
                    vedi = diz_vv.get(mis[9])
                    try:
                        vedi_voce_xpwe(SR, vedi, mis[8])
                    except:
                        MsgBox("""Il file di origine è particolarmente disordinato.
Riordinando il computo trovo riferimenti a voci non ancora inserite.

Al termine dell'impotazione controlla la voce con tariffa """ + dict_articoli.get(ID).get('tariffa') +
"""\nalla riga n.""" + str(lrow+2) + """ del foglio, evidenziata qui a sinistra.""", 'Attenzione!')
                        oSheet.getCellByPosition(44, SR).String = dict_articoli.get(ID).get('tariffa')
                try:
                    mis[7]
                    if '-' in mis[7]:
                        for x in range(5, 8):
                            try:
                                if oSheet.getCellByPosition(x, SR).Value != 0:
                                    oSheet.getCellByPosition(x, SR).Value = abs(oSheet.getCellByPosition(x, SR).Value)
                            except:
                                pass
                        inverti_un_segno(SR)

                    if oSheet.getCellByPosition(5, SR).Type.value == 'FORMULA':
                        va = oSheet.getCellByPosition(5, SR).Formula
                    else:
                        va = oSheet.getCellByPosition(5, SR).Value

                    if oSheet.getCellByPosition(6, SR).Type.value == 'FORMULA':
                        vb = oSheet.getCellByPosition(6, SR).Formula
                    else:
                        vb = oSheet.getCellByPosition(6, SR).Value
                        
                    if oSheet.getCellByPosition(7, SR).Type.value == 'FORMULA':
                        vc = oSheet.getCellByPosition(7, SR).Formula
                    else:
                        vc = oSheet.getCellByPosition(7, SR).Value

                    if oSheet.getCellByPosition(8, SR).Type.value == 'FORMULA':
                        vd = oSheet.getCellByPosition(8, SR).Formula
                    else:
                        vd = oSheet.getCellByPosition(8, SR).Value

                    if mis[3] == None:
                        va =''
                    else:
                        if '^' in mis[3]:
                            va = eval(mis[3].replace('^','**'))
                        else:
                            va = eval(mis[3])
                except:
                    pass
                SR = SR+1
    numera_voci()
    try:
        Rinumera_TUTTI_Capitoli2()
    except:
        pass
    oDoc.CurrentController.ZoomValue = zoom
    refresh(1)
    #~ MsgBox('Importazione eseguita con successo in ' + str((datetime.now() - datarif).total_seconds()) + ' secondi!        \n\nImporto € ' + oSheet.getCellByPosition(0, 1).String ,'')
    oDialogo_attesa.endExecute()
    _gotoSheet(arg)
    #~ if uFindStringCol('Riepilogo strutturale delle Categorie', 2, oSheet) !='None':
        #~ firme_in_calce()
    MsgBox('Importazione di\n\n' + arg + '\n\neseguita con successo!', '')
# XPWE_in ##########################################################
########################################################################
#VARIABILI GLOBALI:#####################################################
########################################################################
Lmajor= 3 #'INCOMPATIBILITA'
Lminor= 20 #'NUOVE FUNZIONALITA'
Lsubv= "0" #'CORREZIONE BUGS
noVoce = ('Livello-0-scritta', 'Livello-1-scritta', 'livello2 valuta', 'comp Int_colonna', 'Ultimus_centro_bordi_lati')
stili_computo =('Comp Start Attributo', 'comp progress', 'comp 10 s','Comp End Attributo')
stili_contab = ('Comp Start Attributo_R', 'comp 10 s_R','Comp End Attributo_R')
stili_analisi =('Analisi_Sfondo', 'An.1v-Att Start', 'An-1_sigla', 'An-lavoraz-desc',
'An-lavoraz-Cod-sx', 'An-lavoraz-desc-CEN', 'An-sfondo-basso Att End')
stili_elenco =('EP-Cs', 'EP-aS')
createUnoService =(
            #~ uno # protocol heandler
            XSCRIPTCONTEXT
            .getComponentContext()
            .getServiceManager()
            .createInstance)
GetmyToolBarNames =('private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar',
    'private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_ELENCO',
    'private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_ANALISI',
    'private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_COMPUTO',
    'private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_CONTABILITA',)
#
codice_da_cercare = ''
sUltimus = ''
########################################################################
def ssUltimus(arg=None):
    oDlgMain.endExecute()
    '''
    Scrive la variabile globale che individua il Documento Principale (DCC)
    che è il file a cui giungono le voci di prezzo inviate da altri file
    '''
    
    global sUltimus
    oDoc = XSCRIPTCONTEXT.getDocument()
    if oDoc.getSheets().hasByName('M1') == False:
        return
    if len(oDoc.getURL()) == 0:
        MsgBox('''Prima di procedere, devi salvare il lavoro!
Provvedi subito a dare un nome al file di computo...''', 'Dai un nome al file...')
        salva_come()
        autoexec()
    sUltimus = uno.fileUrlToSystemPath(oDoc.getURL())
    DlgMain()
    return
########################################################################
def filedia(titolo='Scegli il file...', est='*.*', mode=0):
    """
    titolo  { string }  : titolo del FilePicker
    est     { string }  : filtro di visualizzazione file
    mode    { integer } : modalità di gestione del file

    Apri file:  `mode in(0, 6, 7, 8, 9)`
    Salva file: `mode in(1, 2, 3, 4, 5, 10)`
    see:('''http://api.libreoffice.org/docs/idl/ref/
            namespacecom_1_1sun_1_1star_1_1ui_1_1
            dialogs_1_1TemplateDescription.html''' )
    see:('''http://stackoverflow.com/questions/30840736/
        libreoffice-how-to-create-a-file-dialog-via-python-macro''')
    """
    estensioni = {'*.*'   : 'Tutti i file(*.*)',
                '*.odt' : 'Writer(*.odt)',
                '*.ods' : 'Calc(*.ods)',
                '*.odb' : 'Base(*.odb)',
                '*.odg' : 'Draw(*.odg)',
                '*.odp' : 'Impress(*.odp)',
                '*.odf' : 'Math(*.odf)',
                '*.xpwe': 'Primus(*.xpwe)',
                '*.xml' : 'XML(*.xml)',
                '*.dat' : 'dat(*.dat)',
                }
    try:
        oFilePicker = createUnoService( "com.sun.star.ui.dialogs.OfficeFilePicker" )
        oFilePicker.initialize(( mode,) )
        oDoc = XSCRIPTCONTEXT.getDocument()
        oFilePicker.setDisplayDirectory(os.path.dirname(oDoc.getURL()))
        oFilePicker.Title = titolo
        app = estensioni.get(est)
        oFilePicker.appendFilter(app, est)
        if oFilePicker.execute():
            oDisp = uno.fileUrlToSystemPath(oFilePicker.getFiles()[0])
        return oDisp
    except:
        MsgBox('Il file non è stato selezionato', 'ATTENZIONE!')
        return

########################################################################
from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK, BUTTONS_OK_CANCEL, BUTTONS_YES_NO, BUTTONS_YES_NO_CANCEL, BUTTONS_RETRY_CANCEL, BUTTONS_ABORT_IGNORE_RETRY
from com.sun.star.awt.MessageBoxButtons import DEFAULT_BUTTON_OK, DEFAULT_BUTTON_CANCEL, DEFAULT_BUTTON_RETRY, DEFAULT_BUTTON_YES, DEFAULT_BUTTON_NO, DEFAULT_BUTTON_IGNORE
from com.sun.star.awt.MessageBoxType import MESSAGEBOX, INFOBOX, WARNINGBOX, ERRORBOX, QUERYBOX

#rif.: https://wiki.openoffice.org/wiki/PythonDialogBox

def chi(s): # s = oggetto
    '''
    s    { object }  : oggetto da interrogare

    mostra un dialog che indica il tipo di oggetto ed i metodi ad esso applicabili
    '''
    doc = XSCRIPTCONTEXT.getDocument()
    parentwin = doc.CurrentController.Frame.ContainerWindow
    s1 = str(s) + '\n\n' + str(dir(s).__str__())
    MessageBox(parentwin, str(s1), str(type(s)), 'infobox')
    
def DlgSiNo(s,t='Titolo'): # s = messaggio | t = titolo
    '''
    Visualizza il menù di scelta sì/no
    restituisce 2 per sì e 3 per no
    '''
    doc = XSCRIPTCONTEXT.getDocument()
    parentwin = doc.CurrentController.Frame.ContainerWindow
    #~ s = 'This a message'
    #~ t = 'Title of the box'
    #~ MESSAGEBOX, INFOBOX, WARNINGBOX, ERRORBOX, QUERYBOX
    return MessageBox(parentwin, s, t, QUERYBOX, BUTTONS_YES_NO + DEFAULT_BUTTON_NO)
    

def MsgBox(s,t=''): # s = messaggio | t = titolo
    doc = XSCRIPTCONTEXT.getDocument()
    parentwin = doc.CurrentController.Frame.ContainerWindow
    #~ s = 'This a message'
    #~ t = 'Title of the box'
    #~ res = MessageBox(parentwin, s, t, QUERYBOX, BUTTONS_YES_NO_CANCEL + DEFAULT_BUTTON_NO)
    #~ chi(res)
    #~ return
    #~ s = res
    #~ t = 'Titolo'
    if t == None:
        t='messaggio'
    MessageBox(parentwin, str(s), t, 'infobox')

# Show a message box with the UNO based toolkit
def MessageBox(ParentWin, MsgText, MsgTitle, MsgType=MESSAGEBOX, MsgButtons=BUTTONS_OK):
    ctx = uno.getComponentContext()
    sm = ctx.ServiceManager
    sv = sm.createInstanceWithContext('com.sun.star.awt.Toolkit', ctx)
    myBox = sv.createMessageBox(ParentWin, MsgType, MsgButtons, MsgTitle, MsgText)
   
    return myBox.execute()
# [　入手元　]

def mri(target):
    ctx = XSCRIPTCONTEXT.getComponentContext()
    mri = ctx.ServiceManager.createInstanceWithContext('mytools.Mri',ctx)
    mri.inspect(target)
    MsgBox('MRI in corso...','avviso')

########################################################################
#import pdb; pdb.set_trace() #debugger
########################################################################
#codice di Manuele Pesenti #############################################
########################################################################
def get_Formula(n, a, b):
    """
    n { integer } : posizione cella
    a  { string } : primo parametro da sostituire
    b  { string } : secondo parametro da sostituire
    """
    v = dict(n=n, a=a, b=b)
    formulas = {
        18: '=SUBTOTAL(9;S%(a)s:S%(b)s)',
        24: '=S%(a)s/S%(b)s',
        29: '=AE%(a)s/S%(b)s',
        30: '=SUBTOTAL(9;AE%(a)s:AE%(b)s)'
    }
    return formulas[n] % v

def getCellStyle(l, n):
    """
    l { integer } : livello(1 o 2)
    n { integer } : posizione cella
    """
    styles = {
        2: {
            18: 'livello2 scritta mini',
            24: 'livello2 valuta mini %',
            29: 'livello2 valuta mini %',
            30: 'livello2 valuta mini'
        },
        1: {
            18: 'Livello-1-scritta mini val',
            24: 'Livello-1-scritta mini %',
            29: 'Livello-1-scritta mini %',
            30: 'Livello-1-scritta mini val'
        }
    }
    return styles[l][n]

def SubSum(lrow, sub=False):
    """ Inserisce i dati nella riga
    sub { boolean } : specifica se sotto-categoria
    """
    if sub:
        myrange =('livello2 scritta mini', 'Livello-1-scritta minival', 'Comp TOTALI',)
        level = 2
    else:
        myrange =('Livello-1-scritta mini val', 'Comp TOTALI',)
        level = 1

    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name not in('COMPUTO', 'VARIANTE'):
        return
    lrowE = ultima_voce(oSheet)+1
    nextCap = lrowE
    for n in range(lrow+1, lrowE):
        if oSheet.getCellByPosition(18, n).CellStyle in myrange:
            nextCap = n + 1
            break
    for n,a,b in((18, lrow+1, nextCap,),(24, lrow+1, lrowE+1,),(29, lrow+1, lrowE+1,),(30, lrow+1, nextCap,),):
        oSheet.getCellByPosition(n, lrow).Formula = get_Formula(n, a, b)
        Sheet.getCellByPosition(18, lrow).CellStyle = getCellStyle(level, n)
########################################################################
# GESTIONE DELLE VISTE IN STRUTTURA ####################################
########################################################################
def filtra_codice(voce=None):
# ~def debug(voce=None):
    refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    # ~zoom = oDoc.CurrentController.ZoomValue
    # ~oDoc.CurrentController.ZoomValue = 400
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name == "Elenco Prezzi":
        voce = oDoc.Sheets.getByName('Elenco Prezzi').getCellByPosition(0, Range2Cell()[1]).String
    # ~oSheet = oDoc.CurrentController.ActiveSheet
        try:
            elaborato = scegli_elaborato('Ricerca di ' + voce)
            _gotoSheet(elaborato)
        except:
            return
        oSheet = oDoc.Sheets.getByName(elaborato)
        _gotoCella(0,6)
        next_voice(Range2Cell()[1],1)
    oSheet.clearOutline()
    lrow = Range2Cell()[1]
    if oSheet.getCellByPosition(0, lrow).CellStyle in(stili_computo + stili_contab):
        iSheet = oSheet.RangeAddress.Sheet
        oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
        oCellRangeAddr.Sheet = iSheet
        sStRange = Circoscrive_Voce_Computo_Att(lrow)
        sopra = sStRange.RangeAddress.StartRow
        if not voce:
            voce = oSheet.getCellByPosition(1, sopra+1).String
    else:
        MsgBox('Devi prima selezionare una voce di misurazione.','Avviso!')
        return
    fine = ultima_voce(oSheet)+1
    lista_pt = list()
    _gotoCella(0, 0)
    for n in range(0, fine):
        if oSheet.getCellByPosition(0, n).CellStyle in('Comp Start Attributo','Comp Start Attributo_R'):
            sStRange = Circoscrive_Voce_Computo_Att(n)
            sopra = sStRange.RangeAddress.StartRow
            sotto = sStRange.RangeAddress.EndRow
            if oSheet.getCellByPosition(1, sopra+1).String != voce:
                lista_pt.append((sopra, sotto))
                #~ lista_pt.append((sopra+2, sotto-1))
    for el in lista_pt:
        oCellRangeAddr.StartRow = el[0]
        oCellRangeAddr.EndRow = el[1]
        oSheet.group(oCellRangeAddr,1)
        oSheet.getCellRangeByPosition(0, el[0], 0, el[1]).Rows.IsVisible=False
    _gotoCella(0, lrow)
    refresh(1)
    # ~oDoc.CurrentController.ZoomValue = zoom
    # ~MsgBox('Filtro attivato in base al codice!','Codice voce: ' + voce)

def struttura_ComputoM(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet.clearOutline()
    Rinumera_TUTTI_Capitoli2()
    struct(0)
    struct(1)
    struct(2)
    struct(3)

def struttura_Analisi(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet.clearOutline()
    struct(4)

def struttura_off(arg=None):
    '''Cancella la vista in struttura'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    lrow = Range2Cell()[1]
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet.clearOutline()
    oDoc.CurrentController.setFirstVisibleColumn(0)
    oDoc.CurrentController.setFirstVisibleRow(lrow-4)

def struct(l):
    ''' mette in vista struttura secondo categorie
    l { integer } : specifica il livello di categoria
    ### COMPUTO/VARIANTE ###
    0 = super-categoria
    1 = categoria
    2 = sotto-categoria
    3 = intera voce di misurazione
    ### ANALISI ###
    4 = simile all'elenco prezzi
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    iSheet = oSheet.RangeAddress.Sheet
    oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
    oCellRangeAddr.Sheet = iSheet

    if l == 0:
        stile = 'Livello-0-scritta'
        myrange =('Livello-0-scritta', 'Comp TOTALI',)
        Dsopra = 1
        Dsotto = 1
    elif l == 1:
        stile = 'Livello-1-scritta'
        myrange =('Livello-1-scritta', 'Livello-0-scritta', 'Comp TOTALI',)
        Dsopra = 1
        Dsotto = 1
    elif l == 2:
        stile = 'livello2 valuta'
        myrange =('livello2 valuta','Livello-1-scritta', 'Livello-0-scritta', 'Comp TOTALI',)
        Dsopra = 1
        Dsotto = 1
    elif l == 3:
        stile = 'Comp Start Attributo'
        myrange =('Comp End Attributo', 'Comp TOTALI',)
        Dsopra = 2
        Dsotto = 1

    elif l == 4: #Analisi di Prezzo
        stile = 'An-1_sigla'
        myrange =('An.1v-Att Start', 'Analisi_Sfondo',)
        Dsopra = 1
        Dsotto = -1
        # ~for n in(3, 5, 7):
            # ~oCellRangeAddr.StartColumn = n
            # ~oCellRangeAddr.EndColumn = n
            # ~oSheet.group(oCellRangeAddr,0)
            # ~oSheet.getCellRangeByPosition(n, 0, n, 0).Columns.IsVisible=False

    test = ultima_voce(oSheet)+2
    lista_cat = list()
    for n in range(0, test):
        if oSheet.getCellByPosition(0, n).CellStyle == stile:
            sopra = n+Dsopra
            for n in range(sopra+1, test):
                if oSheet.getCellByPosition(0, n).CellStyle in myrange:
                    sotto = n-Dsotto
                    lista_cat.append((sopra, sotto))
                    break
    for el in lista_cat:
        oCellRangeAddr.StartRow = el[0]
        oCellRangeAddr.EndRow = el[1]
        oSheet.group(oCellRangeAddr,1)
        oSheet.getCellRangeByPosition(0, el[0], 0, el[1]).Rows.IsVisible=False
########################################################################
def apri_manuale(arg=None):
    apri = createUnoService("com.sun.star.system.SystemShellExecute")
    apri.execute(LeenO_path() + '/MANUALE_LeenO.pdf',"", 0)
########################################################################
def autoexec_off(arg=None):
    toolbar_switch(1)
    #~ private:resource/toolbar/standardbar
    sUltimus = ''
    oDoc = XSCRIPTCONTEXT.getDocument()
    for el in ('Analisi di Prezzo', 'COMPUTO', 'VARIANTE', 'Elenco Prezzi', 'CONTABILITA'):
        try:
            oSheet = oDoc.Sheets.getByName(el)
            oSheet.getCellRangeByName("A1:AT1").CellBackColor = -1
            oSheet.getCellRangeByName("A1").String = '' 
        except:
            pass
########################################################################
class trun(threading.Thread):
    '''Avvia processi automatici ad intervalli definiti di tempo'''
    def __init__ (self):
        threading.Thread.__init__(self)
    def run(self):
        while True:
            # ~datarif = datetime.now()
            minuti = 60 * int(conf.read(path_conf, 'Generale', 'pausa_backup'))
            time.sleep(minuti)
            bak()
            # ~MsgBox('eseguita in ' + str((datetime.now() - datarif).total_seconds()) + ' secondi!','')
def autorun(arg=None):
    #~ global utsave
    utsave = trun()
    utsave._stop()
    utsave.start()
########################################################################
def autoexec(arg=None):
    '''
    questa è richiamata da New_File()
    '''
    bak0()
    autorun()
    ctx = XSCRIPTCONTEXT.getComponentContext()
    oGSheetSettings = ctx.ServiceManager.createInstanceWithContext("com.sun.star.sheet.GlobalSheetSettings", ctx)
    oGSheetSettings.UsePrinterMetrics = True #Usa i parametri della stampante per la formattazione del testo

#attiva 'copia di backup', ma dall'apertura successiva di LibreOffice
    node = GetRegistryKeyContent("/org.openoffice.Office.Common/Save/Document", True)
    node.CreateBackup = True
    node.commitChanges()
    
#Crea ed imposta leeno.conf SOLO SE NON PRESENTE.
    if sys.platform == 'win32':
        path = os.getenv("HOMEDRIVE") + os.getenv("HOMEPATH")
    else:
        path = os.getenv("HOME")
    if os.path.exists(path_conf) == False:
        os.makedirs(path_conf[:-11])
    config_default()
    if conf.read(path_conf, 'Generale', 'movedirection') == '0':
        oGSheetSettings.MoveDirection = 0
    else:
        oGSheetSettings.MoveDirection = 1
    oDoc = XSCRIPTCONTEXT.getDocument()
    oDoc.getSheets().getByName('copyright_LeenO').getCellRangeByName('A3').String = '# © 2001-2013 Bartolomeo Aimar - © 2014-'+str(datetime.now().year)+' Giuseppe Vizziello'
    oDoc.getSheets().getByName('S1').getCellRangeByName('G219').String = 'Copyright 2014-'+str(datetime.now().year)
    
    oLayout = oDoc.CurrentController.getFrame().LayoutManager
    if 'Esempio_' not in oDoc.getURL():
        oLayout.hideElement("private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_DEV")
#~ RegularExpressions Wildcards are mutually exclusive, only one can have the value TRUE.
#~ If both are set to TRUE via API calls then the last one set takes precedence.
    try:
        oDoc.Wildcards = False
    except:
        pass
    oDoc.RegularExpressions = False
    oDoc.CalcAsShown = True #precisione come mostrato
    oSheet = oDoc.getSheets().getByName('S1')
    adegua_tmpl() #esegue degli aggiustamenti del template
    toolbar_vedi()
    try:
        oUDP = oDoc.getDocumentProperties().getUserDefinedProperties()

        oSheet.getCellRangeByName('H194').Value = r_version_code()
        oSheet.getCellRangeByName('I194').Value = Lmajor
        oSheet.getCellRangeByName('J194').Value = Lminor
        
        oSheet.getCellRangeByName('H291').Value = oUDP.Versione
        oSheet.getCellRangeByName('I291').String = oUDP.Versione_LeenO.split('.')[0]
        oSheet.getCellRangeByName('J291').String = oUDP.Versione_LeenO.split('.')[1]

        oSheet.getCellRangeByName('H295').String = oUDP.Versione_LeenO.split('.')[0]
        oSheet.getCellRangeByName('I295').String = oUDP.Versione_LeenO.split('.')[1]
        oSheet.getCellRangeByName('J295').String = oUDP.Versione_LeenO.split('.')[2]
        
        oSheet.getCellRangeByName('K194').String = Lsubv
        oSheet.getCellRangeByName('H296').Value = Lmajor
        oSheet.getCellRangeByName('I296').Value = Lminor
        oSheet.getCellRangeByName('J296').String = Lsubv
    except:
        #~ chi("autoexec py")
        return
    #~ if len(oDoc.getURL()) != 0:
    # scegli cosa visualizzare all'avvio:
        #~ vedi = conf.read(path_conf, 'Generale', 'visualizza')
        #~ if vedi == 'Menù Principale':
            #~ DlgMain()
        #~ elif vedi == 'Dati Generali':
            #~ vai_a_variabili()
        #~ elif vedi in('Elenco Prezzi', 'COMPUTO'):
            #~ _gotoSheet(vedi)
#
########################################################################
def computo_terra_terra(arg=None):
    '''
    Settaggio base di configuazione colonne in COMPUTO e VARIANTE
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet.getCellRangeByPosition(33,0,1023,0).Columns.IsVisible = False
    set_larghezza_colonne()
########################################################################
def viste_nuove(sValori):
    '''
    sValori { string } : una tringa di configurazione della visibilità colonne
    permette di visualizzare/nascondere un set di colonne
    T = visualizza
    F = nasconde
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    n = 0
    for el in sValori:
        if el == 'T':
            oSheet.getCellByPosition(n, 2).Columns.IsVisible = True
        elif el == 'F':
            oSheet.getCellByPosition(n, 2).Columns.IsVisible = False
        n += 1
########################################################################
def set_larghezza_colonne(arg=None):
    '''
    regola la larghezza delle colonne a seconda della sheet
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name == 'Analisi di Prezzo':
        oSheet.getColumns().getByName('A').Columns.Width = 2100
        oSheet.getColumns().getByName('B').Columns.Width = 12000
        oSheet.getColumns().getByName('C').Columns.Width = 1600 
        oSheet.getColumns().getByName('D').Columns.Width = 2000
        oSheet.getColumns().getByName('E').Columns.Width = 3400
        oSheet.getColumns().getByName('F').Columns.Width = 3400
        oSheet.getColumns().getByName('G').Columns.Width = 2700
        oSheet.getColumns().getByName('H').Columns.Width = 2700
        oSheet.getColumns().getByName('I').Columns.Width = 2000
        oSheet.getColumns().getByName('J').Columns.Width = 2000
        oSheet.getColumns().getByName('K').Columns.Width = 2000
        oDoc.CurrentController.freezeAtPosition(0, 2)
    if oSheet.Name == 'CONTABILITA':
        viste_nuove('TTTFFTTTTTFTFTFTFTFTTFTTFTFTTTTFFFFFF')
        oSheet.getCellRangeByPosition(13,0,1023,0).Columns.Width = 1900 # larghezza colonne importi
        oSheet.getCellRangeByPosition(19,0,23,0).Columns.Width = 1000 # larghezza colonne importi
        oSheet.getCellRangeByPosition(51,0,1023,0).Columns.IsVisible = False # nascondi colonne
        oSheet.getColumns().getByName('A').Columns.Width = 600
        oSheet.getColumns().getByName('B').Columns.Width = 1500
        oSheet.getColumns().getByName('C').Columns.Width = 6300 #7800
        oSheet.getColumns().getByName('F').Columns.Width = 1300
        oSheet.getColumns().getByName('G').Columns.Width = 1300
        oSheet.getColumns().getByName('H').Columns.Width = 1300
        oSheet.getColumns().getByName('I').Columns.Width = 1300
        oSheet.getColumns().getByName('J').Columns.Width = 1700
        oSheet.getColumns().getByName('L').Columns.Width = 1700
        oSheet.getColumns().getByName('N').Columns.Width = 1900
        oSheet.getColumns().getByName('P').Columns.Width = 1900
        oSheet.getColumns().getByName('T').Columns.Width = 1000
        oSheet.getColumns().getByName('U').Columns.Width = 1000
        oSheet.getColumns().getByName('W').Columns.Width = 1000
        oSheet.getColumns().getByName('X').Columns.Width = 1000
        oSheet.getColumns().getByName('Z').Columns.Width = 1900
        oSheet.getColumns().getByName('AC').Columns.Width = 1700
        oSheet.getColumns().getByName('AD').Columns.Width = 1700
        oSheet.getColumns().getByName('AE').Columns.Width = 1700
        oSheet.getColumns().getByName('AX').Columns.Width = 1900
        oSheet.getColumns().getByName('AY').Columns.Width = 1900
        oDoc.CurrentController.freezeAtPosition(0, 3)
    if oSheet.Name in('COMPUTO', 'VARIANTE'):
        oSheet.getCellRangeByPosition(5,0,8,0).Columns.IsVisible = True # mostra colonne
        oSheet.getColumns().getByName('A').Columns.Width = 600
        oSheet.getColumns().getByName('B').Columns.Width = 1500
        oSheet.getColumns().getByName('C').Columns.Width = 6300 #7800
        oSheet.getColumns().getByName('F').Columns.Width = 1500
        oSheet.getColumns().getByName('G').Columns.Width = 1300
        oSheet.getColumns().getByName('H').Columns.Width = 1300
        oSheet.getColumns().getByName('I').Columns.Width = 1300
        oSheet.getColumns().getByName('J').Columns.Width = 1700
        oSheet.getColumns().getByName('L').Columns.Width = 1700
        oSheet.getColumns().getByName('S').Columns.Width = 1700
        oSheet.getColumns().getByName('AC').Columns.Width = 1700
        oSheet.getColumns().getByName('AD').Columns.Width = 1700
        oSheet.getColumns().getByName('AE').Columns.Width = 1700
        oDoc.CurrentController.freezeAtPosition(0, 3)
        viste_nuove('TTTFFTTTTTFTFFFFFFTFFFFFFFFFFFFFFFFFFFFFFFFFTT')
    if oSheet.Name == 'Elenco Prezzi':
        oSheet.getColumns().getByName('A').Columns.Width = 1600
        oSheet.getColumns().getByName('B').Columns.Width = 10000
        oSheet.getColumns().getByName('C').Columns.Width = 1500
        oSheet.getColumns().getByName('D').Columns.Width = 1500
        oSheet.getColumns().getByName('E').Columns.Width = 1600
        oSheet.getColumns().getByName('F').Columns.Width = 1500
        oSheet.getColumns().getByName('G').Columns.Width = 1500
        oSheet.getColumns().getByName('H').Columns.Width = 1600
        oSheet.getColumns().getByName('I').Columns.Width = 1200
        oSheet.getColumns().getByName('J').Columns.Width = 1200
        oSheet.getColumns().getByName('K').Columns.Width = 100
        oSheet.getColumns().getByName('L').Columns.Width = 1600
        oSheet.getColumns().getByName('M').Columns.Width = 1600
        oSheet.getColumns().getByName('N').Columns.Width = 1600
        oSheet.getColumns().getByName('O').Columns.Width = 100
        oSheet.getColumns().getByName('P').Columns.Width = 1600
        oSheet.getColumns().getByName('Q').Columns.Width = 1600
        oSheet.getColumns().getByName('R').Columns.Width = 1600
        oSheet.getColumns().getByName('S').Columns.Width = 100
        oSheet.getColumns().getByName('T').Columns.Width = 1600
        oSheet.getColumns().getByName('U').Columns.Width = 1600
        oSheet.getColumns().getByName('V').Columns.Width = 1600
        oSheet.getColumns().getByName('W').Columns.Width = 100
        oSheet.getColumns().getByName('X').Columns.Width = 1600
        oSheet.getColumns().getByName('Y').Columns.Width = 1600
        oSheet.getColumns().getByName('Z').Columns.Width = 1600
        oSheet.getColumns().getByName('AA').Columns.Width = 1600
        oDoc.CurrentController.freezeAtPosition(0, 3)
    adatta_altezza_riga(oSheet.Name)
########################################################################
def elimina_stili_cella(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    stili = oDoc.StyleFamilies.getByName('CellStyles').getElementNames()
    for el in stili:
        if oDoc.StyleFamilies.getByName('CellStyles').getByName(el).isInUse() == False:
            oDoc.StyleFamilies.getByName('CellStyles').removeByName(el)
########################################################################
def adegua_tmpl(arg=None):
    '''
    Mantengo la compatibilità con le vecchie versioni del template:
    - dal 200 parte di autoexec è in python
    - dal 203(LeenO 3.14.0 ha templ 202) introdotta la Super Categoria con nuovi stili di cella;
        sostituita la colonna "Tag A" con "Tag Super Cat"
    - dal 207 introdotta la colonna dei materiali in computo e contabilità
    - dal 209 cambia il nome di propietà del file in "Versione_LeenO"
    - dal 211 cambiano le formule del prezzo unitario e dell'importo in Computo e Contabilità
    - dal 212 vengono cancellate le celle che indicano il DCC nel foglio M1
    - dal 213 sposta il VediVoce nella colonna E
    - dal 214 assegna un'approssimazione diversa per ognuno dei valori di misurazione
    - dal 215 adegua del formule degli importi ai prezzi in %
    - dal 216 aggiorna le formule in CONTABILITA
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    #~ refresh(0)

#qui le cose da cambiare comunque
    
    flags = VALUE + DATETIME + STRING + ANNOTATION + FORMULA + OBJECTS + EDITATTR # FORMATTED + HARDATTR 

# LE VARIABILI NUOVE VANNO AGGIUNTE IN config_default()
    # cambiare stile http://bit.ly/2cDcCJI
    ver_tmpl = oDoc.getDocumentProperties().getUserDefinedProperties().Versione
    if ver_tmpl > 200:
        basic_LeenO('_variabili.autoexec') #rinvia a autoexec in basic
    adegua_a = 216 #VERSIONE CORRENTE
    if ver_tmpl < adegua_a:
        if DlgSiNo('''Vuoi procedere con l'adeguamento di questo file
alla versione di LeenO installata?

In caso affermativo dovrai attendere il completamento
dell'operazione che terminerà con un avviso.
''', "Richiesta") !=2:
            MsgBox('''Non avendo effettuato l'adeguamento del file alla versione di LeenO installata, potresti avere dei malfunzionamenti!''', 'Avviso!')
            return
        sproteggi_sheet_TUTTE()
        oDialogo_attesa = dlg_attesa("Adeguamento file alla versione di LeenO installata...")
        zoom = oDoc.CurrentController.ZoomValue
        oDoc.CurrentController.ZoomValue = 400
        attesa().start() #mostra il dialogo
#~ adeguo gli stili secondo il template corrente
        stili = oDoc.StyleFamilies.getByName('CellStyles').getElementNames()
        diz_stili = dict ()
############
# aggiungi stili di cella
        for el in ('comp 1-a PU', 'comp 1-a LUNG','comp 1-a LARG','comp 1-a peso','comp 1-a', 'Blu','Comp-Variante num sotto'):
            oStileCella = oDoc.createInstance("com.sun.star.style.CellStyle")
            if oDoc.StyleFamilies.getByName('CellStyles').hasByName(el) == False:
                oDoc.StyleFamilies.getByName('CellStyles').insertByName(el, oStileCella)
                oStileCella.ParentStyle = 'comp 1-a'
        for el in ('comp 1-a PU', 'comp 1-a LUNG','comp 1-a LARG','comp 1-a peso','comp 1-a', 'Blu','Comp-Variante num sotto'):
            oStileCella = oDoc.createInstance("com.sun.star.style.CellStyle")
            if oDoc.StyleFamilies.getByName("CellStyles").hasByName(el + ' ROSSO') == False:
                oDoc.StyleFamilies.getByName('CellStyles').insertByName(el + ' ROSSO', oStileCella)
                oStileCella.ParentStyle = 'comp 1-a'
                oDoc.StyleFamilies.getByName("CellStyles").getByName(el + ' ROSSO').CharColor = 16711680
############
# copia gli stili di cella dal template, ma non va perché tocca lavorare sulla FormatString - quando imparerò
        #~ sUrl = LeenO_path()+'/template/leeno/Computo_LeenO.ots'
        #~ styles = oDoc.getStyleFamilies()
        #~ styles.loadStylesFromURL(sUrl, list())
############
        oSheet = oDoc.getSheets().getByName('S1')
        oSheet.getCellRangeByName('S1.H291').Value = oDoc.getDocumentProperties().getUserDefinedProperties().Versione = adegua_a
        for el in oDoc.Sheets.ElementNames:
            oDoc.getSheets().getByName(el).IsVisible = True
            oDoc.CurrentController.setActiveSheet(oDoc.getSheets().getByName(el))
            # ~adatta_altezza_riga(el)
            oDoc.getSheets().getByName(el).IsVisible = False
        ### dal template 212
        flags = VALUE + DATETIME + STRING + ANNOTATION + FORMULA + OBJECTS + EDITATTR # FORMATTED + HARDATTR
        _gotoSheet('M1')
        oSheet = oDoc.getSheets().getByName('M1')
        oSheet.getCellRangeByName('B23:E30').clearContents(flags)
        oSheet.getCellRangeByName('B23:E30').CellStyle = 'M1 scritte noP'
        ### dal template 208
        #> adegua le formule delle descrizioni di voci
        _gotoSheet('S1')
        oSheet = oDoc.getSheets().getByName('S1')
        oSheet.getCellRangeByName('G334').String = '[Computo e Variante] Vedi Voce: PRIMI caratteri della voce'
        oSheet.getCellRangeByName('H334').Value = 50
        oSheet.getCellRangeByName('I334').String = "Quanti caratteri della descrizione vuoi visualizzare usando il Vedi Voce?"
        oSheet.getCellRangeByName('G335').String = '[Contabilità] Descrizioni abbreviate: PRIMI caratteri della voce'
        oSheet.getCellRangeByName('H335').Value = 100
        oSheet.getCellRangeByName('I335').String = "Quanti caratteri vuoi visualizzare partendo dall'INIZIO della descrizione?"
        oSheet.getCellRangeByName('G336').String = 'Descrizioni abbreviate: primi caratteri della voce'
        oSheet.getCellRangeByName('H336').Value = 120
        oSheet.getCellRangeByName('I336').String = "[Contabilità] Descrizioni abbreviate: ULTIMI caratteri della voce"
        oSheet.getCellRangeByName('G337').String = 'Descrizioni abbreviate: primi caratteri della voce'
        oSheet.getCellRangeByName('H337').Value = 100
        oSheet.getCellRangeByName('I337').String = "Quanti caratteri vuoi visualizzare partendo dall'INIZIO della descrizione?"
        oSheet.getCellRangeByName('G338').String = 'Descrizioni abbreviate: ultimi caratteri della voce'
        oSheet.getCellRangeByName('H338').Value = 120
        oSheet.getCellRangeByName('I338').String = "Quanti caratteri vuoi visualizzare partendo dalla FINE della descrizione?"
        oSheet.getCellRangeByName('L25').String = ''
        oSheet.getCellRangeByName('G297:G338').CellStyle = 'Setvar b'
        oSheet.getCellRangeByName('H297:H338').CellStyle = 'Setvar C'
        oSheet.getCellRangeByName('I297:I338').CellStyle = 'Setvar D'
        oSheet.getCellRangeByName('H319:H326').CellStyle = 'Setvar C_3'
        oSheet.getCellRangeByName('H311').CellStyle = 'Setvar C_3'
        oSheet.getCellRangeByName('H323').CellStyle = 'Setvar C'
        oDoc.StyleFamilies.getByName("CellStyles").getByName('Setvar C_3').NumberFormat = getNumFormat('0,00%') #percentuale
        #< adegua le formule delle descrizioni di voci
#dal 209 cambia nome di custom propierty
        oUDP = oDoc.getDocumentProperties().getUserDefinedProperties()
        if oUDP.getPropertySetInfo().hasPropertyByName("Versione LeenO"): oUDP.removeProperty('Versione LeenO')
        if oUDP.getPropertySetInfo().hasPropertyByName("Versione_LeenO"): oUDP.removeProperty('Versione_LeenO')
        oUDP.addProperty('Versione_LeenO', MAYBEVOID + REMOVEABLE + MAYBEDEFAULT, str(Lmajor) +'.'+ str(Lminor) +'.x')
        for el in ('COMPUTO', 'VARIANTE'):
            if oDoc.getSheets().hasByName(el) == True:
                _gotoSheet(el)
                oSheet = oDoc.getSheets().getByName(el)
                test = getLastUsedCell(oSheet).EndRow+1
                rigenera_tutte()
                # 214 aggiorna stili di cella per ogni colonna
                for y in range(0, test):
                    if 'comp 1-a' in oSheet.getCellByPosition(2, y).CellStyle:
                        if oSheet.getCellByPosition(9, y).Value < 0:
                            oSheet.getCellByPosition(2, y).CellStyle = 'comp 1-a ROSSO'
                            oSheet.getCellByPosition(5, y).CellStyle = 'comp 1-a PU ROSSO'
                            oSheet.getCellByPosition(6, y).CellStyle = 'comp 1-a LUNG ROSSO'
                            oSheet.getCellByPosition(7, y).CellStyle = 'comp 1-a LARG ROSSO'
                            oSheet.getCellByPosition(8, y).CellStyle = 'comp 1-a peso ROSSO'
                        #~  == 'comp 1-a':
                        else:
                            oSheet.getCellByPosition(5, y).CellStyle = 'comp 1-a PU'
                            oSheet.getCellByPosition(6, y).CellStyle = 'comp 1-a LUNG'
                            oSheet.getCellByPosition(7, y).CellStyle = 'comp 1-a LARG'
                            oSheet.getCellByPosition(8, y).CellStyle = 'comp 1-a peso'
                for y in range(0, test):
                    # aggiorna formula vedi voce #214
                    if oSheet.getCellByPosition(2, y).Type.value == 'FORMULA' and oSheet.getCellByPosition(2, y).CellStyle == 'comp 1-a' and \
                    oSheet.getCellByPosition(5, y).Type.value == 'FORMULA':
                        try:
                            vRif = int(oSheet.getCellByPosition(5, y).Formula.split('=J$')[-1])-1
                        except:
                            vRif = int(oSheet.getCellByPosition(5, y).Formula.split('=J')[-1])-1
                        if oSheet.getCellByPosition(9, y).Value < 0:
                            _gotoCella(2, y)
                            inverti = 1
                        oSheet.getCellByPosition(5, y).String = ''
                        vedi_voce_xpwe(y, vRif)
                        try:
                            inverti
                            inverti_segno()
                        except:
                            pass
                    if '=J' in oSheet.getCellByPosition(5, y).Formula:
                        if '$' in oSheet.getCellByPosition(5, y).Formula:
                            n = oSheet.getCellByPosition(5, y).Formula.split('$')[1]
                        else:
                            n = oSheet.getCellByPosition(5, y).Formula.split('J')[1]
                        oSheet.getCellByPosition(5, y).Formula = '=J$' + n
                    #cambia le formule di prezzo unitario e importo
        if oDoc.getSheets().hasByName('CONTABILITA'):
            oSheet = oDoc.getSheets().getByName('CONTABILITA')
            oSheet.getCellRangeByName('A2').Formula = '=P2'
            test = getLastUsedCell(oSheet).EndRow+1
            for y in range(0, test):
                if 'comp 1-a' in oSheet.getCellByPosition(2, y).CellStyle:
                    if oSheet.getCellByPosition(9, y).Value < 0:
                        oSheet.getCellByPosition(2, y).CellStyle = 'comp 1-a ROSSO'
                        oSheet.getCellByPosition(5, y).CellStyle = 'comp 1-a PU ROSSO'
                        oSheet.getCellByPosition(6, y).CellStyle = 'comp 1-a LUNG ROSSO'
                        oSheet.getCellByPosition(7, y).CellStyle = 'comp 1-a LARG ROSSO'
                        oSheet.getCellByPosition(8, y).CellStyle = 'comp 1-a peso ROSSO'
                    #~  == 'comp 1-a':
                    else:
                        oSheet.getCellByPosition(5, y).CellStyle = 'comp 1-a PU'
                        oSheet.getCellByPosition(6, y).CellStyle = 'comp 1-a LUNG'
                        oSheet.getCellByPosition(7, y).CellStyle = 'comp 1-a LARG'
                        oSheet.getCellByPosition(8, y).CellStyle = 'comp 1-a peso'
            for n in range(0, test):
                if oSheet.getCellByPosition(1, n).CellStyle == 'comp Art-EP_R':
                    oSheet.getCellByPosition(8, n).CellStyle = 'Comp-Bianche in mezzo_R'
                if oSheet.getCellByPosition(9, n).String == '': oSheet.getCellByPosition(9, n).String == ''
                else:
                    oSheet.getCellByPosition(9, n).Formula =='=IF(PRODUCT(E' + str(n+1) + ':I' + str(n+1) + ')=0;"";PRODUCT(E' + str(n+1) + ':I' + str(n+1) + '))'
                if oSheet.getCellByPosition(11, n).String == '':
                    oSheet.getCellByPosition(11, n).String == ''
                else:
                    oSheet.getCellByPosition(11, n).Formula =='=IF(PRODUCT(E' + str(n+1) + ':I' + str(n+1) + ')=0;"";PRODUCT(E' + str(n+1) + ':I' + str(n+1) + '))'
#~ contatta il canale Telegram
#~ https://t.me/leeno_computometrico''', 'AVVISO!')
        ########################################################################
        ### RINVIO L'ADEGUAMENTO DELLA CONTABILITÀ A QUANDO L'AVRÒ COMPLETATA
        ########################################################################
        _gotoSheet('S5')
        oSheet = oDoc.getSheets().getByName('S5')
        oSheet.getCellRangeByPosition(0, 0, 250, getLastUsedCell(oSheet).EndRow).clearContents(EDITATTR + FORMATTED + HARDATTR)
        oSheet.getCellRangeByName('C10').Formula ='=IF(LEN(VLOOKUP(B10;elenco_prezzi;2;FALSE()))<($S1.$H$337+$S1.$H$338);VLOOKUP(B10;elenco_prezzi;2;FALSE());CONCATENATE(LEFT(VLOOKUP(B10;elenco_prezzi;2;FALSE());$S1.$H$337);" [...] ";RIGHT(VLOOKUP(B10;elenco_prezzi;2;FALSE());$S1.$H$338)))'
        oSheet.getCellRangeByName('C24').Formula ='=IF(LEN(VLOOKUP(B24;elenco_prezzi;2;FALSE()))<($S1.$H$335+$S1.$H$336);VLOOKUP(B24;elenco_prezzi;2;FALSE());CONCATENATE(LEFT(VLOOKUP(B24;elenco_prezzi;2;FALSE());$S1.$H$335);" [...] ";RIGHT(VLOOKUP(B24;elenco_prezzi;2;FALSE());$S1.$H$336)))'
        oSheet.getCellRangeByName('I24').CellStyle = 'Comp-Bianche in mezzo_R'
        oSheet.getCellRangeByName('S12').Formula ='=IF(VLOOKUP(B10;elenco_prezzi;3;FALSE())="%";J12*L12/100;J12*L12)'
        #~ oSheet.getCellRangeByName('S12').Formula ='=J12*L12'
        oSheet.getCellRangeByName('P27').Formula ='=IF(VLOOKUP(B24;elenco_prezzi;3;FALSE())="%";J27*N27/100;J27*N27)'
        #~ oSheet.getCellRangeByName('P27').Formula ='=N27*J27'
        ###
        oSheet.getCellRangeByName('AC12').Formula = '=S12-AE12'
        oSheet.getCellRangeByName('AC12').CellStyle = 'Comp-sotto euri'
        oSheet.getCellRangeByName('AC27').Formula = '=P27-AE27'
        oSheet.getCellRangeByName('AC27').CellStyle = 'Comp-sotto euri'
        
        oSheet.getCellRangeByName('J26').Formula = '=IF(SUBTOTAL(9;J24:J26)<0;"";SUBTOTAL(9;J24:J26))'
        oSheet.getCellRangeByName('L26').Formula = '=IF(SUBTOTAL(9;L24:L26)<0;"";SUBTOTAL(9;L24:L26))'
        oSheet.getCellRangeByName('L26').CellStyle = 'Comp-Variante num sotto ROSSO'

        for el in('CONTABILITA', 'VARIANTE', 'COMPUTO'):
            if oDoc.getSheets().hasByName(el) == True:
                _gotoSheet(el)
                oSheet = oDoc.getSheets().getByName(el)
                # sposto il vedivoce nella colonna E
                fine = getLastUsedCell(oSheet).EndRow
                oSheet.getCellRangeByPosition(3, 0, 4, fine).clearContents(HARDATTR)
                for n in range(0, fine):
                    if '=CONCATENATE("' in oSheet.getCellByPosition(2,n).Formula and oSheet.getCellByPosition(4, n).Type.value == 'EMPTY':
                        oSheet.getCellByPosition(4, n).Formula = oSheet.getCellByPosition(5, n).Formula
                        oSheet.getCellByPosition(5, n).String = ''
                        oSheet.getCellByPosition(9, n).Formula='=IF(PRODUCT(E' + str(n+1) + ':I' + str(n+1) + ')=0;"";PRODUCT(E' + str(n+1) + ':I' + str(n+1) + '))'
                # sposto il vedivoce nella colonna E/
                if oSheet.Name != 'CONTABILITA': Rinumera_TUTTI_Capitoli2()
                oSheet.getCellByPosition(31,2).String = 'Super Cat'
                oSheet.getCellByPosition(32,2).String = 'Cat'
                oSheet.getCellByPosition(33,2).String = 'Sub Cat'
                oSheet.getCellByPosition(28,2).String = 'Materiali\ne Noli €'
                n = ultima_voce(oSheet)
                oSheet.getCellByPosition(28,n+1).Formula = '=SUBTOTAL(9;AC3:AC'+ str(n+2)
                lrow = 0
                while lrow < n:
                    try:
                        sStRange = Circoscrive_Voce_Computo_Att(lrow)
                        sopra = sStRange.RangeAddress.StartRow
                        sotto = sStRange.RangeAddress.EndRow
                        if oSheet.Name == 'CONTABILITA':
                            oSheet.getCellByPosition(28,sotto).Formula = '=P' + str(sotto+1) + '-AE' + str(sotto+1)
                            oSheet.getCellByPosition(9,sotto-1).Formula = '=IF(SUBTOTAL(9;J' + str(sopra+2) + ':J' + str(sotto) + ')<0;"";SUBTOTAL(9;J' + str(sopra+2) + ':J' + str(sotto) + '))'
                            oSheet.getCellByPosition(11,sotto-1).Formula = '=IF(SUBTOTAL(9;L' + str(sopra+2) + ':L' + str(sotto) + ')<0;"";SUBTOTAL(9;L' + str(sopra+2) + ':L' + str(sotto) + '))'
                            for x in range (sopra+1, sotto-1):
                                if oSheet.getCellByPosition(2, x).CellStyle == 'comp 1-a':
                                    oSheet.getCellByPosition(5, x).CellStyle = 'comp 1-a PU'
                                    oSheet.getCellByPosition(6, x).CellStyle = 'comp 1-a LUNG'
                                    oSheet.getCellByPosition(7, x).CellStyle = 'comp 1-a LARG'
                                    oSheet.getCellByPosition(8, x).CellStyle = 'comp 1-a peso'
                                    oSheet.getCellByPosition(9, x).CellStyle = 'Blu'
                                    oSheet.getCellByPosition(11, x).CellStyle = 'Blu'
                                    oSheet.getCellByPosition(11, sotto-1).CellStyle = 'Comp-Variante num sotto ROSSO'
                                    oSheet.getCellByPosition(13, sotto).CellStyle = 'comp sotto Unitario'
                                    oSheet.getCellByPosition(15, sotto).CellStyle = 'comp sotto Euro Originale'
                                    oSheet.getCellByPosition(17, sotto).CellStyle = 'comp sotto Euro Originale'
                                if oSheet.getCellByPosition(9, x).String == '':
                                    oSheet.getCellByPosition(9, x).String = ''
                                else:
                                    oSheet.getCellByPosition(11, x).String = ''
                        else:
                            oSheet.getCellByPosition(28,sotto).Formula = '=S' + str(sotto+1) + '-AE' + str(sotto+1)
                        oSheet.getCellByPosition(28,sotto).CellStyle = 'Comp-sotto euri'
                        lrow =next_voice(lrow,1)
                    except:
                        lrow += 1
        oDoc.getSheets().getByName('S1').IsVisible = False
        for el in oDoc.Sheets.ElementNames:
            oDoc.CurrentController.setActiveSheet(oDoc.getSheets().getByName(el))
            adatta_altezza_riga(el)
        oDoc.CurrentController.ZoomValue = zoom
        _gotoSheet('COMPUTO')
        oDialogo_attesa.endExecute() #chiude il dialogo
        MsgBox("Adeguamento del file completato con successo.", "Avviso")
#~ ########################################################################
def r_version_code(arg=None):
    if os.altsep:
        code_file = uno.fileUrlToSystemPath(LeenO_path() + os.altsep + 'leeno_version_code')
    else:
        code_file = uno.fileUrlToSystemPath(LeenO_path() + os.sep + 'leeno_version_code')
    f = open(code_file, 'r')
    return f.readline().split('-')[-1]
########################################################################
def XPWE_export_run(arg=None):
    '''
    Viasualizza il menù export/import XPWE
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    if oDoc.getSheets().hasByName('S2') == False: return
    psm = uno.getComponentContext().ServiceManager
    dp = psm.createInstance("com.sun.star.awt.DialogProvider")
    Dialog_XPWE = dp.createDialog("vnd.sun.star.script:UltimusFree2.Dialog_XPWE?language=Basic&location=application")
    oSheet = oDoc.CurrentController.ActiveSheet
    oDialog1Model = Dialog_XPWE.Model
    for el in ("COMPUTO", "VARIANTE", "CONTABILITA"):
        try:
            importo = oDoc.getSheets().getByName(el).getCellRangeByName('A2').String
            if el == 'COMPUTO':  Dialog_XPWE.getControl(el).Label  = 'Computo: €: ' + importo
            if el == 'VARIANTE':  Dialog_XPWE.getControl(el).Label  = 'Variante: €: ' + importo
            if el == 'CONTABILITA':  Dialog_XPWE.getControl(el).Label  = 'Contabilità: €: ' + importo
            Dialog_XPWE.getControl(el).Enable = True
        except:
            Dialog_XPWE.getControl(el).Enable = False
    Dialog_XPWE.Title = 'Esportazione XPWE'
    try:
        Dialog_XPWE.getControl(oSheet.Name).State = True
    except:
        pass
    Dialog_XPWE.getControl('FileControl1').Text = 'C:\\tmp\\prova.txt'#uno.fileUrlToSystemPath(oDoc.getURL())
    # ~systemPathToFileUrl
    lista = list()
    #~ Dialog_XPWE.execute()
    # ~try:
        # ~Dialog_XPWE.execute()
    # ~except:
        # ~pass
    if Dialog_XPWE.execute() ==1:
        for el in ("COMPUTO", "VARIANTE", "CONTABILITA"):
            if Dialog_XPWE.getControl(el).State == 1:
                lista.append (el)
                pass
    out_file = filedia('Salva con nome...', '*.xpwe', 1)
    testo = '\n'
    for el in lista:
        XPWE_out(el, out_file)
        testo = testo + '● ' + out_file +'-'+ el + '.xpwe\n\n'
    MsgBox('Esportazione in formato XPWE eseguita con successo su:\n' + testo ,'Avviso.')
def scegli_elaborato(titolo):
    '''
    Permetta la scelta dell'elaborato da trattare e restituisce il suo nome
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    psm = uno.getComponentContext().ServiceManager
    dp = psm.createInstance("com.sun.star.awt.DialogProvider")
    oDlgXLO = dp.createDialog("vnd.sun.star.script:UltimusFree2.Dialog_XLO?language=Basic&location=application")
    oDialog1Model = oDlgXLO.Model
    oDlgXLO.Title = titolo #'Menù import XPWE'

    for el in ("COMPUTO", "VARIANTE", "CONTABILITA"):
        try:
            importo = oDoc.getSheets().getByName(el).getCellRangeByName('A2').String
            if el == 'COMPUTO':  oDlgXLO.getControl("CME_XLO").Label     = '~Computo:     € ' + importo
            if el == 'VARIANTE':  oDlgXLO.getControl("VAR_XLO").Label    = '~Variante:    € ' + importo
            if el == 'CONTABILITA': oDlgXLO.getControl("CON_XLO").Label  = 'C~ontabilità: € ' + importo
            #~ else:
                #~ oDlgXLO.getControl("CON_XLO").Label  = 'Contabilità: €: 0,0'
        except:
            pass

    if oDlgXLO.execute() ==1:
        if oDlgXLO.getControl("CME_XLO").State == True:
            elaborato ='COMPUTO'
        elif  oDlgXLO.getControl("VAR_XLO").State == True:
            elaborato ='VARIANTE'
        elif  oDlgXLO.getControl("CON_XLO").State == True:
            elaborato ='CONTABILITA'
        elif  oDlgXLO.getControl("EP_XLO").State == True:
            elaborato ='Elenco'
    return elaborato
########################################################################
def chiudi_dialoghi(event=None):
    if event:
        event.Source.Context.endExecute()
    return
########################################################################
def DlgMain(arg=None):
    '''
    Visualizza il menù principaledialog_fil
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    psm = uno.getComponentContext().ServiceManager
    oSheet = oDoc.CurrentController.ActiveSheet
    x = Range2Cell()[0]
    y = Range2Cell()[1]
    if oDoc.getURL() != '':
        for el in ('Analisi di Prezzo', 'COMPUTO', 'VARIANTE', 'Elenco Prezzi', 'CONTABILITA'):
            try:
                oSheet = oDoc.Sheets.getByName(el)
                if sUltimus == uno.fileUrlToSystemPath(oDoc.getURL()):
                    oSheet.getCellRangeByName("A1:AT1").CellBackColor = 16773632 #13434777
                    oSheet.getCellRangeByName("A1").String = 'DCC'
                else:
                    oSheet.getCellRangeByName("A1:AT1").CellBackColor = -1
                    oSheet.getCellRangeByName("A1").String = '' 
            except:
                pass
    if oDoc.getSheets().hasByName('S2') == False:
        for bar in GetmyToolBarNames:
            toolbar_on(bar, 0)
        if len(oDoc.getURL())==0 and \
        getLastUsedCell(oSheet).EndColumn ==0 and \
        getLastUsedCell(oSheet).EndRow ==0:
            oDoc.close(True)
        New_file.computo()
    toolbar_vedi()
    dp = psm.createInstance("com.sun.star.awt.DialogProvider")
    global oDlgMain
    oDlgMain = dp.createDialog("vnd.sun.star.script:UltimusFree2.DlgMain?language=Basic&location=application")
    oDialog1Model = oDlgMain.Model
    oDlgMain.Title = 'Menù Principale (Ctrl+0)'
    
    sUrl = LeenO_path()+'/icons/Immagine.png'
    oDlgMain.getModel().ImageControl1.ImageURL=sUrl

    if os.altsep:
        code_file = uno.fileUrlToSystemPath(LeenO_path() + os.altsep + 'leeno_version_code')
    else:
        code_file = uno.fileUrlToSystemPath(LeenO_path() + os.sep + 'leeno_version_code')
    f = open(code_file, 'r')
    
    sString = oDlgMain.getControl("CommandButton13")
    try:
        if sUltimus == uno.fileUrlToSystemPath(oDoc.getURL()):
            sString.setEnable(False)
        else:
            sString.setEnable(True)
    except:
        pass

    sString = oDlgMain.getControl("Label12")
    sString.Text = f.readline()
    
    sString = oDlgMain.getControl("Label_DDC")
    sString.Text = sUltimus 

    sString = oDlgMain.getControl("Label1")
    sString.Text = str(Lmajor) +'.'+ str(Lminor) +'.'+ Lsubv

    sString = oDlgMain.getControl("Label2")
    try:
        oSheet = oDoc.Sheets.getByName('S1')
    except:
        return
    sString.Text = oDoc.getDocumentProperties().getUserDefinedProperties().Versione #oSheet.getCellByPosition(7, 290).String
    #~ sString = oDlgMain.getControl("Label14") #Oggetto del lavoro
    sString = oDlgMain.getControl("TextField1") #Oggetto del lavoro
    
    sString.Text = oDoc.Sheets.getByName('S2').getCellRangeByName('C3').String
    try:
        oSheet = oDoc.Sheets.getByName('COMPUTO')
        sString = oDlgMain.getControl("Label8")
        sString.Text = "€ {:,.2f}".format(oSheet.getCellByPosition(18, 1).Value)
    except:
        pass
    try:
        oSheet = oDoc.Sheets.getByName('VARIANTE')
        sString = oDlgMain.getControl("Label5")
        sString.Text = "€ {:,.2f}".format(oSheet.getCellByPosition(18, 1).Value)
    except:
        pass
    try:
        oSheet = oDoc.Sheets.getByName('CONTABILITA')
        sString = oDlgMain.getControl("Label9")
        sString.Text = "€ {:,.2f}".format(oSheet.getCellByPosition(15, 1).Value)
    except:
        pass
    #~ sString = oDlgMain.getControl("ComboBox1")
    #~ sString.Text = conf.read(path_conf, 'Generale', 'visualizza')
    oDlgMain.getControl('CheckBox1').State = int(conf.read(path_conf, 'Generale', 'dialogo'))
    _gotoCella(x, y)
    oDlgMain.execute()
    if oDlgMain.getControl('CheckBox1').State == 1:
        conf.write(path_conf, 'Generale', 'dialogo', '1')
        #~ sString = oDlgMain.getControl("ComboBox1")
        #~ conf.write(path_conf, 'Generale', 'visualizza', sString.getText())
    else:
        conf.write(path_conf, 'Generale', 'dialogo', '0')
        #~ conf.write(path_conf, 'Generale', 'visualizza', 'Senza Menù')
    oDoc.Sheets.getByName('S2').getCellRangeByName('C3').String = oDlgMain.getControl("TextField1").Text
    return
########################################################################
def InputBox(sCella='', t=''):
    '''
    sCella  { string } : stringa di default nella casella di testo
    t       { string } : titolo del dialogo
    Viasualizza un dialogo di richiesta testo
    '''

    psm = uno.getComponentContext().ServiceManager
    dp = psm.createInstance("com.sun.star.awt.DialogProvider")
    oDialog1 = dp.createDialog("vnd.sun.star.script:UltimusFree2.DlgTesto?language=Basic&location=application")
    oDialog1Model = oDialog1.Model

    oDialog1Model.Title = t

    sString = oDialog1.getControl("TextField1")
    sString.Text = sCella

    if oDialog1.execute()==0:
        return
    else:
        return sString.Text
########################################################################
def hide_error(lErrori, icol):
    '''
    lErrori  { tuple } : nome dell'errore es.: '#DIV/0!'
    icol { integer } : indice di colonna della riga da nascondere
    Viasualizza o nascondi una toolbar
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    zoom = oDoc.CurrentController.ZoomValue
    oDoc.CurrentController.ZoomValue = 400
    oSheet = oDoc.CurrentController.ActiveSheet
    #~ oSheet.clearOutline()
    n = 3
    test = ultima_voce(oSheet)+1
    iSheet = oSheet.RangeAddress.Sheet
    oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
    oCellRangeAddr.Sheet = iSheet
    for i in range(n, test):
        for el in lErrori:
            if oSheet.getCellByPosition(icol, i).String == el:
                oCellRangeAddr.StartRow = i
                oCellRangeAddr.EndRow = i
                oSheet.group(oCellRangeAddr,1)
                oSheet.getCellByPosition(0, i).Rows.IsVisible = False
    oDoc.CurrentController.ZoomValue = zoom
########################################################################
def bak0(arg=None):
    '''
    Fa il backup del file di lavoro all'aperura. 
    '''
    tempo = ''.join(''.join(''.join(str(datetime.now()).split('.')[0].split(' ')).split('-')).split(':'))[:12]
    oDoc = XSCRIPTCONTEXT.getDocument()
    orig = oDoc.getURL()
    dest = '.'.join(os.path.basename(orig).split('.')[0:-1])+ '.bak.ods'
    dir_bak = os.path.dirname(oDoc.getURL()) + '/leeno-bk/'
    filename = '.'.join(os.path.basename(orig).split('.')[0:-1])+ '-'
    if len(orig) ==0:
        return
    if not os.path.exists(uno.fileUrlToSystemPath(dir_bak)):
        os.makedirs(uno.fileUrlToSystemPath(dir_bak))
    orig = uno.fileUrlToSystemPath(orig)
    dest = uno.fileUrlToSystemPath(dest)
    shutil.copyfile(orig, uno.fileUrlToSystemPath(dir_bak) + dest)
########################################################################
def bak(arg=None):
    '''
    Esegue un numero definito di backup durante il lavoro.
    '''
    tempo = ''.join(''.join(''.join(str(datetime.now()).split('.')[0].split(' ')).split('-')).split(':'))[:12]
    oDoc = XSCRIPTCONTEXT.getDocument()
    orig = oDoc.getURL()
    dest = '.'.join(os.path.basename(orig).split('.')[0:-1])+ '-' + tempo + '.ods'
    dir_bak = os.path.dirname(oDoc.getURL()) + '/leeno-bk/'
    filename = '.'.join(os.path.basename(orig).split('.')[0:-1])+ '-'
    if len(orig) ==0:
        return
    if not os.path.exists(uno.fileUrlToSystemPath(dir_bak)):
        os.makedirs(uno.fileUrlToSystemPath(dir_bak))
    orig = uno.fileUrlToSystemPath(orig)
    dest = uno.fileUrlToSystemPath(dest)
    oDoc.storeToURL(dir_bak + dest, list())
    lista = os.listdir(uno.fileUrlToSystemPath(dir_bak))
    n =0
    nb = int(conf.read(path_conf, 'Generale', 'copie_backup')) #numero di copie)
    for el in reversed (lista):
        if filename in el:
            if n > nb-1:
                os.remove(uno.fileUrlToSystemPath(dir_bak)+el)
            n += 1
    return
########################################################################
# Scrive un file.
def w_version_code(arg=None):
    '''
    scrive versione e timestamp nel file leeno_version_code
    '''
    tempo = ''.join(''.join(''.join(str(datetime.now()).split('.')[0].split(' ')).split('-')).split(':'))

    if os.altsep:
        out_file = uno.fileUrlToSystemPath(LeenO_path() + os.altsep + 'leeno_version_code')
    else:
        out_file = uno.fileUrlToSystemPath(LeenO_path() + os.sep + 'leeno_version_code')
        
    of = open(out_file,'w')
    of.write(str(Lmajor) +'.'+ str(Lminor) +'.'+ Lsubv +'-'+ tempo[:-2])
    of.close()
    return str(Lmajor) +'.'+ str(Lminor) +'.'+ Lsubv +'-'+ tempo[:-2]
########################################################################
def toolbar_vedi(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    try:
        oLayout = oDoc.CurrentController.getFrame().LayoutManager

        if conf.read(path_conf, 'Generale', 'toolbar_contestuali') == '0':
            for bar in GetmyToolBarNames: #toolbar sempre visibili
                toolbar_on(bar)
        else:
            for bar in GetmyToolBarNames: #toolbar contestualizzate
                toolbar_on(bar, 0)
        #~ oLayout.hideElement("private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_DEV")
        toolbar_ordina()
        oLayout.showElement("private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar")
        nSheet = oDoc.CurrentController.ActiveSheet.Name

        if nSheet == 'Elenco Prezzi':
            toolbar_on('private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_ELENCO')
        elif nSheet == 'Analisi di Prezzo':
            toolbar_on('private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_ANALISI')
        #~ elif nSheet == 'CONTABILITA':
            #~ toolbar_on('private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_CONTABILITA')
        elif nSheet in('COMPUTO','VARIANTE','CONTABILITA'):
            toolbar_on('private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_COMPUTO')
            toolbar_on('private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_CONTABILITA')
        fissa()
    except:
        pass
########################################################################
def grid_switch(arg=None):
    '''Mostra / nasconde griglia'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oDoc.CurrentController.ShowGrid = not oDoc.CurrentController.ShowGrid
#######################################################################
def toolbar_switch(arg=1):
    '''Nasconde o mostra le toolbar di Libreoffice.'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oLayout = oDoc.CurrentController.getFrame().LayoutManager
    for el in oLayout.Elements:
        if el.ResourceURL not in GetmyToolBarNames +('private:resource/menubar/menubar', 'private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_DEV', 'private:resource/toolbar/findbar','private:resource/statusbar/statusbar',):
            #~ if oLayout.isElementVisible(el.ResourceURL):
            if arg == 0:
                oLayout.hideElement(el.ResourceURL)
            else:
                oLayout.showElement(el.ResourceURL)
    return
    #~ private:resource/toolbar/standardbar
def toolbar_on(toolbarURL, flag=1):
    '''
    toolbarURL  { string } : indirizzo toolbar
    flag { integer } : 1 = acceso; 0 = spento
    Viasualizza o nascondi una toolbar
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oLayout = oDoc.CurrentController.getFrame().LayoutManager
    if flag == 0:
        oLayout.hideElement(toolbarURL)
    else:
        oLayout.showElement(toolbarURL)
#######################################################################
from com.sun.star.awt import Point
def toolbar_ordina(arg=None):
    #~ https://www.openoffice.org/api/docs/common/ref/com/sun/star/ui/DockingArea.html
    oDoc = XSCRIPTCONTEXT.getDocument()
    oLayout = oDoc.CurrentController.getFrame().LayoutManager
    i = 0
    for bar in GetmyToolBarNames:
        oLayout.dockWindow(bar, 'DOCKINGAREA_TOP', Point(i, 4))
        i += 1
    oLayout.dockWindow('private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_DEV', 'DOCKINGAREA_RIGHT', Point(0, 0))
#######################################################################
def make_pack(arg=None, bar=0):
    '''
    bar { integer } : toolbar 0=spenta 1=accesa
    Pacchettizza l'estensione in duplice copia: LeenO.oxt e LeenO-yyyymmddhhmm.oxt
    in una directory precisa(per ora - da parametrizzare)
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    try:
        if oDoc.getSheets().getByName('S1').getCellByPosition(7,338).String == '':
            src_oxt ='_LeenO'
        else:
            src_oxt = oDoc.getSheets().getByName('S1').getCellByPosition(7,338).String
    except:
        pass
    tempo = w_version_code()
    if bar == 0:
        oDoc = XSCRIPTCONTEXT.getDocument()
        for bar in GetmyToolBarNames: #toolbar sempre visibili
            toolbar_on(bar, 0)
        oLayout = oDoc.CurrentController.getFrame().LayoutManager
        oLayout.hideElement("private:resource/toolbar/addon_ULTIMUS_3.OfficeToolBar_DEV")
    oxt_path = uno.fileUrlToSystemPath(LeenO_path())
    if sys.platform == 'linux' or sys.platform == 'darwin':
        dest = '/media/giuserpe/PRIVATO/_dwg/ULTIMUSFREE/_SRC/leeno/src/Ultimus.oxt'
        if not os.path.exists(dest):
            try:
                dest = os.getenv("HOME") +'/'+ src_oxt +'/leeno/src/Ultimus.oxt/'
                os.makedirs(dest)
                #~ os.makedirs(os.getenv("HOME") +'/'+ src_oxt +'/bin/')
                os.makedirs(os.getenv("HOME") +'/'+ src_oxt +'/_SRC/OXT')
            except FileExistsError:
                pass
            nomeZip2= os.getenv("HOME") +'/'+ src_oxt +'/_SRC/OXT/LeenO-' + tempo + '.oxt'
            nomeZip = os.getenv("HOME") +'/'+ src_oxt +'/_SRC/OXT/LeenO.oxt'
            subprocess.Popen('nemo '+ os.getenv("HOME") +'/'+ src_oxt +'/_SRC/OXT', shell=True, stdout=subprocess.PIPE)

        else: 
            nomeZip2= '/media/giuserpe/PRIVATO/_dwg/ULTIMUSFREE/_SRC/OXT/LeenO-' + tempo + '.oxt'
            nomeZip = '/media/giuserpe/PRIVATO/_dwg/ULTIMUSFREE/_SRC/OXT/LeenO.oxt'
            subprocess.Popen('nemo /media/giuserpe/PRIVATO/_dwg/ULTIMUSFREE/_SRC/OXT/', shell=True, stdout=subprocess.PIPE)
    elif sys.platform == 'win32':
        if not os.path.exists('w:/_dwg/ULTIMUSFREE/_SRC/OXT/'):
            try:
                os.makedirs(os.getenv("HOMEPATH") +'/'+ src_oxt +'/')
            except FileExistsError:
                pass
            nomeZip2= os.getenv("HOMEPATH") +'/'+ src_oxt +'/OXT/LeenO-' + tempo + '.oxt'
            nomeZip = os.getenv("HOMEPATH") +'/'+ src_oxt +'/OXT/LeenO.oxt'
            subprocess.Popen('explorer.exe ' + os.getenv("HOMEPATH") +'\\'+ src_oxt +'\\OXT\\', shell=True, stdout=subprocess.PIPE)
        else:
            nomeZip2= 'w:/_dwg/ULTIMUSFREE/_SRC/OXT/LeenO-' + tempo + '.oxt'
            nomeZip = 'w:/_dwg/ULTIMUSFREE/_SRC/OXT/LeenO.oxt'
            subprocess.Popen('explorer.exe w:\\_dwg\\ULTIMUSFREE\\_SRC\\OXT\\', shell=True, stdout=subprocess.PIPE)
    shutil.make_archive(nomeZip2, 'zip', oxt_path)
    shutil.move(nomeZip2 + '.zip', nomeZip2)
    shutil.copyfile(nomeZip2, nomeZip)
#######################################################################
def dlg_attesa(msg=''):
    '''
    definisce la variabile globale oDialogo_attesa
    che va gestita così negli script:
    
    oDialogo_attesa = dlg_attesa()
    attesa().start() #mostra il dialogo
    ...
    oDialogo_attesa.endExecute() #chiude il dialogo
    '''
    psm = uno.getComponentContext().ServiceManager
    dp = psm.createInstance("com.sun.star.awt.DialogProvider")
    global oDialogo_attesa
    oDialogo_attesa = dp.createDialog("vnd.sun.star.script:UltimusFree2.DlgAttesa?language=Basic&location=application")

    oDialog1Model = oDialogo_attesa.Model # oDialogo_attesa è una variabile generale
    
    sString = oDialogo_attesa.getControl("Label2")
    sString.Text = msg #'ATTENDI...'
    oDialogo_attesa.Title = 'Operazione in corso...'
    sUrl = LeenO_path()+'/icons/attendi.png'
    oDialogo_attesa.getModel().ImageControl1.ImageURL=sUrl
    return oDialogo_attesa
#~ #

class attesa(threading.Thread):
    #~ http://bit.ly/2fzfsT7
    '''avvia il dialogo di attesa'''
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        oDialogo_attesa.execute()
        return
########################################################################
#~ class firme_in_calce_th(threading.Thread):
    #~ def __init__(self):
        #~ threading.Thread.__init__(self)
    #~ def run(self):
        #~ firme_in_calce_run()
#~ def firme_in_calce(arg=None):
    #~ firme_in_calce_th().start()
########################################################################
class XPWE_export_th(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        XPWE_export_run()
def XPWE_export(arg=None):
    XPWE_export_th().start()
########################################################################
class inserisci_nuova_riga_con_descrizione_th(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        oDialogo_attesa = dlg_attesa()
        oDoc = XSCRIPTCONTEXT.getDocument()
        oSheet = oDoc.CurrentController.ActiveSheet
        if oSheet.Name not in('COMPUTO', 'VARIANTE'):
            return
        descrizione = InputBox(t='inserisci una descrizione per la nuova riga')
        attesa().start() #mostra il dialogo
        zoom = oDoc.CurrentController.ZoomValue
        oDoc.CurrentController.ZoomValue = 400
        i =0
        while(i < getLastUsedCell(oSheet).EndRow):

            if oSheet.getCellByPosition(2, i ).CellStyle == 'comp 1-a':
                sStRange = Circoscrive_Voce_Computo_Att(i)
                qui = sStRange.RangeAddress.StartRow+1

                i = sotto = sStRange.RangeAddress.EndRow+3
                oDoc.CurrentController.select(oSheet.getCellByPosition(2, qui ))
                Copia_riga_Ent()
                oSheet.getCellByPosition(2, qui+1 ).String = descrizione
                next_voice(sotto)

                oDoc.CurrentController.select(oSheet.getCellByPosition(2, i ))
            i += 1
        oDialogo_attesa.endExecute() #chiude il dialogo
        oDoc.CurrentController.ZoomValue = zoom
def inserisci_nuova_riga_con_descrizione(arg=None):
    '''
    inserisce, all'inizio di ogni voce di computo o variante,
    una nuova riga con una descrizione a scelta
    '''
    inserisci_nuova_riga_con_descrizione_th().start()
########################################################################
def ctrl_d(arg=None):
    '''
    Copia il valore della prima cella superiore utile.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oCell= oDoc.CurrentSelection
    oSheet = oDoc.CurrentController.ActiveSheet
    x = Range2Cell()[0]
    lrow = Range2Cell()[1]
    y = lrow-1
    try:
        while oSheet.getCellByPosition(x, y).Type.value == 'EMPTY':
            y -= 1
    except:
        return
    oDoc.CurrentController.select(oSheet.getCellByPosition(x, y))
    copy_clip()
    oDoc.CurrentController.select(oCell)
    paste_clip(insCell = 0)
    oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
########################################################################
def taglia_x(arg=None):
    '''
    taglia il contenuto della selezione
    senza cancellare la formattazione delle celle
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    ctx = XSCRIPTCONTEXT.getComponentContext()
    desktop = XSCRIPTCONTEXT.getDesktop()
    oFrame = desktop.getCurrentFrame()

    dispatchHelper = ctx.ServiceManager.createInstanceWithContext( 'com.sun.star.frame.DispatchHelper', ctx )
    dispatchHelper.executeDispatch(oFrame, ".uno:Copy", "", 0, list())

    try:
        sRow = oDoc.getCurrentSelection().getRangeAddresses()[0].StartRow
        sCol = oDoc.getCurrentSelection().getRangeAddresses()[0].StartColumn
        eRow = oDoc.getCurrentSelection().getRangeAddresses()[0].EndRow
        eCol = oDoc.getCurrentSelection().getRangeAddresses()[0].EndColumn
    except AttributeError:
        sRow = oDoc.getCurrentSelection().getRangeAddress().StartRow
        sCol = oDoc.getCurrentSelection().getRangeAddress().StartColumn
        eRow = oDoc.getCurrentSelection().getRangeAddress().EndRow
        eCol = oDoc.getCurrentSelection().getRangeAddress().EndColumn
    oRange = oSheet.getCellRangeByPosition(sCol, sRow, eCol, eRow)
    flags = VALUE + DATETIME + STRING + ANNOTATION + FORMULA + OBJECTS + EDITATTR # FORMATTED + HARDATTR 
    oSheet.getCellRangeByPosition(sCol, sRow, eCol, eRow).clearContents(flags)
########################################################################
def calendario_mensile(arg=None):
    '''
    Colora le colonne del sabato e della domenica, oltre le festività,
    nel file ../PRIVATO/LeenO/extra/calendario.ods che potrei implementare
    in LeenO per la gestione delle ore in economia o del diagramma di Gantt.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.getSheets().getByName('elenco festività')
    oRangeAddress=oDoc.NamedRanges.feste.ReferredCells.RangeAddress
    SR = oRangeAddress.StartRow
    ER = oRangeAddress.EndRow
    lFeste = list()
    for x in range(SR, ER):
        if oSheet.getCellByPosition(0, x).Value != 0:
            lFeste.append(oSheet.getCellByPosition(0, x).String)
    oSheet = oDoc.getSheets().getByName('CALENDARIO')
    test = getLastUsedCell(oSheet).EndColumn+1
    slist = list()
    for x in range(0, test):
        if oSheet.getCellByPosition(x, 3).String == 's' or oSheet.getCellByPosition(x, 3).String == 'd':
            slist.append(x)
    for x in range(0, test):
        if oSheet.getCellByPosition(x, 1).String in lFeste:
            slist.append(x)

    for x in range(2, getLastUsedCell(oSheet).EndColumn+1):
        for y in range(1, getLastUsedCell(oSheet).EndRow+1):
            if x in slist:
                oSheet.getCellByPosition(x, y).CellStyle = 'ok'
            else:
                oSheet.getCellByPosition(x, y).CellStyle = 'tabella'
    return
########################################################################
def sistema_cose(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lcol = Range2Cell()[0]
    try:
        oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
    except AttributeError:
        oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
    el_y = list()
    el_x = list()
    lista_y = list()
    try:
        len(oRangeAddress)
        for el in oRangeAddress:
            el_y.append((el.StartRow, el.EndRow))
    except TypeError:
        el_y.append ((oRangeAddress.StartRow, oRangeAddress.EndRow))
    for y in el_y:
        for el in range (y[0], y[1]+1):
            lista_y.append(el)
    for y in lista_y:
        oDoc.CurrentController.select(oSheet.getCellByPosition(lcol, y))
        testo = oDoc.getCurrentSelection().String.replace('\t',' ').replace('\n',' ').replace('Ã¨','è').replace('Â°','°').replace('Ã','à')
        # ~testo = oDoc.getCurrentSelection().String.replace('\r','fbfxvcbsc')
        # ~testo = testo.replace(' \n','\n')
        while '  ' in testo:
            testo = testo.replace('  ',' ')
        oDoc.getCurrentSelection().String = testo
    return
########
def debug_link(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()

    window = oDoc.getCurrentController().getFrame().getContainerWindow()
    ctx = XSCRIPTCONTEXT.getComponentContext()
    def create(name):
        return ctx.getServiceManager().createInstanceWithContext(name, ctx)
    
    toolkit = create("com.sun.star.awt.Toolkit")
    msgbox = toolkit.createMessageBox(window, 0, 1, "Message", 'foo')
    
    link = create("com.sun.star.awt.UnoControlFixedHyperlink")
    link_model = create("com.sun.star.awt.UnoControlFixedHyperlinkModel")
    link.setModel(link_model)
    link.createPeer(toolkit, msgbox)
    link.setPosSize(35, 8, 100, 15, 15)
    link.setText("Canale Telegram")
    link.setURL("https://t.me/leeno_computometrico")
    link.setVisible(True)
    
    msgbox.execute()
    msgbox.dispose()
    return
########################################################################
def descrizione_in_una_colonna (flag=False):
#~ def debug(arg=None):
    '''
    Consente di estedere su più colonne o ridurre ad una colonna lo spazio
    occupato dalla descrizione di voce in COMPUTO, VARIANTE e CONTABILITA.
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    oSheet = oDoc.getSheets().getByName('S5')
    #~ if oSheet.getCellRangeByName('C9').IsMerged == True:
        #~ flag = False
    #~ else:
        #~ flag = True
    oSheet.getCellRangeByName('C9:I9').merge(flag)
    oSheet.getCellRangeByName('C10:I10').merge(flag)

    oSheet = oDoc.getSheets().getByName('COMPUTO')
    for y in range(3, getLastUsedCell(oSheet).EndRow):
        if oSheet.getCellByPosition(2, y).CellStyle in ('Comp-Bianche sopraS', 'Comp-Bianche in mezzo Descr'):
            oSheet.getCellRangeByPosition(2, y, 8, y).merge(flag)
    if oDoc.getSheets().hasByName('VARIANTE') == True:
        oSheet = oDoc.getSheets().getByName('VARIANTE')
        for y in range(3, getLastUsedCell(oSheet).EndRow):
            if oSheet.getCellByPosition(2, y).CellStyle in ('Comp-Bianche sopraS', 'Comp-Bianche in mezzo Descr'):
                oSheet.getCellRangeByPosition(2, y, 8, y).merge(flag)
    if oDoc.getSheets().hasByName('CONTABILITA') == True:
        if oDoc.NamedRanges.hasByName("#Lib#1") == True:
            MsgBox("Risulta già registrato un SAL. NON E' POSSIBILE PROCEDERE.",'ATTENZIONE!')
            return
        oSheet = oDoc.getSheets().getByName('S5')
        oSheet.getCellRangeByName('C23').merge(flag)
        oSheet.getCellRangeByName('C24').merge(flag)
        oSheet = oDoc.getSheets().getByName('CONTABILITA')
        for y in range(3, getLastUsedCell(oSheet).EndRow):
            if oSheet.getCellByPosition(2, y).CellStyle in ('Comp-Bianche sopra_R', 'Comp-Bianche in mezzo Descr_R'):
                oSheet.getCellRangeByPosition(2, y, 8, y).merge(flag)
    else:
            oSheet = oDoc.getSheets().getByName('S5')
            oSheet.getCellRangeByName('C23:I23').merge(flag)
            oSheet.getCellRangeByName('C24:I24').merge(flag)
    return
########################################################################
def numera_colonna(arg=None):
    '''Inserisce l'indice di colonna nelle prime 100 colonne del rigo selezionato
Associato a Atrl+Shift+C'''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lrow = Range2Cell()[1]
    #~ for x in range(0, 50):
        #~ oSheet.getCellByPosition(x, lrow).String = oSheet.getCellByPosition(x, lrow).CellStyle
    #~ return
    for x in range(0, 50):
        if oSheet.getCellByPosition(x, lrow).Type.value == 'EMPTY':
            oSheet.getCellByPosition(x, lrow).Formula = '=CELL("col")-1'
            oSheet.getCellByPosition(x, lrow).HoriJustify = 'CENTER'
        elif oSheet.getCellByPosition(x, lrow).Formula == '=CELL("col")-1':
            oSheet.getCellByPosition(x, lrow).String = ''
            oSheet.getCellByPosition(x, lrow).HoriJustify = 'STANDARD'
    return
########################################################################
def subst_str (arg=None):
    '''
    Sostituisce stringhe di testi nel foglio corrente
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    ReplaceDescriptor = oSheet.createReplaceDescriptor()
    ReplaceDescriptor.SearchString = "str1"
    ReplaceDescriptor.ReplaceString = "str2"
    oSheet.replaceAll(ReplaceDescriptor)
########################################################################
def processo (arg):
    '''Verifica l'esistenza di un processo di sistema'''
    ps = subprocess.Popen("ps -A", shell=True, stdout=subprocess.PIPE)
    #~ arg = 'soffice'
    if arg in (str(ps.stdout.read())):
        return True
    else:
        return False
########################################################################
def GetRegistryKeyContent(sKeyName, bForUpdate):
    '''Dà accesso alla configurazione utente di LibreOffice'''
    oConfigProvider = createUnoService("com.sun.star.configuration.ConfigurationProvider")
    arg = uno.createUnoStruct('com.sun.star.beans.PropertyValue')
    arg.Name = "nodepath"
    arg.Value = sKeyName
    if bForUpdate:
        GetRegistryKeyContent = oConfigProvider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationUpdateAccess", (arg,))
    else:
        GetRegistryKeyContent = oConfigProvider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (arg,))
    return GetRegistryKeyContent
########################################################################
def sistema_pagine (arg=None):
    '''
    Configura intestazioni e pie' di pagina degli stili di stampa
    e propone un'anteprima
    '''
    oDoc = XSCRIPTCONTEXT.getDocument()
    if oDoc.getSheets().hasByName('M1') == False:
        return
    #~ committente = oDoc.NamedRanges.Super_ego_8.ReferredCells.String 
    committente = oDoc.getSheets().getByName('S2').getCellRangeByName("C6").String #committente
    luogo = oDoc.getSheets().getByName('S2').getCellRangeByName("C4").String
    try:
        oSheet = oDoc.CurrentController.ActiveSheet
    except:
        pass
    #~ su_dx = oDoc.NamedRanges.Bozza_8.ReferredCells.String
    
    ### cancella stili di pagina #######################################
    # ~stili_pagina = list()
    # ~fine = oDoc.StyleFamilies.getByName('PageStyles').Count
    # ~for n in range(0, fine):
        # ~oAktPage = oDoc.StyleFamilies.getByName('PageStyles').getByIndex(n)
        # ~stili_pagina.append(oAktPage.DisplayName)
    # ~for el in stili_pagina:
        # ~if el not in ('PageStyle_Analisi di Prezzo', 'Page_Style_COPERTINE', 'Page_Style_Libretto_Misure2', 'PageStyle_REGISTRO_A4', 'PageStyle_COMPUTO_A4', 'PageStyle_Elenco Prezzi'):
            # ~oDoc.StyleFamilies.getByName('PageStyles').removeByName(el)
    # ~return
    ### cancella stili di pagina #######################################
    stili = {
        'cP_Cop' : 'Page_Style_COPERTINE',
        'COMPUTO': 'PageStyle_COMPUTO_A4',
        'VARIANTE': 'PageStyle_COMPUTO_A4',
        'Elenco Prezzi': 'PageStyle_Elenco Prezzi',
        'Analisi di Prezzo': 'PageStyle_Analisi di Prezzo',
        'CONTABILITA': 'Page_Style_Libretto_Misure2',
        'Registro': 'PageStyle_REGISTRO_A4',
        'SAL': 'PageStyle_REGISTRO_A4',
        }
    for el in stili.keys():
        try:
            oDoc.getSheets().getByName(el).PageStyle = stili[el]
        except:
            pass
    ###
    #~ oAktPage = oDoc.StyleFamilies.getByName('PageStyles').getByName('PageStyle_COMPUTO_A4')
    #~ mri(oAktPage)
    #~ return
    ###
    if conf.read(path_conf, 'Generale', 'dettaglio') == '1':
        dettaglio_misure(0)
        dettaglio_misure(1)
    else:
        dettaglio_misure(0)
    for n in range(0, oDoc.StyleFamilies.getByName('PageStyles').Count):
        oAktPage = oDoc.StyleFamilies.getByName('PageStyles').getByIndex(n)
        # ~chi((n , oAktPage.DisplayName))
        oAktPage.HeaderIsOn = True
        oAktPage.FooterIsOn = True

        if oAktPage.DisplayName == 'Page_Style_COPERTINE':
            oAktPage.HeaderIsOn = False
            oAktPage.FooterIsOn = False
            # Adatto lo zoom alla larghezza pagina
            oAktPage.PageScale = 0
            oAktPage.CenterHorizontally = True
            oAktPage.ScaleToPagesX = 1
            oAktPage.ScaleToPagesY = 0
        if oAktPage.DisplayName in ('PageStyle_Analisi di Prezzo', 'PageStyle_COMPUTO_A4', 'PageStyle_Elenco Prezzi'):
            htxt = 8.0
            if oAktPage.DisplayName in ('PageStyle_Analisi di Prezzo'):
                htxt = 10.0
            bordo = oAktPage.TopBorder
            bordo.LineWidth = 0
            bordo.OuterLineWidth = 0
            oAktPage.TopBorder = bordo

            bordo = oAktPage.BottomBorder
            bordo.LineWidth = 0
            bordo.OuterLineWidth = 0
            oAktPage.BottomBorder = bordo

            bordo = oAktPage.LeftBorder
            bordo.LineWidth = 0
            bordo.OuterLineWidth = 0
            oAktPage.LeftBorder = bordo
            #bordo lato destro attivo in attesa di LibreOffice 6.2
            #~ bordo = oAktPage.RightBorder
            #~ bordo.Color = 0
            #~ bordo.LineWidth = 2
            #~ bordo.OuterLineWidth = 2
            #~ oAktPage.RightBorder = bordo
            # Adatto lo zoom alla larghezza pagina
            oAktPage.PageScale = 0
            oAktPage.ScaleToPagesX = 1
            oAktPage.ScaleToPagesY = 0

            # ~HEADER
            oHeader = oAktPage.RightPageHeaderContent
            # ~oAktPage.PageScale = 95
            oHLText = oHeader.LeftText.Text.String = committente
            oHRText = oHeader.LeftText.Text.Text.CharFontName = 'Liberation Sans Narrow'
            oHRText = oHeader.LeftText.Text.Text.CharHeight = htxt #/ 100 * oAktPage.PageScale
            oHRText = oHeader.RightText.Text.String = luogo
            oHRText = oHeader.RightText.Text.Text.CharFontName = 'Liberation Sans Narrow'
            oHRText = oHeader.RightText.Text.Text.CharHeight = htxt #/ 100 * oAktPage.PageScale
            
            oAktPage.RightPageHeaderContent = oHeader
            # ~FOOTER
            oFooter = oAktPage.RightPageFooterContent
            oHLText = oFooter.CenterText.Text.String = ''
            oHLText = oFooter.LeftText.Text.String = "realizzato con LeenO.org\n" + os.path.basename(oDoc.getURL())
            oHRText = oFooter.LeftText.Text.Text.CharFontName = 'Liberation Sans Narrow'
            oHRText = oFooter.LeftText.Text.Text.CharHeight = htxt #/ 100 * oAktPage.PageScale
            oHRText = oFooter.RightText.Text.Text.CharFontName = 'Liberation Sans Narrow'
            oHRText = oFooter.RightText.Text.Text.CharHeight = htxt #/ 100 * oAktPage.PageScale
            #~ oHRText = oFooter.RightText.Text.String = '#/##'
            oAktPage.RightPageFooterContent= oFooter
            
        if oAktPage.DisplayName == 'Page_Style_Libretto_Misure2':
            # ~HEADER
            oHeader = oAktPage.RightPageHeaderContent
            oHLText = oHeader.LeftText.Text.String = committente + '\nLibretto delle misure n.'
            oHRText = oHeader.RightText.Text.String = luogo
            oAktPage.RightPageHeaderContent = oHeader
            # ~FOOTER
            oFooter = oAktPage.RightPageFooterContent
            oHLText = oFooter.CenterText.Text.String = "L'IMPRESA					IL DIRETTORE DEI LAVORI"
            oHLText = oFooter.LeftText.Text.String = "realizzato con LeenO.org\n" + os.path.basename(oDoc.getURL() + '\n\n\n')
            oAktPage.RightPageFooterContent= oFooter
            
        if oAktPage.DisplayName == 'PageStyle_REGISTRO_A4':
            # ~HEADER
            oHeader = oAktPage.RightPageHeaderContent
            oHLText = oHeader.LeftText.Text.String =  committente + '\nRegistro di contabilità n.'
            oHRText = oHeader.RightText.Text.String = luogo
            oAktPage.RightPageHeaderContent = oHeader
            # ~FOOTER
            oFooter = oAktPage.RightPageFooterContent
            oHLText = oFooter.CenterText.Text.String = ''
            oHLText = oFooter.LeftText.Text.String = "realizzato con LeenO.org\n" + os.path.basename(oDoc.getURL() + '\n\n\n')
            oAktPage.RightPageFooterContent= oFooter
    try:
        if oDoc.CurrentController.ActiveSheet.Name in ('COMPUTO', 'VARIANTE', 'CONTABILITA', 'Elenco Prezzi'):
            _gotoCella(0, 3)
        if oDoc.CurrentController.ActiveSheet.Name in ('Analisi di Prezzo'):
            _gotoCella(0, 2)
        setPreview(1)
    except:
        pass
        #bordo lato destro in attesa di LibreOffice 6.2
        #~ bordo = oAktPage.RightBorder
        #~ bordo.LineWidth = 0
        #~ bordo.OuterLineWidth = 0
        #~ oAktPage.RightBorder = bordo
    return
########################################################################
def fissa (arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    lcol = Range2Cell()[0]
    lrow = Range2Cell()[1]
    if oSheet.Name in('COMPUTO', 'VARIANTE', 'CONTABILITA',):
        oDoc.CurrentController.freezeAtPosition(0, 3)
    elif oSheet.Name in('Elenco Prezzi'):
        #~ _gotoCella(0, 3)
        oDoc.CurrentController.freezeAtPosition(0, 3)
    elif oSheet.Name in('Analisi di Prezzo'):
        oDoc.CurrentController.freezeAtPosition(0, 2)
    _gotoCella(lcol, lrow)
    return

########################################################################
def debug_errore(arg=None):
    #~ sStRange = Circoscrive_Voce_Computo_Att(lrow)
    #~ return

    try:
        sStRange = Circoscrive_Voce_Computo_Att(lrow)

    except Exception as e:
        #~ MsgBox ("CSV Import failure exception " + str(type(e)) +
                #~ ". Messaggio: " + str(e) + " args " + str(e.args) +
                #~ traceback.format_exc());
        MsgBox ("Eccezione " + str(type(e)) +
                "\nMessaggio: " + str(e.args) + '\n' +
                traceback.format_exc());
########################################################################
def trova_ricorrenze(arg=None):
    '''
    Consente la visualizzazione selettiva delle voci di COMPUTO che fanno
    capo alla stezza voce di Elenco Prezzi.
    '''
    chiudi_dialoghi()
    def ricorrenze(arg=None):
        '''Trova i codici di prezzo ricorrenti nel COMPUTO'''
        oDoc = XSCRIPTCONTEXT.getDocument()
        oSheet = oDoc.CurrentController.ActiveSheet
        struttura_off()
        last = getLastUsedCell(oSheet).EndRow
        lista = list()
        for n in range (3, last):
            if oSheet.getCellByPosition(1, n).CellStyle == 'comp Art-EP_R':
                lista.append(oSheet.getCellByPosition(1, n).String)
        unici = (set(lista))
        for el in unici:
            lista.remove(el)
        iSheet = oSheet.RangeAddress.Sheet
        oCellRangeAddr = uno.createUnoStruct('com.sun.star.table.CellRangeAddress')
        oCellRangeAddr.Sheet = iSheet
        lrow = 0 
        for n in range (0, last):
            if oSheet.getCellByPosition(1, n).CellStyle == 'comp Art-EP_R':
                if oSheet.getCellByPosition(1, n).String not in lista:
                    oRange = Circoscrive_Voce_Computo_Att(n).RangeAddress
                    oCellRangeAddr.StartRow = oRange.StartRow
                    oCellRangeAddr.EndRow = oRange.EndRow
                    oSheet.group(oCellRangeAddr, 1)
        lista = list(set(lista))
        lista.sort()
        return lista
    global lista_ricorrenze
    #~ try:
        #~ lista_ricorrenze
    #~ except:
    lista_ricorrenze = ricorrenze()
    if len(lista_ricorrenze) == 0:
        MsgBox('Non ci sono voci di prezzo ricorrenti.', 'Informazione')
        return
    psm = uno.getComponentContext().ServiceManager
    dp = psm.createInstance("com.sun.star.awt.DialogProvider")
    oDlg = dp.createDialog("vnd.sun.star.script:UltimusFree2.DlgLista?language=Basic&location=application")
    oDialog1Model = oDlg.Model
    #~ oDlg.Title = 'Si ripetono '+ str(len(lista_ricorrenze)) + ' voci di prezzo'
    oDlg.Title = 'Seleziona il codice e dai OK...'
    oDlg.getControl('ListBox1').addItems(lista_ricorrenze, 0)
    if oDlg.execute() == 0:
        return
    else:
        filtra_codice(oDlg.getControl('ListBox1').SelectedItem)
    #~ if oDlg.getControl('CheckBox1').State == 1:
        #~ oDlg.getControl('ListBox1').removeItems(0, len(lista_ricorrenze))
        #~ lista_ricorrenze = ricorrenze()
        #~ oDlg.getControl('ListBox1').addItems(lista_ricorrenze, 0)
        #~ oDlg.getControl('CheckBox1').State = 0
        #~ oDlg.execute()


########################################################################
def debug_(arg=None):
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    if oSheet.Name in('COMPUTO', 'VARIANTE', 'CONTABILITA'):
        try:
            sRow = oDoc.getCurrentSelection().getRangeAddresses()[0].StartRow
            eRow = oDoc.getCurrentSelection().getRangeAddresses()[0].EndRow

        except:
            sRow = oDoc.getCurrentSelection().getRangeAddress().StartRow
            eRow = oDoc.getCurrentSelection().getRangeAddress().EndRow
    chi((sRow, eRow))
def debug_(arg=None):
    refresh(0)
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    try:
        oRangeAddress = oDoc.getCurrentSelection().getRangeAddresses()
    except AttributeError:
        oRangeAddress = oDoc.getCurrentSelection().getRangeAddress()
    el_y = list()
    try:
        len(oRangeAddress)
        for el in oRangeAddress:
            el_y.append((el.StartRow, el.EndRow))
    except TypeError:
        el_y.append ((oRangeAddress.StartRow, oRangeAddress.EndRow))
    lista = list()
    for y in el_y:
        for el in range (y[0], y[1]+1):
            lista.append(el)
    # ~chi(lista)
    for el in lista:
        oSheet.getCellByPosition(7, el).Formula = '=' + oSheet.getCellByPosition(6, el).Formula + '*' + oSheet.getCellByPosition(7, el).Formula
        oSheet.getCellByPosition(6, el).String = ''
    refresh(1)

########################################################################
def trova_np(arg=None ):
    '''
    Raggruppa le righe in modo da rendere evidenti i nuovi prezzi
    '''
    chiudi_dialoghi()
    oDoc = XSCRIPTCONTEXT.getDocument()
    oSheet = oDoc.CurrentController.ActiveSheet
    refresh(0)
    struttura_off()
    oCellRangeAddr=oDoc.NamedRanges.elenco_prezzi.ReferredCells.RangeAddress
    for el in range(3, getLastUsedCell(oSheet).EndRow):
        if oSheet.getCellByPosition(12, el).Value == 0 and oSheet.getCellByPosition(20, el).Value > 0:
            pass
        else:
            oCellRangeAddr.StartRow = el
            oCellRangeAddr.EndRow = el
            oSheet.group(oCellRangeAddr, 1)
            oSheet.getCellRangeByPosition(0, el, 1, el).Rows.IsVisible = False
    refresh(1)
def debug_syspath(arg=None):
    # ~pydevd.settrace()
    pathsstring = "paths \n"
    somestring = ''
    for i in sys.path:
        somestring = somestring + i +"\n"
    chi(somestring)
def debug_progressbar (arg=None):
    try:
        oDoc = XSCRIPTCONTEXT.getDocument()
# set up Status Indicator
        oCntl = oDoc.getCurrentController()
        oFrame = oCntl.getFrame()
        oSI = oFrame.createStatusIndicator()
        oEnd = 100
        oSI.reset        # Reset : NG
        oSI.start('Excuting',oEnd)    # Start : NG

        for i in range(1,11):
            oSI.setText('Processing: ' + str(i) )
            oSI.setValue(20*i)
            time.sleep(0.1)

        oSI.setText('Finished')
        oDisp = 'Success'
    except Exception as er:
        oDisp = ''
        oDisp = str(traceback.format_exc()) + '\n' + str(er)
    finally:
        MsgBox(oDisp)
        oSI.end()
########################################################################
#~ def debug_elimina_voci_doppie (arg=None):
def debug (arg=None):
    'elimina voci doppie hard - grezza e lenta, ma efficace'
    oDoc = XSCRIPTCONTEXT.getDocument()
    _gotoSheet('Elenco Prezzi')
    oSheet = oDoc.CurrentController.ActiveSheet
    riordina_ElencoPrezzi()
    fine = getLastUsedCell(oSheet).EndRow+1

    oSheet.getCellByPosition(30, 3).Formula = '=IF(A4=A3;1;0)'
    oDoc.CurrentController.select(oSheet.getCellByPosition(30, 3))
    copy_clip()
    oDoc.CurrentController.select(oSheet.getCellRangeByPosition(30, 3, 30, fine))
    paste_clip(1)
    # ~oDoc.CurrentController.select(oDoc.createInstance("com.sun.star.sheet.SheetCellRanges")) #'unselect
    # ~for i in range (3, fine):
        # ~oSheet.getCellByPosition(30, i).Formula = '=IF(A' + str(i+1) + '=A' + str(i) + ';1;0)'
    # ~return
    
        
    for i in reversed (range (0, fine)):
        if oSheet.getCellByPosition(30, i).Value == 1:
            _gotoCella(30, i)
            oSheet.getRows().removeByIndex(i, 1)
    oSheet.getCellRangeByPosition(30, 3, 30, fine).clearContents(FORMULA)
########################################################################
def errore(arg=None):
    MsgBox (traceback.format_exc())
########################################################################
########################################################################
# ELENCO DEGLI SCRIPT VISUALIZZATI NEL SELETTORE DI MACRO              #
#~ g_exportedScripts = analisi_in_ElencoPrezzi,
########################################################################
########################################################################
# ... here is the python script code
# this must be added to every script file(the
# name org.openoffice.script.DummyImplementationForPythonScripts should be changed to something
# different(must be unique within an office installation !)
# --- faked component, dummy to allow registration with unopkg, no functionality expected
#~ import unohelper
# questo mi consente di inserire i comandi python in Accelerators.xcu
# vedi pag.264 di "Manuel du programmeur oBasic"
# <<< vedi in description.xml
########################################################################
