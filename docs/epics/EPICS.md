# Arca Suite — Epics

> Gouvernance : ce document est le référentiel unique des epics de la Suite
> (`arca-*`). Toute évolution passe par une PR sur `arca-platform`.
> Dernière mise à jour : 2026-09-20 — intégration de l'analyse optimale
> (lentille reward-hacking) et des constats d'audit ArcaQ/ArcaX.

## Règle d'or — ne jamais casser ArcaQ ni ArcaX

La Suite compose **autour** des deux produits, elle ne les modifie pas.
Conséquences contraignantes, déjà validées dans `docs/integration/arcaq-linkage-audit.md` :

1. **Aucune dépendance compile-time ni runtime** vers `arcaq` ou `arcax` — intégration par contrats versionnés de ce repo (`contracts/`) uniquement.
2. **Pattern d'intégration unique** : `Protocol` + implémentation `Null` (désactivée par défaut) + implémentation `Http` opt-in par feature flag, timeout court, dégradation gracieuse — jamais de blocage métier si un produit est absent.
3. **Ontologies : référencer, ne jamais redéfinir** — un seul namespace `http://arcaq.com/ontology#` ; les instances cœur (`Jurisdiction_MA`, `Jurisdiction_FR`, `Regulation_Loi0908_MA`, RGPD…) se référencent, jamais se re-déclarent ; pas de namespace par territoire.
4. **Un produit ne dépend pas de la Suite pour exister** — ArcaQ et ArcaX restent autonomes et commercialisables seuls ; la Suite ajoute la valeur de composition.
5. **Correction complète = double-loop** — toute révision de règle embarque dans le même changement : modèle + contrat (SHACL/OpenAPI) + données + gate qui les applique. Une révision qui reste dans un document pendant que les systèmes appliquent l'ancienne règle n'est pas une correction.

---

## Vue d'ensemble

| Epic | Titre | Priorité | Statut |
|---|---|---|---|
| EP-01 | Intégration événementielle ArcaQ (backbone Kafka) | P0 | En cours (~80 %) |
| EP-02 | Ponts décisionnels (contexte KG, gate OOC) | P0 | Fait |
| EP-03 | Chaîne de confiance incorruptible (bench externe) | P0 | Planifié |
| EP-04 | Conformance sémantique des packs (RDF/SHACL) | P0 | Fait |
| EP-05 | France Sovereignty Pack | P1 | Planifié |
| EP-06 | Unification des schémas transverses (SOC, topics, shared-kernel, OLM/OOC, provenance) | P1 | Planifié |
| EP-07 | Recherche sémantique ArcaQ dans le cockpit | P1 | Planifié |
| EP-08 | Métriques revendiquées sous méthodologie reproductible | P2 | Planifié |

---

## EP-01 — Intégration événementielle ArcaQ

**Statut : en cours.** Consommer les topics `arcaq.*` sans jamais écrire chez ArcaQ.

- Fait : `arca-hub` (timeline cockpit, consumer opt-in `kafka_arcaq_enabled`), `arca-exchange` (`ArcaqEnrichmentConsumer` → registres ontologies/OOC), `arca-flow` gate OOC, `arca-decision-room` (`ArcaqContextClient` Protocol Null/Http).
- Partiel : `arca-trust` (provenance PROV-O consommée ; **reste : `arcaq.soc.verdicts` → scores de posture**), `arca-cert` (preuves ArcaQ dans les dossiers), `arca-studio` (catalogue hydratable).
- Critères d'acceptation : chaque consumer opt-in a un test Null (désactivé = pas d'appel) et un test Http (payload contrat validé) ; aucun consumer ne bloque le flux métier en cas d'indisponibilité ArcaQ.

## EP-02 — Ponts décisionnels

**Statut : fait.** Contexte KG embarqué dans les Decision Packages avant scellement (decision-room), validation d'étapes workflow contre `/api/v1/ooc` (flow). Reste un gap documenté dans EP-07.

## EP-03 — Chaîne de confiance incorruptible (bench externe)

**Statut : planifié.** Né de l'analyse reward-hacking (2026-09-20).

Problème : la Suite a internalisé une boucle de notation — les modules émettent leurs propres événements d'audit → Trust calcule 6 scores → Cert assemble des dossiers → Bench re-note → remédiation retourne aux modules. Surfaces de hacking : **score inflation** (le noté contrôle la source de sa métrique), **gardien non gardé** (Trust/Bench ne sont audités par personne), **boucle de confirmation** (Cert ← Trust ← Bench se citent entre eux).

