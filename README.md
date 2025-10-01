# Welcome to Arches Lingo!

Arches Lingo is an Arches application designed to support the creation of thesaurus/vocabulary data.  It supports the creation of polyhierarchical thesauri, and provides a user interface for managing thesauri and their terms. Arches Lingo is built on top of the Arches platform, which is an open-source software platform for managing cultural heritage data.

Please see the [project page](http://archesproject.org/) for more information on the Arches project.


## Installation

If you are installing Arches Lingo for the first time, we strongly recommend that you install it as an Arches application into a existing (or new) project. Running Arches Lingo as a standalone project can provide some convenience if you are a developer contributing to the Arches Lingo project but you risk conflicts when upgrading to the next version of Arches Lingo.

Install Arches Lingo using the following command:
```
pip install arches-lingo
```

For developer install instructions, see the [Developer Setup](#developer-setup-for-contributing-to-the-arches-lingo-project) section below.


## Project Configuration

1. If you don't already have an Arches project, you'll need to create one by following the instructions in the Arches [documentation](http://archesproject.org/documentation/).

2. When your project is ready, add "arches_querysets", "arches_component_lab", "arches_controlled_lists", "arches_lingo", and "pgtrigger" to INSTALLED_APPS **below** the name of your project:
    ```
    INSTALLED_APPS = (
        ...
        "my_project_name",
        "arches_querysets",
        "arches_component_lab",
        "arches_controlled_lists",
        "arches_lingo",
        "pgtrigger",
    )
    ```

3. Make sure the following settings are added to your project
    ```
    REFERENCES_INDEX_NAME = "references"
    ELASTICSEARCH_CUSTOM_INDEXES = [
        {
            "module": "arches_controlled_lists.search_indexes.reference_index.ReferenceIndex",
            "name": REFERENCES_INDEX_NAME,
            "should_update_asynchronously": True,
        }
    ]
    TERM_SEARCH_TYPES = [
        {
            "type": "term",
            "label": _("Term Matches"),
            "key": "terms",
            "module": "arches.app.search.search_term.TermSearch",
        },
        {
            "type": "concept",
            "label": _("Concepts"),
            "key": "concepts",
            "module": "arches.app.search.concept_search.ConceptSearch",
        },
        {
            "type": "reference",
            "label": _("References"),
            "key": REFERENCES_INDEX_NAME,
            "module": "arches_controlled_lists.search_indexes.reference_index.ReferenceIndex",
        },
    ]

    ES_MAPPING_MODIFIER_CLASSES = [
        "arches_controlled_lists.search.references_es_mapping_modifier.ReferencesEsMappingModifier"
    ]
    ```

4. Next ensure arches and arches_lingo are included as dependencies in package.json
    ```
    "dependencies": {
        "arches": "archesproject/arches#dev/8.0.x",
        "arches_lingo": "archesproject/arches-lingo#main"
    }
    ```

5. Update urls.py to include the arches_lingo urls
    ```
    urlpatterns = [
        path("", include("arches_lingo.urls")),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    ```

6. Install the arches application package (models and other data)
    ```
    python manage.py packages -o load_package -a arches_lingo -dev -y
    ```

7. Start your project
    ```
    python manage.py runserver
    ```

8. Next cd into your project's app directory (the one with package.json) install and build front-end dependencies:
    ```
    npm install
    npm run build_development
    ```

## Developer Setup (for contributing to the Arches Lingo project)

1. Download the arches-lingo repo:

    a.  If using the [Github CLI](https://cli.github.com/): `gh repo clone archesproject/arches-lingo`
    
    b.  If not using the Github CLI: `git clone https://github.com/archesproject/arches-lingo.git`

2. Download the arches package:

    a.  If using the [Github CLI](https://cli.github.com/): `gh repo clone archesproject/arches`

    b.  If not using the Github CLI: `git clone https://github.com/archesproject/arches.git`

3. Create a virtual environment outside of both repositories: 
    ```
    python3 -m venv ENV
    ```

4. Activate the virtual enviroment in your terminal:
    ```
    source ENV/bin/activate
    ```

5. Navigate to the `arches-lingo` directory, and install the project (with development dependencies):
    ```
    cd arches-lingo
    pip install -e . --group dev
    ```

6. Also install core arches for local development:
    ```
    pip install -e ../arches
    ```

1. Create a settings_local.py file with `DEBUG=True`:
    ```
    echo "DEBUG = True" > arches_lingo/settings_local.py
    ```

7. Run the Django server:
    ```
    python manage.py runserver
    ```

8.  (From the `arches-lingo` top-level directory) install the frontend dependencies:
    ```
    npm install
    ```

9.  Once the dependencies have been installed, generate the static asset bundle:

    a. If you're planning on editing HTML/CSS/JavaScript files, run `npm start`. This will start a development server that will automatically detect changes to static assets and rebuild the bundle.

    b. If you're not planning on editing HTML/CSS/JavaScript files, run `npm run build_development`

10. If you ran `npm start` in the previous step, you will need to open a new terminal window and activate the virtual environment in the new terminal window. If you ran `npm run build_development` then you can skip this step.

11. Install the ontologies, branches, and resource models from the package.
    ```
    python manage.py setup_db
    python manage.py packages -o load_package -a arches_lingo --yes -db
    ```

12. Load the test data:
    ```
    python manage.py loaddata tests/fixtures/data/FISH_Thesauri_example_data_resources.json tests/fixtures/data/FISH_Thesauri_example_data_tiles.json
    ```

13. In the terminal window that is running the Django server, halt the server and restart it.
    ```
    (ctrl+c to halt the server)
    python manage.py runserver
    ```

## Committing changes

NOTE: Changes are committed to the arches-lingo repository. 

1. Navigate to the repository
    ```
    cd arches-lingo
    ```

2. Cut a new git branch
    ```
    git checkout origin/main -b my-descriptive-branch-name
    ```

3. If updating models or branches

    1. Manually export the model or branch from the project

    2. Manually move the exported model or branch into one of the subdirectories in the `arches-lingo/arches_lingo/pkg/graphs` directory.

4. Add your changes to the current git commit
    ```
    git status
    git add -- path/to/file path/to/second/file
    git commit -m "Descriptive commit message"
    ```

5. Update the remote repository with your commits:
    ```
    git push origin HEAD
    ```

6. Navigate to https://github.com/archesproject/arches-lingo/pulls to see and commit the pull request

## Roadmap

### 1.0.0 alpha (Released June 2025)

- Adds resource  models and controlled lists for managing thesauri and their terms as Arches resource data
- Introduces the Arches Lingo UI, a dedicated, custom experience for creating and managing thesauri and their terms including:
  - Hierarchy viewer for exploring thesauri hierarchically
  - Basic search for finding terms in thesauri
  - Basic Scheme and Concept reports and editors for editing thesauri and their terms

### 1.0.0 beta (Released September 2025)

- Improves the Arches Lingo UI with improved hierarchy viewer and search
- Extends the Scheme and Concept reports and editors with additional fields and features

### 1.0.0 (To Be Released March 2025)

- Adds support for managing scheme and concept lifecycles including
  - Publishing schemes and their concepts to create new versions of schemes
  - Managing the automatic generation and assignment of friendly identifiers and URIs for schemes and concepts
  - Deprecating concepts and schemes
- Adds support for bulk import and export of thesauri and their terms as SKOS RDF
- Enhances the Lingo UI with user dashboards
- Advanced search and filtering capabilities for thesauri and their terms
- Allow users to view edit log for thesauri and their terms and revert changes as part of a draft edit
- Saved searches and search results for managing lists of terms 

### Future Releases

- Adds support for additional import/export formats
- Public search interface for searching over published thesauri and their terms even during draft edits
- SPARQL endpoint for querying thesauri and their terms
- Support for splitting and merging concepts within thesauri
- A "candidate scheme" for managing terms before they are added to a thesaurus
- Managing hierarchies of additional models:
  - People and groups
  - Places
  - Time periods

## References

- [1] Contains information from the J. Paul Getty Trust, Getty Research Institute, the Art & Architecture Thesaurus, which is made available under the ODC Attribution License.
