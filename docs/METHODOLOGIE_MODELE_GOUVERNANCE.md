# Dossier Methodologie, Limites et Gouvernance Modele

## 1) Cadre Methodologique

Le moteur couvre la mesure IRRBB en double vision:
- EVE (Economic Value of Equity): **EVE = PV(actifs) − PV(passifs)**.
- NII 12 mois: impact resultat comptable court terme.
- EAR (Earnings-at-Risk): ecart de resultat en stress vs baseline NII.
- SOT EVE (15% Tier 1, 6 chocs) et SOT NII (5% Tier 1, Parallel Up/Down, 1 an).
- LCR / NSFR: dimension liquidite structurelle (caps HQLA L2 ≤ 40%, L2B ≤ 15%).
- FTP: transfer pricing interne pour pilotage commercial vs funding.

### Modeles de taux
- Courbe initiale: Nelson-Siegel-Svensson.
- Dynamique court terme: Hull-White 1 facteur.
- Benchmark: Vasicek pour comparaison pedagogique.

### Scenarios reglementaires
- 6 scenarios standards IRRBB:
  - Parallel Up
  - Parallel Down (avec floor a 0)
  - Steepener
  - Flattener
  - Short Rate Up
  - Short Rate Down

### Supervisory Outlier Tests
- **SOT EVE**: |ΔEVE| ≥ 15% Tier 1 sur l'un des 6 chocs → flag `outlier`.
- **SOT NII**: large decline NII 1 an > 5% Tier 1 sur Parallel Up/Down uniquement → flag `outlier_nii`.
  - Indicateur de supervision (pas declencheur automatique de capital).
  - Seuil historiquement propose a 2,5% puis recalibre a 5% (paquet EBA / CDR 2024/856).

### Feux tricolores ALCO
- RED (≥15%): aligne le SOT EVE.
- AMBER (10–15%): **early-warning interne**, non reglementaire.
- GREEN (<10%): confort interne.

### Instruments et hypotheses comportementales
- Pret taux fixe: amortissement, prepayment CPR.
- Pret taux variable: index + spread.
- NMD: approche par portefeuille replicant, beta de pass-through, core ratio et maturite comportementale.
- Hedge overlay: swap de couverture simplifie pour illustrer la reduction potentielle de sensibilite NII.

## 2) Calibration et Donnees

### Source principale
- API ECB Data pour historique de taux court terme.
- API ECB Data multi-maturités (1Y, 2Y, 5Y, 10Y, 20Y, 30Y) pour fit NSS de la courbe initiale.
- Appel a chaque run (series mensuelles) — pas un flux tick-by-tick temps reel.

### Mecanisme de resilience
- En cas d indisponibilite API: fallback synthetique controle pour garantir la continuite des tests et demos.

### Calibration Hull-White
- Calibration simplifiee sur historique de short rate (regression discrete type OU).
- Parametres produits:
  - mean reversion (a)
  - volatilite (sigma)
  - moyenne long terme (mu)

### Calibration courbe initiale NSS
- Fit sur le dernier point de structure par terme BCE complete.
- Approche de minimisation numerique legere (random search robuste) pour rester sans dependance lourde.

## 3) Gouvernance modele (Model Risk)

### Controles de premier niveau
- Tests unitaires automatiques (pytest), incluant SOT NII et caps LCR.
- Verification de coherence des sorties (6 scenarios, floor, WAL positif, dual SOT).

### Controles de second niveau (a mettre en place en cible)
- Recalibration periodique (mensuelle/trimestrielle).
- Backtesting de sensibilites EVE/NII.
- Benchmarks alternatifs (multi-factor, replicas plus fins).

### Documentation et auditabilite
- Exports ALCO standards (Excel + PDF) versionnes.
- Metadonnees de run inclues: date run, source calibration, parametres, flags SOT.
- Synthese management auto (pire scenario, SOT EVE/NII, feux internes).

## 4) Limites connues

- Calibration HW simplifiee sans instruments optionnels cap/floor.
- Scenarios definis via implementation pedagogique mais conformes dans l esprit IRRBB/EBA.
- NMD simplifie: pas de segmentation client/produit.
- NII simplifie: sans strategie dynamique de hedging ni production nouvelle.
- SOT NII: logique seuil pedagogique (decline vs Tier 1) sans tout le detail modelling assumptions du RTS.

## 5) Roadmap vers niveau production bancaire

- Calibration sur surface cap/floor OTC.
- Segmentation NMD multi-portefeuilles (retail, SME, corporate).
- Moteur de hedge transfer pricing / FTP integre.
- Scenarios idiosyncratiques internes ICAAP + reverse stress testing.
- Pipeline CI/CD complet avec qualite code, couverture minimale et validations model risk.
- Enrichissement des indicateurs ALCO (duration gap, convexity breakdown).
- Affinage SOT NII aux hypotheses communes de modelisation EBA (constant balance sheet, etc.).
