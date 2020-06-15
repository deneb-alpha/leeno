'''
    LeenO menu and basic function dispatcher
'''

import sys
import os
import inspect
import importlib

from os import listdir
from os.path import isfile, join

import unohelper
from com.sun.star.task import XJobExecutor

import uno
import traceback
from com.sun.star.awt import MessageBoxButtons as MSG_BUTTONS
def msgbox(*, Title='Errore interno', Message=''):
    """ Create message box
        type_msg: infobox, warningbox, errorbox, querybox, messbox
        http://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1awt_1_1XMessageBoxFactory.html
    """
    ctx = uno.getComponentContext()
    sm = ctx.getServiceManager()
    toolkit = sm.createInstance('com.sun.star.awt.Toolkit')
    parent = toolkit.getDesktopWindow()
    buttons=MSG_BUTTONS.BUTTONS_OK
    type_msg='errorbox'
    mb = toolkit.createMessageBox(parent, type_msg, buttons, Title, str(Message))
    return mb.execute()

# set this to 1 to enable debugging
# set to 0 before deploying
ENABLE_DEBUG = 1

# set this one to 0 for deploy mode
# leave to 1 if you want to disable python cache
# to be able to modify and run installed extension
DISABLE_CACHE = 1

if ENABLE_DEBUG == 1:
    pass




def fixPythonPath():
    '''
    This function should fix python path adding it to current sys path
    if not already there
    Useless here, just kept for reference
    '''
    # dirty trick to have pythonpath added if missing
    myPath = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    myPath = os.path.join(myPath, "pythonpath")
    if myPath not in sys.path:
        sys.path.append(myPath)


def reloadLeenoModules():
    '''
    This function reload all Leeno modules found in pythonpath
    '''
    # get our pythonpath
    myPath = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    myPath = os.path.join(myPath, "pythonpath")

    # we need a listing of modules. We look at pythonpath ones
    pythonFiles = [f[: -3] for f in listdir(myPath) if isfile(join(myPath, f)) and f.endswith(".py")]
    for f in pythonFiles:
        #~ print("Loading module:", f)
        module = importlib.import_module(f)

        # reload the module
        importlib.reload(module)


class Dispatcher(unohelper.Base, XJobExecutor):
    '''
    LeenO menu and basic function dispatcher
    '''

    def __init__(self, ctx, *args):

        # CTX is XComponentContext - we store it
        self.ComponentContext = ctx

        # store any passed arg
        self.args = args

        # just in case...
        fixPythonPath()

    def trigger(self, arg):
        '''
        This function gets called when a menu item is selected
        or when a basic function calls PyScript()
        '''
        try:
            # reload all Leeno Modules
            if DISABLE_CACHE != 0:
                reloadLeenoModules()

            # menu items are passed as module.function
            # so split them in 2 strings
            ModFunc = arg.split('.')

            # locate the module from its name and check it
            module = importlib.import_module(ModFunc[0])
            if module is None:
                print("Module '", ModFunc[0], "' not found")
                return

            # reload the module if we don't want the cache
            # if DISABLE_CACHE != 0:
            #     importlib.reload(module)

            # locate the function from its name and check it
            func = getattr(module, ModFunc[1])
            if func is None:
                print("Function '", ModFunc[1], "' not found in Module '", ModFunc[0], "'")
                Dialogs.Exclamation(
                    Title="Errore interno",
                    Text=f"Funzione '{ModFunc[1]}' non trovata nel modulo '{ModFunc[0]}'")
                return

            # call the handler, depending of number of arguments
            if len(self.args) == 0:
                func()
            else:
                func(self.args)

        except Exception as e:
            # msg = traceback.format_exc()
            print("sys.exc_info:", sys.exc_info())
            sysinfo = sys.exc_info()
            exceptionClass = sysinfo[0].__name__
            message = str(sysinfo[1])
            tb = sysinfo[2]
            tbInfo = traceback.extract_tb(tb, 1)[0]
            function = tbInfo.name
            line = tbInfo.lineno
            file = os.path.split(tbInfo.filename)[1]
            msg = (
                message + "\n\n" +
                "File:     '" + file + "'\n" +
                "Line:     '" + str(line) + "'\n\n" +
                "Function: '" + function + "'\n\n")
            msgbox(Title="Errore interno", Message=msg)


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    Dispatcher,
    "org.giuseppe-vizziello.leeno.dispatcher",
    ("com.sun.star.task.Job",),)
