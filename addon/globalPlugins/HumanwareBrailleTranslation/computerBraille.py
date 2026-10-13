# BrailleNoteEvolve add-on
# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# Copyright (C) 2026 Technologies Humanware

#handling of the computerBraille translation duties from the plugin
#making use of louiHelper/Wrapper
#

import sys
import os
import platform
import config
import globalVars
from logHandler import log
from typing import Callable

import louisHelper
import addonHandler

try:
    addonHandler.initTranslation()
except addonHandler.AddonError:
    _ = lambda x: x
else:
    _: Callable[[str], str]

with os.add_dll_directory(globalVars.appDir):
	import louis


DEFAULT_COMPUTER_BRAILLE_TABLE = "English US computer braille"
"""The name of default computer braille table, 
the one that we provide in this addon and guarantee to be there"""


def translate(tableName, inbuf, typeform=None, cursorPos=None, mode=0):

    log.info(f"computer braille translate + '{inbuf}', {cursorPos}") 


    if cursorPos is not None:
        if cursorPos > len(inbuf):
            cursorPos = len(inbuf) + 1

        if cursorPos < 0 :
            cursorPos = 0 

    if (inbuf == " "):
         return [0],[0,1],[0,1], cursorPos


    mode |= louis.dotsIO 
    braille, brailleToRawPos, rawToBraillePos, brailleCursorPos = louisHelper.translate([tableName, "braille-patterns.cti"], inbuf, typeform=typeform, cursorPos=cursorPos, mode=mode)
    
    log.info(f"C braille '{braille}, brailleToRawPos {brailleToRawPos},rawToBraillePos {rawToBraillePos}, brailleCursorPos {brailleCursorPos}")
    #at times we get completely wild brailleCursorPos values (ex: 211680792 when we'd expect something 0< p <20)
    #that seems to come deep from within liblouis
    #we can limit that     
    if brailleCursorPos is not None: 
        if brailleCursorPos >= len(braille):
            log.info(f"#######################    brailleCursorPos is way out!!!")
            #brailleCursorPos = len(braille)
    # or because we're here in the special case of computer braille
    # we can use the fact that
    brailleCursorPos = cursorPos        

    return braille, brailleToRawPos, rawToBraillePos, brailleCursorPos


def backTranslate(tableName, brl: str, cursorPos=None, mode=0) -> str:

    mode |= louis.ucBrl | louis.noUndefinedDots 
    return louis.backTranslate(
        [tableName, "braille-patterns.cti"],
        brl,
        cursorPos=cursorPos or 0,
        mode=mode,
        )[0]

