# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - Unreleased

## [1.1.1] - 2026-07-31

### Fixed
-   Fix installation and configuration instructions in the README [#763](https://github.com/archesproject/arches-lingo/pull/763)

## [1.1.0] - 2026-07-31

### Added
-   Add progressive hierarchy loading [#707](https://github.com/archesproject/arches-lingo/pull/707)
-   Add saved sets to the explore panel [#713](https://github.com/archesproject/arches-lingo/pull/713)
-   Add all results to a set from advanced search [#715](https://github.com/archesproject/arches-lingo/pull/715)
-   Add router links to the hierarchical position section of the concept page [#719](https://github.com/archesproject/arches-lingo/pull/719)
-   Add icon for concepts that are hierarchy names [#721](https://github.com/archesproject/arches-lingo/pull/721)
-   Add sources and contributors facets to advanced search [#722](https://github.com/archesproject/arches-lingo/pull/722)
-   Add narrower concepts section to reports [#732](https://github.com/archesproject/arches-lingo/pull/732)
-   Add URI copy button to headers [#743](https://github.com/archesproject/arches-lingo/pull/743)
-   Add multiline config for notes and image descriptions [#745](https://github.com/archesproject/arches-lingo/pull/745)
-   Add scheme attribution [#752](https://github.com/archesproject/arches-lingo/pull/752)
-   Add ability to lock/unlock schemes and related concepts [#753](https://github.com/archesproject/arches-lingo/pull/753)
-   Add scripts to dump and load fixtures [#755](https://github.com/archesproject/arches-lingo/pull/755)
-   Add advanced search facet for searching on related images [#756](https://github.com/archesproject/arches-lingo/pull/756)
-   Add content-negotiated SKOS dereferencing for scheme and concept URIs [#759](https://github.com/archesproject/arches-lingo/pull/759)

### Changed
-   Optimize search performance for large-scale datasets [#704](https://github.com/archesproject/arches-lingo/pull/704)
-   Improve dashboard performance for large-scale datasets [#705](https://github.com/archesproject/arches-lingo/pull/705)
-   Improve scheme header display for schemes with many languages [#717](https://github.com/archesproject/arches-lingo/pull/717)
-   Improve dashboard display for large datasets [#718](https://github.com/archesproject/arches-lingo/pull/718)
-   Improve performance of concept select dropdowns via per-term search [#720](https://github.com/archesproject/arches-lingo/pull/720)
-   Improve advanced search with additional enhancements and fixes [#729](https://github.com/archesproject/arches-lingo/pull/729)
-   Improve explore concept sets [#730](https://github.com/archesproject/arches-lingo/pull/730)
-   Harden lifecycle retirement [#695](https://github.com/archesproject/arches-lingo/issues/695) [#731](https://github.com/archesproject/arches-lingo/pull/731)
-   Improve report UX for large datasets [#732](https://github.com/archesproject/arches-lingo/pull/732)
-   Polish scheme header [#733](https://github.com/archesproject/arches-lingo/pull/733)
-   Make narrower concepts count tag consistent with other headers [#737](https://github.com/archesproject/arches-lingo/pull/737)
-   Make top concepts section consistent with other concept lists [#738](https://github.com/archesproject/arches-lingo/pull/738)
-   Improve image upload and display [#744](https://github.com/archesproject/arches-lingo/pull/744)
-   Resolve matched concept URIs locally when available [#749](https://github.com/archesproject/arches-lingo/pull/749)
-   Migrate from arches-component-lab to arches-vue-components [#741](https://github.com/archesproject/arches-lingo/pull/741)

### Fixed
-   Fix bugs to support AAT data load [#702](https://github.com/archesproject/arches-lingo/pull/702)
-   Fix import handling for AAT data load [#703](https://github.com/archesproject/arches-lingo/pull/703)
-   Prevent UUID from displaying in basic search on select [#746](https://github.com/archesproject/arches-lingo/pull/746)
-   Hide form on save [#747](https://github.com/archesproject/arches-lingo/pull/747)
-   Guard against unnecessary tree requests [#750](https://github.com/archesproject/arches-lingo/pull/750)
-   Put exported CSVs into per-model folders to prevent filename clashes [#754](https://github.com/archesproject/arches-lingo/pull/754)

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
-   Polish concept page frontend interactions and editor loading states [#688](https://github.com/archesproject/arches-lingo/pull/688)

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

[1.1.1]: https://github.com/archesproject/arches-lingo/releases/tag/1.1.1
[1.1.0]: https://github.com/archesproject/arches-lingo/releases/tag/1.1.0
[1.0.0]: https://github.com/archesproject/arches-lingo/releases/tag/1.0.0
