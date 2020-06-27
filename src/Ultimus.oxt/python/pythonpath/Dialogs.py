"""
Module for generating dynamic dialogs
i.e. dialogs that auto-adjust their layout based on contents and
external constraints

Copyright 2020 by Massimo Del Fedele
"""
import os
import inspect
import uno
import unohelper


from com.sun.star.awt import Size
from com.sun.star.awt import XActionListener
from com.sun.star.task import XJobExecutor

from com.sun.star.awt import XTopWindowListener

from com.sun.star.util import MeasureUnit

from LeenoConfig import Config
import LeenoUtils


def getCurrentPath():
    ''' get current script's path '''
    return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


def getParentWindowSize():
    '''
        Get Size of parent window in order to
        be able to create a dialog on center of it
    '''
    ctx = LeenoUtils.getComponentContext()
    serviceManager = ctx.ServiceManager
    toolkit = serviceManager.createInstanceWithContext(
        "com.sun.star.awt.Toolkit", ctx)

    oWindow = toolkit.getActiveTopWindow()
    if oWindow is None:
        oDesktop = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)
        oDoc = oDesktop.getCurrentComponent()

        oView = oDoc.getCurrentController()
        oWindow = oView.getFrame().getComponentWindow()
    rect = oWindow.getPosSize()
    return rect.Width, rect.Height


def getScreenInfo():
    '''
    Get screen size
    '''
    ctx = LeenoUtils.getComponentContext()
    oToolkit = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.awt.Toolkit", ctx)
    aWorkArea = oToolkit.WorkArea
    nWidht = aWorkArea.Width
    nHeight = aWorkArea.Height

    return nWidht, nHeight


def getScaleFactors():
    '''
    Dialog positions are scaled by weird factors
    so we need to figure them out before proceeding
    pix = appfont / scale
    appfont = pix * scale

    '''
    doc = LeenoUtils.getDocument()
    docframe = doc.getCurrentController().getFrame()
    docwindow = docframe.getContainerWindow()

    sc = docwindow.convertSizeToPixel(Size(1000, 1000), MeasureUnit.APPFONT)

    return 1000.0 / float(sc.Width), 1000.0 / float(sc.Height)

def getImageSize(Image):
    '''
    gets the size of a given image
    BEWARE : SIZE IN PIXEL !
    '''
    ctx = LeenoUtils.getComponentContext()
    serviceManager = ctx.ServiceManager

    imageModel = serviceManager.createInstance(
        "com.sun.star.awt.UnoControlImageControlModel")
    image = serviceManager.createInstance(
        "com.sun.star.awt.UnoControlImageControl")
    image.setModel(imageModel)
    imageModel.ImageURL = uno.systemPathToFileUrl(os.path.join(getCurrentPath(), Image))
    size = imageModel.Graphic.SizePixel
    imageModel.dispose()
    return size.Width,  size.Height

def getBigIconSize():
    '''
    Get 'best' size for a big dialog icon
    (like the one of alert and ok dialogs)
    '''
    scWidth,  scHeight = getScreenInfo()
    siz = min(scWidth, scHeight)
    siz = int(siz / 20)

    return siz, siz


def getTextBox(txt):
    '''
    Get the size needed to display a multiline text box
    BEWARE : SIZE IN PIXEL !
    '''
    ctx = LeenoUtils.getComponentContext()
    serviceManager = ctx.ServiceManager

    textModel = serviceManager.createInstance(
        "com.sun.star.awt.UnoControlFixedTextModel")
    text = serviceManager.createInstance(
        "com.sun.star.awt.UnoControlFixedText")
    text.setModel(textModel)
    text.setText(txt)
    size = text.getMinimumSize()
    textModel.dispose()
    return size.Width,  size.Height


def getRadioButtonSize(label):
    '''
    Get the size needed to display a radio button
    BEWARE : SIZE IN PIXEL !
    '''
    ctx = LeenoUtils.getComponentContext()
    serviceManager = ctx.ServiceManager

    rbModel = serviceManager.createInstance(
        "com.sun.star.awt.UnoControlRadioButtonModel")
    rb = serviceManager.createInstance(
        "com.sun.star.awt.UnoControlRadioButton")
    rb.setModel(rbModel)
    rb.setLabel(label)
    size = rb.getMinimumSize()
    rbModel.dispose()
    return size.Width,  size.Height


def getRadioButtonHeight():
    '''
    Get the height needed to display a radio button
    BEWARE : SIZE IN PIXEL !
    '''
    return getRadioButtonSize("X")[1]


def getCheckBoxSize(label):
    '''
    Get the size needed to display a checkbox
    BEWARE : SIZE IN PIXEL !
    '''
    ctx = LeenoUtils.getComponentContext()
    serviceManager = ctx.ServiceManager

    cbModel = serviceManager.createInstance(
        "com.sun.star.awt.UnoControlCheckBoxModel")
    cb = serviceManager.createInstance(
        "com.sun.star.awt.UnoControlCheckBox")
    cb.setModel(cbModel)
    cb.setLabel(label)
    size = cb.getMinimumSize()
    cbModel.dispose()
    return size.Width,  size.Height


def getCheckBoxHeight():
    '''
    Get the height needed to display a checkbox
    BEWARE : SIZE IN PIXEL !
    '''
    return getCheckBoxSize("X")[1]


def getButtonSize(txt, Icon=None):
    '''
    Get 'best' button size in a dialog
    based on text
    '''
    width,  height = getTextBox(txt)
    if Icon is not None:
        width += 32
        height = max(height, 24)
    return max(width + 15, 100),   height + 15


class DialogException(Exception):

    '''
    Base class for all dialog exceptions
    '''
    pass


class AbstractError(DialogException):
    '''
    Try to instantiate base class DialogItem
    '''
    def __init__(self):
        ''' constructor '''
        self.message = "Can't instantiate abstract class"


class LayoutError(DialogException):
    ''' Error during layout calculation in dialogs '''

    def __init__(self):
        ''' constructor '''
        self.message = 'Layout error'


'''
Dialog items alignment when size is bigger than mininum one
'''
HORZ_ALIGN_LEFT = 1
HORZ_ALIGN_CENTER = 2
HORZ_ALIGN_RIGHT = 4

