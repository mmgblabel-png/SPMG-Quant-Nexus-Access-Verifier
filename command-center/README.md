# SPMG AI Command Center v1.0 — geen ZIP-updates

Een privé chatinterface op `http://127.0.0.1:8792` voor de **bestaande** SPMG Desktop Agent in `Documents\SPMG-Sandbox\AI-Agent-Work\SPMG-Desktop-Agent`. Broncode staat bij je bestaande GitHub-repository onder `command-center/`; updates worden bij starten gecontroleerd op SHA-256 en geïnstalleerd met een terugzetkopie.

## Eenmalig op Windows installeren

Open PowerShell (normale rechten) en voer uit:

```powershell
$installer = Join-Path $env:TEMP 'SPMG-Command-Center-bootstrap.ps1'
Invoke-WebRequest 'https://raw.githubusercontent.com/mmgblabel-png/SPMG-Quant-Nexus-Access-Verifier/main/command-center/bootstrap.ps1' -OutFile $installer
powershell -NoProfile -ExecutionPolicy Bypass -File $installer
```

Daarna staat er één blijvende map:
`%USERPROFILE%\Documents\SPMG-Sandbox\AI-Agent-Work\SPMG-Command-Center`

Start voortaan `START-SPMG.cmd`. Dat controleert bij de start op updates en opent de lokale chat. Handmatig bijwerken kan met `UPDATE-SPMG.cmd`. Geen nieuwe ZIP-pakketten.

**Eenmalige overgang:** stop de vorige Agent Bridge (`run-bridge.ps1`) met `Ctrl+C`, anders weigert het Command Center bewust gelijktijdige Game Maker-besturing.

## Chatfuncties (wat werkt / wat nog niet)

- **`status`**: leest de nieuwste bestaande bouwrun en uitvoerstatus.
- **`controleer Game Maker`**: maakt een screenshot met de bestaande `agent.py --probe` zonder API-verzoeken.
- **`kalibreer het stenen pad`**: voert het bestaande beperkte kalibratieplan uit via v0.9.1.
- **`test eerste steen`**: voert hoogstens één gecontroleerde, niet-opgeslagen vervangingsproef uit. De juiste plaatsing is nog niet op Windows bewezen.
- **`plaats een boom`**: wordt terecht geblokkeerd totdat de Actors-telling betrouwbaar en actueel is; er zijn eerder dubbele bomen geplaatst.
- **`ontwerp Welcome Plaza`**: levert, met geconfigureerde AI-chat, een plan; nog geen onbewezen volledige autonoom gebouwde wereld.
- **`update jezelf`**: wijst je naar de geïntegreerde updatefunctie; de bron wordt bij volgende start automatisch gecontroleerd.

Alle bouwruns blijven beschikbaar in de bestaande `SPMG-Desktop-Agent\runs` map. Geen publicatie, marketplace, wallet of NFT-acties; Game Maker alleen op de bekende **AI Build Backup**. Geen willekeurige shell-opdrachten uit AI-antwoorden. Krijgt de agent de verkeerde Game Maker-indeling of ontbrekende status, dan weigert hij de bouwactie.

## Eigen ChatGPT-gesprek / OpenAI

Voor vrije gesprekken gebruikt de lokale chat de **OpenAI Responses API** via je bestaande Python `openai` bibliotheek. Stel optioneel op je Windows-account een `OPENAI_API_KEY` in via de normale omgeving. **Deel de sleutel nooit in de chat of broncode.** Je ChatGPT Plus/Pro-abonnement is niet automatisch API-tegoed. Zonder sleutel werken alle lokale vaste opdrachten en de monitor nog steeds.

Bijvoorbeeld in een *tijdelijk* PowerShell-venster (sleutel niet in code plakken):
```powershell
$env:OPENAI_API_KEY = Read-Host 'OpenAI API-key (lokaal)'
& "$HOME\Documents\SPMG-Sandbox\AI-Agent-Work\SPMG-Command-Center\start.ps1"
```

Opmerkingen: de app luistert alleen op `127.0.0.1`, chatberichten worden lokaal opgeslagen in `data/command-center.sqlite3`, API-aanroepen kosten afhankelijk van je OpenAI-verbruik, en een lokale desktop-agent kan alleen draaien zolang Windows ontgrendeld en de applicatie actief is. Publicatie is altijd handmatig.

## Tests

```powershell
py -3 -m unittest test_app.py -v
```

Test de app eerst met `status`, daarna `controleer Game Maker`; stuur niet zomaar meerdere terreinproeven omdat eerdere wijzigingen niet per se zijn opgeslagen.