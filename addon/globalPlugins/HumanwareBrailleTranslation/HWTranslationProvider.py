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
import configparser
import languageHandler

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

def _get_locale_defaults() -> tuple:
    lang_base = languageHandler.getLanguage().split("_")[0]

    addon_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ini_path = os.path.join(addon_root, "locale", lang_base, "defaultBrailleTable.ini")

    if os.path.exists(ini_path):
        try:
            parser = configparser.ConfigParser()
            parser.read(ini_path, encoding="utf-8")
            return parser.get("Defaults", "literary_braille_table"), parser.get("Defaults", "computer_braille_table")
        except Exception as e:
            log.error(f"HWTranslation: Error reading file {ini_path}: {e}")

    en_ini_path = os.path.join(addon_root, "locale", "en", "defaultBrailleTable.ini")
    if os.path.exists(en_ini_path):
        try:
            parser = configparser.ConfigParser()
            parser.read(en_ini_path, encoding="utf-8")
            return parser.get("Defaults", "literary_braille_table"), parser.get("Defaults", "computer_braille_table")
        except Exception as e:
            log.error(f"HWTranslation: Error reading file {en_ini_path}: {e}")

    return "", ""

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


# BNW-3578 the positions BrailleTranslationLib reports are uint16, so an input long enough to
# push them past 65535 comes back with unusable position maps, which is what makes the routing
# cursors stop working after a certain point in large files. Long texts are therefore forward
# translated one chunk of that many characters at a time, well under the uint16 ceiling.
LITERARY_CHUNK_SIZE = 10000

