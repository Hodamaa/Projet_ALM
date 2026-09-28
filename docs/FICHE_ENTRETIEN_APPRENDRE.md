# Fiche entretien ALM — à apprendre par cœur

> Projet prêt pour démo entretien BPAURA (forme finalisée *démo / stage*).  
> Ce n’est **pas** un moteur production : assume les limites, c’est un plus.

---

## 1) Pitch 30 secondes (ouvre avec ça)

« J’ai construit un moteur ALM retail pour mesurer le risque de taux du banking book (IRRBB) dans l’esprit Bâle / EBA.  
Il calibre une courbe NSS et un Hull-White sur données BCE, projette un bilan (prêts fixes, flottants, NMD), applique les 6 chocs réglementaires + scénarios ICAAP, et sort EVE, NII, EAR, avec les **deux SOT** (EVE 15% Tier 1 et NII 5% Tier 1), plus LCR/NSFR/FTP.  
Le tout est pilotable via un dashboard Streamlit type comité ALCO, avec hedge overlay, exports et tests/CI.  
L’objectif : montrer que je comprends la dualité valeur économique / résultat, le cadre de supervision, et les limites d’un modèle comportemental. »

---

## 2) Verdict : le laisser ainsi ?

**Oui, pour l’entretien.** Le projet est dans une forme finalisée *démonstration* :

| Critère | Statut |
|---|---|
| Problème métier clair (IRRBB) | OK |
| Cadre réglementaire (6 chocs + SOT EVE 15% + SOT NII 5%) | OK |
| Stack technique démontrable | OK |
| Dashboard démo 2 min | OK |
| Limites documentées | OK |
| Tests + CI | OK |

**Ne pas promettre** : modèle NMD de production, calibration caps/floors, pipeline bilan réel.  
**Promettre** : compréhension ALM, rigueur, conscience du model risk, roadmap claire.

---

## 3) Problème métier (pourquoi ça existe)

- Banque de détail = actifs longs à taux fixe (crédits immo) vs passifs courts / sans maturité (dépôts NMD).
- Quand les taux bougent → écart de duration → risque de valeur (EVE) et de marge (NII).
- Régulateur (Bâle / EBA IRRBB) exige des chocs standardisés + un **Supervisory Outlier Test**.
- ALCO doit arbitrer : accepter le risque, hedger, ou revoir la structure du bilan.

---

## 4) Dualité EVE vs NII (question #1 d’entretien)

| | **EVE** | **NII** |
|---|---|---|
| Question | Quelle est la sensibilité de la **valeur économique** des fonds propres ? | Quel impact sur le **résultat** à 12 mois ? |
| Définition | **EVE = PV(actifs) − PV(passifs)** (écart actif/passif, pas une somme brute de CF) | Intérêts reçus − coûts de dépôts sur 1 an |
| Horizon | Long (tous les CF actualisés) | Court (1 an) |
| Focus | Duration / valeur | Marge d’intérêt |
| Qui regarde | Régulateur + ALCO solvabilité | ALCO P&L + commercial |

**Phrase clé :** « EVE et NII peuvent donner des signaux opposés : un Parallel Up peut détériorer l’EVE (actifs longs) tout en améliorant le NII si les actifs se reprice plus vite que les dépôts. D’où la double vision. »

**Ne jamais dire :** « EVE = somme des CF actualisés » → c’est la **PV**. L’EVE est la **différence** PV actifs − PV passifs.

**EAR** = Earnings-at-Risk = écart de NII en stress vs baseline (lecture “combien de résultat je perds”).

---

## 5) Cadre réglementaire IRRBB (à connaître)

### 6 scénarios Bâle / EBA (pour le SOT EVE)
1. **Parallel Up** (+200 bp typiquement dans l’esprit standard)
2. **Parallel Down** (−200 bp, avec floor à 0 dans le moteur)
3. **Steepener** (court ↓, long ↑)
4. **Flattener** (court ↑, long ↓)
5. **Short Rate Up**
6. **Short Rate Down**

### Deux Supervisory Outlier Tests (SOT)

| | **SOT EVE** | **SOT NII** |
|---|---|---|
| Seuil | **15 % du Tier 1** | **5 % du Tier 1** (ex-2,5 %, recalibré EBA/Commission) |
| Scénarios | les **6** chocs | **Parallel Up / Down uniquement** |
| Horizon | valeur économique (run-off) | **NII 1 an** |
| Nature | seuil de supervision | indicateur de supervision (pas auto-capital) |
| Dans le moteur | colonne `outlier` | colonne `outlier_nii` + metadata `sot_nii_*` |

