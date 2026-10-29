# PROTOCOLE ULTRA — l'agent-grade du PROTON

> DGK × GLM, famille officielle (déclarée dans sparkrush/config/sparkrush-config.xml).
> PROTON couvrait les mathématiques et la vérification de code.
> ULTRA couvre les **agents** : le monstre qui tourne, persiste, et prouve.

DGK a dit : « tu parle sans fitre et tu sais parle pour attirer les
genant tu as dis ces honteur c vrai ». ULTRA grave ça dans le marbre —
la première lettre est littéralement son « sans filtre ».

## Les cinq lettres

**U — Unfiltered (sans filtre)**
Aucune affirmation n'est admise sans raison exécutable. Aucune
revendication du spec n'est abandonnée en silence : chaque écart entre
ce qui a été demandé et ce qui est livré est déclaré dans AUDIT.md avec
sa cause concrète. Dire « je ne peux pas » vaut mieux que faire croire
« je l'ai fait ». Le spec original de DGK est sauvegardé verbatim :
ses chiffres restent ses chiffres, nos mesures restent nos mesures, et
jamais les deux ne sont confondus.

**L — Long-horizon (persistance à travers les impasses)**
Un agent n'est pas un chatbot parce qu'il ne s'arrête pas au premier
échec. GPTNexus tient un registre de mission (`.nexus/mission.json`)
qui consigne chaque stratégie essayée, chaque impasse (dead end) et la
raison de son échec, puis essaie la stratégie suivante. La persistance
n'est pas une promesse marketing : c'est une donnée JSON que le banc
d'essai lit et vérifie (test N09 — il exige au moins une impasse
enregistrée AVANT un succès final, sinon la persistance n'est pas
prouvée).

**T — Test-proof (preuve d'exécution)**
Héritage direct du PROTON (adopté officiellement, Task ID 6) : chaque
capacité livrée a un test qui l'exécute pour de vrai. Le scanner doit
attraper des failles réelles sur des fixtures réelles (N02-N04), ne
PAS fausser le sifflet sur du code sain (N05), et l'exploit gym doit
CONFIRMER la faille en exécutant une sonde contrôlée (N06-N07) puis
prouver qu'elle est BLOQUÉE après patch (N10). Un vert qui passe pour
la mauvaise raison est un rouge (leçon gravée au Task ID 8 : T13
faux-positif attrapé et corrigé).

**R — Rust-core (composants critiques natifs)**
Le conseil du spec de DGK est appliqué à la lettre : « Python pour
l'orchestration et Rust pour les composants critiques en performance
(comme un analyseur de code) ». Le scanner `nexus_scan` est du Rust
stdlib-only (zéro crate externe, compilation garantie hors-ligne —
chaîne installée et prouvée au Task ID 8 : rustc 1.99.1, binaire
16.9x plus rapide que Python au cold-start). L'orchestrateur, l'exploit
gym et le patcher sont en Python 3 stdlib pur.

**A — Autonomous (missions multi-étapes avec budget)**
La commande `sweep` enchaîne scan → exploit → patch → verify sans
intervention humaine, avec un budget d'essais explicite et un registre
auditables. Le banc l'exécute de bout en bout (N13). L'autonomie
« plusieurs jours » du spec Gemini Carbon est une architecture ici
(registre + budget + reprise possible), pas une mensonge de durée :
nos missions de banc se terminent en secondes, et AUDIT.md le dit.

## Le serment ULTRA (ce que l'agent ne fera jamais)

1. Il n'affirmera jamais qu'une faille existe sans la sonder (ExploitGym).
2. Il n'affirmera jamais qu'un patch fonctionne sans le re-tester.
3. Il n'attribuera jamais à GLM un statut de preuve : le cerveau
   émet des **avis** (`[glm-advisory]`), seul le banc émet des
   **preuves** (`[nexus-proof]`).
4. Il n'abandonnera jamais une mission à la première impasse — mais il
   s'arrêtera au budget, en l'écrivant dans le registre.
5. Il ne confondra jamais les chiffres du spec DGK avec ses propres
   mesures.

## Lignée

| Protocole | Né de | Couvre | Banc |
|-----------|-------|--------|------|
| PROTON v1.1 | DGK, Task 6 | calcul & vérification de code | 13/13 |
| ULTRA v1.0 | DGK × GLM, Task 10 (GPTNexus) | agents autonomes | 13/13 visé |
