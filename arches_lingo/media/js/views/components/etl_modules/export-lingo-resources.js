import ko from 'knockout';
import $ from 'jquery';
import uuid from 'uuid';
import arches from 'arches';
import JsonErrorAlertViewModel from 'viewmodels/alert-json';
import exportLingoResources from 'templates/views/components/etl_modules/export-lingo-resources.htm';

const viewModel = function(params) {
    const self = this;

    if(typeof params.load_details === 'string'){
        this.loadDetails = JSON.parse(params.load_details);
    } else {
        this.loadDetails = params.load_details;
    }
    this.state = params.state;
    this.loading = params.loading || ko.observable();
    this.alert = params.alert;
    this.moduleId = params.etlmoduleid || "4302e334-33ed-4e85-99f2-fdac7c7c32fa";
    this.loadId = params.loadId || uuid.generate();
    this.selectedLoadEvent = params.selectedLoadEvent || ko.observable();
    this.formatTime = params.formatTime;
    this.timeDifference = params.timeDifference;
    this.activeTab = params.activeTab || ko.observable();
        
    this.formData = new window.FormData();
    this.schemes = ko.observable();
    this.selectedScheme = ko.observable();
    this.selectedSchemeName = ko.observable();
    this.filename = ko.observable();
    this.format = ko.observable();
    
    this.getSchemes = async function(){
        try {
            const response = await fetch(arches.urls.api_lingo_resources("scheme"));
            const data = await response.json();
            self.schemes(data);
        } catch (error) {
            self.alert(
                new JsonErrorAlertViewModel(
                    'ep-alert-red',
                    error.responseJSON["data"],
                    null,
                    function(){}
                )
            );
        }
        this.loading(false);
    };

    this.selectedScheme.subscribe(function(newValue) {
        if (newValue) {
            const scheme = self.schemes().find(({ conceptid }) => conceptid === newValue);
            if (scheme) {
                self.selectedSchemeName(scheme.prefLabel);
            }
        }
    });

    this.ready = ko.computed(function(){
        const ready = !!self.selectedScheme();
        return ready;
    });

    self.executeExport = function() {
        if (!self.ready()) {
            return;
        }
        self.loading(true);
        self.formData.append('resourceid', self.selectedScheme());
        if (self.filename()) {
            self.formData.append('filename', self.filename());
        }
        if (self.format()) {
            self.formData.append('format', self.format());
        }
        self.submit('start').then(data => {
            params.activeTab("import");
            self.formData.append('async', true);
        }).fail(error => {
            self.alert(
                new JsonErrorAlertViewModel(
                    'ep-alert-red',
                    error.responseJSON["data"],
                    null,
                    function(){}
                )
            );
        }).always(() => {
            self.loading(false);
        });
    };

    this.submit = function(action) {
        self.formData.append('action', action);
        self.formData.append('load_id', self.loadId);
        self.formData.append('module', self.moduleId);
        return $.ajax({
            type: "POST",
            url: arches.urls.etl_manager,
            data: self.formData,
            cache: false,
            processData: false,
            contentType: false,
        });
    };

    this.init = function(){
        this.getSchemes();
    };

    this.init();
};
ko.components.register('export-lingo-resources', {
    viewModel: viewModel,
    template: exportLingoResources,
});
export default viewModel;