**Phrase :** « Le SOT NII est devenu opérationnel avec le paquet EBA / CDR 2024/856 : large decline = baisse du NII 1 an > 5 % du Tier 1, sur les deux parallèles. »

### Feux tricolores du dashboard
- **RED (≥ 15 %)** : aligne le SOT EVE réglementaire
- **AMBER (10–15 %)** : **early-warning interne ALCO**, **pas** un seuil EBA
- **GREEN (< 10 %)** : zone de confort interne

### ICAAP
- En plus du réglementaire : scénarios internes (stagflation, recession bull-flattening, policy shock).
- Phrase : « Bâle/EBA = socle commun ; ICAAP = risques idiosyncratiques de la banque. »

### Coopératives / capital (si on te pousse)
- Ne dis **pas** « CCI = CET1 » au pied de la lettre.
- Dis : « les parts sociales / instruments coopératifs **contribuent aux fonds propres** ; l’éligibilité CET1 dépend du CRR (ex. art. 29) et du traitement de l’instrument. »

---

## 6) Architecture du projet (carte mentale)

```
Données BCE (API + fallback)
        ↓
Courbe NSS  +  Calibration Hull-White 1F
        ↓
Instruments : Fixed loan | Floating loan | NMD
        ↓
Chocs Bâle (6) + ICAAP (3)
        ↓
Métriques : EVE | NII | EAR | Hedge overlay
        +
Liquidité : LCR | NSFR | FTP
        ↓
Sorties : CLI | Streamlit | Excel/PDF | ZIP entretien
```

### Modules clés
| Dossier | Rôle |
|---|---|
| `alm_engine/models/` | NSS, Hull-White, Vasicek |
| `alm_engine/instruments/` | Prêts fixe/flottant, NMD |
| `alm_engine/risk/` | Scénarios, EVE, NII, EAR, hedge, optimiser |
| `alm_engine/liquidity/` + `funding/` | LCR, NSFR, FTP |
| `alm_engine/calibration/` + `data/` | BCE + fit |
| `alm_engine/engine.py` | Orchestrateur `run_engine` |
| `alm_engine/dashboard/` | Streamlit démo |
| `alm_engine/reporting/` | ALCO Excel/PDF + pack |

### Commandes
```bash
pip install -r requirements.txt
python main.py --tier1 120000000 --cpr 0.06 --hedge-notional 100000000
streamlit run alm_engine/dashboard/app.py
python -m pytest -q
```

---

## 7) Modèles de taux (ce que tu dois savoir dire)

### Nelson-Siegel-Svensson (NSS)
- **Courbe zéro** paramétrique (niveau, pente, courbure…).
- Sert de **courbe initiale** pour actualiser et pour les forwards.
- Calibrée sur structure par terme BCE multi-maturités (1Y…30Y), sinon fallback.

### Hull-White 1 facteur
- Modèle de **taux court** avec retour à la moyenne : `dr = [θ(t) − a·r] dt + σ dW`.
- `a` = mean reversion, `σ` = vol, `θ(t)` calé pour coller à la courbe.
- Calibré de façon **simplifiée** sur historique short-rate (régression type OU).
- **Limite assumée :** pas de calibration sur caps/floors OTC.

### Vasicek
- Benchmark pédagogique (OU simple) — pas le cœur de la démo.

---

## 8) Instruments du bilan

### Prêt taux fixe
- Amortissement + **CPR** (prépayment annuel) → SMM mensuel.
- **WAL** = Weighted Average Life (durée de vie moyenne pondérée).
- Sensible à Parallel Down (refi) — mais CPR encore **constant** (limite).

### Prêt taux variable
- Index (forward courbe) + **spread**.
- Se reprice → protège mieux le NII en hausse de taux.

### NMD (Non-Maturity Deposits)
- Dépôts sans maturité contractuelle (comptes, livrets…).
- Modèle : **beta** (pass-through des taux), **core ratio**, maturité comportementale, portefeuille **réplicatif**.
- **Cœur du risque ALM retail / coopérative.**
- Limite #1 : comportement **statique**, pas de fuite dynamique en stress.

