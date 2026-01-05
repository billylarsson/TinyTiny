TinyTiny: Magic the Gathering deckbuilder

---
<b>Installation:</b> If you're not geeky I'll assume that you wont be able to get this up and running, but its something like: 
* pip install pyqt6 pillow certifi
* python3 tiny.py
---

* Not sure how well this will perform under other screen resolutions than 2160p.

* Tested once inside Windows 11, tested a lot inside Linux.

 * Most features are hardcoded to suit my building behavor, many features arent visualized.

* There’s a lot of hidden searchflags, having a glance inside breakdown.py and look into the <b>smartkeys list[SmartKey]</b>: to figure some of them out, power, toughness, cmc, setcode, owned, stupid, artist, etc etc etc…. use coding operators when searching, power>5 power!=7 setcode=LRW creature=true rarity=common legal=commander legal!=legacy color=temur year<ORI year>2011 ... so on so forth.

* Searching owned cards using owned=True

* Drag and drop cards from search area into your deck, everything is autosaved

* Mouse button thats not 1, 2 or 3 will cycle cards threw expansions sorted by their releasedate.

* Import/Export decklists from Moxfield, Cardmarket or just Plain text using copy-paste.

_theres ton of more stuff that I maybe fill in later_...

random thing: _if someone is looking into the code, I kinda took the opportunity to get better at typehints when crafting this so they're very overrepresented!_

---

Hacks:

* You can manually add your owned cards using “scryfall_id” separated with commas in this file scryfall_ids.csv

---

<img width="3840" height="2160" alt="Screenshot from 2026-01-05 10-53-49" src="https://github.com/user-attachments/assets/60a0bf2b-91eb-4f0e-9ae4-b50beeda5ffa" />

