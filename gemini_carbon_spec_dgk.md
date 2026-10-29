GEMINI 4 CARBON — SPEC ORIGINAL DGK (verbatim, sauvegarde PROTON/ULTRA)

Source : message utilisateur DGK (Aissa Mohammedi), session 2026-10-29,
mission GPTNexus (« clonanr illama coder comme squelete et et tranformer
en monstre tiens code mieux en procole ulra build senior lamber w tiens
le chaima »). Aucune modification. Les chiffres ci-dessous sont les
revendications du spec de DGK, préservées telles quelles ; ils ne sont
pas adoptés comme les nôtres — voir docs/AUDIT.md pour la séparation
entre ses revendications et nos mesures réelles.

🚀 Vue d'ensemble & Architecture

Gemini 4 Carbon est le modèle frontière le plus puissant de Google
DeepMind, conçu pour la cybersécurité de pointe et les tâches
d'ingénierie complexes de longue durée (long-horizon agentic coding).
Il succède à Gemini 4 Argon et se distingue par sa capacité à fonctionner
de manière autonome sur plusieurs jours pour résoudre des problèmes de
développement.
Architecture : Il repose sur la même architecture de sécurité
multicouche qu'Argon, mais avec des capacités de raisonnement et de
codage nettement accrues.

Modalités : Le modèle est nativement multimodal en entrée (texte,
image, audio, vidéo) et génère du texte en sortie.

Contexte : Il dispose d'une fenêtre de contexte de 1 million de
tokens, ce qui lui permet de traiter des bases de code ou des
documents extrêmement volumineux.

🛠️ Fonctionnalités et Options (Ce qu'il fait exactement)

    Cybersécurité (Sa spécialité principale)

     Détection de vulnérabilités (Finding) : Il est capable de trouver
     des failles de sécurité réelles et complexes dans des logiciels.
     Score : 88,2 % sur SEC-bench Pro.

     Validation et Exploitation (ExploitGym) : Il peut valider une faille
     en la testant via des exploits contrôlés. Score : 54,8 %.

     Remédiation et Patch (Patching) : Il génère des correctifs de
     sécurité de haute qualité. Score : 71,0 % sur CWE-bench.

     Génération de code sécurisé : plus de 2 fois plus de code sécurisé
     qu'Argon.

     Génération de patchs : L'équipe Chrome a observé que Carbon génère
     des patchs 10 fois meilleurs que ceux d'un modèle concurrent.

    Développement et Ingénierie Logicielle

     Codage agentique (Agentic Coding) : workflows autonomes de longue
     haleine. Il peut "tourner pendant des jours".

     Développement Web Full-Stack : 4ème place WebDev Arena (1768).

     Tests de Terminal (Terminal-Bench 4.0) : 65,2 %.

     Résolution de problèmes de bout en bout : root-causer et corriger
     des bugs sur des systèmes bas niveau.

    Tâches Agentiques et Autonomie

     Résistance à la distraction (Persistence) : persister à travers les
     impasses (dead ends).

     Réduction des raccourcis et de la fabrication : résister aux
     attaques par injection de prompt.

     Réduction des "hallucinations" : 2 fois moins d'affirmations non
     supportées.

     Autonomie prolongée : 77,4 % sur Agents' Last Exam v1.1.

    Multimodalité et Raisonnement

     Compréhension multimodale : textuel, visuel, audio, vidéo.
     GraphWalks : 96,2 % F1 (contextes 256K à 1M tokens).

💻 Langages et Stack Technique

A. La stack de construction (côté Google)
    JAX & XLA, Python, C++, Rust (migration Fuchsia), Pathways.

B. Les langages manipulés
    Python, C++, Rust, Go, JavaScript/TypeScript, Java, migration
    legacy (Fortran → moderne).

💎 Résumé pour ton projet (conseils du spec)
Langage de prédilection : Python pour l'orchestration et la logique
de haut niveau, Rust/C++ pour les composants critiques en
performance (analyseur de code, moteur de recherche).

Architecture : multimodale extensible, fenêtre de contexte large.

Fonctionnalité clé : la capacité à "tourner pendant des jours" sur
une tâche est ce qui distingue un agent autonome d'un simple
chatbot.