---

        ## 9) Hedge overlay

        - Swap **pay fixed / receive float** sur un notionnel.
        - Objectif démo : **réduire la sensibilité NII** (pire ΔNII).
        - Optimiseur = grille de notionnels → minimise le max |ΔNII|.
        - Phrase : « Ce n’est pas un moteur de hedge accounting ; c’est un what-if ALCO. »

        ---

        ## 10) Liquidité & FTP (bonus crédible)

        | Indicateur | Idée |
        |---|---|
        | **LCR** | HQLA / sorties nettes 30j (≥ 100 %) |
        | **NSFR** | ASF / RSF (≥ 100 %) — financement stable |
        | **FTP** | Prix de transfert interne : marge commerciale vs coût de funding |

        Phrase : « J’ai relié IRRBB et liquidité/funding pour coller au pilotage ALCO, même si LCR/NSFR restent simplifiés et non encore corrélés aux chocs de taux. »

---

## 11) Chiffres preset BPAURA (mémorise-les)

| Poste | Valeur |
|---|---|
| Tier 1 | **150 M€** |
| Crédits fixes | **250 M€** @ 2,5 %, maturité 15 ans |
| Crédits flottants | **100 M€** (Euribor + 1,5 %) |
| NMD | **300 M€**, beta **0,30**, core ~85 % |
| Wholesale | **50 M€** |
| CPR | **5 %** |
| Hedge | **75 M€** |

Démo générique : Tier1 120 M€, CPR 6 %, hedge 0.

---

## 12) Script démo 2 minutes (chrono)

1. **0:00–0:20** — Pitch 30s + ouvrir dashboard.  
2. **0:20–0:40** — Cliquer **Preset BPAURA** → « bilan type coopérative retail ».  
3. **0:40–1:10** — Onglet **Synthèse ALCO** : pire ΔEVE, **SOT EVE + SOT NII**, feux (préciser AMBER = interne).  
4. **1:10–1:40** — **Mode Présentation** : EVE bars → waterfall NII → courbe NSS → heatmap.  
5. **1:40–2:00** — Ouvrir **Limites du modèle** + une phrase roadmap (NMD dynamique / CPR optionnel).

Si question hedge : bouton **Optimiser hedge** → montrer l’effet sur NII.

---

## 13) Limites (à réciter sans hésiter)

1. **NMD** : modèle statique, pas de segmentation client/produit, pas de dynamique de volume en stress.  
2. **CPR** : constant, pas d’optionalité / sensibilité aux taux.  
3. **Calibration HW** : historique short-rate, **pas** surface caps/floors.  
4. **Corrélation crédit–taux** : absente.  
5. **NII** : pas de production nouvelle ni hedge dynamique.  
6. **LCR/NSFR** : simplifiés, pas liés aux scénarios de taux.

**Phrase magique :**  
« Le modèle est volontairement transparent sur ses limites : en comité modèle, je prioriserais d’abord le comportemental NMD, puis le CPR optionnel, puis la calibration optionnelle. »

---

## 14) Roadmap (si on te demande “et après ?”)

1. Segmentation NMD multi-portefeuilles + betas en stress  
2. CPR dynamique (incentive refi)  
3. Calibration HW sur caps/floors  
4. Lien IRRBB ↔ liquidité (fuite dépôts)  
5. Backtesting sensibilités 2022–2023  
6. Reverse stress / limites ALCO contraintes sur hedge  

---

## 15) Q&R express (prépare ces réponses)

**Q. Pourquoi Hull-White et pas juste des chocs sur la courbe ?**  
R. Les chocs réglementaires suffisent au SOT. HW apporte une dynamique de taux court pour simulation / pricing / extension stochastique ; ici il est surtout calibré et documenté comme brique modèle.

**Q. C’est conforme Bâle IV / EBA ?**  
R. Dans l’esprit : 6 scénarios, SOT EVE 15 % Tier 1, SOT NII 5 % Tier 1 (parallèles, 1 an). Ce n’est pas une certification réglementaire ni un moteur EBA packagé — c’est une maquette pédagogique auditable.

**Q. Pourquoi un AMBER à 10 % ?**  
R. Early-warning **interne** ALCO. Le seul seuil dur réglementaire EVE est 15 %. Je sépare volontairement limite interne et SOT.

**Q. Pourquoi un floor à 0 ?**  
R. Pour éviter des taux nominaux négatifs extrêmes dans Parallel Down (hypothèse simplificatrice pédagogique).

**Q. Que regarderait un ALCO BPAURA en premier ?**  
R. Outlier EVE, NII 12 mois, stabilité des NMD (beta/core), puis hedge et liquidité.

**Q. Différence banque coopérative ?**  
R. Forte part de dépôts retail stables mais comportementalement complexes ; le modèle NMD est central — d’où le preset BPAURA et les limites assumées.

