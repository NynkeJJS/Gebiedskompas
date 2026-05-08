# Gebiedskompas
Github repository voor het Project Gebiedskompas


# Mappenstructuur
## 📁 data/
Bevat alle datasets die binnen het project worden gebruikt, gescheiden naar verwerkingsfase:

raw/
Onbewerkte brondata zoals opgehaald uit externe databronnen of APIs.

bewerkt/
Opgeschoonde en verrijkte data na bewerking door preprocessingstappen.

output/
Resultaten zoals figuren en rapport.


## 📁 ETL/
Scripts en modules voor het Extract, Transform, Load‑proces.
Hier wordt data opgehaald, gevalideerd, opgeschoond en voorbereid voor analyse en experimenten.
Deze ELT is geschreven voor de gemeente Sudwest Fryslan en kan nog niet worden gebruikt.
Ten opzichte van het origineel is aangepast dat cbs_mapping_v2.json wordt gebruikt ipv cbs_mapping_v3.json. Dit in verband met gebruikte CBS dataset.
Het bestand kan niet volledig gerund worden, omdat de benodigde datasets niet op de gebruikte server staan, zoals bij de gemeente.

## 📁 experiment/
Bevat alle experimentele en analytische data‑science‑logica. Deze map vormt het hart van het onderzoeks- en modelleringstraject.
Submappen


config/
Configuratiebestand
themas.yaml bevat een themastructuur voor het bottom-up experiment


### Belangrijke scripts
main_experiment.py
Centrale entrypoint voor het uitvoeren van een experiment.


data_pipeline.py
Definieert de volledige dataverwerkings‑ en analysepipeline.


data_inlezen.py
Functies voor het inladen en voorbereiden van data.


analyse_bottom_up.py
Analyse van experimentele uitkomsten en modelresultaten van de bottom-up methode.


analyse_top_down.py
Analyse en validatie van samengestelde variabelen op basis van de top-down methode.


kerncijfers_ophalen_ETL_experiment.py
Specifieke ETL‑logica voor het ophalen en verwerken van kerncijfers binnen experimenten.
**Wordt niet gebruikt. Zie beschrijving ETL.**


config.py
Python‑gebaseerde configuratie voor experiment‑instellingen.


## 📁 gebied/
Virtuele Python‑omgeving (venv) voor dit project.
Bevat geïnstalleerde packages

Wordt niet gedeeld via Git en is lokaal reproduceerbaar via requirements.txt.


## 📁 structuur/
Bevat structuur zoals gebruikt in het Gebiedskompas van de gemeente Sudwest-Fryslan


## Overige bestanden
📄 requirements.txt
Overzicht van alle Python‑dependencies die nodig zijn om het project uit te voeren.
📄 README.md
Projectdocumentatie met uitleg over doel, aanpak, datastructuur en gebruik.
📄 .gitignore
Specificeert bestanden en mappen die niet worden meegenomen in versiebeheer 