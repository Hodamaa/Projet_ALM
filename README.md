# Projet ALM Engine (IRRBB - Bâle IV)

Moteur ALM orienté banque de détail pour mesurer le risque de taux:
- Modèle de taux `Hull-White 1 factor` calibrable sur historiques BCE
- Courbe initiale `Nelson-Siegel-Svensson`
- Instruments `fixed-rate`, `floating-rate`, `NMD`
- Métriques `EVE` (valeur économique) et `NII` (12 mois)
- 6 scénarios réglementaires IRRBB + **SOT EVE (15% Tier 1)** et **SOT NII (5% Tier 1, Parallel)**
- Prépayment `CPR` et indicateur `WAL`
- Dashboard Streamlit pour démonstration entretien
- Données BCE branchées automatiquement (avec fallback robuste)
- Calibration de courbe initiale NSS sur structure par terme BCE (multi-maturités)
- Exports ALCO professionnels (Excel + PDF)
- EAR (Earnings-at-Risk) et stratégie de hedge overlay (swap)
- Optimiseur automatique de hedge (minimisation du pire delta NII)
- Ratios liquidité LCR / NSFR et pilotage FTP intégrés
- Dossier méthodologie / gouvernance modèle
- Tests unitaires `pytest`
- Scénarios internes ICAAP (en plus des 6 scénarios réglementaires)
- Pack entretien auto (ZIP: rapport + docs)

## Installation

```bash
pip install -r requirements.txt
```

## Exécution CLI

```bash
python main.py --tier1 120000000 --cpr 0.06 --hedge-notional 100000000
```

Optimisation automatique du hedge:

```bash
python main.py --optimize-hedge
```

Option pour ne garder que Bâle IV (sans ICAAP):

```bash
python main.py --no-internal-scenarios
```

## Exécution Dashboard

```bash
streamlit run alm_engine/dashboard/app.py
```

Le dashboard inclut:
- onglet `Synthèse ALCO` (KPIs, feux tricolores, recommandation)
- onglet `Bilan A/P` (composition actif/passif + lien vers les métriques)
- visualisations Plotly (EVE, NII waterfall, courbe NSS, heatmap)
- bouton `Mode Demo 2 min` + `Mode Présentation` (timer 2 min)
- bouton `Preset BPAURA` (bilan banque coopérative retail)
- section `Limites du modèle`
- bouton `Optimiser hedge`
- onglet `Liquidity & Funding` avec jauges LCR/NSFR/FTP
- historique des runs et tendances des ratios

## Calibration BCE (historique)

Le module `alm_engine/calibration/calibrate_hw.py` inclut:
- `load_ecb_yields(csv_path)` pour charger un CSV `date,yield`
- `calibrate_from_historical_short_rate(df)` pour calibrer `(a, sigma, mu)`
- `calibrate_hw_from_ecb()` pour calibration automatique depuis l'API BCE

Tu peux brancher ensuite ces paramètres dans `HullWhite1F`.

## Exports ALCO

La CLI génère automatiquement dans `outputs/`:
- `alco_report_*.xlsx`
- `alco_report_*.pdf`
- `interview_pack_*.zip`

Le dashboard permet aussi le téléchargement direct.
Le reporting inclut désormais:
- feuille KPI avec feu tricolore (GREEN/AMBER/RED)
- commentaire de gestion automatique de type comité ALCO
- métriques EAR et effet hedge sur NII
- synthèse LCR/NSFR/FTP (metadata + onglets Excel dédiés)

## Tests

```bash
python -m pytest -q
```

CI GitHub Actions fournie dans `.github/workflows/ci.yml`.

## Documentation méthodologique

Consulte `docs/METHODOLOGIE_MODELE_GOUVERNANCE.md` pour:
- hypothèses
- limites
- contrôles
- roadmap production

Pour l'entretien, fiche à apprendre par cœur :
`docs/FICHE_ENTRETIEN_APPRENDRE.md`.