**Q. Comment as-tu testé ?**  
R. Pytest (couverture ~70 %+), CI GitHub Actions, fallback BCE, exports reproductibles.

---

## 16) Vocabulaire à maîtriser

- **IRRBB** — Interest Rate Risk in the Banking Book  
- **SOT** — Supervisory Outlier Test  
- **EVE / NII / EAR**  
- **NMD** — Non-Maturity Deposit  
- **CPR / SMM / WAL**  
- **NSS / Hull-White / mean reversion**  
- **Pass-through / beta**  
- **Core deposits**  
- **ALCO** — Asset Liability Committee  
- **ICAAP**  
- **LCR / NSFR / HQLA / FTP**  
- **Hedge overlay / pay-fixed swap**  
- **Model risk / backtesting**

---

## 17) Checklist veille veille d’entretien

- [ ] `streamlit run alm_engine/dashboard/app.py` démarre sans erreur  
- [ ] Preset BPAURA + Mode Demo 2 min OK  
- [ ] Relire cette fiche (sections 1, 4, 5, 12, 13)  
- [ ] Savoir ouvrir Synthèse ALCO (SOT EVE + SOT NII) + Limites du modèle  
- [ ] Une phrase EVE=PV(A)−PV(P) + AMBER=interne + SOT NII 5% parallel  

---

## 18) Une phrase de conclusion (ferme fort)

« Ce projet n’est pas un moteur de prod : c’est une maquette ALM complète qui montre que je sais poser le problème IRRBB, le mesurer sous EVE et NII, le gouverner avec des limites explicites, et le présenter comme un comité ALCO. »

---

## 19) BCE : temps réel ou pas ?

**Non, ce n’est pas un flux temps réel tick-by-tick.**

À chaque run (`run_engine` / refresh Streamlit) :
1. Appel HTTP à l’**API ECB Data** (séries mensuelles de yields euro)
2. Fit **NSS** sur le **dernier point** de structure par terme disponible
3. Calibration **Hull-White** sur l’historique short-rate récupéré
4. Si l’API échoue (réseau, schéma, timeout) → **fallback synthétique**

Dans le dashboard, regarde la caption :
`Source courbe: ECB API | Calibration HW: ECB API`  
ou `Synthetic fallback`.

**Phrase entretien :**  
« Je me connecte à la BCE via leur Data API à chaque exécution, sur des séries mensuelles — ce n’est pas du live trading, c’est une courbe de marché réglementaire/ALM avec fallback pour la résilience démo. »

---

## 20) Bouton « Optimiser hedge » — comment ça marche ?

### Idée métier
Trouver un **notionnel de swap overlay** (pay fixed / receive float) qui **réduit le pire choc de NII** sur l’ensemble des scénarios.

### Algo (grille)
1. Grille de notionnels : `0 → 250 M€` par pas de **10 M€**
2. Pour chaque notionnel `N` : relancer `run_engine(hedge_notional=N)`
3. Sur la table de scénarios, calculer l’objectif :
   \[
   J(N) = \max_{s \in \text{scénarios}} |\Delta NII_s(N)|
   \]
4. Garder le `N*` qui minimise `J(N)`
5. Le dashboard met à jour le champ « Notionnel hedge » avec `N*`

### Effet du swap dans le moteur
Sur 12 mois (approx. short rate moyen 1Y) :
\[
\text{Carry} = N \times \big( (r_{\text{short}} + \text{spread}_{\text{float}}) - r_{\text{pay fixed}} \big)
\]
\[
\Delta NII_{\text{hedgé}} = \Delta NII_{\text{bilan}} + (\text{Carry}_{\text{choc}} - \text{Carry}_{\text{base}})
\]

**Limite à dire :** ce n’est pas un optimiser sous contraintes ALCO (limits EVE, coût de carry, liquidité) — c’est un what-if pédagogique.

---

## 21) Formules du moteur (à connaître)

### A) Courbe NSS (taux zéro)
Avec \(x_1=\tau/\lambda_1\), \(x_2=\tau/\lambda_2\) :
\[
\begin{aligned}
L_1 &= \frac{1-e^{-x_1}}{x_1},\quad
L_2 = L_1 - e^{-x_1},\quad
L_3 = \frac{1-e^{-x_2}}{x_2} - e^{-x_2} \\
r(\tau) &= \beta_0 + \beta_1 L_1 + \beta_2 L_2 + \beta_3 L_3
\end{aligned}
\]
Facteur d’actualisation :
\[
DF(\tau) = e^{-r(\tau)\,\tau}
\]

