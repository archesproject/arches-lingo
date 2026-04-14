"""SPARQL query evaluator for Lingo.

Evaluates parsed SPARQL queries against an rdflib Graph using
the graph.triples() API (which works fine in rdflib 4.2.2 on
Python 3.12, unlike the built-in SPARQL algebra engine).

The evaluator:
  1. Resolves prefixed names to full URIs
  2. Matches triple patterns against the graph
  3. Joins binding tables for multi-pattern queries
  4. Applies FILTER expressions
  5. Handles OPTIONAL as left joins
  6. Applies ORDER BY, LIMIT, OFFSET
  7. Handles basic aggregation (COUNT + GROUP BY)
"""

import re

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, SKOS

from arches_lingo.utils.sparql.parser import (
    FilterExpression,
    SparqlParseError,
    resolve_prefixed_name,
)

MAX_RESULTS = 10000


class SparqlEvaluationError(Exception):
    pass


def evaluate_query(parsed_query, graph):
    """Evaluate a ParsedSparqlQuery against an rdflib Graph.

    Returns a dict with 'variables' (list of variable names)
    and 'bindings' (list of dicts mapping variable names to values).
    """
    prefixes = {**parsed_query.prefixes}

    bindings = [{}]

    for pattern in parsed_query.triple_patterns:
        pattern_bindings = _match_triple_pattern(pattern, graph, prefixes)
        bindings = _join_bindings(bindings, pattern_bindings)

    for optional_block in parsed_query.optional_blocks:
        optional_bindings = [{}]
        for pattern in optional_block.patterns:
            pattern_results = _match_triple_pattern(pattern, graph, prefixes)
            optional_bindings = _join_bindings(optional_bindings, pattern_results)

        for filter_expr in optional_block.filters:
            optional_bindings = _apply_filter(optional_bindings, filter_expr, prefixes)

        bindings = _left_join_bindings(bindings, optional_bindings)

    for filter_expr in parsed_query.filters:
        bindings = _apply_filter(bindings, filter_expr, prefixes)

    if parsed_query.group_by and parsed_query.aggregates:
        bindings = _apply_aggregation(
            bindings, parsed_query.group_by, parsed_query.aggregates
        )

    if parsed_query.distinct:
        bindings = _distinct_bindings(bindings)

    if parsed_query.order_by:
        bindings = _apply_order_by(bindings, parsed_query.order_by)

    if parsed_query.offset:
        bindings = bindings[parsed_query.offset :]

    effective_limit = parsed_query.limit or MAX_RESULTS
    bindings = bindings[:effective_limit]

    variables = parsed_query.select_variables
    if variables == ["*"]:
        all_vars = set()
        for binding in bindings:
            all_vars.update(binding.keys())
        variables = sorted(all_vars)

    output_bindings = []
    for binding in bindings:
        output_bindings.append({var: binding.get(var) for var in variables})

    return {"variables": variables, "bindings": output_bindings}


def _resolve_term(term, prefixes):
    """Resolve a SPARQL term to an rdflib term or return None for variables."""
    if term.startswith("?"):
        return None

    if term.startswith("<") and term.endswith(">"):
        return URIRef(term[1:-1])

    if term.startswith('"') or term.startswith("'"):
        return _parse_literal(term)

    if term == "a" or term == "rdf:type":
        return RDF.type

    try:
        uri = resolve_prefixed_name(term, prefixes)
        return URIRef(uri)
    except SparqlParseError:
        return Literal(term)


def _parse_literal(term):
    """Parse a quoted literal, handling language tags."""
    quote_char = term[0]
    lang_match = re.match(
        rf"{quote_char}((?:[^{quote_char}\\]|\\.)*){quote_char}@(\w[\w-]*)",
        term,
    )
    if lang_match:
        return Literal(lang_match.group(1), lang=lang_match.group(2))

    content_match = re.match(
        rf"{quote_char}((?:[^{quote_char}\\]|\\.)*){quote_char}", term
    )
    if content_match:
        return Literal(content_match.group(1))

    return Literal(term)


