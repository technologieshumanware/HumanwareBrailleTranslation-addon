# HumanwareBrailleTranslation Introduction

HumanwareBrailleTranslation is an NVDA add-on that provides alternative Braille translation options.
From the beginning NVDA has used LibLouis braille translation library, while HumanWare has historically partnered with Duxbury Systems for braille translation on a range of products. So this aims to bring continuity for the user base. There's been some incredible efforts put on the LibLouis project with worldwide contributions, and preference is up to the user. Some countries favor such and such translator for various reasons. 
This addon provides some learning tables required for some curiculums which allows to support legacy partnerships with various schools and programs.  
Organization is more in line to the legacy of braille settings on BrailleNote devices, and the language profiles used on those.

It also aims to separate Literary Braille from Computer Braille, as opposed to contracted vs the rest.
Traditionally, literary braille has been Uncontracted (Grade 1), or Contracted (Grade 2), and it requires translation of text to braille according to preferences. Computer braille (Grade 0) involves only a mapping of 256 characters to a braille combination of 8 dots and a direct 1 to 1 conversion of characters. Although for display, different characters can be mapped to the same combination of dots. (For ex: there are many division signs in the Unicode range, and they can all use the same braille dots combination, since the nuance of character is irrelevant).
Typically Literary Braille is 6 dots only, while Computer Braille involves 8 dots to extend range of assigned characters. 
There are some nuances however, intermediates and extras in the Grades, with things like Grade 1.5 or 3, for different levels of contractions, and to adapt to locale specificities. There could be some contracted 8 dots in existence. There is sometimes misuse of the "Grade 0" for things that are actually uncontracted literary braille, and not computer braille.

 


## HumanwareBrailleTranslation settings
* Selection of Literary Braille translator
* Selection of Computer Braille translator
* type of Braille for display
* type of Braille for entry

A shortcut Backspace with G, or CTRL+ALT+G allows to toggle between literary braille and computer braille. That toggle affects both display and input.  

An option to bypass the addon (requires reloading addon) to fallback to the standard braille implementation in NVDA. 
This is essentially an alternative to disabling the addon. 




## Main usages
System wide translations from Braille to print (back translation) and print to Braille  (translation, or forward translation)

## Limitations
Rendering the font formattings, or typeforms in the Braille translation is not supported at the moment. And the typeforms would be simply ignored.
Not all Braille codes cater for typeforms, UEB has some rules to display those, but many don't. Computer braille by definition wouldn't support those. 
Therefore it would be preferable for someone wanting to have typeforms displayed, to have the setting set to "Tags" instead of "LibLouis". 
For more info about those formatting tags, see https://download.nvaccess.org/releases/stable/documentation/userGuide.html#BrailleFormattingDisplayTags
A warning will be given on startup if the settings don't match.
 


## License. 

This hopefully falls under the NVDA plugin exemption where the plugin uses a non-GPL library to process some translations, a situation analog to a speech engine plugin using a proprietary driver.


## Contact and developer information
Technologies HumanWare <ca.info@humanware.com>