# Preferred cut points within a chunk, best first: a page break disturbs the translation context
# least, then a line break, then a word break as a last resort before cutting a word in two.
CHUNK_SEPARATORS = ("\f", "\n", " ")


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
            return [0], [0, 1], [0, 1], cursorPos if cursorPos is not None else 0
        

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

    def _chunkText(self, txt: str, chunkSize: int, respectWordBoundaries: bool = True) -> list[str]:
        """Split the text into chunks of at most the specified size, optionally respecting word boundaries.
        The chunks always partition the text exactly, ie "".join(chunks) == txt, so that the position
        maps of the individual chunks can be offset and concatenated.
        @param txt: The text to be chunked.
        @param chunkSize: The maximum size of each chunk.
        @param respectWordBoundaries: Whether to split on spaces when possible, defaults to True.
        @return: A list of text chunks, empty if txt is empty.
        """
        if not respectWordBoundaries:
            return [txt[i:i + chunkSize] for i in range(0, len(txt), chunkSize)]

        chunks = []
        index = 0
        length = len(txt)

        while index < length:
            if index + chunkSize >= length:
                chunks.append(txt[index:])
                break

            # last space within the window, so we don't cut a word in two
            end = txt.rfind(" ", index, index + chunkSize)
            if end == -1 or end <= index:
                # a single word longer than the window, or a leading space: cut it anyway
                end = index + chunkSize
            else:
                # keep the space itself in the chunk, otherwise it is lost from both the
                # braille output and the position maps, and every offset past this boundary drifts
                end += 1

            chunks.append(txt[index:end])
            index = end

        return chunks

    def _forwardTranslateChunked(self, translator, txt: str, cursorPos: int):
        """Forward translate the text with the given literary translator, one chunk at a time.
        BNW-3578 the translator cannot be trusted with arbitrarily long inputs, so the text is
        translated in chunks and the results are offset and reassembled. For a text short enough
        to fit in a single chunk this is equivalent to calling the translator directly.
        @param translator: The literary braille translator to use.
        @param txt: Text to translate.
        @param cursorPos: Cursor position in text. A position sitting just past the end of the
            text is mapped to the end of the last chunk.
        @return: A tuple, list of braille cells, a brailleToText position array, a textToBraille
            position array, and the matching cursorPos in the translation.
        """
        # an empty text still has to go through the translator, so that a blank line gets the
        # same position maps it would have got from a single direct call
        chunkedText: list[str] = self._chunkText(txt, LITERARY_CHUNK_SIZE) or [txt]

        braille, posMap, rPosMap = [], [], []
        textOffset = 0
        outputPos = 0
        cursorFound = False

        for i, chunk in enumerate(chunkedText):
            isLastChunk = i == len(chunkedText) - 1
            # does the cursor belong to this chunk? one sitting just past the end of the text
            # (caret at end of line) falls through to the last chunk
            inChunk = not cursorFound and (cursorPos < textOffset + len(chunk) or isLastChunk)
            chunkPos = cursorPos - textOffset if inChunk else 0

            result: BrailleTranslationLib.Models.BrlTranslationResultEx = (
                translator.ForwardWithFullPositions(chunk, chunkPos)
            )

            # Force immediate conversion from .NET to Python to avoid lazy evaluation freezes
            cells = [int(ord(cell) & 255) for cell in str(result.Translated)]
            chunkPosMap = [int(x) for x in result.PosMap]
            chunkRPosMap = [int(x) for x in result.RPosMap]

            brailleOffset = len(braille)

            if inChunk:
                outputPos = int(result.OutputPos) + brailleOffset
                cursorFound = True

            # A map may carry a trailing past the end entry. Only the last chunk gets to keep its
            # own, otherwise the maps end up longer than the cells and characters they index and
            # every lookup after a chunk boundary is off by one. No-op if the translator returns
            # exactly one entry per cell / character.
            if not isLastChunk:
                del chunkPosMap[len(cells):]
                del chunkRPosMap[len(chunk):]

            braille += cells
            posMap += [x + textOffset for x in chunkPosMap]
            rPosMap += [x + brailleOffset for x in chunkRPosMap]
            textOffset += len(chunk)

        return braille, posMap, rPosMap, outputPos

    def _performLiteraryTranslation(self, txt: str, cursorPos: int, noPosOnEntry: bool):
        """Perform literary braille translation.
        @param txt: Text to translate.
        @param cursorPos: Cursor position in text.
        @param noPosOnEntry: Whether cursor position was None on entry.
        @return: Translation result tuple.
        """
        preferredTranslator = config.conf["HumanwareBrailleTranslation"]["translatorChoice"]
        translator = self.translatorManager.GetBrailleTranslator(preferredTranslator)

        braille, posMap, rPosMap, outputPos = self._forwardTranslateChunked(translator, txt, cursorPos)

        returnPos = None if noPosOnEntry else outputPos
        return braille, posMap, rPosMap, returnPos

    def _getComputerBrailleTable(self):
        """Returns the filename of the selected computer braille table."""
        requestedTable = config.conf["HumanwareBrailleTranslation"]["G0TranslatorChoice"]
            
        # BNW-2204 We USED TO store in the settings the DisplayName.
        # But the list can be localized, and therefore after switching languages, that name might not be found anymore
        # This is a bit of a clash with what we were doing so far, because our list of translator choices was presenting
        # each entry in its own native language (and charset). Which makes sense in terms of multilingual use, first boot wizard context, ...
        # table name has always been some sort of table unique ID.
        # still the case for literary braille, but computer braille has to follow what's done in NVDA/LibLouis

        #Anyway... now for Update 1 we store the filename of the computer braille table.
        #therefore we need to now call getTable and not the getTableByDisplayName
        try:
            computerBrailleTable = brailleTables.getTable(requestedTable)
        except LookupError:
            # We absolutely need a table!
            _, defaultComputerBrailleFileName = _get_locale_defaults()
            computerBrailleTable = brailleTables.getTable(defaultComputerBrailleFileName)
            log.info(f"error getting requested table {requestedTable}, fallback to {computerBrailleTable.displayName}:{computerBrailleTable.fileName}")

        return computerBrailleTable.fileName

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
        # BNW-3578 related refactor here
        brailleBefore, posMapBefore, rPosMapBefore, outputPos = self._forwardTranslateChunked(translator, before, 0)


        # translate after
        #BNW-3578 related refactor here too
        brailleAfter, posMapAfter, rPosMapAfter, outputPos = self._forwardTranslateChunked(translator, after, 0)
        

        # reassemble
        braille = brailleBefore + g0CurrentWord + brailleAfter

        posMapCurrentWord = [x + spaceBefore for x in currentWordPos]
        # what's the corresponding position of "spaceBefore" in brailleBefore, which can be contracted?
        # it's the end of the braille
        spaceBeforePos = len(brailleBefore)

        rPosMapCurrentWord = [x + spaceBeforePos for x in currentWordRPos]

        adjustedPosMapAfter = [x + spaceAfter for x in posMapAfter]
        # need to find spaceAfter in the RPos...
        # it's spaceBeforePos + length of currentWord
        spaceAfterPos = spaceBeforePos + len(g0CurrentWord)
        adjustedRPosMapAfter = [x + spaceAfterPos for x in rPosMapAfter]

        posMap = posMapBefore + posMapCurrentWord + adjustedPosMapAfter
        rPosMap = rPosMapBefore + rPosMapCurrentWord + adjustedRPosMapAfter

        return braille, posMap, rPosMap, g0Pos + spaceBeforePos
