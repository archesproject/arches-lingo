import csv
import io
import json
import logging
from http import HTTPStatus

from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.mixins.permissions import AnonymousAccessMixin
from arches_lingo.utils.sparql.evaluator import (
    SparqlEvaluationError,
    evaluate_query,
    format_binding_value,
)
from arches_lingo.utils.sparql.examples import EXAMPLE_QUERIES
from arches_lingo.utils.sparql.graph_builder import (
    build_graph_for_all,
    build_graph_for_scheme,
)
from arches_lingo.utils.sparql.orm_evaluator import (
    can_evaluate_via_orm,
    evaluate_query_via_orm,
)
from arches_lingo.utils.sparql.parser import (
    SparqlParseError,
    SparqlUnsupportedError,
    parse_sparql,
)

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 10000


class SparqlQueryView(AnonymousAccessMixin, View):
    """SPARQL query endpoint for Lingo concept data.

    Accepts SPARQL SELECT queries via POST (JSON body) or GET (query params).
    Returns results in SPARQL JSON Results format by default, with optional
    CSV download support.
    """

    def get(self, request):
        query_string = request.GET.get("query", "").strip()
        scheme_id = request.GET.get("scheme_id", "").strip() or None
        result_format = request.GET.get("format", "json").strip()

        if not query_string:
            return JSONErrorResponse(
                title=_("Missing query."),
                message=_("Provide a SPARQL query via the 'query' parameter."),
                status=HTTPStatus.BAD_REQUEST,
            )

        return self._execute_sparql(query_string, scheme_id, result_format)

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JSONErrorResponse(
                title=_("Invalid request."),
                message=_("Request body must be valid JSON."),
                status=HTTPStatus.BAD_REQUEST,
            )

        query_string = body.get("query", "").strip()
        scheme_id = body.get("scheme_id") or None
        result_format = body.get("format", "json").strip()

        if not query_string:
            return JSONErrorResponse(
                title=_("Missing query."),
                message=_("Provide a SPARQL query in the 'query' field."),
                status=HTTPStatus.BAD_REQUEST,
            )

        return self._execute_sparql(query_string, scheme_id, result_format)

    def _execute_sparql(self, query_string, scheme_id, result_format):
        if len(query_string) > MAX_QUERY_LENGTH:
            return JSONErrorResponse(
                title=_("Query too large."),
                message=_("Query exceeds the maximum length of %(max)d characters.")
                % {"max": MAX_QUERY_LENGTH},
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            parsed = parse_sparql(query_string)
        except SparqlUnsupportedError as unsupported_error:
            return JSONErrorResponse(
                title=_("Unsupported query."),
                message=str(unsupported_error),
                status=HTTPStatus.BAD_REQUEST,
            )
        except SparqlParseError as parse_error:
            return JSONErrorResponse(
                title=_("Parse error."),
                message=str(parse_error),
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            if can_evaluate_via_orm(parsed):
                raw_results = evaluate_query_via_orm(parsed, scheme_id)
            else:
                if scheme_id:
                    graph = build_graph_for_scheme(scheme_id)
                else:
                    graph = build_graph_for_all()
                raw_results = evaluate_query(parsed, graph)
        except SparqlEvaluationError as evaluation_error:
            return JSONErrorResponse(
                title=_("Evaluation error."),
                message=str(evaluation_error),
                status=HTTPStatus.BAD_REQUEST,
            )
        except Exception:
            logger.exception("Error evaluating SPARQL query")
            return JSONErrorResponse(
                title=_("Evaluation error."),
                message=_("An error occurred while evaluating the query."),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        if result_format == "csv":
            return self._format_csv(raw_results)

        return self._format_json(raw_results)

    def _format_json(self, raw_results):
        variables = raw_results["variables"]
        formatted_bindings = []
        for binding in raw_results["bindings"]:
            formatted = {}
            for variable in variables:
                formatted[variable] = format_binding_value(binding.get(variable))
            formatted_bindings.append(formatted)

        response_data = {
            "head": {"vars": [var.lstrip("?") for var in variables]},
            "results": {
                "bindings": [
                    {
                        var.lstrip("?"): value
                        for var, value in binding.items()
                        if value is not None
                    }
                    for binding in formatted_bindings
                ]
            },
        }
        return JSONResponse(response_data)

    def _format_csv(self, raw_results):
        from django.http import HttpResponse

        variables = [var.lstrip("?") for var in raw_results["variables"]]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(variables)
        for binding in raw_results["bindings"]:
            row = []
            for variable in raw_results["variables"]:
                value = binding.get(variable)
                row.append(str(value) if value is not None else "")
            writer.writerow(row)

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="sparql_results.csv"'
        return response


class SparqlExamplesView(AnonymousAccessMixin, View):
    """Returns the curated list of example SPARQL queries."""

    def get(self, request):
        return JSONResponse(EXAMPLE_QUERIES)