VERT_ALIGN_TOP = 8
VERT_ALIGN_CENTER = 16
VERT_ALIGN_BOTTOM = 32

MIN_SPACER_SIZE = 10

DIALOG_BORDERS = 10

GROUPBOX_TOP_BORDER = 25
GROUPBOX_BOTTOM_BORDER = 10
GROUPBOX_LEFT_BORDER = 10
GROUPBOX_RIGHT_BORDER = 10


class DialogItem:
    '''
    Base class for every dialog item
    '''
    def __init__(
        self,  Id=None,
        MinWidth=None, MinHeight=None,
        MaxWidth=None, MaxHeight=None,
        FixedWidth=None, FixedHeight=None
    ):
        ''' constructor '''

        self._minWidth = MinWidth
        self._minHeight = MinHeight

        self._maxWidth = MaxWidth
        self._maxHeight = MaxHeight

        self._fixedWidth = FixedWidth
        self._fixedHeight = FixedHeight

        self._x = 0
        self._y = 0

        self._width = 0
        self._height = 0

        self.align = HORZ_ALIGN_LEFT | VERT_ALIGN_TOP
        self._id = Id

        # we need both owning dialog and UNO widget pointers
        # so we can act on running dialogs
        self._owner = None
        self._UNOWidget = None

    def _adjustSize(self):
        ''' calculate min size and adjust considering minimum, maximum and fixed ones '''

        # calculate minimum size (depending on object)
        self._width,  self._height = self.calcMinSize()

        # adjust it

        # fixed size takes precedence
        if self._fixedWidth is not None:
            self._width = self._fixedWidth
        else:
            if self._minWidth is not None:
                self._width = max(self._width,   self._minWidth)
            if self._maxWidth is not None:
                self._width = min(self._width,   self._maxWidth)

        if self._fixedHeight is not None:
            self._height = self._fixedHeight
        else:
            if self._minHeight is not None:
                self._height = max(self._height,   self._minHeight)
            if self._maxHeight is not None:
                self._height = min(self._height,   self._maxHeight)

        return self._width,  self._height

    def calcMinSize(self):
        '''
        gets minimum control size (from content / type)
        MUST be defined in derived classes
        '''
        raise AbstractError

    def _equalizeElements(self):
        '''
        This one is meant for grouping controls
        like Sizers or GroupBox
        '''
        pass

    def _adjustLayout(self):
        '''
        This one is meant for grouping controls
        like Sizers or GroupBox
        '''
        pass

    def dump(self,   indent):
        '''
        bring a string representation of object
        '''
        res = 4 * indent * ' ' + type(self).__name__ + ': {'
        res += f'Id:{self._id}'
        res += f', X:{self._x}, Y:{self._y}'
        res += f',  Width:{self._width}, Height:{self._height}'
        if self._fixedWidth is not None:
            res += f', fixedWidth:{self._fixedWidth}'
        else:
            if self._minWidth is not None:
                res += f', minWidth:{self._minWidth}'
            if self._maxWidth is not None:
                res += f', maxWidth:{self._maxWidth}'

        if self._fixedHeight is not None:
            res += f', fixedHeight:{self._fixedHeight}'
        else:
            if self._minHeight is not None:
                res += f', minHeight:{self._minHeight}'
            if self._maxHeight is not None:
                res += f', maxHeight:{self._maxHeight}'

        return res

    def __repr__(self):
        '''
        convert object to string
        '''
        return self.dump(0)

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        return {}

    def getAction(self):
        '''
        Gets a string representing the action on the control
        This string will be sent to event handler along with control name
        If the value returned is None or an empty string, no action will be performed
        '''
        return None

    def _addUnoItems(self,  owner):
        '''
        Add uno item(s) to owning UNO dialog
        '''
        dialogModel = owner._dialogModel
        dialogContainer = owner._dialogContainer
        clsName = type(self).__name__

        # create the control
        oControlModel = dialogModel.createInstance(
            "com.sun.star.awt.UnoControl" + clsName + "Model")

        # still dont' know why, but we've got to scale items coordinates
        # so get the factors
        xScale,  yScale = getScaleFactors()

        # set base properties (position, size)
        uno.invoke(oControlModel, "setPropertyValue",  ("PositionX",  int(self._x * xScale)))
        uno.invoke(oControlModel, "setPropertyValue",  ("PositionY",  int(self._y * yScale)))
        uno.invoke(oControlModel, "setPropertyValue",  ("Width",  int(self._width * xScale)))
        uno.invoke(oControlModel, "setPropertyValue",  ("Height",  int(self._height * yScale)))

        # set control's specific properties
        props = self.getProps()
        for key,  val in props.items():
            if val is not None:
                uno.invoke(oControlModel, "setPropertyValue", (key,  val))

        if self._id is None:
            self._id = owner._getNextId()
        oControlModel.Name = self._id

        # insert the control into dialog
        dialogModel.insertByName(self._id, oControlModel)

        # store the control for running usage
        self._UNOWidget = oControlModel

        # store owner pointer too
        self._owner = owner

        # if the control shall handle actions, setup an event handler
        action = self.getAction()
        if action is not None and action != '':
            dialogContainer.getControl(self._id).addActionListener(owner)
            dialogContainer.getControl(self._id).setActionCommand(self._id + '_' + action)

    def _destruct(self):
        '''
        removes all reference to owner and UNO widget
        so we know that dialog is not in running state
        '''
        self._UNOWidget = None
        self._owner = None

    def _actionPerformed(self):
        ''' an action on underlying widget happened '''
        pass


class Spacer(DialogItem):
    ''' A virtual widget used to leave space among other widgets'''

    def __init__(self,  MinSize=None):
        ''' constructor '''
        if MinSize is None:
            MinSize = MIN_SPACER_SIZE
        super().__init__(MinWidth=MinSize,  MinHeight=MinSize)

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        return self._minWidth, self._minHeight

    def _addUnoItems(self,  owner):
        ''' DO NOTHING'''
        pass


