"""SPARQL query parser for Lingo.

Parses a subset of SPARQL 1.1 SELECT queries into an intermediate
representation that the evaluator can process against an rdflib Graph.

Supported features:
  - PREFIX declarations
  - SELECT with named variables
  - SELECT * (all variables)
  - SELECT DISTINCT
  - WHERE clause with basic graph patterns (triple patterns)
  - OPTIONAL { ... }
  - FILTER with: regex(), lang(), str(), bound(), ||, &&, =, !=, !, ()
  - LIMIT / OFFSET
  - ORDER BY (ASC/DESC on a variable)
  - COUNT / GROUP BY (basic aggregation)

Unsupported (returns an informative error):
  - CONSTRUCT, DESCRIBE, ASK
  - INSERT, DELETE (update operations)
  - UNION, MINUS, SERVICE, VALUES
  - Subqueries, property paths
"""

import re
from dataclasses import dataclass, field


class SparqlParseError(Exception):
    pass


class SparqlUnsupportedError(Exception):
    pass


@dataclass
class TriplePattern:
    subject: str
    predicate: str
    obj: str


@dataclass
class FilterExpression:
    raw: str


@dataclass
class OptionalBlock:
    patterns: list = field(default_factory=list)
    filters: list = field(default_factory=list)


@dataclass
class OrderClause:
    variable: str
    ascending: bool = True


@dataclass
class AggregateExpression:
    function: str
    argument: str
    alias: str


@dataclass
class ParsedSparqlQuery:
    prefixes: dict = field(default_factory=dict)
    select_variables: list = field(default_factory=list)
    distinct: bool = False
    triple_patterns: list = field(default_factory=list)
    optional_blocks: list = field(default_factory=list)
    filters: list = field(default_factory=list)
    limit: int = None
    offset: int = 0
    order_by: list = field(default_factory=list)
    group_by: list = field(default_factory=list)
    aggregates: list = field(default_factory=list)


WELL_KNOWN_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcterms": "http://purl.org/dc/terms/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def parse_sparql(query_string):
    """Parse a SPARQL query string into a ParsedSparqlQuery.

    Raises SparqlParseError for malformed queries and
    SparqlUnsupportedError for valid but unsupported query forms.
    """
    _reject_unsupported_forms(query_string)
    stripped = _strip_comments(query_string)
    result = ParsedSparqlQuery()
    remaining = _parse_prefixes(stripped, result)
    remaining = _parse_select_clause(remaining, result)
    remaining = _parse_where_clause(remaining, result)
    _parse_solution_modifiers(remaining, result)
    return result


