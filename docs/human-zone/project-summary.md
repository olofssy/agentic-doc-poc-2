# Project summary

> A free-form working page for notes, reflections, and sketches. Edit this file directly or run
> `uv run agentic-doc-poc-summary` and open <http://127.0.0.1:8767/>.

<details open>
<summary><strong>Uppgiften: instruktioner, fokus / </strong></summary>
 <!-- Syfte: påminna om uppgiften, klargöra hur jag prioriterat (samt min roll?)  -->

Uppgiftsinstruktioner <!-- Väldigt öppna! -->
- Hitta use-case dokumentprocessering, som motiverar ett "agentiskt system" (jmf workflow)
- Använd ramverk såsom LangGraph / Agno
- Mer: Prova RAG; no-vibe coding, Codex 5.6+, ~3h

Mitt fokus 
- Hitta "realistiskt" use-case *som går att utvärdera* (och förstå)
- Bygg icke-linjärt ("loopande") system i LangGraph
- Prova RAG (minimal skala)
- Automatiska kvalitetstester medelst "Evals"

</details>

<details>
<summary><strong>Use-case sökning</strong></summary>
 <!-- Syfte: redovisa tankeprocess  -->
Exempel dokumenttyper: Fakturor, produktbeskrivningar, användarvillkor, (externa)regleringar, juridiska avtal, CV:n

Vad utmärker problem där linjära workflow ej räcker?
- open-endedness
- selective tool use
- "miljö" som utforskas (?)

Vilka use-cases passar för demo?
- Output som går att bedömma kvalitetsmässigt
    - automatiskt via evals
    - snabbkoll av männsika
- "Begripliga" dokument tillgänliga / syntetisk datagenerering möjlig
- RAG kan motiveras

</details>

<details>
<summary><strong>*Var* går gränsen mellan workflow / agentisk?></strong></summary> 
 <!-- Syfte: motivera vilken typ av system jag zonat in på  -->

Spektrum: Linear workflow -> non-linear -> agentic?

Dimensioner
- Flödesvägar i grafen (linjär, branching, loopar),
- Actions
    - antal: få -> många
    - åtkomsts-/behörightsnivåer och flexibilitet - t.ex. get_time vs rag_retrieve(...) vs readonly-DB vs sudo bash shell?
- (State vs stateless?)

</details>

<details>
<summary><strong>Valt use case</strong></summary>

Två idéer:
- (1) "Warranty claim investigator" 
    - Bedömning av garantiärenden för industripump  <!--Avslogs pga svårt motivera RAG-->
    - input: Garanti-formulär från kund + produktbeskrivning med villkor
    - miljö / actions: läs inspektionsrapporter, driftsloggar
    - output: bevilja / avslå / eskalera inkl. motivering med dokumentreferenser

- **(2) "Policy coherence investigator" 
    - Vad: Bedömning av intern "policykoherens" på företag**
    - input: Fråga ("Är våra polcies kring återkallande systemaccesser vid uppsägning tvetydiga?")
    - miljö / actions: Sök(RAG) & läs i policy-arkiv
    - output: flagga (in)koherens alt. oklart inkl. motivering med dokumentreferenser
    - Möjliga flöden:
        - Initial retrive+review -> finish
        - Initial retrive+review -> (loop: re-retrieve -> re-review) -> finish
    
Hur agentisk? Dimensionerna igen:
- Flödesvägar i grafen (linjär, branching, *loopar*),
- Actions
    - antal=1
    - åtkomsts-/behörightsnivåer  & flexibilitet - t.ex. get_time() vs *rag_retrieve(...)* vs readonly-DB vs bash shell?
- (*State* vs stateless?)


- TODO: Se use-case exploren: http://127.0.0.1:8767

</details>

<details>
<summary><strong>Go-to-prod förbättringar / blandade utmaningar</strong></summary>

<!-- Syfte: Vad hade varit naturliga "nästa steg" om detta hade byggts som en faktiskt produkt?-->


Att testa:
- Större dataset, äkta dokument (utmaning: vad är ground-truth?)
- Benchmarka mot baseline(s):
    - Linjärt flöde med/utan RAG

Integrera i produktionsmiljöer: hur exponeras dokument, hur lösa accesser etc?

Observabilityet: beslut måsta kunna förklaras(?)

</details>

<details>
<summary><strong>Sketches and images</strong></summary>

<!-- Put image files in docs/human-zone/assets/ and link them with standard Markdown. -->

Example:

![Description of the sketch](assets/test.png)

</details>

<details>
<summary><strong>Next session</strong></summary>

<!-- What is the smallest useful next step? -->

Write here.

</details>