class Sizer(DialogItem):
    '''
    Base class for horizontal and vertical sizers
    Every dialog MUST contain exactly one sizer
    '''
    def __init__(self, *, Id=None, Items):
        ''' constructor '''
        super().__init__(Id=Id)
        if Items is None:
            Items = []
        self._items = Items
        self._x = 0
        self._y = 0
        self._width = 0
        self._height = 0

    def dump(self, indent):
        '''
        bring a string representation of object
        '''
        res = super().dump(indent) + '\n'
        for item in self._items:
            res += item.dump(indent + 1) + '\n'
        res += 4 * indent * ' ' + '}'
        return res

    def add(self, *items):
        '''
        Add widgets to sizer
        '''
        for item in items:
            self._items.append(item)

    def _addUnoItems(self, owner):
        '''
        fill UNO dialog with items
        '''
        for item in self._items:
            item._addUnoItems(owner)

    def _destruct(self):
        '''
        removes all reference to owner and UNO widget
        so we know that dialog is not in running state
        '''
        for item in self._items:
            item._destruct()

    def getWidget(self, wId):
        ''' get widget by ID'''
        if self._id == wId:
            return self
        for item in self._items:
            if hasattr(item,  'getWidget'):
                widget = item.getWidget(wId)
                if widget is not None:
                    return widget
            else:
                if wId == item._id:
                    return item
        return None

    def __getitem__(self, key):
        return self.getWidget(key)


class HSizer(Sizer):
    '''
    Horizontal sizer
    Used to arrange controls horizontally
    '''
    def __init__(self, *, Id=None, Items=None):
        ''' constructor '''
        super().__init__(Id=Id, Items=Items)

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        w = 0
        h = 0
        for item in self._items:
            # calculate min size for item
            itemMinWidth,  itemMinHeight = item._adjustSize()

            # store it to item, we'll need later on
            item._width,  item._height = itemMinWidth,  itemMinHeight

            # update our size
            w += itemMinWidth
            h = max(h, itemMinHeight)
        return w,  h

    def _equalizeElements(self):
        '''
        equalize elements inside container
        for hSizer, that means to put all of them at max height
        '''
        maxH = 0
        for item in self._items:
            maxH = max(maxH, item._height)
        for item in self._items:
            item._height = maxH
            item._equalizeElements()
        self.height = maxH

    def _adjustLayout(self):
        u"""
        based on requested size and (previously calculated) minimum size
        layout contained items
        WARNING : we need a PREVIOUS call to calcMinSize and  _equalizeElements ¯on widget three
        """
        xOrg,  yOrg = self._x,  self._y

        # store previous origin, we need it later
        curXOrg,  curYOrg = xOrg,  yOrg

        # get total of contained elements size
        totW = 0
        for item in self._items:
            totW += item._width

        # this is an hSizer, so we shall divide horizontal spare space
        # between items somehow. if there's some Spacer inside, divide
        # the space among them. Oterwise divide the space among contained
        # items based on their sizes. Not an easy task...
        dW = self._width - totW
        if dW > 0:
            # count spacer items
            nSpacers = 0
            for item in self._items:
                if isinstance(item, Spacer):
                    nSpacers += 1

            # it we've got spacers, divide tspaces among them
            if nSpacers > 0:
                # the size must contain spacer's minimum size
                # so se add it BEFORE dividing
                dW += nSpacers * MIN_SPACER_SIZE

                space = int(dW / nSpacers)
                lastSpace = dW - space * (nSpacers - 1)
                n = 0
                for item in self._items:
                    if isinstance(item, Spacer):
                        n += 1
                        if n == nSpacers:
                            sp = lastSpace
                        else:
                            sp = space
                        item._width = sp
                        # set item position
                        item._x,  item._y = curXOrg,  curYOrg
                        # move to next item
                        curXOrg += sp
                    else:
                        # set item position
                        item._x,  item._y = curXOrg,  curYOrg
                        # move to next item
                        curXOrg += item._width
            else:
                # no spacers inside, we shall divide space between items

                # calculate at first the ratio of items space / total space
                ratios = []
                for item in self._items:
                    ratios.append(item._width / self._width)

                # now divide the space between items
                # last space gets the remainder
                spaceRemainder = 0
                iItem = 0
                for item in self._items:
                    itemSpace = int(dW * ratios[iItem])
                    if iItem < len(self._items) - 1:
                        item._width += itemSpace
                        spaceRemainder -= itemSpace
                    else:
                        item._width += spaceRemainder

                    # set item position
                    item._x,  item._y = curXOrg,  curYOrg
                    # move to next item
                    curXOrg += item._width

                    iItem += 1
        else:
            # no space to divide, requested size identical to minimum
            for item in self._items:
                # set item position
                item._x,  item._y = curXOrg,  curYOrg
                # move to next item
                curXOrg += item._width

        # run _adjustLayout on all contained containers
        for item in self._items:
            item._adjustLayout()