def _strip_comments(query_string):
    lines = query_string.split("\n")
    cleaned = []
    for line in lines:
        in_string = False
        in_uri = False
        string_char = None
        comment_start = None
        for i, char in enumerate(line):
            if in_string:
                if char == string_char:
                    in_string = False
            elif in_uri:
                if char == ">":
                    in_uri = False
            else:
                if char in ('"', "'"):
                    in_string = True
                    string_char = char
                elif char == "<":
                    in_uri = True
                elif char == "#":
                    comment_start = i
                    break
        if comment_start is not None:
            cleaned.append(line[:comment_start])
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def _reject_unsupported_forms(query_string):
    upper = query_string.upper()
    for keyword in ("CONSTRUCT", "DESCRIBE", "ASK"):
        pattern = re.compile(r"\b" + keyword + r"\b", re.IGNORECASE)
        if pattern.search(query_string):
            if keyword == "ASK" and not re.search(
                r"\bASK\s*\{", query_string, re.IGNORECASE
            ):
                continue
            raise SparqlUnsupportedError(
                f"{keyword} queries are not yet supported. "
                "Only SELECT queries are currently available."
            )
    for keyword in ("INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "CREATE"):
        pattern = re.compile(r"\b" + keyword + r"\b", re.IGNORECASE)
        if pattern.search(query_string) and keyword in upper:
            raise SparqlUnsupportedError(
                "SPARQL Update operations are not supported. "
                "This endpoint is read-only."
            )


def _parse_prefixes(query_string, result):
    prefix_pattern = re.compile(r"PREFIX\s+(\w+):\s*<([^>]+)>", re.IGNORECASE)
    remaining = query_string
    for match in prefix_pattern.finditer(query_string):
        result.prefixes[match.group(1)] = match.group(2)
    remaining = prefix_pattern.sub("", remaining).strip()
    return remaining


def _parse_select_clause(query_string, result):
    select_match = re.match(
        r"SELECT\s+(DISTINCT\s+)?(.*?)\s*WHERE\s*\{",
        query_string,
        re.IGNORECASE | re.DOTALL,
    )
    if not select_match:
        raise SparqlParseError(
            "Could not parse SELECT clause. Expected: SELECT [DISTINCT] <variables> WHERE { ... }"
        )

    if select_match.group(1):
        result.distinct = True

    variables_str = select_match.group(2).strip()
    if variables_str == "*":
        result.select_variables = ["*"]
    else:
        _parse_select_variables(variables_str, result)

    after_where_open = query_string[select_match.end() :]
    return after_where_open


def _parse_select_variables(variables_str, result):
    aggregate_pattern = re.compile(
        r"\(\s*(\w+)\s*\(\s*(\?\w+|\*)\s*\)\s+AS\s+(\?\w+)\s*\)",
        re.IGNORECASE,
    )
    remaining = variables_str
    for match in aggregate_pattern.finditer(variables_str):
        result.aggregates.append(
            AggregateExpression(
                function=match.group(1).upper(),
                argument=match.group(2),
                alias=match.group(3),
            )
        )
        result.select_variables.append(match.group(3))

    remaining = aggregate_pattern.sub("", remaining).strip()
    for var in re.findall(r"\?\w+", remaining):
        result.select_variables.append(var)


def _parse_where_clause(query_string, result):
    brace_depth = 1
    position = 0
    body = query_string

    while position < len(body) and brace_depth > 0:
        char = body[position]
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
        position += 1

    if brace_depth != 0:
        raise SparqlParseError("Unmatched braces in WHERE clause.")

    where_body = body[: position - 1]
    remainder = body[position:].strip()

    _parse_group_graph_pattern(where_body, result)
    return remainder


def _parse_group_graph_pattern(body, result):
    remaining = body.strip()

    while remaining:
        remaining = remaining.strip()
        if not remaining:
            break

        optional_match = re.match(r"OPTIONAL\s*\{", remaining, re.IGNORECASE)
        if optional_match:
            remaining = remaining[optional_match.end() :]
            block_body, remaining = _extract_braced_block(remaining)
            optional = OptionalBlock()
            _parse_basic_patterns(block_body, optional)
            result.optional_blocks.append(optional)
            continue

        filter_match = re.match(r"FILTER\s*\(", remaining, re.IGNORECASE)
        if filter_match:
            remaining = remaining[filter_match.end() :]
            depth = 1
            pos = 0
            while pos < len(remaining) and depth > 0:
                if remaining[pos] == "(":
                    depth += 1
                elif remaining[pos] == ")":
                    depth -= 1
                pos += 1
            filter_body = remaining[: pos - 1]
            result.filters.append(FilterExpression(raw=filter_body.strip()))
            remaining = remaining[pos:].strip()
            if remaining.startswith("."):
                remaining = remaining[1:].strip()
            continue

        triple_match = _try_parse_triple(remaining, result)
        if triple_match is not None:
            remaining = triple_match
            continue

        if remaining.startswith("."):
            remaining = remaining[1:].strip()
            continue

        raise SparqlParseError(f"Could not parse WHERE clause near: {remaining[:80]}")


def _parse_basic_patterns(body, container):
    remaining = body.strip()
    while remaining:
        remaining = remaining.strip()
        if not remaining:
            break

        filter_match = re.match(r"FILTER\s*\(", remaining, re.IGNORECASE)
        if filter_match:
            remaining = remaining[filter_match.end() :]
            depth = 1
            pos = 0
            while pos < len(remaining) and depth > 0:
                if remaining[pos] == "(":
                    depth += 1
                elif remaining[pos] == ")":
                    depth -= 1
                pos += 1
            filter_body = remaining[: pos - 1]
            container.filters.append(FilterExpression(raw=filter_body.strip()))
            remaining = remaining[pos:].strip()
            if remaining.startswith("."):
                remaining = remaining[1:].strip()
            continue

        triple_match = _try_parse_triple(remaining, container)
        if triple_match is not None:
            remaining = triple_match
            continue

        if remaining.startswith("."):
            remaining = remaining[1:].strip()
            continue

        raise SparqlParseError(f"Could not parse pattern near: {remaining[:80]}")


def _extract_braced_block(text):
    depth = 1
    pos = 0
    while pos < len(text) and depth > 0:
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
        pos += 1
    if depth != 0:
        raise SparqlParseError("Unmatched braces in OPTIONAL block.")
    return text[: pos - 1], text[pos:].strip()


def _try_parse_triple(text, container):
    """Try to parse one or more triple patterns from text.

    Handles:
      - Simple triples: ?s <pred> ?o .
      - Predicate-object lists: ?s pred1 obj1 ; pred2 obj2 .
      - Abbreviated 'a' for rdf:type
    """
    term_pattern = (
        r"(?:"
        r"<[^>]+>"
        r"|\"(?:[^\"\\]|\\.)*\"(?:@\w[\w-]*)?"
        r"|'(?:[^'\\]|\\.)*'(?:@\w[\w-]*)?"
        r"|\?\w+"
        r"|[a-zA-Z_]\w*:[a-zA-Z_]\w*"
        r"|\ba\b"
        r")"
    )

    triple_re = re.compile(
        rf"({term_pattern})\s+({term_pattern})\s+({term_pattern})\s*"
    )

    match = triple_re.match(text)
    if not match:
        return None

    subject = match.group(1)
    predicate = match.group(2)
    obj = match.group(3)

    if predicate == "a":
        predicate = "rdf:type"

    pattern = TriplePattern(subject=subject, predicate=predicate, obj=obj)
    if hasattr(container, "triple_patterns"):
        container.triple_patterns.append(pattern)
    else:
        container.patterns.append(pattern)

    remaining = text[match.end() :].strip()

    while remaining.startswith(";"):
        remaining = remaining[1:].strip()
        if not remaining or remaining.startswith("}"):
            break
        pair_re = re.compile(rf"({term_pattern})\s+({term_pattern})\s*")
        pair_match = pair_re.match(remaining)
        if pair_match:
            pred = pair_match.group(1)
            obj = pair_match.group(2)
            if pred == "a":
                pred = "rdf:type"
            pattern = TriplePattern(subject=subject, predicate=pred, obj=obj)
            if hasattr(container, "triple_patterns"):
                container.triple_patterns.append(pattern)
            else:
                container.patterns.append(pattern)
            remaining = remaining[pair_match.end() :].strip()
        else:
            break

    if remaining.startswith("."):
        remaining = remaining[1:].strip()

    return remaining


def _parse_solution_modifiers(text, result):
    remaining = text.strip()

    group_by_match = re.search(
        r"GROUP\s+BY\s+((?:\?\w+\s*)+)", remaining, re.IGNORECASE
    )
    if group_by_match:
        result.group_by = re.findall(r"\?\w+", group_by_match.group(1))
        remaining = (
            remaining[: group_by_match.start()] + remaining[group_by_match.end() :]
        )

    order_by_match = re.search(
        r"ORDER\s+BY\s+(.*?)(?=LIMIT|OFFSET|GROUP|$)",
        remaining,
        re.IGNORECASE,
    )
    if order_by_match:
        order_str = order_by_match.group(1).strip()
        for clause in re.finditer(
            r"(ASC|DESC)\s*\(\s*(\?\w+)\s*\)|(\?\w+)",
            order_str,
            re.IGNORECASE,
        ):
            if clause.group(3):
                result.order_by.append(OrderClause(variable=clause.group(3)))
            else:
                result.order_by.append(
                    OrderClause(
                        variable=clause.group(2),
                        ascending=clause.group(1).upper() == "ASC",
                    )
                )
        remaining = (
            remaining[: order_by_match.start()] + remaining[order_by_match.end() :]
        )

    limit_match = re.search(r"LIMIT\s+(\d+)", remaining, re.IGNORECASE)
    if limit_match:
        result.limit = int(limit_match.group(1))
        remaining = remaining[: limit_match.start()] + remaining[limit_match.end() :]

    offset_match = re.search(r"OFFSET\s+(\d+)", remaining, re.IGNORECASE)
    if offset_match:
        result.offset = int(offset_match.group(1))


def resolve_prefixed_name(name, prefixes):
    """Expand a prefixed name (e.g. skos:Concept) to a full URI string."""
    if name.startswith("<") and name.endswith(">"):
        return name[1:-1]
    if ":" in name:
        prefix, local = name.split(":", 1)
        namespace = prefixes.get(prefix) or WELL_KNOWN_PREFIXES.get(prefix)
        if namespace:
            return namespace + local
        raise SparqlParseError(f"Unknown prefix: {prefix}")
    return name
