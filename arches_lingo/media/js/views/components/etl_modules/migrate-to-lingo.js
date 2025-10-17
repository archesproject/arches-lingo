import ko from 'knockout';
import $ from 'jquery';
import uuid from 'uuid';
import arches from 'arches';
import JsonErrorAlertViewModel from 'viewmodels/alert-json';
import migrateRDMTemplate from 'templates/views/components/etl_modules/migrate-to-lingo.htm';


const viewModel = function(params) {
    const self = this;

    if(Array.isArray(params.load_details)){
        let details = {};
        this.loadDetails = params.load_details.map(item => {
            if(typeof item === 'string'){
                details = {...details, ...JSON.parse(item)};
            }
            else {
                details = {...details, ...item};
            }
        });
        this.loadDetails = ko.observable(details);
    } else {
        this.loadDetails = ko.observable(params.load_details);
    }
    this.state = params.state;
    this.loading = params.loading || ko.observable();
    this.alert = params.alert;
    this.moduleId = params.etlmoduleid;
    this.loadId = params.loadId || uuid.generate();
    this.formData = new window.FormData();
    this.schemes = ko.observable();
    this.selectedScheme = ko.observable();
    this.selectedSchemeName = ko.observable();
    this.selectedLoadEvent = params.selectedLoadEvent || ko.observable();
    this.formatTime = params.formatTime;
    this.timeDifference = params.timeDifference;
    this.activeTab = params.activeTab || ko.observable();
    this.editHistoryUrl = `${arches.urls.edit_history}?transactionid=${ko.unwrap(params.selectedLoadEvent)?.loadid}`;
    
    this.getSchemes = function(){
        self.loading(true);
        self.submit('get_schemes').then(function(response){
            self.schemes(response.result);
            self.loading(false);
        });
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

    self.runRDMMigration = function() {
        if (!self.ready()) {
            return;
        }
        self.loading(true);
        self.formData.append('scheme', self.selectedScheme());
        self.submit('start').then(data => {
            params.activeTab("import");
            self.formData.append('async', true);
            self.submit('write').then(data => {
            }).fail(function(err) {
                console.log(err);
                self.alert(
                    new JsonErrorAlertViewModel(
                        'ep-alert-red',
                        err.responseJSON["data"],
                        null,
                        function(){}
                    )
                );
            }).always(() => {
                self.loading(false);
            });
        }).fail(error => console.log(error.responseJSON.data));
    };

    this.submit = function(action) {
        self.formData.append('action', action);
        self.formData.append('loadid', self.loadId);
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
ko.components.register('migrate-to-lingo', {
    viewModel: viewModel,
    template: migrateRDMTemplate,
});
export default viewModel;
