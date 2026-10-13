import sys
from datetime import date

print(sys.copyright)
today = date.today().strftime("%Y.%m.%d")
print(today)
print("test")
print("Ceci est une ligne de texte réellementlongue qui va " +
      "deuxième partie")
