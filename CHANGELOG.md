# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-03-31

### Added
-   Add login interface [#13](https://github.com/archesproject/arches-lingo/issues/13)
-   Add front-end router [#11](https://github.com/archesproject/arches-lingo/issues/11)
-   Add dark mode toggle [#91](https://github.com/archesproject/arches-lingo/issues/91)
-   Add concept and scheme serializers [#103](https://github.com/archesproject/arches-lingo/issues/103)
-   Add backend for search [#67](https://github.com/archesproject/arches-lingo/issues/67)
-   Add concept and scheme pages [#15](https://github.com/archesproject/arches-lingo/issues/15)
-   Add concept hierarchy component [#18](https://github.com/archesproject/arches-lingo/issues/18)
-   Add scheme creation [#157](https://github.com/archesproject/arches-lingo/issues/157)
-   Add advanced search with facets [#67](https://github.com/archesproject/arches-lingo/issues/67)
-   Add language selector and gettext/i18n translation support [#569](https://github.com/archesproject/arches-lingo/pull/569)
-   Add basic dashboard for the Lingo homepage [#579](https://github.com/archesproject/arches-lingo/pull/579)
-   Add edit log to concept and scheme reports [#577](https://github.com/archesproject/arches-lingo/pull/577)
-   Add SKOS XML and JSON-LD export formats
-   Add user profile page [#589](https://github.com/archesproject/arches-lingo/pull/589)
-   Add display of concept and scheme URIs and identifiers in header [#330](https://github.com/archesproject/arches-lingo/issues/330)
-   Add top concepts section to scheme page
-   Add sources and contributors pages [#620](https://github.com/archesproject/arches-lingo/pull/620)
-   Add anonymous/readonly access to Lingo [#617](https://github.com/archesproject/arches-lingo/pull/617)
-   Add import/export with improved status UX [#619](https://github.com/archesproject/arches-lingo/pull/619)
-   Add concept resource widgets and related components [#474](https://github.com/archesproject/arches-lingo/issues/474) [#475](https://github.com/archesproject/arches-lingo/issues/475) [#456](https://github.com/archesproject/arches-lingo/issues/456) [#512](https://github.com/archesproject/arches-lingo/pull/512)
-   Allow Lingo editors to access ETL modules and history [#625](https://github.com/archesproject/arches-lingo/issues/625) [#626](https://github.com/archesproject/arches-lingo/pull/626)
-   Add alphabetical sorting by label in hierarchy and top concepts [#630](https://github.com/archesproject/arches-lingo/pull/630)
-   Add scheme lifecycle states [#521](https://github.com/archesproject/arches-lingo/pull/521)
-   Add "top concept of" section for top concepts [#646](https://github.com/archesproject/arches-lingo/pull/646)
-   Add owner name display in concept and scheme headers [#654](https://github.com/archesproject/arches-lingo/pull/654)
-   Add improved hierarchical position viewer [#650](https://github.com/archesproject/arches-lingo/pull/650)
-   Add top concept handling in advanced search [#661](https://github.com/archesproject/arches-lingo/pull/661)
-   Add cycle detection in concept builder to prevent infinite recursion [#663](https://github.com/archesproject/arches-lingo/pull/663)
-   Add permissions handling for scheme identifier/URI interfaces [#662](https://github.com/archesproject/arches-lingo/pull/662)
-   Add centralized resource data store for optimized API calls [#574](https://github.com/archesproject/arches-lingo/pull/574)
-   Add navigation prompt when leaving a form with unsaved changes [#571](https://github.com/archesproject/arches-lingo/pull/571)
-   Add sortable datatable for reports [#573](https://github.com/archesproject/arches-lingo/pull/573)
-   Add in-UI notifications display [#490](https://github.com/archesproject/arches-lingo/pull/490)
-   Add concept type widget to concept header [#546](https://github.com/archesproject/arches-lingo/issues/546)
-   Add language count display in scheme header [#544](https://github.com/archesproject/arches-lingo/issues/544)
-   Add matched concept support via URL datatype [#491](https://github.com/archesproject/arches-lingo/issues/491)
-   Add RDM-to-Lingo migration path for matched concepts [#491](https://github.com/archesproject/arches-lingo/issues/491)
-   Add inline "add child" and "add top concept" buttons to hierarchy header
-   Add reciprocal concept relationship handling
-   Add concept images section [#452](https://github.com/archesproject/arches-lingo/pull/452)
-   Add default concept type value on concept creation [#552](https://github.com/archesproject/arches-lingo/issues/552)
-   Add lifecycle state badges throughout the UI [#676](https://github.com/archesproject/arches-lingo/pull/676)
-   Add help content [#590](https://github.com/archesproject/arches-lingo/issues/590)
-   Add lifecycle state filter to hierarchy view [#628](https://github.com/archesproject/arches-lingo/pull/628)
-   Add ability to delete and deprecate concepts [#674](https://github.com/archesproject/arches-lingo/pull/674)
-   Add label editor on new scheme and concept creation [#538](https://github.com/archesproject/arches-lingo/issues/538)
-   Assign correct lifecycle state to schemes and concepts during import [#653](https://github.com/archesproject/arches-lingo/issues/653)
-   Add landing page [#693](https://github.com/archesproject/arches-lingo/pull/693)
-   Surface node-level validation errors to user [#691](https://github.com/archesproject/arches-lingo/pull/691)

### Changed
-   Upgrade Lingo to Arches 8.1 [#453](https://github.com/archesproject/arches-lingo/pull/453)
-   Improve JSON-LD export performance
-   Use label type URIs for label-type comparison instead of label strings [#649](https://github.com/archesproject/arches-lingo/pull/649)
-   Adjust ontology namespace [#648](https://github.com/archesproject/arches-lingo/pull/648)
-   Swap in populated reference lists for person, organization, and source types [#635](https://github.com/archesproject/arches-lingo/pull/635)
-   Retrieve scheme from resource store [#476](https://github.com/archesproject/arches-lingo/issues/476) [#627](https://github.com/archesproject/arches-lingo/pull/627)
-   Hide Arches resource link from resource selector and viewer [#622](https://github.com/archesproject/arches-lingo/issues/622) [#629](https://github.com/archesproject/arches-lingo/pull/629)
-   Standardize metastring labels for schemes and concepts
-   Update Lingo models to use language datatype [#544](https://github.com/archesproject/arches-lingo/issues/544)
-   Render URIs as clickable links when they are valid URLs [#491](https://github.com/archesproject/arches-lingo/issues/491)
-   Remove URL clashes on graph slug [#605](https://github.com/archesproject/arches-lingo/pull/605)
-   Use alternate icon for guide terms [#604](https://github.com/archesproject/arches-lingo/pull/604)
-   General UI cleaning, styling, and polish [#506](https://github.com/archesproject/arches-lingo/pull/506)
-   Improve dashboard UI [#623](https://github.com/archesproject/arches-lingo/issues/623)
-   Update side navigation with admin-only menu items [#655](https://github.com/archesproject/arches-lingo/pull/655)
-   Enforce single value for statement type nodes [#530](https://github.com/archesproject/arches-lingo/issues/530)
-   Assign ontology property on concept migration [#671](https://github.com/archesproject/arches-lingo/pull/671)
-   Update concept model resource relationships [#511](https://github.com/archesproject/arches-lingo/issues/511)
-   Catch missing gettext strings [#675](https://github.com/archesproject/arches-lingo/pull/675)
-   Hide lifecycle state buttons from non-editor users [#683](https://github.com/archesproject/arches-lingo/pull/683)
-   General UI style updates [#686](https://github.com/archesproject/arches-lingo/issues/686)

### Fixed
-   Merge language finder implementations [#92](https://github.com/archesproject/arches-lingo/issues/92)
-   Fix reference list nodes [#584](https://github.com/archesproject/arches-lingo/pull/584)
-   Fix celery broker URLs [#643](https://github.com/archesproject/arches-lingo/pull/643)
-   Fix concept header display distinguishing "top concept of" from parent concepts [#656](https://github.com/archesproject/arches-lingo/pull/656)
-   Remove current concept from associated concept selection [#558](https://github.com/archesproject/arches-lingo/issues/558) [#633](https://github.com/archesproject/arches-lingo/pull/633)
-   Fix SKOS XML export
-   Fix dark mode display in advanced search
-   Fix scheme list vertical scrolling [#564](https://github.com/archesproject/arches-lingo/pull/564)
-   Fix matched concept date form labels [#535](https://github.com/archesproject/arches-lingo/issues/535)
-   Surface error messages from file list validation [#492](https://github.com/archesproject/arches-lingo/pull/492)
-   Ensure dirty state is cleared after saving a new resource [#613](https://github.com/archesproject/arches-lingo/pull/613)
-   Fix export handling for orphaned and deleted concepts [#652](https://github.com/archesproject/arches-lingo/issues/652)
-   Fix edit log revert exception handling [#667](https://github.com/archesproject/arches-lingo/pull/667)
-   Fix text direction change on language selection [#673](https://github.com/archesproject/arches-lingo/pull/673)
-   Fix encoded HTML strings in hierarchy labels [#685](https://github.com/archesproject/arches-lingo/pull/685)
-   Fix scheme header action buttons displaying for unsaved new schemes [#684](https://github.com/archesproject/arches-lingo/pull/684)
-   Fix revert button displaying in edit log for non-editable resources [#694](https://github.com/archesproject/arches-lingo/pull/694)
-   Fix translatable strings in script tags not updating on language change [#692](https://github.com/archesproject/arches-lingo/pull/692)

[1.0.0]: https://github.com/archesproject/arches-lingo/releases/tag/1.0.0