Livrables :
1. `arca-bench` rejoue les **décisions scellées** et vérifie le quorum **indépendamment** des événements émis (reconstruction à partir des artefacts scellés, pas du flux).
2. Un test bench croise au moins un événement métier avec une preuve externe avant qu'il n'alimente un score Trust.
3. Le seul score qui compte est celui qu'un module ne peut pas s'auto-émettre.
4. **Critère « AI removes the pause »** : toute action auto-déclenchée embarque les concepts, sources et règles utilisés (pas seulement une trace d'événement) — une explication fluide ne prouve rien sur ce qui a été réellement utilisé.

Critères d'acceptation : supprimer artificiellement un événement d'audit en amont fait échouer le bench (test de falsification).

## EP-04 — Conformance sémantique des packs

**Statut : fait** (PR arca-packs #3, mergée 2026-09-20).

MA-CONF-002/003 sont des assertions sur un graphe rdflib parsé (triplets + littéraux à tags de langue), plus MA-CONF-008 (contrats SHACL pack-locaux) et MA-CONF-009 (le chargement du pack dans le graphe partagé arcaq n'introduit **aucune** nouvelle violation SHACL). Les checks string-matching étaient un Goodhart target — la validation sémantique a immédiatement détecté : classe `LegalDomain` inexistante dans le cœur, ancres `belongsToDomain` absentes, usage objet de `legalBasis` (DatatypeProperty) sur un individu.

Règle désormais obligatoire pour tout futur pack : **conformance = RDF+SHACL**, les checks textuels ne sont que des gardes-fou secondaires.

## EP-05 — France Sovereignty Pack

**Statut : planifié.** Gabarit : `src/packs/morocco-sovereignty/` (mergé, aligné namespace `arcaq:`).

- Référencer `arcaq:Jurisdiction_FR` + RGPD (`arcaq:Regulation_GDPR`) — ne pas redéfinir.
- Labels en/fr (le trilingue arabe est spécifique Maroc).
- Conformance dès la première PR : validation RDF/SHACL réelle (MA-CONF-008/009 comme exigences du Definition of Done).
- Réutiliser la déclaration pack de `arcaq:LegalDomain` (introduite par le pack Maroc) ou la classe cœur si ArcaQ l'y remonte (voir F-AQ-08 dans le registre des failles).

## EP-06 — Unification des schémas transverses

**Statut : planifié.** Trois écosystèmes implémentent les mêmes briques avec des formats différents (constat d'audit) : SOC 5 pods, registre de topics Kafka, shared-kernel, OLM/OOC, provenance PROV-O.

Livrables :
1. `arca-platform/contracts` devient le **seul référentiel de schémas côté Suite** (son rôle déclaré) ; les SOC embarqués des modules n'émettent qu'au format du shared-kernel.
2. Adopter la règle d'import public d'ArcaX : seuls des packages/contrats publics versionnés sont importables, jamais de sous-module interne.
3. **Principe bounded contexts** : l'unification ne crée pas un schéma universel unique — elle construit des *contrats de traduction explicites* entre contextes (les contextes métier gardent leurs distinctions ; la traduction se fait délibérément, pas par accident). Un namespace d'identification partagé ≠ une définition unique forcée.
4. Documenter la frontière : côté Suite → `arca-platform` est source de vérité ; côté produits → ArcaQ (`arcaq-kafka-topics`) et ArcaX restent autonomes (EP règle d'or n°4). La Suite n'unifie pas les produits entre eux, elle s'unifie elle-même.

## EP-07 — Recherche sémantique ArcaQ dans le cockpit

**Statut : planifié.** Exposer la surface `GET /api/v1/search` d'ArcaQ dans `arca-hub` (cockpit), même pattern Protocol/Null/Http, opt-in. Gap issu de l'audit d'interfaçage (2026-09-14).

## EP-08 — Métriques revendiquées sous méthodologie reproductible

**Statut : planifié.** Toute métrique affichée (dashboards, README, badges) doit pointer vers : méthodologie + jeux de données + résultat reproductible, ou être reformulée en revendication non chiffrée. S'applique en interne (Suite) et en recommandation externe (badges produits — voir registre des failles F-AQ-07).

---

*Références : `docs/integration/arcaq-linkage-audit.md` (2026-09-14), audit ArcaQ/ArcaX (2026-09-19), analyse optimale reward-hacking (2026-09-20), registre des failles ArcaQ/ArcaX (2026-09-20).*
