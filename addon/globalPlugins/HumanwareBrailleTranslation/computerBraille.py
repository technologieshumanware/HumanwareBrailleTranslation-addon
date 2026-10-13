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

def translate(tableName, inbuf, typeform=None, cursorPos=None, mode=0):

    #disabled logs, reinstate only for investigations of particular issues 
    #log.info(f"computer braille translate + '{inbuf}', {cursorPos}") 


    if cursorPos is not None:
        if cursorPos > len(inbuf):
            cursorPos = len(inbuf) + 1

        if cursorPos < 0 :
            cursorPos = 0 

    if (inbuf == " "):
         return [0],[0,1],[0,1], cursorPos


    mode |= louis.dotsIO 
    braille, brailleToRawPos, rawToBraillePos, brailleCursorPos = louisHelper.translate([tableName, "braille-patterns.cti"], inbuf, typeform=typeform, cursorPos=cursorPos, mode=mode)
    
   
    if cursorPos is None:
        brailleCursorPos = None
    elif cursorPos is not None and rawToBraillePos and cursorPos < len(rawToBraillePos):
        brailleCursorPos = rawToBraillePos[cursorPos]
    elif brailleCursorPos is None or (braille and brailleCursorPos >= len(braille)):
        brailleCursorPos = len(braille) - 1 if braille else 0

    #disabled logs, reinstate only for investigations of particular issues
    #log.info(f"C braille '{braille}, brailleToRawPos {brailleToRawPos},rawToBraillePos {rawToBraillePos}, brailleCursorPos {brailleCursorPos}")

    return braille, brailleToRawPos, rawToBraillePos, brailleCursorPos


def backTranslate(tableName, brl: str, cursorPos=None, mode=0) -> str:

    mode |= louis.ucBrl | louis.noUndefinedDots 
    return louis.backTranslate(
        [tableName, "braille-patterns.cti"],
        brl,
        cursorPos=cursorPos or 0,
        mode=mode,
        )[0]
