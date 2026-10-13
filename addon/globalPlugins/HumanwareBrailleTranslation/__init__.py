# BrailleNoteEvolve add-on
# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# Copyright (C) 2026 Technologies Humanware

# entry point for HWTranslation
import brailleTranslation
from .HWTranslationProvider import HWTranslationProvider
from .computerBraille import DEFAULT_COMPUTER_BRAILLE_TABLE
from .constants import BRAILLE_TYPE_LITERARY, BRAILLE_TYPE_COMPUTER

import api
import addonHandler
import globalPluginHandler
import globalCommands
import wx
import config
from config.featureFlagEnums import FontFormattingBrailleModeFlag

from scriptHandler import script

import ui
import gui
from gui.settingsDialogs import SettingsPanel, NVDASettingsDialog

from logHandler import log
from globalCommands import SCRCAT_CONFIG
from typing import Callable
import brailleTables

try:
    addonHandler.initTranslation()
except addonHandler.AddonError:
    # Running from scratchpad - use defaults
    _ = lambda x: x
else:
    _: Callable[[str], str]

# Get addon summary from manifest
try:
    ADDON_SUMMARY = addonHandler.getCodeAddon().manifest['summary']
except:
    ADDON_SUMMARY = _("HumanWare Braille Translation")

translationProvider = HWTranslationProvider()
translationProvider.init()

TRANSLATOR_TYPE_MAP = {
    # Translators: This is the label for Literary braille in the addon settings panel.
    _("Literary Braille"): BRAILLE_TYPE_LITERARY,
    # Translators: This is the label for Computer braille in the addon settings panel.
    _("Computer Braille"): BRAILLE_TYPE_COMPUTER
}

def getLocalizedBrailleType(brailleTypeConstant: str) -> str:
    """Get the localized display string for a braille type constant.
    @param brailleTypeConstant: Non-localized constant (BRAILLE_TYPE_LITERARY or BRAILLE_TYPE_COMPUTER)
    @return: Localized string for display
        """
    for localizedLabel, constant in TRANSLATOR_TYPE_MAP.items():
        if constant == brailleTypeConstant:
            return localizedLabel
        
    # Fallback to constant if not found
    log.debugWarning(f"No localized label found for braille type '{brailleTypeConstant}', using default")
    return next(iter(TRANSLATOR_TYPE_MAP.keys()))

instanceGP = None

confspec = {
    "bypass": 'boolean(default="False")',
    "translatorChoice": 'string(default="English UEB Duxbury grade 2")',
    "G0TranslatorChoice": f'string(default="{DEFAULT_COMPUTER_BRAILLE_TABLE}")',
    "TranslatorTypeForEntry": f'string(default="{BRAILLE_TYPE_LITERARY}")',
    "TranslatorTypeForDisplay": f'string(default="{BRAILLE_TYPE_LITERARY}")'
}

config.conf.spec["HumanwareBrailleTranslation"] = confspec


class AddonSettingsPanel(SettingsPanel):

    title = ADDON_SUMMARY

    def makeSettings(self, settingsSizer):

        # Translators: This is the label for a checkbox in the addon settings panel.
        bypass_title = _("Disable and use default Braille translation")
        
        braille_settings_gui_helper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.bypasscheckbox = braille_settings_gui_helper.addItem(wx.CheckBox(
            self,
            label=bypass_title,
        ),)
        self.bindHelpEvent("TranslationAddonBypassHelp", self.bypasscheckbox)
        self.bypasscheckbox.SetValue(
            config.conf["HumanwareBrailleTranslation"]["bypass"],
        )
        
        # Translators: This is the label for a combobox in the addon settings panel.
        self._translator_choice_title = _("Literary Braille translator:")
        self._translator_choices = translationProvider.getTranslators()
        
        self._translator_choice = braille_settings_gui_helper.addLabeledControl(self._translator_choice_title, wx.Choice, choices=self._translator_choices)
        cur_choice = config.conf["HumanwareBrailleTranslation"]["translatorChoice"]
        try:
            index = self._translator_choices.index(cur_choice)
            self._translator_choice.SetSelection(index)
        except ValueError:
            log.debugWarning(f"Could not find '{cur_choice}' in translator choices")

        #extra settings for input/output ? 
        #computer braille 
        #self._G0_translator_choices = [ #TODO where do we get a list of G0 ? 
        #    _("English US computer braille"), #the one we provide
        #    _("English (U.S.) 8 dot computer braille"),
        #    _("French (unified) 8 dot computer braille"),
        #    _("Spanish 8 dot computer braille")
        #]
        self._G0_translator_choices = []
        for table in brailleTables.listTables():
            if (table.computerBraille == True):
                self._G0_translator_choices.append(table.displayName) # TODO need to verify if these are localized to make sure we don't save localized value into the config file

        # Translators: This is the label for a combobox in the addon settings panel.
        self._G0_translator_choice_title = _("Computer Braille translator:")

        self._G0_translator_choice = braille_settings_gui_helper.addLabeledControl(self._G0_translator_choice_title, wx.Choice, choices=self._G0_translator_choices)
        cur_choice = config.conf["HumanwareBrailleTranslation"]["G0TranslatorChoice"]
        try:
            index = self._G0_translator_choices.index(cur_choice)
            self._G0_translator_choice.SetSelection(index)
        except ValueError:
            log.debugWarning(f"Could not find '{cur_choice}' in G0 translator choices")

        # Translators: Label for the preferred braille grade for entry.
        self.translator_entry_type_choice_title = _("Preferred Braille grade for entry")
        self._translator_types = list(TRANSLATOR_TYPE_MAP.keys())
        self._translator_entry_type_choice = braille_settings_gui_helper.addLabeledControl(self.translator_entry_type_choice_title, wx.Choice, choices=self._translator_types)
        currentType = config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"]
        localizedType = getLocalizedBrailleType(currentType)
        try:
            index = self._translator_types.index(localizedType)
            self._translator_entry_type_choice.SetSelection(index)
        except ValueError:
            log.debugWarning(f"Could not find '{currentType}' in translator entry type choices, using default")
            self._translator_entry_type_choice.SetSelection(0)

        # Translators: Label for the preferred braille grade for display.
        self.translator_display_type_choice_title = _("Preferred Braille grade for display")
        self._translator_display_type_choice = braille_settings_gui_helper.addLabeledControl(self.translator_display_type_choice_title, wx.Choice, choices=self._translator_types)
        currentType = config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForDisplay"]
        localizedType = getLocalizedBrailleType(currentType)
        try:
            index = self._translator_types.index(localizedType)
            self._translator_display_type_choice.SetSelection(index)
        except ValueError:
            log.debugWarning(f"Could not find '{currentType}' in translator display type choices, using default")
            self._translator_display_type_choice.SetSelection(0)



    def postInit(self):
        self._translator_choice.SetFocus()

    def onSave(self):
        config.conf["HumanwareBrailleTranslation"]["bypass"] = self.bypasscheckbox.IsChecked()
        #could we unregister and restart brailleTranslation init?
        config.conf["HumanwareBrailleTranslation"]["translatorChoice"] = self._translator_choices[self._translator_choice.GetSelection()]
        config.conf["HumanwareBrailleTranslation"]["G0TranslatorChoice"] = self._G0_translator_choices[self._G0_translator_choice.GetSelection()]
        config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"] = TRANSLATOR_TYPE_MAP[self._translator_types[self._translator_entry_type_choice.GetSelection()]]
        config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForDisplay"] = TRANSLATOR_TYPE_MAP[self._translator_types[self._translator_display_type_choice.GetSelection()]]




