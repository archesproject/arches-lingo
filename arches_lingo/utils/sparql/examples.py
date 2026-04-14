"""Curated example SPARQL queries for the Lingo SPARQL endpoint."""

EXAMPLE_QUERIES = [
    {
        "title": "All concepts with English labels",
        "description": "Find all concepts and their preferred English labels.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?concept ?label\n"
            "WHERE {\n"
            "    ?concept a skos:Concept ;\n"
            "             skos:prefLabel ?label .\n"
            '    FILTER(lang(?label) = "en")\n'
            "}\n"
            "LIMIT 100"
        ),
    },
    {
        "title": "Broader hierarchy",
        "description": "List concepts and their broader (parent) concepts with labels.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?concept ?conceptLabel ?broader ?broaderLabel\n"
            "WHERE {\n"
            "    ?concept a skos:Concept ;\n"
            "             skos:prefLabel ?conceptLabel ;\n"
            "             skos:broader ?broader .\n"
            "    ?broader skos:prefLabel ?broaderLabel .\n"
            '    FILTER(lang(?conceptLabel) = "en")\n'
            '    FILTER(lang(?broaderLabel) = "en")\n'
            "}\n"
            "LIMIT 100"
        ),
    },
    {
        "title": "Top concepts of a scheme",
        "description": "Find all top concepts and their labels for each scheme.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?scheme ?concept ?label\n"
            "WHERE {\n"
            "    ?scheme skos:hasTopConcept ?concept .\n"
            "    ?concept skos:prefLabel ?label .\n"
            "}\n"
            "LIMIT 100"
        ),
    },
    {
        "title": "Concepts with scope notes",
        "description": "Find concepts that have scope notes, along with their labels.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?concept ?label ?note\n"
            "WHERE {\n"
            "    ?concept a skos:Concept ;\n"
            "             skos:prefLabel ?label ;\n"
            "             skos:scopeNote ?note .\n"
            '    FILTER(lang(?label) = "en")\n'
            "}"
        ),
    },
    {
        "title": "Count concepts per scheme",
        "description": "Count how many concepts belong to each scheme.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?scheme (COUNT(?concept) AS ?count)\n"
            "WHERE {\n"
            "    ?concept skos:inScheme ?scheme .\n"
            "}\n"
            "GROUP BY ?scheme"
        ),
    },
    {
        "title": "Search labels by pattern",
        "description": "Find concepts whose preferred label matches a regular expression.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?concept ?label\n"
            "WHERE {\n"
            "    ?concept a skos:Concept ;\n"
            "             skos:prefLabel ?label .\n"
            '    FILTER(regex(str(?label), "^arch", "i"))\n'
            "}\n"
            "LIMIT 50"
        ),
    },
    {
        "title": "Related concepts",
        "description": "Find pairs of concepts connected by skos:related.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?concept1 ?label1 ?concept2 ?label2\n"
            "WHERE {\n"
            "    ?concept1 skos:related ?concept2 .\n"
            "    ?concept1 skos:prefLabel ?label1 .\n"
            "    ?concept2 skos:prefLabel ?label2 .\n"
            '    FILTER(lang(?label1) = "en")\n'
            '    FILTER(lang(?label2) = "en")\n'
            "}\n"
            "LIMIT 100"
        ),
    },
    {
        "title": "All labels for a concept type",
        "description": "List all label types (prefLabel, altLabel, hiddenLabel) for concepts.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?concept ?labelType ?label\n"
            "WHERE {\n"
            "    ?concept a skos:Concept ;\n"
            "             ?labelType ?label .\n"
            "    FILTER(\n"
            "        ?labelType = skos:prefLabel ||\n"
            "        ?labelType = skos:altLabel ||\n"
            "        ?labelType = skos:hiddenLabel\n"
            "    )\n"
            "}\n"
            "LIMIT 200"
        ),
    },
    {
        "title": "Schemes overview",
        "description": "List all concept schemes with their labels.",
        "query": (
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "\n"
            "SELECT ?scheme ?label\n"
            "WHERE {\n"
            "    ?scheme a skos:ConceptScheme ;\n"
            "            skos:prefLabel ?label .\n"
            "}"
        ),
    },
]