def _match_triple_pattern(pattern, graph, prefixes):
    """Match a triple pattern against the graph, returning bindings."""
    subject_term = _resolve_term(pattern.subject, prefixes)
    predicate_term = _resolve_term(pattern.predicate, prefixes)
    object_term = _resolve_term(pattern.obj, prefixes)

    results = []
    for subject, predicate, obj in graph.triples(
        (subject_term, predicate_term, object_term)
    ):
        binding = {}
        if pattern.subject.startswith("?"):
            binding[pattern.subject] = subject
        if pattern.predicate.startswith("?"):
            binding[pattern.predicate] = predicate
        if pattern.obj.startswith("?"):
            binding[pattern.obj] = obj
        results.append(binding)

    return results


def _join_bindings(left_bindings, right_bindings):
    """Inner join two sets of bindings on shared variables."""
    if not left_bindings:
        return right_bindings
    if not right_bindings:
        return []

    results = []
    for left_binding in left_bindings:
        for right_binding in right_bindings:
            if _bindings_compatible(left_binding, right_binding):
                merged = {**left_binding, **right_binding}
                results.append(merged)
    return results


def _left_join_bindings(left_bindings, right_bindings):
    """Left outer join: keep all left bindings, extend with right where compatible."""
    if not right_bindings:
        return left_bindings

    results = []
    for left_binding in left_bindings:
        matched = False
        for right_binding in right_bindings:
            if _bindings_compatible(left_binding, right_binding):
                merged = {**left_binding, **right_binding}
                results.append(merged)
                matched = True
        if not matched:
            results.append(left_binding)
    return results


def _bindings_compatible(binding_a, binding_b):
    """Check if two bindings are compatible (shared variables have equal values)."""
    for key in binding_a:
        if key in binding_b and binding_a[key] != binding_b[key]:
            return False
    return True


def _distinct_bindings(bindings):
    """Remove duplicate bindings."""
    seen = set()
    result = []
    for binding in bindings:
        key = tuple(sorted((k, str(v)) for k, v in binding.items()))
        if key not in seen:
            seen.add(key)
            result.append(binding)
    return result


def _apply_order_by(bindings, order_clauses):
    """Sort bindings by order clauses."""

    def sort_key(binding):
        keys = []
        for clause in order_clauses:
            value = binding.get(clause.variable)
            sort_value = str(value) if value is not None else ""
            keys.append(sort_value)
        return keys

    reverse_flags = [not clause.ascending for clause in order_clauses]
    if all(flag == reverse_flags[0] for flag in reverse_flags):
        return sorted(bindings, key=sort_key, reverse=reverse_flags[0])
    return sorted(bindings, key=sort_key)


def _apply_aggregation(bindings, group_by_variables, aggregates):
    """Apply GROUP BY and aggregate functions."""
    groups = {}
    for binding in bindings:
        group_key = tuple(binding.get(var) for var in group_by_variables)
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(binding)

    results = []
    for group_key, group_bindings in groups.items():
        result_binding = {}
        for variable, value in zip(group_by_variables, group_key):
            result_binding[variable] = value

        for aggregate in aggregates:
            if aggregate.function == "COUNT":
                if aggregate.argument == "*":
                    result_binding[aggregate.alias] = Literal(len(group_bindings))
                else:
                    count = sum(
                        1
                        for binding in group_bindings
                        if binding.get(aggregate.argument) is not None
                    )
                    result_binding[aggregate.alias] = Literal(count)
        results.append(result_binding)

    return results


def _apply_filter(bindings, filter_expr, prefixes):
    """Apply a FILTER expression to bindings."""
    raw = filter_expr.raw
    return [binding for binding in bindings if _evaluate_filter(raw, binding, prefixes)]