class VSizer(Sizer):
    '''
    Vertical sizer
    Used to arrange controls vertically
    '''
    def __init__(self, *, Id=None, Items=None):
        ''' constructor '''
        super().__init__(Id=Id, Items=Items)

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        w = 0
        h = 0
        for item in self._items:
            # calculate min size for item
            itemMinWidth,  itemMinHeight = item._adjustSize()

            # store it to item, we'll need later on
            item._width,  item._height = itemMinWidth,  itemMinHeight

            # update our size
            w = max(w, itemMinWidth)
            h += itemMinHeight
        return w,  h

    def _equalizeElements(self):
        '''
        equalize elements inside container
        for hSizer, that means to put all of them at max height
        '''
        maxW = 0
        for item in self._items:
            maxW = max(maxW,  item._width)
        for item in self._items:
            item._width = maxW
            item._equalizeElements()
        self._width = maxW

    def _adjustLayout(self):
        u"""
        based on requested size and (previously calculated) minimum size
        layout contained items
        WARNING : we need a PREVIOUS call to calcMinSize and  _equalizeElements ¯on widget three
        """
        xOrg,  yOrg = self._x,  self._y

        # store previous origin, we need it later
        curXOrg,  curYOrg = xOrg,  yOrg

        # get total of contained elements size
        totH = 0
        for item in self._items:
            totH += item._height

        # this is an hSizer, so we shall divide horizontal spare space
        # between items somehow. if there's some Spacer inside, divide
        # the space among them. Oterwise divide the space among contained
        # items based on their sizes. Not an easy task...
        dH = self._height - totH
        if dH > 0:
            # count spacer items
            nSpacers = 0
            for item in self._items:
                if isinstance(item, Spacer):
                    nSpacers += 1

            # it we've got spacers, divide tspaces among them
            if nSpacers > 0:
                # the size must contain spacer's minimum size
                # so we add it BEFORE dividing
                dH += nSpacers * MIN_SPACER_SIZE

                space = int(dH / nSpacers)
                lastSpace = dH - space * (nSpacers - 1)
                n = 0
                for item in self._items:
                    if isinstance(item, Spacer):
                        n += 1
                        if n == nSpacers:
                            sp = lastSpace
                        else:
                            sp = space
                        item._height = sp
                        # set item position
                        item._x,  item._y = curXOrg,  curYOrg
                        # move to next item
                        curYOrg += sp
                    else:
                        # set item position
                        item._x,  item._y = curXOrg,  curYOrg
                        # move to next item
                        curYOrg += item._height
            else:
                # no spacers inside, we shall divide space between items

                # calculate at first the ratio of items space / total space
                ratios = []
                for item in self._items:
                    ratios.append(item._height / self._height)

                # now divide the space between items
                # last space gets the remainder
                spaceRemainder = 0
                iItem = 0
                for item in self._items:
                    itemSpace = int(dH * ratios[iItem])
                    if iItem < len(self._items) - 1:
                        item._height += itemSpace
                        spaceRemainder -= itemSpace
                    else:
                        item._height += spaceRemainder

                    # set item position
                    item._x,  item._y = curXOrg,  curYOrg
                    # move to next item
                    curYOrg += item._height
        else:
            # no space to divide, requested size identical to minimum
            for item in self._items:
                # set item position
                item._x,  item._y = curXOrg,  curYOrg
                # move to next item
                curYOrg += item._height

        # run _adjustLayout on all contained containers
        for item in self._items:
            item._adjustLayout()


class FixedText(DialogItem):
    '''
    Fixed text box
    Display a box of text
    '''
    def __init__(self, *, Id=None,  Text='',
                 MinWidth=None, MinHeight=None,
                 MaxWidth=None, MaxHeight=None,
                 FixedWidth=None, FixedHeight=None):
        ''' constructor '''
        super().__init__(Id=Id,
                         MinWidth=MinWidth, MinHeight=MinHeight,
                         MaxWidth=MaxWidth, MaxHeight=MaxHeight,
                         FixedWidth=FixedWidth, FixedHeight=FixedHeight)
        self._text = Text

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        return getTextBox(self._text)

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        return {'Label': self._text,  'Align': 0}

    def dump(self,  indent):
        '''
        convert object to string
        '''
        txt = self._text.replace("\n", "\\n")
        return super().dump(indent) + f", Text: '{txt}'" + '}'

    def setText(self, txt):
        self._text = txt
        if self._UNOWidget is not None:
            self._UNOWidget.Label = txt

    def getText(self):
        return self._text


class ImageControl(DialogItem):
    '''
    Fixed image
    Display an image
    '''
    def __init__(self, *, Id=None,  Image,
                 MinWidth=None, MinHeight=None,
                 MaxWidth=None, MaxHeight=None,
                 FixedWidth=None, FixedHeight=None):
        ''' constructor '''

        # for images we do some smart sizing here...
        iW, iH = getImageSize(Image)
        ratio = iH / iW

        # take minimum sizes as the "true" minimum
        if MinWidth is not None:
            minH = int(MinWidth * ratio)
            if MinHeight is None or MinHeight < minH:
                MinHeight = minH
        elif MinHeight is not None:
            MinWidth = int(MinHeight / ratio)

        # take maximum sizes as the "true" maximum
        if MaxWidth is not None:
            maxH = int(MaxWidth * ratio)
            if MaxHeight is None or MaxHeight > maxH:
                MaxHeight = maxH
        elif MaxHeight is not None:
            MaxWidth = int(MaxHeight / ratio)

        super().__init__(Id=Id,
                         MinWidth=MinWidth, MinHeight=MinHeight,
                         MaxWidth=MaxWidth, MaxHeight=MaxHeight,
                         FixedWidth=FixedWidth, FixedHeight=FixedHeight)
        self._image = Image


    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        return getBigIconSize()

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        return {
            "Border": 0,
            "ImageURL": uno.systemPathToFileUrl(os.path.join(getCurrentPath(), self._image)),
            "ScaleImage": True,
            "ScaleMode": 1
        }

    def dump(self,  indent):
        '''
        convert object to string
        '''
        return super().dump(indent) + f", Image: '{self._image}'" + '}'


class ProgressBar(DialogItem):
    '''
    ProgressBar
    Display a ProgressBar
    '''
    def __init__(self, *, Id=None, MinVal=0, MaxVal=100, Value=0,
                 MinWidth=None, MinHeight=None,
                 MaxWidth=None, MaxHeight=None,
                 FixedWidth=None, FixedHeight=None):
        ''' constructor '''
        super().__init__(Id=Id,
                         MinWidth=MinWidth, MinHeight=MinHeight,
                         MaxWidth=MaxWidth, MaxHeight=MaxHeight,
                         FixedWidth=FixedWidth, FixedHeight=FixedHeight)
        self._minVal = MinVal
        self._maxVal = MaxVal
        self._value = Value

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        # try to get an "optimal" size from current window
        pW, pH = getParentWindowSize()
        Width = int(2 * pW / 3)

        # correct the width just to be not too small nor too big
        ws,  hs = getScreenInfo()
        if Width < ws / 8:
            Width = int(ws / 8)
        elif Width > ws / 4:
            Width = int(ws / 4)

        return Width,  20

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        res = {
               "ProgressValueMin": self._minVal,
               "ProgressValueMax": self._maxVal,
               "ProgressValue": self._value}
        return res

    def dump(self,  indent):
        '''
        convert object to string
        '''
        return super().dump(indent) + '}'

    def setLimits(self,  minVal, maxVal):
        self._minVal = minVal
        self._maxVal = maxVal
        if self._UNOWidget is not None:
            self._UNOWidget.ProgressValueMin = minVal
            self._UNOWidget.ProgressValueMax = maxVal

    def getLimits(self):
        return self._minVal, self._maxVal

    def setValue(self, val):
        self._value = val
        if self._UNOWidget is not None:
            self._UNOWidget.ProgressValue = val

    def getValue(self):
        return self._value