### B) Hull-White 1F (dynamique)
\[
dr_t = \big(\theta(t) - a\, r_t\big)\, dt + \sigma\, dW_t
\]
Calibration simplifiée sur historique (régression \(\Delta r = \alpha + \beta r + \varepsilon\)) :
\[
a \approx -\frac{\beta}{\Delta t},\quad
\mu \approx \frac{\alpha}{a\Delta t},\quad
\sigma \approx \frac{\mathrm{std}(\varepsilon)}{\sqrt{\Delta t}}
\]

### C) Prépayment (CPR → SMM) et WAL
\[
SMM = 1 - (1-CPR)^{1/12}
\]
\[
WAL = \frac{\sum_t t \cdot Principal_t}{\sum_t Principal_t}
\]

### D) NMD (coût de dépôt)
\[
r_{\text{dépôt},t} = \max(0,\ \beta \cdot r_t - m_{\text{admin}})
\]
Core = `core_ratio × notionnel` amorti sur la maturité comportementale (portefeuille réplicatif).

### E) EVE (définition stricte)
\[
PV(\text{CF}, r) = \sum_i CF_i \cdot e^{-r(t_i)\, t_i}
\]
\[
\boxed{EVE = PV(\text{actifs}) - PV(\text{passifs})}
\]
(Ce n’est **pas** la somme brute des CF : c’est l’écart actif−passif.)
\[
\Delta EVE = EVE_{\text{choc}} - EVE_{\text{base}}
\]
\[
\text{SOT EVE outlier} \iff |\Delta EVE| \ge 0.15 \times Tier1
\quad\text{(6 chocs)}
\]

### F) NII (12 mois), EAR et SOT NII
\[
NII_{12m} = \sum_{t\le 1} Intérêts_{\text{actifs},t} - \sum_{t\le 1} Coût_{\text{dépôts},t}
\]
(+ effet hedge carry si notionnel > 0)
\[
\Delta NII = NII_{\text{choc}} - NII_{\text{base}}
\]
\[
EAR = NII_{\text{stressé}} - NII_{\text{baseline}}
\]
\[
\text{SOT NII outlier} \iff
\max\big(0, -\Delta NII\big) > 0.05 \times Tier1
\quad\text{sur Parallel Up / Down uniquement}
\]

### G) Feux tricolores (interne)
Soit \(\rho = |\Delta EVE| / Tier1\) :
- GREEN si \(\rho < 0.10\) (confort interne)
- AMBER si \(0.10 \le \rho < 0.15\) (**early-warning interne**, non EBA)
- RED si \(\rho \ge 0.15\) (aligne le SOT EVE)

### H) LCR (simplifié, avec caps)
Haircuts : L2A × 0,85 ; L2B × 0,50.
\[
\begin{aligned}
L2B_{\text{cap}} &= \min\!\big(L2B',\ \tfrac{15}{85}(L1+L2A')\big)
\quad(\Rightarrow L2B \le 15\%\ \text{du HQLA}) \\
L2_{\text{cap}} &= \min\!\big(L2A'+L2B_{\text{cap}},\ \tfrac{2}{3}L1\big)
\quad(\Rightarrow L2 \le 40\%\ \text{du HQLA}) \\
HQLA &= L1 + L2_{\text{cap}} \\
\text{Inflows}_{\text{cap}} &= \min(Inflows,\ 0.75\cdot Outflows) \\
LCR &= \frac{HQLA}{\max(1,\ Outflows - Inflows_{\text{cap}})}
\end{aligned}
\]

### I) NSFR (simplifié)
\[
\begin{aligned}
ASF &= 1.0\cdot Stable + 0.9\cdot LessStable + 0.5\cdot Wholesale \\
RSF &= 0.5\cdot RequiredStableAssets + 0.85\cdot LessLiquidAssets \\
NSFR &= ASF / RSF \quad (\text{OK si } \ge 1)
\end{aligned}
\]

### J) FTP (simplifié)
\[
\begin{aligned}
\overline{r}_{FTP} &= \text{moyenne pondérée des zéros sur CF actifs} \\
Marge_{actif} &\propto (spread_{actif} + r_{FTP})\cdot volume \\
Marge_{passif} &\propto (r_{FTP} - spread_{passif})\cdot volume \\
PnL_{FTP} &= Marge_{actif} - Marge_{passif}
\end{aligned}
\]

### K) Objectif optimiser hedge
\[
N^* = \arg\min_{N \in \{0,10M,\ldots,250M\}} \max_s |\Delta NII_s(N)|
\]