class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = globalCommands.SCRCAT_BRAILLE

    @script(
        # Translators: Description for the toggle braille grade command.
        description=_("Toggles between Literary Braille and Computer Braille"),
        gesture="kb:control+alt+g"
    )
    def script_toggleBrailleGrade(self, gesture):
        self._toggleBrailleGrade( )


    def _toggleBrailleGrade(self):
        #get current type
        typeOfBrailleForEntry = config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"]
        if typeOfBrailleForEntry == BRAILLE_TYPE_COMPUTER:
            newBrailleType = BRAILLE_TYPE_LITERARY
        else:
            newBrailleType = BRAILLE_TYPE_COMPUTER

        #apply to both input and display
        config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"] = newBrailleType
        config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForDisplay"] = newBrailleType
        log.info(newBrailleType)
        ui.message(getLocalizedBrailleType(newBrailleType))
        #need to force a refresh of all regions
        import braille
        braille.handler.handleGainFocus(api.getFocusObject(), shouldAutoTether=False)

    def __init__(self):
        log.debug("HWTranslation plugin init-")
        global instanceGP
        super().__init__()
        instanceGP = self

        #if we only registerProvider here
        #we can check that the settings are compatible with the plugin use
        #If user prefers to use plain liblouis or 100% computer braille
        #then we can bypass "us" and not register, or deregister. 

        #or there could be a "bypass setting"
        if config.conf["HumanwareBrailleTranslation"]["bypass"] is False: 
            brailleTranslation.registerProvider(translationProvider)
        else :
            log.debug("HumanwareBrailleTranslation plugin BYPASS")


        #we can also check and warn if some options are unsupported
        if config.conf["braille"]["fontFormattingDisplay"].calculated() != FontFormattingBrailleModeFlag.TAGS:
            # Translators: Warning message when starting and incompatible options are detected.
            warningMessage = _("Rendering of the typeforms in Braille translation is not supported")
            log.debug(warningMessage)
            ui.message(warningMessage)

        self.isEnabled = False
        NVDASettingsDialog.categoryClasses.append(AddonSettingsPanel)

        # Register to post config reset event so we can apply default
        # HW braille translation config after factory reset
        config.post_configReset.register(self.onPostConfigReset)


    def onPostConfigReset(self, factoryDefaults=False):
        if factoryDefaults:
            # Reset all values to their defaults from confspec
            config.conf["HumanwareBrailleTranslation"]["bypass"] = False
            config.conf["HumanwareBrailleTranslation"]["translatorChoice"] = "English UEB Duxbury grade 2"
            config.conf["HumanwareBrailleTranslation"]["G0TranslatorChoice"] = DEFAULT_COMPUTER_BRAILLE_TABLE
            config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForEntry"] = BRAILLE_TYPE_LITERARY
            config.conf["HumanwareBrailleTranslation"]["TranslatorTypeForDisplay"] = BRAILLE_TYPE_LITERARY

    def onSettings(self, evt):
        gui.mainFrame.popupSettingsDialog(NVDASettingsDialog, AddonSettingsPanel)

    @script(
        # Translators: Describes a command.
        description=_("Shows the %s settings.") % ADDON_SUMMARY,
        category=SCRCAT_CONFIG
    )
    def script_settings(self, gesture):
        wx.CallAfter(self.onSettings, None)

    def handleConfigProfileSwitch(self):
        if self.isEnabled:
            self.disable()
            self.enable()

    def terminate(self):
        translationProvider.terminate()
        self.disable()
        #NVDASettingsDialog.categoryClasses.remove(AddonSettingsPanel)

    def enable(self):
        if self.isEnabled:
            return
        self.isEnabled = True

    def disable(self):
        if not self.isEnabled:
            return
        self.isEnabled = False