class Button(DialogItem):
    '''
    Push button
    Display a push button which reacts to presses
    If 'RetVal' is given, button closes the dialog and returns this value
    If 'RetVal' is None, button DOESN'T close the dialog, but external handler is called
    '''
    def __init__(self, *, Id=None, Label='aLabel', RetVal=None, Icon=None,
                 MinWidth=None, MinHeight=None,
                 MaxWidth=None, MaxHeight=None,
                 FixedWidth=None, FixedHeight=None):
        ''' constructor '''
        if Id is None:
            Id = Label
        super().__init__(Id=Id,
                         MinWidth=MinWidth, MinHeight=MinHeight,
                         MaxWidth=MaxWidth, MaxHeight=MaxHeight,
                         FixedWidth=FixedWidth, FixedHeight=FixedHeight)
        self._label = Label
        self._retVal = RetVal
        self._icon = Icon

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        return getButtonSize(self._label, self._icon)

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        res = {'Label': self._label}
        if self._icon is not None:
            res['ImageAlign'] = 0
            res['ImageURL'] = uno.systemPathToFileUrl(os.path.join(getCurrentPath(), self._icon))
        return res

    def getAction(self):
        '''
        Gets a string representing the action on the control
        This string will be sent to event handler along with control name
        If the value returned is None or an empty string, no action will be performed
        '''
        return "OnClick"

    def dump(self,  indent):
        '''
        convert object to string
        '''
        res = super().dump(indent)
        res += f", Label: '{self._label}'"
        res += f", Icon: '{self._icon}'" + '}'
        return res


class CheckBox(DialogItem):
    '''
    Checkbox
    Display a check box (aka option)
    '''
    def __init__(self, *, Id=None, Label='aLabel', State=False,
                 MinWidth=None, MinHeight=None,
                 MaxWidth=None, MaxHeight=None,
                 FixedWidth=None, FixedHeight=None):
        ''' constructor '''
        super().__init__(Id=Id,
                         MinWidth=MinWidth, MinHeight=MinHeight,
                         MaxWidth=MaxWidth, MaxHeight=MaxHeight,
                         FixedWidth=FixedWidth, FixedHeight=FixedHeight)
        self._label = Label
        self._state = State

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        return getCheckBoxSize(self._label)

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        return {
            'Label': self._label,
            'State': int(self._state)
        }

    def getAction(self):
        '''
        Gets a string representing the action on the control
        This string will be sent to event handler along with control name
        If the value returned is None or an empty string, no action will be performed
        '''
        return "OnChange"

    def setState(self, state):
        self._state = state
        if self._UNOWidget:
            self._UNOWidget.State = self._state

    def getState(self):
        return self._state

    def _actionPerformed(self):
        ''' an action on underlying widget happened '''
        self._state = True if self._UNOWidget.State else False

    def dump(self, indent):
        '''
        convert object to string
        '''
        res = super().dump(indent)
        res += f", Label: '{self._label}'"
        res += f", State: '{self._state}'"
        return res


class RadioButton(DialogItem):
    '''
    Radio button
    Display a radio button connected with others
    '''
    def __init__(self, *, Id=None, Label='aLabel',
                 MinWidth=None, MinHeight=None,
                 MaxWidth=None, MaxHeight=None,
                 FixedWidth=None, FixedHeight=None):
        ''' constructor '''
        super().__init__(Id=Id,
                         MinWidth=MinWidth, MinHeight=MinHeight,
                         MaxWidth=MaxWidth, MaxHeight=MaxHeight,
                         FixedWidth=FixedWidth, FixedHeight=FixedHeight)
        self._label = Label

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        return getRadioButtonSize(self._label)

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        return {
            'Label': self._label
        }

    def getAction(self):
        '''
        Gets a string representing the action on the control
        This string will be sent to event handler along with control name
        If the value returned is None or an empty string, no action will be performed
        '''
        return "OnSelect"

    def dump(self, indent):
        '''
        convert object to string
        '''
        res = super().dump(indent)
        res += f", Label: '{self._label}'"
        return res


class RadioGroup(DialogItem):
    '''
    Radio group
    Groups a sequence of radio buttons
    It has no label not border, if those are required
    you shall insert it into a GroupBox item
    '''
    def __init__(self, *, Id=None, Horz=False, Items=None, Default=0):
        ''' constructor '''
        super().__init__(Id=Id)
        if Items is None:
            Items = []
        self._items = Items
        if Default is None:
            Default = 0
        elif Default >= len(Items):
            Default = len(Items) - 1
        if Default < 0:
            Default = 0
        self._default = Default
        self._current = Default
        if Horz:
            self._sizer = HSizer()
        else:
            self._sizer = VSizer()

        # as Id can be None now, and we dont' have a reference to Dialog object
        # we can't setup the buttons ids, which are composed
        # by box id + '_' + button index.
        # We'll do it later when constructing the UNO dialog
        for item in self._items:
            self._sizer.add(RadioButton(Label=item))
        self._sizer._x,  self._sizer._y = 0,  0
        self._x,  self._y = 0,  0
        self._width,  self._height = 0,  0

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        return self._sizer.calcMinSize()

    def _equalizeElements(self):
        '''
        Equalize all elements sizes in Sizer
        '''
        self._sizer._equalizeElements()

    def _adjustLayout(self):
        '''
        Adjust layout of contained Sizer
        '''
        self._sizer._x = self._x
        self._sizer._y = self._y
        self._sizer._adjustLayout()

    def add(self, *items):
        ''' add elements to group '''
        for item in items:
            self._items.append(item)

    def _addUnoItems(self,  owner):
        '''
        fill UNO dialog with items
        '''
        self._owner = owner

        # fix Id, if it's None
        # we need it to handle buttons
        if self._id is None:
            self._id = owner._getNextId()
        # adjust buttons ids - they must follow
        # the schema "RadioGroup_rgID_buttonIdx
        # so we can handle the events
        curId = 0
        for item in self._sizer._items:
            item._id = 'RadioGroup_' + self._id + '_' + str(curId)
            curId += 1

        # now add the radio buttons
        self._sizer._addUnoItems(owner)

        # select current item
        self.setCurrent(self._current)

    def _destruct(self):
        '''
        removes all reference to owner and UNO widget
        so we know that dialog is not in running state
        '''
        self._sizer._destruct()

    def getWidget(self,  wId):
        ''' gets widget by Id '''
        if self._id == wId:
            return self
        return self._sizer.getWidget(wId)

    def __getitem__(self, key):
        return self.getWidget(key)

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        return None

    def getAction(self):
        '''
        Gets a string representing the action on the control
        This string will be sent to event handler along with control name
        If the value returned is None or an empty string, no action will be performed
        '''
        return None

    def getCount(self):
        ''' get number of radio buttons '''
        return len(self._sizer._items)

    def getCurrent(self):
        '''
        gets the currently active radio button index
        starting from 0
        '''
        return self._current

    def setCurrent(self,  current):
        '''
        sets the currently active radio button index
        if dialog is displaying, set also the widget on it
        '''
        self._current = current
        if self._owner is not None:
            idx = 0
            for item in self._sizer._items:
                item._UNOWidget.State = idx == current
                idx += 1

    def dump(self,  indent):
        '''
        bring a string representation of object
        '''
        res = super().dump(indent) + '\n'
        for item in self._sizer._items:
            res += item.dump(indent + 1) + '\n'
        res += 4 * indent * ' ' + '}'
        return res