def _evaluate_filter(expression, binding, prefixes):
    """Evaluate a filter expression against a single binding."""
    expression = expression.strip()

    negation_match = re.match(r"^!\s*(.+)$", expression, re.DOTALL)
    if negation_match:
        return not _evaluate_filter(negation_match.group(1), binding, prefixes)

    or_parts = _split_logical(expression, "||")
    if len(or_parts) > 1:
        return any(_evaluate_filter(part, binding, prefixes) for part in or_parts)

    and_parts = _split_logical(expression, "&&")
    if len(and_parts) > 1:
        return all(_evaluate_filter(part, binding, prefixes) for part in and_parts)

    if expression.startswith("(") and expression.endswith(")"):
        return _evaluate_filter(expression[1:-1], binding, prefixes)

    regex_match = re.match(
        r'regex\s*\(\s*(.+?)\s*,\s*"([^"]*)"(?:\s*,\s*"([^"]*)")?\s*\)',
        expression,
        re.IGNORECASE,
    )
    if regex_match:
        target_expr = regex_match.group(1).strip()
        pattern = regex_match.group(2)
        flags_str = regex_match.group(3) or ""
        target_value = _evaluate_value_expression(target_expr, binding, prefixes)
        if target_value is None:
            return False
        regex_flags = 0
        if "i" in flags_str:
            regex_flags = re.IGNORECASE
        try:
            return bool(re.search(pattern, str(target_value), regex_flags))
        except re.error:
            return False

    lang_match = re.match(
        r"lang\s*\(\s*(\?\w+)\s*\)\s*=\s*\"([^\"]*)\"\s*$",
        expression,
        re.IGNORECASE,
    )
    if lang_match:
        var_name = lang_match.group(1)
        expected_lang = lang_match.group(2)
        value = binding.get(var_name)
        if isinstance(value, Literal) and value.language:
            return value.language.lower() == expected_lang.lower()
        return not expected_lang

    bound_match = re.match(r"bound\s*\(\s*(\?\w+)\s*\)", expression, re.IGNORECASE)
    if bound_match:
        var_name = bound_match.group(1)
        return binding.get(var_name) is not None

    equality_match = re.match(r"(.+?)\s*(=|!=)\s*(.+)", expression, re.DOTALL)
    if equality_match:
        left_expr = equality_match.group(1).strip()
        operator = equality_match.group(2)
        right_expr = equality_match.group(3).strip()
        left_value = _evaluate_value_expression(left_expr, binding, prefixes)
        right_value = _evaluate_value_expression(right_expr, binding, prefixes)
        if operator == "=":
            return (
                str(left_value) == str(right_value)
                if left_value is not None and right_value is not None
                else False
            )
        else:
            return (
                str(left_value) != str(right_value)
                if left_value is not None and right_value is not None
                else True
            )

    return True


def _evaluate_value_expression(expression, binding, prefixes):
    """Evaluate a value expression (variable, str(), lang(), or literal)."""
    expression = expression.strip()

    str_match = re.match(r"str\s*\(\s*(\?\w+)\s*\)", expression, re.IGNORECASE)
    if str_match:
        var_name = str_match.group(1)
        value = binding.get(var_name)
        return str(value) if value is not None else None

    lang_match = re.match(r"lang\s*\(\s*(\?\w+)\s*\)", expression, re.IGNORECASE)
    if lang_match:
        var_name = lang_match.group(1)
        value = binding.get(var_name)
        if isinstance(value, Literal) and value.language:
            return value.language
        return ""

    if expression.startswith("?"):
        return binding.get(expression)

    if expression.startswith('"') or expression.startswith("'"):
        return _parse_literal(expression)

    if expression.startswith("<") or ":" in expression:
        return _resolve_term(expression, prefixes)

    return Literal(expression)


def _split_logical(expression, operator):
    """Split a filter expression by logical operator, respecting parentheses."""
    parts = []
    depth = 0
    current = []
    i = 0
    while i < len(expression):
        char = expression[i]
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
        elif depth == 0 and expression[i : i + len(operator)] == operator:
            parts.append("".join(current).strip())
            current = []
            i += len(operator)
            continue
        else:
            current.append(char)
        i += 1
    if current:
        parts.append("".join(current).strip())
    return parts


def format_binding_value(value):
    """Convert an rdflib term to a serializable dict for JSON output."""
    if value is None:
        return None
    if isinstance(value, URIRef):
        return {"type": "uri", "value": str(value)}
    if isinstance(value, Literal):
        result = {"type": "literal", "value": str(value)}
        if value.language:
            result["xml:lang"] = value.language
        if value.datatype:
            result["datatype"] = str(value.datatype)
        return result
    return {"type": "literal", "value": str(value)}
