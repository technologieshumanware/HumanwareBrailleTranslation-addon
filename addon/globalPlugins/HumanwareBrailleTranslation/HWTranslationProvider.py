# BrailleNoteEvolve add-on
# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# Copyright (C) 2026 Technologies Humanware

import os
import brailleTranslation
from logHandler import log
import logging

import sys
import config
import brailleTables
import louisHelper

from . import computerBraille
from .constants import BRAILLE_TYPE_LITERARY, BRAILLE_TYPE_COMPUTER

from typing import Callable
import addonHandler
from core import postNvdaStartup
from gui.message import MessageDialog, DialogType

try:
    addonHandler.initTranslation()
except addonHandler.AddonError:
    # Running from scratchpad - use passthrough function
    _ = lambda x: x
else:
    _: Callable[[str], str]

initSuccess = True

def showError(message: str):
    dialog = MessageDialog(
        parent=None,
        message=message,
        #Translators: dialog title when announcing an error for HumanwareBrailleTranslation addon
        title=_("HumanWare Braille translation error"),
        dialogType=DialogType.ERROR
    )
    dialog.Show()

def checkInitFailed():
    if not initSuccess:
        # Translators: Label to inform user that HumanwareBrailleTranslation addon could not be loaded correctly
        showError(_("HumanWare Braille translation Add-on could not be loaded correctly."))


try:
    # Setup paths
    _base_path = os.path.dirname(os.path.realpath(__file__))
    pythonnet_path = os.path.join(_base_path, 'pythonnet')
    if pythonnet_path not in sys.path:
        sys.path.insert(0, pythonnet_path)
        log.debug(f"Added {pythonnet_path} to sys.path")

    translationlib_path = os.path.join(_base_path, 'BrailleTranslationLib')
    translationlib_dll = os.path.join(translationlib_path, 'BrailleTranslationLib.dll')

    # For pythonnet/CLR, we need to add the assembly with its full path
    if os.path.exists(translationlib_dll):
        try:
            import pythonnet
            pythonnet.load("coreclr")
            import clr
            import System
            from System.Reflection import Assembly
            
            assembly = Assembly.LoadFrom(translationlib_dll)
            translatorManagerType = assembly.GetType("BrailleTranslationLib.TranslatorManager")
            if translatorManagerType is None:
                raise Exception("Could not find BrailleTranslationLib.TranslatorManager type in assembly")

            import BrailleTranslationLib
            log.debug(f"Loaded BrailleTranslationLib from {translationlib_dll}")
        except:
            raise Exception("BrailleTranslationLib assembly error")
    else:
        log.error(f"BrailleTranslationLib.dll not found at {translationlib_dll}")
        raise FileNotFoundError(f"BrailleTranslationLib.dll not found at {translationlib_dll}")

except Exception as e:
    log.error(f"Unable to load BrailleTranslationLib: {e}")
    initSuccess = False