class GroupBox(DialogItem):
    '''
    Group box
    Display a box with optional border and label
    Used mostly to group items
    In behaviour is similar to Dialog
    '''
    def __init__(self, *, Id=None, Label='aLabel', Horz=False, Items=None):
        ''' constructor '''
        super().__init__(Id=Id)
        self._label = Label
        if Horz:
            self._sizer = HSizer(Items=Items)
        else:
            self._sizer = VSizer(Items=Items)
        self._sizer._x,  self._sizer._y = GROUPBOX_LEFT_BORDER,  GROUPBOX_TOP_BORDER
        self._x,  self._y = 0,  0
        self._width,  self._height = 0,  0

    def calcMinSize(self):
        '''
        Calculate widget's minimum size
        '''
        wl,  hl = getTextBox(self._label)
        ws,  hs = self._sizer.calcMinSize()
        return (
                max(wl, ws + GROUPBOX_LEFT_BORDER + GROUPBOX_RIGHT_BORDER),
                max(hl, hs + GROUPBOX_TOP_BORDER + GROUPBOX_BOTTOM_BORDER))

    def _equalizeElements(self):
        '''
        Equalize all elements sizes in Sizer
        '''
        self._sizer._equalizeElements()

    def _adjustLayout(self):
        '''
        Adjust layout of contained Sizer
        '''
        self._sizer._x = self._x + GROUPBOX_LEFT_BORDER
        self._sizer._y = self._y + GROUPBOX_TOP_BORDER
        self._sizer._adjustLayout()

    def add(self, *items):
        ''' add elements to group '''
        for item in items:
            self._sizer._items.append(item)

    def _addUnoItems(self,  owner):
        '''
        fill UNO dialog with items
        '''
        super()._addUnoItems(owner)
        self._sizer._addUnoItems(owner)

    def _destruct(self):
        '''
        removes all reference to owner and UNO widget
        so we know that dialog is not in running state
        '''
        super()._destruct()
        self._sizer._destruct()

    def getWidget(self,  wId):
        ''' gets widget by Id '''
        if self._id == wId:
            return self
        return self._sizer.getWidget(wId)

    def __getitem__(self, key):
        return self.getWidget(key)

    def getProps(self):
        '''
        Get control's properties (name+value)
        to be set in UNO
        MUST be redefined on each visible control
        '''
        return {
            'Label': self._label
        }

    def getAction(self):
        '''
        Gets a string representing the action on the control
        This string will be sent to event handler along with control name
        If the value returned is None or an empty string, no action will be performed
        '''
        return None

    def dump(self,  indent):
        '''
        bring a string representation of object
        '''
        res = super().dump(indent) + '\n'
        for item in self._sizer._items:
            res += item.dump(indent + 1) + '\n'
        res += 4 * indent * ' ' + '}'
        return res


class Dialog(unohelper.Base, XActionListener, XJobExecutor,  XTopWindowListener):
    '''
    Main dialog class
    '''
    def __init__(self, *, Title='', Horz=False, Handler=None, CanClose=True, Items=None):
        ''' constructor '''
        unohelper.Base.__init__(self)
        self._title = Title
        if Horz:
            self._sizer = HSizer(Items=Items)
        else:
            self._sizer = VSizer(Items=Items)
        self._sizer._x,  self._sizer._y = DIALOG_BORDERS,  DIALOG_BORDERS
        self._x,  self._y = 0,  0
        self._width,  self._height = 0,  0
        self._handler = Handler
        self._canClose = CanClose
        self._showing = False
        self._retVal = None

        self._nextId = 0

    def _layout(self):
        '''
        Optimize widget's placement inside dialog based on
        constraints, sizers and spacers
        '''
        # first, calculate minimum size for ALL widgets on widget tree
        # and adjust it on constraints
        self._sizer._adjustSize()

        # equalize all container's elements
        self._sizer._equalizeElements()

        self._sizer._adjustLayout()
        self._width = self._sizer._width + 2 * DIALOG_BORDERS
        self._height = self._sizer._height + 2 * DIALOG_BORDERS

    def add(self, *items):
        ''' add elements to dialog '''
        for item in items:
            self._sizer._items.append(item)

    def dump(self):
        '''
        convert object to string
        '''
        res = f'Dialog: {{X:{self._x}, Y:{self._y}'
        res += f' , Width:{self._width}, Height:{self._height}\n'
        res += self._sizer.dump(1) + "\n"
        res += "}"
        return res

    def __repr__(self):
        '''
        convert object to string
        '''
        return self.dump()

    def _getNextId(self):
        ''' gets next free Id '''
        self._nextId += 1
        return str(self._nextId)

    def _construct(self):
        '''
        build internal dialog's UNO structures
        '''
        self._nextId = 0

        # Optimize widget's placement inside dialog based on
        # constraints, sizers and spacers
        self._layout()

        # we try to place the dialog bar at center of parent window
        pW, pH = getParentWindowSize()
        self._x = int((pW - self._width) / 2)
        self._y = int((pH - self._height) / 2)

        # create UNO dialog
        self._localContext = LeenoUtils.getComponentContext()
        self._serviceManager = self._localContext.ServiceManager
        self._toolkit = self._serviceManager.createInstanceWithContext(
            "com.sun.star.awt.Toolkit", self._localContext)

        # create dialog model and set its properties properties
        self._dialogModel = self._serviceManager.createInstance(
            "com.sun.star.awt.UnoControlDialogModel")

        xScale,  yScale = getScaleFactors()
        self._dialogModel.PositionX = int(self._x * xScale)
        self._dialogModel.PositionY = int(self._y * yScale)
        self._dialogModel.Width = int(self._width * xScale)
        self._dialogModel.Height = int(self._height * yScale)

        self._dialogModel.Name = "Default"
        self._dialogModel.Moveable = True
        self._dialogModel.Title = self._title
        self._dialogModel.DesktopAsParent = False

        # setup the Closeable flag to False
        # this makes the dialog impossible to close clicking on X
        # on top bar or pressing escape; this MUST be done in
        # windowClosing handler
        self._dialogModel.Closeable = False

        # create the dialog container and set our dialog model into it
        self._dialogContainer = self._serviceManager.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog", self._localContext)

        self._dialogContainer.setModel(self._dialogModel)

        self._showing = False

        # fill UNO dialog with items
        self._sizer._addUnoItems(self)

        # add close listener
        self._dialogContainer.addTopWindowListener(self)

    def _destruct(self):
        '''
        Resets internal pointers to UNO objects
        so we'll be able to know if dialog is running or not
        '''
        self._sizer._destruct()

    def windowClosing(self,  evt):
        '''
        We didn't find a way to stop closing here, so we use the
        Closeable property of DialogModel to disallow closing
        Here we just catch the closing op to set return value
        Even if Closeable is set to False, this hook gets called
        '''
        if self._canClose:
            self._dialogContainer.endDialog(-1)
            self._retVal = -1
            self._showing = False

    def actionPerformed(self, oActionEvent):
        '''
        internal event handler
        will call a provided external event handler
        '''
        # get the id of triggering widget
        cmdList = oActionEvent.ActionCommand.split('_')
        widgetId = cmdList[0]
        cmdStr = '_'.join(cmdList[1:])
        widget = self.getWidget(widgetId)

        # radio group events are handled differently
        # so it will be easy to use them
        if widgetId == 'RadioGroup':
            # this is NOT the true widget id, so get it
            cmdList = cmdStr.split('_')
            # this is the Id of group
            widgetId = cmdList[0]
            # and this is the index of radio button in group
            cmdStr = cmdList[1]
            # we pass the group to handler, not the single buttons
            widget = self.getWidget(widgetId)
            #update current item in group
            widget._current = int(cmdStr)
        # otherwise we signal the widget that some action was performed on it
        else:
            widget._actionPerformed()

        # if we've got an handler, we process the command inside it
        # and if returning True we close the dialog
        # if no handler or returning false, we process the event from here
        if self._handler is not None:
            if self._handler(self, widgetId, widget, cmdStr):
                return

        if widget is None:
           return

        if hasattr(widget,  '_retVal') and widget._retVal is not None:
            self.stop(widget._retVal)

    def run(self):
        '''
        Runs the dialog and wait for completion
        '''
        # constructs the dialog
        self._construct()

        # execute it
        # signal that we showed the dialog
        self._showing = True

        self._dialogContainer.setVisible(True)
        self._dialogContainer.createPeer(self._toolkit, None)
        self._dialogContainer.execute()

        self._showing = False

        self._destruct()

        return self._retVal

    def stop(self,  RetVal=None):
        '''
        Stops the dialog
        Shall be called from inside an handler
        '''
        if RetVal is not None:
            self._retVal = RetVal
        self._showing = False
        self._dialogContainer.endExecute()

    def show(self):
        '''
        Shows the dialog without waiting for completion
        '''
        # constructs the dialog
        self._construct()

        self._showing = True
        self._dialogContainer.setVisible(True)

    def hide(self):
        '''
        Hide the dialog
        '''
        self._dialogContainer.setVisible(False)
        self._showing = False

        self._destruct()

    def getWidget(self,  wId):
        ''' get widget by ID'''
        return self._sizer.getWidget(wId)

    def __getitem__(self, key):
        return self.getWidget(key)

    def showing(self):
        return self._showing

    def getValue(self):
        return self._retVal


######################################################################
## SOME COMMON DIALOGS
######################################################################

def FileSelect(titolo='Scegli il file...', est='*.*', mode=0):
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
    estensioni = {'*.*': 'Tutti i file(*.*)',
                  '*.odt': 'Writer(*.odt)',
                  '*.ods': 'Calc(*.ods)',
                  '*.odb': 'Base(*.odb)',
                  '*.odg': 'Draw(*.odg)',
                  '*.odp': 'Impress(*.odp)',
                  '*.odf': 'Math(*.odf)',
                  '*.xpwe': 'Primus(*.xpwe)',
                  '*.xml': 'XML(*.xml)',
                  '*.dat': 'dat(*.dat)', }
    oFilePicker = LeenoUtils.createUnoService("com.sun.star.ui.dialogs.FilePicker")
    oFilePicker.initialize((mode, ))
    oDoc = LeenoUtils.getDocument()

    # try to get path from current document, if any
    # if not, look into config to fetch last used one
    oPath = oDoc.getURL()
    if oPath == '':
        oPath = uno.systemPathToFileUrl(Config().read('Generale', 'ultimo_percorso'))
    else:
        oPath = os.path.dirname(oPath)
    oFilePicker.setDisplayDirectory(oPath)

    oFilePicker.Title = titolo
    app = estensioni.get(est)
    oFilePicker.appendFilter(app, est)
    if oFilePicker.execute():
        oPath = uno.fileUrlToSystemPath(oFilePicker.getFiles()[0])
        Config().write('Generale', 'ultimo_percorso', os.path.dirname(oPath))
        return oPath
    return None