class HWTranslationProvider(brailleTranslation.BrailleTranslationProvider):
    
    # If initialization failed, show an error dialog when nvda is ready
    postNvdaStartup.register(checkInitFailed)

    try:
        translatorManager = System.Activator.CreateInstance(translatorManagerType, [False])
    except Exception as e:
        log.error(f"Unable to resolve TranslatorManager: {e}")
        initSuccess = False

    def __init__(self):
        log.info("HWTranslationProvider _init_")

    def init(self):
        log.warning("HWTranslationProvider init")
        if config.conf["braille"]["expandAtCursor"]:
            log.warning("HWTranslationProvider doesn't support expansion of word under cursor")
            louisHelper.initialize()

    def backTranslate(self, brl: str, cursorPos=None, mode=0) -> str:
        """Get text for specified braille string.
        @param brl: A string of Unicode braille.
        @return: A Unicode string.
        """
        try:
            # what kind of braille is selected for entry?
            typeOfBrailleForEntry = config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"]
            if mode == brailleTranslation.partialTranslation or typeOfBrailleForEntry == BRAILLE_TYPE_COMPUTER:
                return computerBraille.backTranslate(self._getComputerBrailleTable(), brl, cursorPos, mode)

            # for Literary Braille:
            # call functions in BrlTranslationLibrary
            preferredTranslator = config.conf["HumanwareBrailleTranslation"]["translatorChoice"]
            translator = self.translatorManager.GetBrailleTranslator(preferredTranslator)
            
            if cursorPos is None:
                cursorPos = 0

            result = translator.Back(brl, cursorPos)
            return result.Translated
        
        except Exception as e:
            log.error(f"Back translation error: {e}")
            return ""

    def translate(self, txt: str, typeform=None, cursorPos=None, mode=0):
        """Get text for specified string.
        @param txt: Unicode string.
        @param cursorPos: position in the input string.
        @return: A tuple, string of Unicode braille, a brailleToText position array,
            a textToBraille position array, and matching cursorPos in the translation.
        """

        try:
            # Log only if text is long or for debugging
            if log.isEnabledFor(logging.DEBUG) and len(txt) > 100:
                log.debug(f"translate long text: length={len(txt)}, cursorPos={cursorPos}")

            # special trivial case
            if txt == " ":
                return [0], [0, 1], [0, 1], cursorPos

            # what kind of braille is selected for display?
            typeOfBrailleForDisplay = config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForDisplay"]
            if typeOfBrailleForDisplay == BRAILLE_TYPE_COMPUTER:
                return computerBraille.translate(self._getComputerBrailleTable(), txt, typeform, cursorPos, mode)

            # Literary Braille translation with expansion to computer braille under cursor
            # cursorPos None is clearly not compatible with concept of word under cursor

            noPosOnEntry = False
            if cursorPos is None:
                cursorPos = 0
                noPosOnEntry = True

            elif mode & brailleTranslation.compbrlAtCursor:
                return self._translateWithWordUnderCursorExpansion( txt, typeform, cursorPos, mode)

            # Literary Braille translation
            return self._performLiteraryTranslation(txt, cursorPos, noPosOnEntry)
        
        except Exception as e:
            log.error(f"Translation error: {e}")
            return ""
        

    def translateInGradeForEntry(self, txt: str, typeform=None, cursorPos=None, mode=0):
        """Forward translate the specified string, using the braille translator defined
        for input. That translator typically deals with backtranslation, but there are odd
        cases where it needs to perform forward translation too.
        @param txt: Unicode string.
        @param cursorPos: position in the input string.
        @return: A tuple, string of Unicode braille, a brailleToText position array,
            a textToBraille position array, and matching cursorPos in the translation.
        """

        try:
            # special trivial case
            if txt == " ":
                return [0], [0, 1], [0, 1], cursorPos
            
            # what kind of braille is selected for ENTRY?
            # the typical usage of translateInGradeForEntry so far is for literary braille, but
            # there is no reason we cannot let this function in computer braille
            typeOfBrailleForEntry = config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"]
            if typeOfBrailleForEntry == BRAILLE_TYPE_COMPUTER:
                return computerBraille.translate(self._getComputerBrailleTable(), txt, typeform, cursorPos, mode)

            # Expansion to computer braille under cursor doesn't make any sense in that context
            # so we can happily ignore that
            
            noPosOnEntry = False
            if cursorPos is None:
                cursorPos = 0
                noPosOnEntry = True
            
            # "proper" Literary Braille translation
            return self._performLiteraryTranslation(txt, cursorPos, noPosOnEntry)
        
        except Exception as e:
            log.error(f"Translation error, braille entry type {typeOfBrailleForEntry}: {e}")
            return ""


    def terminate(self):
        log.info("HWTranslationProvider terminate")

    def useLiteraryBrailleForInput(self) -> bool:
        """Check if literary braille is selected for entry."""
        typeOfBrailleForEntry = config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"]
         # Translators: This is the label for Literary braille in the addon settings panel.
        return typeOfBrailleForEntry == BRAILLE_TYPE_LITERARY
    
    def useComputerBrailleForInput(self) -> bool:
        """Check if computer braille is selected for entry."""
        typeOfBrailleForEntry = config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"]
         # Translators: This is the label for Computer braille in the addon settings panel.
        return typeOfBrailleForEntry == BRAILLE_TYPE_COMPUTER

    def getTranslators(self):
        """Get list of available translator names."""
        return self.translatorManager.TranslatorNames

    # internal functions

    def _performLiteraryTranslation(self, txt: str, cursorPos: int, noPosOnEntry: bool):
        """Perform literary braille translation.
        @param txt: Text to translate.
        @param cursorPos: Cursor position in text.
        @param noPosOnEntry: Whether cursor position was None on entry.
        @return: Translation result tuple.
        """
        preferredTranslator = config.conf["HumanwareBrailleTranslation"]["translatorChoice"]
        translator = self.translatorManager.GetBrailleTranslator(preferredTranslator)

        result: BrailleTranslationLib.Models.BrlTranslationResultEx = translator.ForwardWithFullPositions(txt, cursorPos)
        
        # Force immediate conversion from .NET to Python to avoid lazy evaluation freezes
        braille = str(result.Translated)
        braille = [int(ord(cell) & 255) for cell in braille]
        posMap = [int(x) for x in result.PosMap]
        rPosMap = [int(x) for x in result.RPosMap]

        returnPos = None if noPosOnEntry else result.OutputPos
        return braille, posMap, rPosMap, returnPos

    def _getComputerBrailleTable(self):
        """Returns the filename of the selected computer braille table."""
        requestedTableName = config.conf["HumanwareBrailleTranslation"]["G0TranslatorChoice"]
        
        # BNW-2204 We store in the settings the DisplayName.
        # But the list can be localized, and therefore after switching languages, that name might not be found anymore
        # This is a bit of a clash with what we were doing so far, because our list of translator choices was presenting
        # each entry in its own native language (and charset). Which makes sense in terms of multilingual use, first boot wizard context, ...
        # table name has always been some sort of table unique ID.
        try:
            computerbrailletable = brailleTables.getTableByDisplayName(requestedTableName)
        except LookupError:
            # We absolutely need a table!
            computerbrailletable = brailleTables.getTableByDisplayName(computerBraille.DEFAULT_COMPUTER_BRAILLE_TABLE)
            log.info(f"error getting requested table {requestedTableName}, fallback to {computerbrailletable.displayName}:{computerbrailletable.fileName}")

        return computerbrailletable.fileName

    def _translateWithWordUnderCursorExpansion(self, txt: str, typeform=None, cursorPos=None, mode=0):
        """Translate with word under cursor expanded to computer braille.
        
        Split content into before, word under cursor, after.
        Translate word under cursor in computer braille.
        Translate before and after.
        Reassemble translations and position maps.
        """
        # get the literary braille translator
        preferredTranslator = config.conf["HumanwareBrailleTranslation"]["translatorChoice"]
        translator = self.translatorManager.GetBrailleTranslator(preferredTranslator)

        # todo: what about multiple spaces, are they compressed, stripped, different than liblouis?
        # we can force preservation of spaces in the BrlTranslationLib.

        spaceBefore = txt[:cursorPos].rfind(" ")
        spaceAfter = txt.find(" ", cursorPos + 1)
        before = ""
        after = ""
        currentWord = ""

        if spaceBefore != -1:
            before = txt[:spaceBefore]
        else:
            spaceBefore = 0

        if spaceAfter != -1:
            after = txt[spaceAfter:]
        else:
            spaceAfter = len(txt)

        currentWord = txt[spaceBefore:spaceAfter]
        currentTypeform = typeform[spaceBefore:spaceAfter] if typeform is not None else None
        posInCurrentWord = cursorPos - spaceBefore

        g0CurrentWord, currentWordPos, currentWordRPos, g0Pos = computerBraille.translate(
            self._getComputerBrailleTable(), currentWord, typeform=currentTypeform, cursorPos=posInCurrentWord, mode=mode
        )

        # translate before
        beforeResult: BrailleTranslationLib.Models.BrlTranslationResultEx = translator.ForwardWithFullPositions(before, 0)

        # translate after
        afterResult: BrailleTranslationLib.Models.BrlTranslationResultEx = translator.ForwardWithFullPositions(after, 0)

        # reassemble
        brailleBefore = [ord(cell) & 255 for cell in beforeResult.Translated]
        brailleAfter = [ord(cell) & 255 for cell in afterResult.Translated]
        braille = brailleBefore + g0CurrentWord + brailleAfter

        # there are some offsets involved in the translations posMaps
        # Force immediate conversion from .NET to Python
        posMapBefore = [int(x) for x in beforeResult.PosMap]
        rPosMapBefore = [int(x) for x in beforeResult.RPosMap]
        
        posMapCurrentWord = [x + spaceBefore for x in currentWordPos]
        # what's the corresponding position of "spaceBefore" in brailleBefore, which can be contracted?
        # it's the end of the braille
        spaceBeforePos = len(brailleBefore)
        
        rPosMapCurrentWord = [x + spaceBeforePos for x in currentWordRPos]
        
        posMapAfter = [x + spaceAfter for x in [int(y) for y in afterResult.PosMap]]
        # need to find spaceAfter in the RPos...
        # it's spaceBeforePos + length of currentWord
        spaceAfterPos = spaceBeforePos + len(g0CurrentWord)
        rPosMapAfter = [x + spaceAfterPos for x in [int(y) for y in afterResult.RPosMap]]

        posMap = posMapBefore + posMapCurrentWord + posMapAfter
        rPosMap = rPosMapBefore + rPosMapCurrentWord + rPosMapAfter

        return braille, posMap, rPosMap, g0Pos + spaceBeforePos