def NotifyDialog(*, Image, Title, Text):
    dlg = Dialog(Title=Title,  Horz=False, CanClose=True,  Items=[
        HSizer(Items=[
            ImageControl(Image=Image),
            Spacer(),
            FixedText(Text=Text)
        ]),
        Spacer(),
        HSizer(Items=[
            Spacer(),
            Button(Label='Ok', Icon='Icons-24x24/ok.png',  RetVal=1),
            Spacer()
        ])
    ])
    return dlg.run()

def Exclamation(*, Title='', Text=''):
    return NotifyDialog(Image='Icons-Big/exclamation.png', Title=Title, Text=Text)

def Info(*, Title='', Text=''):
    return NotifyDialog(Image='Icons-Big/info.png', Title=Title, Text=Text)

def Ok(*, Title='', Text=''):
    return NotifyDialog(Image='Icons-Big/ok.png', Title=Title, Text=Text)

def YesNoDialog(*, Title, Text):
    dlg = Dialog(Title=Title,  Horz=False, CanClose=False,  Items=[
        HSizer(Items=[
            ImageControl(Image='Icons-Big/question.png'),
            Spacer(),
            FixedText(Text=Text)
        ]),
        Spacer(),
        HSizer(Items=[
            Spacer(),
            Button(Label='Si', Icon='Icons-24x24/ok.png',  RetVal=1),
            Spacer(),
            Button(Label='No', RetVal=0),
            Spacer()
        ])
    ])
    return dlg.run()

def YesNoCancelDialog(*, Title, Text):
    dlg = Dialog(Title=Title,  Horz=False, CanClose=True,  Items=[
        HSizer(Items=[
            ImageControl(Image='Icons-Big/question.png'),
            Spacer(),
            FixedText(Text=Text)
        ]),
        Spacer(),
        HSizer(Items=[
            Spacer(),
            Button(Label='Si', Icon='Icons-24x24/ok.png',  RetVal=1),
            Spacer(),
            Button(Label='No', RetVal=0),
            Spacer(),
            Button(Label='Annulla', Icon='Icons-24x24/cancel.png',  RetVal=-1),
            Spacer()
        ])
    ])
    return dlg.run()

class Progress:
    '''
    Display a progress bar with some options
    '''
    def __init__(self, *, Title='', Closeable=False, MinVal=0, MaxVal=100, Value=0, Text=''):
        ''' constructor '''
        self._dlg = Dialog(
            Title=Title, Horz=False, CanClose=Closeable,
            Handler=lambda dialog, widgetId, widget, cmdStr :
            self._dlgHandler(dialog, widgetId,  widget, cmdStr)
        )
        self._progress = ProgressBar(MinVal=MinVal, MaxVal=MaxVal, Value=Value)
        self._dlg.add(self._progress)
        self._text = Text
        if Text is not None:
            self._textWidget = FixedText(Text=Text)
            self._dlg.add(self._textWidget)

        if Closeable:
            self._dlg.add(Spacer())
            self._dlg.add(
                HSizer(Items=[
                    Spacer(),
                    Button(Label='Annulla', RetVal=-1),
                    Spacer()
                ])
            )

    def _dlgHandler(self,  dialog,  widgetId,  widget,  cmdStr):
        self._dlg.hide()

    def show(self):
        self._dlg.show()

    def hide(self):
        self._dlg.hide()

    def showing(self):
        return self._dlg.showing()

    def setLimits(self,  pMin,  pMax):
        self._progress.setLimits(pMin, pMax)

    def getLimits(self):
        return self._progress.getLimits()

    def setValue(self,  val):
        self._progress.setValue(val)
        if self._text is not None and self._textWidget is not None:
            minVal, maxVal = self.getLimits()
            percent = '{:.0f}%'.format(100 * (val - minVal) / (maxVal - minVal))
            txt = self._text + ' (' + percent + ')'
            self._textWidget.setText(txt)

    def getValue(self):
        return self._progress.getValue()

    def setText(self,  txt):
        self._text = txt
        if self._text is not None and self._textWidget is not None:
            minVal, maxVal = self.getLimits()
            val = self.getValue()
            percent = '{:.0f}%'.format(100 * (val - minVal) / (maxVal - minVal))
            txt = self._text + ' (' + percent + ')'
            self._textWidget.setText(txt)

def MultiButton(*, Icon=None, Title='', Text='', Buttons=None):
    if Buttons is None:
        return None
    top = HSizer()
    if Icon is not None:
        top.add(ImageControl(Image=Icon))
        top.add(Spacer())
    top.add(FixedText(Text=Text))
    bottom = HSizer()
    idx = 0
    for label, value in Buttons.items():
        bottom.add(Button(Label=label, RetVal=value))
        if idx < len(Buttons) - 1:
            bottom.add(Spacer())
        idx += 1
    dlg = Dialog(Title=Title, Items=[top, Spacer(), bottom])
    return dlg.run()


def YesNo(*, Title='', Text='', CanClose=True):
    '''
    Yes/No dialog
    by default (CanClose=True) dialog may be dismissed
    closing it on topbar or pressing escape, with result 'No'
    '''
    res = MultiButton(
        Icon="Icons-Big/question.png",
        Title=Title, Text=Text, CanClose=CanClose,
        Buttons={'Si':'si', 'No':'no'}
    )
    if res == -1:
        res = 'no'
    return res

def YesNoCancel(*, Title='', Text=''):
    '''
    Yes/No/Cancel dialog
    by default (CanClose=True) dialog may be dismissed
    closing it on topbar or pressing escape, with result 'No'
    '''
    res = MultiButton(
        Icon="Icons-Big/question.png",
        Title=Title, Text=Text, CanClose=True,
        Buttons={'Si':'si', 'No':'no', 'Annulla':-1}
    )
    if res == -1:
        res = 'annulla'
    return res

