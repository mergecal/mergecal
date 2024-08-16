/*!
FullCalendar Resource Plugin v6.1.15
Docs & License: https://fullcalendar.io/docs/premium
(c) 2024 Adam Shaw
*/
FullCalendar.Resource = (function (exports, core, premiumCommonPlugin, internal$1, preact) {
    'use strict';

    function _interopDefault (e) { return e && e.__esModule ? e : { 'default': e }; }

    var premiumCommonPlugin__default = /*#__PURE__*/_interopDefault(premiumCommonPlugin);

    function massageEventDragMutation(eventMutation, hit0, hit1) {
        let resource0 = hit0.dateSpan.resourceId;
        let resource1 = hit1.dateSpan.resourceId;
        if (resource0 && resource1 &&
            resource0 !== resource1) {
            eventMutation.resourceMutation = {
                matchResourceId: resource0,
                setResourceId: resource1,
            };
        }
    }
    /*
    TODO: all this would be much easier if we were using a hash!
    */
    function applyEventDefMutation(eventDef, mutation, context) {
        let resourceMutation = mutation.resourceMutation;
        if (resourceMutation && computeResourceEditable(eventDef, context)) {
            let index = eventDef.resourceIds.indexOf(resourceMutation.matchResourceId);
            if (index !== -1) {
                let resourceIds = eventDef.resourceIds.slice(); // copy
                resourceIds.splice(index, 1); // remove
                if (resourceIds.indexOf(resourceMutation.setResourceId) === -1) { // not already in there
                    resourceIds.push(resourceMutation.setResourceId); // add
                }
                eventDef.resourceIds = resourceIds;
            }
        }
    }
    /*
    HACK
    TODO: use EventUi system instead of this
    */
    function computeResourceEditable(eventDef, context) {
        let { resourceEditable } = eventDef;
        if (resourceEditable == null) {
            let source = eventDef.sourceId && context.getCurrentData().eventSources[eventDef.sourceId];
            if (source) {
                resourceEditable = source.extendedProps.resourceEditable; // used the Source::extendedProps hack
            }
            if (resourceEditable == null) {
                resourceEditable = context.options.eventResourceEditable;
                if (resourceEditable == null) {
                    resourceEditable = context.options.editable; // TODO: use defaults system instead
                }
            }
        }
        return resourceEditable;
    }
    function transformEventDrop(mutation, context) {
        let { resourceMutation } = mutation;
        if (resourceMutation) {
            let { calendarApi } = context;
            return {
                oldResource: calendarApi.getResourceById(resourceMutation.matchResourceId),
                newResource: calendarApi.getResourceById(resourceMutation.setResourceId),
            };
        }
        return {
            oldResource: null,
            newResource: null,
        };
    }

    class ResourceDataAdder {
        constructor() {
            this.filterResources = internal$1.memoize(filterResources);
        }
        transform(viewProps, calendarProps) {
            if (calendarProps.viewSpec.optionDefaults.needsResourceData) {
                return {
                    resourceStore: this.filterResources(calendarProps.resourceStore, calendarProps.options.filterResourcesWithEvents, calendarProps.eventStore, calendarProps.dateProfile.activeRange),
                    resourceEntityExpansions: calendarProps.resourceEntityExpansions,
                };
            }
            return null;
        }
    }
    function filterResources(resourceStore, doFilterResourcesWithEvents, eventStore, activeRange) {
        if (doFilterResourcesWithEvents) {
            let instancesInRange = filterEventInstancesInRange(eventStore.instances, activeRange);
            let hasEvents = computeHasEvents(instancesInRange, eventStore.defs);
            Object.assign(hasEvents, computeAncestorHasEvents(hasEvents, resourceStore));
            return internal$1.filterHash(resourceStore, (resource, resourceId) => hasEvents[resourceId]);
        }
        return resourceStore;
    }
    function filterEventInstancesInRange(eventInstances, activeRange) {
        return internal$1.filterHash(eventInstances, (eventInstance) => internal$1.rangesIntersect(eventInstance.range, activeRange));
    }
    function computeHasEvents(eventInstances, eventDefs) {
        let hasEvents = {};
        for (let instanceId in eventInstances) {
            let instance = eventInstances[instanceId];
            for (let resourceId of eventDefs[instance.defId].resourceIds) {
                hasEvents[resourceId] = true;
            }
        }
        return hasEvents;
    }
    /*
    mark resources as having events if any of their ancestors have them
    NOTE: resourceStore might not have all the resources that hasEvents{} has keyed
    */
    function computeAncestorHasEvents(hasEvents, resourceStore) {
        let res = {};
        for (let resourceId in hasEvents) {
            let resource;
            while ((resource = resourceStore[resourceId])) {
                resourceId = resource.parentId; // now functioning as the parentId
                if (resourceId) {
                    res[resourceId] = true;
                }
                else {
                    break;
                }
            }
        }
        return res;
    }
    /*
    for making sure events that have editable resources are always draggable in resource views
    */
    function transformIsDraggable(val, eventDef, eventUi, context) {
        if (!val) {
            let state = context.getCurrentData();
            let viewSpec = state.viewSpecs[state.currentViewType];
            if (viewSpec.optionDefaults.needsResourceData) {
                if (computeResourceEditable(eventDef, context)) {
                    return true;
                }
            }
        }
        return val;
    }

    // for when non-resource view should be given EventUi info (for event coloring/constraints based off of resource data)
    class ResourceEventConfigAdder {
        constructor() {
            this.buildResourceEventUis = internal$1.memoize(buildResourceEventUis, internal$1.isPropsEqual);
            this.injectResourceEventUis = internal$1.memoize(injectResourceEventUis);
        }
        transform(viewProps, calendarProps) {
            if (!calendarProps.viewSpec.optionDefaults.needsResourceData) {
                return {
                    eventUiBases: this.injectResourceEventUis(viewProps.eventUiBases, viewProps.eventStore.defs, this.buildResourceEventUis(calendarProps.resourceStore)),
                };
            }
            return null;
        }
    }
    function buildResourceEventUis(resourceStore) {
        return internal$1.mapHash(resourceStore, (resource) => resource.ui);
    }
    function injectResourceEventUis(eventUiBases, eventDefs, resourceEventUis) {
        return internal$1.mapHash(eventUiBases, (eventUi, defId) => {
            if (defId) { // not the '' key
                return injectResourceEventUi(eventUi, eventDefs[defId], resourceEventUis);
            }
            return eventUi;
        });
    }
    function injectResourceEventUi(origEventUi, eventDef, resourceEventUis) {
        let parts = [];
        // first resource takes precedence, which fights with the ordering of combineEventUis, thus the unshifts
        for (let resourceId of eventDef.resourceIds) {
            if (resourceEventUis[resourceId]) {
                parts.unshift(resourceEventUis[resourceId]);
            }
        }
        parts.unshift(origEventUi);
        return internal$1.combineEventUis(parts);
    }

    let defs = []; // TODO: use plugin system
    function registerResourceSourceDef(def) {
        defs.push(def);
    }
    function getResourceSourceDef(id) {
        return defs[id];
    }
    function getResourceSourceDefs() {
        return defs;
    }

    // TODO: make this a plugin-able parser
    // TODO: success/failure
    const RESOURCE_SOURCE_REFINERS = {
        id: String,
        // for array. TODO: move to resource-array
        resources: internal$1.identity,
        // for json feed. TODO: move to resource-json-feed
        url: String,
        method: String,
        startParam: String,
        endParam: String,
        timeZoneParam: String,
        extraParams: internal$1.identity,
    };
    function parseResourceSource(input) {
        let inputObj;
        if (typeof input === 'string') {
            inputObj = { url: input };
        }
        else if (typeof input === 'function' || Array.isArray(input)) {
            inputObj = { resources: input };
        }
        else if (typeof input === 'object' && input) { // non-null object
            inputObj = input;
        }
        if (inputObj) {
            let { refined, extra } = internal$1.refineProps(inputObj, RESOURCE_SOURCE_REFINERS);
            warnUnknownProps(extra);
            let metaRes = buildResourceSourceMeta(refined);
            if (metaRes) {
                return {
                    _raw: input,
                    sourceId: internal$1.guid(),
                    sourceDefId: metaRes.sourceDefId,
                    meta: metaRes.meta,
                    publicId: refined.id || '',
                    isFetching: false,
                    latestFetchId: '',
                    fetchRange: null,
                };
            }
        }
        return null;
    }
    function buildResourceSourceMeta(refined) {
        let defs = getResourceSourceDefs();
        for (let i = defs.length - 1; i >= 0; i -= 1) { // later-added plugins take precedence
            let def = defs[i];
            let meta = def.parseMeta(refined);
            if (meta) {
                return { meta, sourceDefId: i };
            }
        }
        return null;
    }
    function warnUnknownProps(props) {
        for (let propName in props) {
            console.warn(`Unknown resource prop '${propName}'`);
        }
    }

    function reduceResourceSource(source, action, context) {
        let { options, dateProfile } = context;
        if (!source || !action) {
            return createSource(options.initialResources || options.resources, dateProfile.activeRange, options.refetchResourcesOnNavigate, context);
        }
        switch (action.type) {
            case 'RESET_RESOURCE_SOURCE':
                return createSource(action.resourceSourceInput, dateProfile.activeRange, options.refetchResourcesOnNavigate, context);
            case 'PREV': // TODO: how do we track all actions that affect dateProfile :(
            case 'NEXT':
            case 'CHANGE_DATE':
            case 'CHANGE_VIEW_TYPE':
                return handleRangeChange(source, dateProfile.activeRange, options.refetchResourcesOnNavigate, context);
            case 'RECEIVE_RESOURCES':
            case 'RECEIVE_RESOURCE_ERROR':
                return receiveResponse(source, action.fetchId, action.fetchRange);
            case 'REFETCH_RESOURCES':
                return fetchSource(source, dateProfile.activeRange, context);
            default:
                return source;
        }
    }
    function createSource(input, activeRange, refetchResourcesOnNavigate, context) {
        if (input) {
            let source = parseResourceSource(input);
            source = fetchSource(source, refetchResourcesOnNavigate ? activeRange : null, context);
            return source;
        }
        return null;
    }
    function handleRangeChange(source, activeRange, refetchResourcesOnNavigate, context) {
        if (refetchResourcesOnNavigate &&
            !doesSourceIgnoreRange(source) &&
            (!source.fetchRange || !internal$1.rangesEqual(source.fetchRange, activeRange))) {
            return fetchSource(source, activeRange, context);
        }
        return source;
    }
    function doesSourceIgnoreRange(source) {
        return Boolean(getResourceSourceDef(source.sourceDefId).ignoreRange);
    }
    function fetchSource(source, fetchRange, context) {
        let sourceDef = getResourceSourceDef(source.sourceDefId);
        let fetchId = internal$1.guid();
        sourceDef.fetch({
            resourceSource: source,
            range: fetchRange,
            context,
        }, (res) => {
            context.dispatch({
                type: 'RECEIVE_RESOURCES',
                fetchId,
                fetchRange,
                rawResources: res.rawResources,
            });
        }, (error) => {
            context.dispatch({
                type: 'RECEIVE_RESOURCE_ERROR',
                fetchId,
                fetchRange,
                error,
            });
        });
        return Object.assign(Object.assign({}, source), { isFetching: true, latestFetchId: fetchId });
    }
    function receiveResponse(source, fetchId, fetchRange) {
        if (fetchId === source.latestFetchId) {
            return Object.assign(Object.assign({}, source), { isFetching: false, fetchRange });
        }
        return source;
    }

    const PRIVATE_ID_PREFIX = '_fc:';
    const RESOURCE_REFINERS = {
        id: String,
        parentId: String,
        children: internal$1.identity,
        title: String,
        businessHours: internal$1.identity,
        extendedProps: internal$1.identity,
        // event-ui
        eventEditable: Boolean,
        eventStartEditable: Boolean,
        eventDurationEditable: Boolean,
        eventConstraint: internal$1.identity,
        eventOverlap: Boolean,
        eventAllow: internal$1.identity,
        eventClassNames: internal$1.parseClassNames,
        eventBackgroundColor: String,
        eventBorderColor: String,
        eventTextColor: String,
        eventColor: String,
    };
    /*
    needs a full store so that it can populate children too
    */
    function parseResource(raw, parentId = '', store, context) {
        let { refined, extra } = internal$1.refineProps(raw, RESOURCE_REFINERS);
        let resource = {
            id: refined.id || (PRIVATE_ID_PREFIX + internal$1.guid()),
            parentId: refined.parentId || parentId,
            title: refined.title || '',
            businessHours: refined.businessHours ? internal$1.parseBusinessHours(refined.businessHours, context) : null,
            ui: internal$1.createEventUi({
                editable: refined.eventEditable,
                startEditable: refined.eventStartEditable,
                durationEditable: refined.eventDurationEditable,
                constraint: refined.eventConstraint,
                overlap: refined.eventOverlap,
                allow: refined.eventAllow,
                classNames: refined.eventClassNames,
                backgroundColor: refined.eventBackgroundColor,
                borderColor: refined.eventBorderColor,
                textColor: refined.eventTextColor,
                color: refined.eventColor,
            }, context),
            extendedProps: Object.assign(Object.assign({}, extra), refined.extendedProps),
        };
        // help out ResourceApi from having user modify props
        Object.freeze(resource.ui.classNames);
        Object.freeze(resource.extendedProps);
        if (store[resource.id]) ;
        else {
            store[resource.id] = resource;
            if (refined.children) {
                for (let childInput of refined.children) {
                    parseResource(childInput, resource.id, store, context);
                }
            }
        }
        return resource;
    }
    /*
    TODO: use this in more places
    */
    function getPublicId(id) {
        if (id.indexOf(PRIVATE_ID_PREFIX) === 0) {
            return '';
        }
        return id;
    }

    function reduceResourceStore(store, action, source, context) {
        if (!store || !action) {
            return {};
        }
        switch (action.type) {
            case 'RECEIVE_RESOURCES':
                return receiveRawResources(store, action.rawResources, action.fetchId, source, context);
            case 'ADD_RESOURCE':
                return addResource(store, action.resourceHash);
            case 'REMOVE_RESOURCE':
                return removeResource(store, action.resourceId);
            case 'SET_RESOURCE_PROP':
                return setResourceProp(store, action.resourceId, action.propName, action.propValue);
            case 'SET_RESOURCE_EXTENDED_PROP':
                return setResourceExtendedProp(store, action.resourceId, action.propName, action.propValue);
            default:
                return store;
        }
    }
    function receiveRawResources(existingStore, inputs, fetchId, source, context) {
        if (source.latestFetchId === fetchId) {
            let nextStore = {};
            for (let input of inputs) {
                parseResource(input, '', nextStore, context);
            }
            return nextStore;
        }
        return existingStore;
    }
    function addResource(existingStore, additions) {
        // TODO: warn about duplicate IDs
        return Object.assign(Object.assign({}, existingStore), additions);
    }
    function removeResource(existingStore, resourceId) {
        let newStore = Object.assign({}, existingStore);
        delete newStore[resourceId];
        // promote children
        for (let childResourceId in newStore) { // a child, *maybe* but probably not
            if (newStore[childResourceId].parentId === resourceId) {
                newStore[childResourceId] = Object.assign(Object.assign({}, newStore[childResourceId]), { parentId: '' });
            }
        }
        return newStore;
    }
    function setResourceProp(existingStore, resourceId, name, value) {
        let existingResource = existingStore[resourceId];
        // TODO: sanitization
        if (existingResource) {
            return Object.assign(Object.assign({}, existingStore), { [resourceId]: Object.assign(Object.assign({}, existingResource), { [name]: value }) });
        }
        return existingStore;
    }
    function setResourceExtendedProp(existingStore, resourceId, name, value) {
        let existingResource = existingStore[resourceId];
        if (existingResource) {
            return Object.assign(Object.assign({}, existingStore), { [resourceId]: Object.assign(Object.assign({}, existingResource), { extendedProps: Object.assign(Object.assign({}, existingResource.extendedProps), { [name]: value }) }) });
        }
        return existingStore;
    }

    function reduceResourceEntityExpansions(expansions, action) {
        if (!expansions || !action) {
            return {};
        }
        switch (action.type) {
            case 'SET_RESOURCE_ENTITY_EXPANDED':
                return Object.assign(Object.assign({}, expansions), { [action.id]: action.isExpanded });
            default:
                return expansions;
        }
    }

    function reduceResources(state, action, context) {
        let resourceSource = reduceResourceSource(state && state.resourceSource, action, context);
        let resourceStore = reduceResourceStore(state && state.resourceStore, action, resourceSource, context);
        let resourceEntityExpansions = reduceResourceEntityExpansions(state && state.resourceEntityExpansions, action);
        return {
            resourceSource,
            resourceStore,
            resourceEntityExpansions,
        };
    }

    const EVENT_REFINERS = {
        resourceId: String,
        resourceIds: internal$1.identity,
        resourceEditable: Boolean,
    };
    function generateEventDefResourceMembers(refined) {
        return {
            resourceIds: ensureStringArray(refined.resourceIds)
                .concat(refined.resourceId ? [refined.resourceId] : []),
            resourceEditable: refined.resourceEditable,
        };
    }
    function ensureStringArray(items) {
        return (items || []).map((item) => String(item));
    }

    function transformDateSelectionJoin(hit0, hit1) {
        let resourceId0 = hit0.dateSpan.resourceId;
        let resourceId1 = hit1.dateSpan.resourceId;
        if (resourceId0 && resourceId1) {
            return { resourceId: resourceId0 };
        }
        return null;
    }

    class ResourceApi {
        constructor(_context, _resource) {
            this._context = _context;
            this._resource = _resource;
        }
        setProp(name, value) {
            let oldResource = this._resource;
            this._context.dispatch({
                type: 'SET_RESOURCE_PROP',
                resourceId: oldResource.id,
                propName: name,
                propValue: value,
            });
            this.sync(oldResource);
        }
        setExtendedProp(name, value) {
            let oldResource = this._resource;
            this._context.dispatch({
                type: 'SET_RESOURCE_EXTENDED_PROP',
                resourceId: oldResource.id,
                propName: name,
                propValue: value,
            });
            this.sync(oldResource);
        }
        sync(oldResource) {
            let context = this._context;
            let resourceId = oldResource.id;
            // TODO: what if dispatch didn't complete synchronously?
            this._resource = context.getCurrentData().resourceStore[resourceId];
            context.emitter.trigger('resourceChange', {
                oldResource: new ResourceApi(context, oldResource),
                resource: this,
                revert() {
                    context.dispatch({
                        type: 'ADD_RESOURCE',
                        resourceHash: {
                            [resourceId]: oldResource,
                        },
                    });
                },
            });
        }
        remove() {
            let context = this._context;
            let internalResource = this._resource;
            let resourceId = internalResource.id;
            context.dispatch({
                type: 'REMOVE_RESOURCE',
                resourceId,
            });
            context.emitter.trigger('resourceRemove', {
                resource: this,
                revert() {
                    context.dispatch({
                        type: 'ADD_RESOURCE',
                        resourceHash: {
                            [resourceId]: internalResource,
                        },
                    });
                },
            });
        }
        getParent() {
            let context = this._context;
            let parentId = this._resource.parentId;
            if (parentId) {
                return new ResourceApi(context, context.getCurrentData().resourceStore[parentId]);
            }
            return null;
        }
        getChildren() {
            let thisResourceId = this._resource.id;
            let context = this._context;
            let { resourceStore } = context.getCurrentData();
            let childApis = [];
            for (let resourceId in resourceStore) {
                if (resourceStore[resourceId].parentId === thisResourceId) {
                    childApis.push(new ResourceApi(context, resourceStore[resourceId]));
                }
            }
            return childApis;
        }
        /*
        this is really inefficient!
        TODO: make EventApi::resourceIds a hash or keep an index in the Calendar's state
        */
        getEvents() {
            let thisResourceId = this._resource.id;
            let context = this._context;
            let { defs, instances } = context.getCurrentData().eventStore;
            let eventApis = [];
            for (let instanceId in instances) {
                let instance = instances[instanceId];
                let def = defs[instance.defId];
                if (def.resourceIds.indexOf(thisResourceId) !== -1) { // inefficient!!!
                    eventApis.push(new internal$1.EventImpl(context, def, instance));
                }
            }
            return eventApis;
        }
        get id() { return getPublicId(this._resource.id); }
        get title() { return this._resource.title; }
        get eventConstraint() { return this._resource.ui.constraints[0] || null; } // TODO: better type
        get eventOverlap() { return this._resource.ui.overlap; }
        get eventAllow() { return this._resource.ui.allows[0] || null; } // TODO: better type
        get eventBackgroundColor() { return this._resource.ui.backgroundColor; }
        get eventBorderColor() { return this._resource.ui.borderColor; }
        get eventTextColor() { return this._resource.ui.textColor; }
        // NOTE: user can't modify these because Object.freeze was called in event-def parsing
        get eventClassNames() { return this._resource.ui.classNames; }
        get extendedProps() { return this._resource.extendedProps; }
        toPlainObject(settings = {}) {
            let internal = this._resource;
            let { ui } = internal;
            let publicId = this.id;
            let res = {};
            if (publicId) {
                res.id = publicId;
            }
            if (internal.title) {
                res.title = internal.title;
            }
            if (settings.collapseEventColor && ui.backgroundColor && ui.backgroundColor === ui.borderColor) {
                res.eventColor = ui.backgroundColor;
            }
            else {
                if (ui.backgroundColor) {
                    res.eventBackgroundColor = ui.backgroundColor;
                }
                if (ui.borderColor) {
                    res.eventBorderColor = ui.borderColor;
                }
            }
            if (ui.textColor) {
                res.eventTextColor = ui.textColor;
            }
            if (ui.classNames.length) {
                res.eventClassNames = ui.classNames;
            }
            if (Object.keys(internal.extendedProps).length) {
                if (settings.collapseExtendedProps) {
                    Object.assign(res, internal.extendedProps);
                }
                else {
                    res.extendedProps = internal.extendedProps;
                }
            }
            return res;
        }
        toJSON() {
            return this.toPlainObject();
        }
    }
    function buildResourceApis(resourceStore, context) {
        let resourceApis = [];
        for (let resourceId in resourceStore) {
            resourceApis.push(new ResourceApi(context, resourceStore[resourceId]));
        }
        return resourceApis;
    }

    internal$1.CalendarImpl.prototype.addResource = function (input, scrollTo = true) {
        let currentState = this.getCurrentData();
        let resourceHash;
        let resource;
        if (input instanceof ResourceApi) {
            resource = input._resource;
            resourceHash = { [resource.id]: resource };
        }
        else {
            resourceHash = {};
            resource = parseResource(input, '', resourceHash, currentState);
        }
        this.dispatch({
            type: 'ADD_RESOURCE',
            resourceHash,
        });
        if (scrollTo) {
            // TODO: wait til dispatch completes somehow
            this.trigger('_scrollRequest', { resourceId: resource.id });
        }
        let resourceApi = new ResourceApi(currentState, resource);
        currentState.emitter.trigger('resourceAdd', {
            resource: resourceApi,
            revert: () => {
                this.dispatch({
                    type: 'REMOVE_RESOURCE',
                    resourceId: resource.id,
                });
            },
        });
        return resourceApi;
    };
    internal$1.CalendarImpl.prototype.getResourceById = function (id) {
        id = String(id);
        let currentState = this.getCurrentData(); // eslint-disable-line react/no-this-in-sfc
        if (currentState.resourceStore) { // guard against calendar with no resource functionality
            let rawResource = currentState.resourceStore[id];
            if (rawResource) {
                return new ResourceApi(currentState, rawResource);
            }
        }
        return null;
    };
    internal$1.CalendarImpl.prototype.getResources = function () {
        let currentState = this.getCurrentData();
        let { resourceStore } = currentState;
        let resourceApis = [];
        if (resourceStore) { // guard against calendar with no resource functionality
            for (let resourceId in resourceStore) {
                resourceApis.push(new ResourceApi(currentState, resourceStore[resourceId]));
            }
        }
        return resourceApis;
    };
    internal$1.CalendarImpl.prototype.getTopLevelResources = function () {
        let currentState = this.getCurrentData();
        let { resourceStore } = currentState;
        let resourceApis = [];
        if (resourceStore) { // guard against calendar with no resource functionality
            for (let resourceId in resourceStore) {
                if (!resourceStore[resourceId].parentId) {
                    resourceApis.push(new ResourceApi(currentState, resourceStore[resourceId]));
                }
            }
        }
        return resourceApis;
    };
    internal$1.CalendarImpl.prototype.refetchResources = function () {
        this.dispatch({
            type: 'REFETCH_RESOURCES',
        });
    };
    function transformDatePoint(dateSpan, context) {
        return dateSpan.resourceId ?
            { resource: context.calendarApi.getResourceById(dateSpan.resourceId) } :
            {};
    }
    function transformDateSpan(dateSpan, context) {
        return dateSpan.resourceId ?
            { resource: context.calendarApi.getResourceById(dateSpan.resourceId) } :
            {};
    }

    /*
    splits things BASED OFF OF which resources they are associated with.
    creates a '' entry which is when something has NO resource.
    */
    class ResourceSplitter extends internal$1.Splitter {
        getKeyInfo(props) {
            return Object.assign({ '': {} }, props.resourceStore);
        }
        getKeysForDateSpan(dateSpan) {
            return [dateSpan.resourceId || ''];
        }
        getKeysForEventDef(eventDef) {
            let resourceIds = eventDef.resourceIds;
            if (!resourceIds.length) {
                return [''];
            }
            return resourceIds;
        }
    }

    function isPropsValidWithResources(combinedProps, context) {
        let splitter = new ResourceSplitter();
        let sets = splitter.splitProps(Object.assign(Object.assign({}, combinedProps), { resourceStore: context.getCurrentData().resourceStore }));
        for (let resourceId in sets) {
            let props = sets[resourceId];
            // merge in event data from the non-resource segment
            if (resourceId && sets['']) { // current segment is not the non-resource one, and there IS a non-resource one
                props = Object.assign(Object.assign({}, props), { eventStore: internal$1.mergeEventStores(sets[''].eventStore, props.eventStore), eventUiBases: Object.assign(Object.assign({}, sets[''].eventUiBases), props.eventUiBases) });
            }
            if (!internal$1.isPropsValid(props, context, { resourceId }, filterConfig.bind(null, resourceId))) {
                return false;
            }
        }
        return true;
    }
    function filterConfig(resourceId, config) {
        return Object.assign(Object.assign({}, config), { constraints: filterConstraints(resourceId, config.constraints) });
    }
    function filterConstraints(resourceId, constraints) {
        return constraints.map((constraint) => {
            let defs = constraint.defs;
            if (defs) { // we are dealing with an EventStore
                // if any of the events define constraints to resources that are NOT this resource,
                // then this resource is unconditionally prohibited, which is what a `false` value does.
                for (let defId in defs) {
                    let resourceIds = defs[defId].resourceIds;
                    if (resourceIds.length && resourceIds.indexOf(resourceId) === -1) { // TODO: use a hash?!!! (for other reasons too)
                        return false;
                    }
                }
            }
            return constraint;
        });
    }

    function transformExternalDef(dateSpan) {
        return dateSpan.resourceId ?
            { resourceId: dateSpan.resourceId } :
            {};
    }

    const optionChangeHandlers = {
        resources: handleResources,
    };
    function handleResources(newSourceInput, context) {
        let oldSourceInput = context.getCurrentData().resourceSource._raw;
        if (oldSourceInput !== newSourceInput) {
            context.dispatch({
                type: 'RESET_RESOURCE_SOURCE',
                resourceSourceInput: newSourceInput,
            });
        }
    }

    const DEFAULT_RESOURCE_ORDER = internal$1.parseFieldSpecs('id,title');
    function handleResourceStore(resourceStore, calendarData) {
        let { emitter } = calendarData;
        if (emitter.hasHandlers('resourcesSet')) {
            emitter.trigger('resourcesSet', buildResourceApis(resourceStore, calendarData));
        }
    }

    const OPTION_REFINERS = {
        initialResources: internal$1.identity,
        resources: internal$1.identity,
        eventResourceEditable: Boolean,
        refetchResourcesOnNavigate: Boolean,
        resourceOrder: internal$1.parseFieldSpecs,
        filterResourcesWithEvents: Boolean,
        resourceGroupField: String,
        resourceAreaWidth: internal$1.identity,
        resourceAreaColumns: internal$1.identity,
        resourcesInitiallyExpanded: Boolean,
        datesAboveResources: Boolean,
        needsResourceData: Boolean,
        resourceAreaHeaderClassNames: internal$1.identity,
        resourceAreaHeaderContent: internal$1.identity,
        resourceAreaHeaderDidMount: internal$1.identity,
        resourceAreaHeaderWillUnmount: internal$1.identity,
        resourceGroupLabelClassNames: internal$1.identity,
        resourceGroupLabelContent: internal$1.identity,
        resourceGroupLabelDidMount: internal$1.identity,
        resourceGroupLabelWillUnmount: internal$1.identity,
        resourceLabelClassNames: internal$1.identity,
        resourceLabelContent: internal$1.identity,
        resourceLabelDidMount: internal$1.identity,
        resourceLabelWillUnmount: internal$1.identity,
        resourceLaneClassNames: internal$1.identity,
        resourceLaneContent: internal$1.identity,
        resourceLaneDidMount: internal$1.identity,
        resourceLaneWillUnmount: internal$1.identity,
        resourceGroupLaneClassNames: internal$1.identity,
        resourceGroupLaneContent: internal$1.identity,
        resourceGroupLaneDidMount: internal$1.identity,
        resourceGroupLaneWillUnmount: internal$1.identity,
    };
    const LISTENER_REFINERS = {
        resourcesSet: internal$1.identity,
        resourceAdd: internal$1.identity,
        resourceChange: internal$1.identity,
        resourceRemove: internal$1.identity,
    };

    internal$1.EventImpl.prototype.getResources = function () {
        let { calendarApi } = this._context;
        return this._def.resourceIds.map((resourceId) => calendarApi.getResourceById(resourceId));
    };
    internal$1.EventImpl.prototype.setResources = function (resources) {
        let resourceIds = [];
        // massage resources -> resourceIds
        for (let resource of resources) {
            let resourceId = null;
            if (typeof resource === 'string') {
                resourceId = resource;
            }
            else if (typeof resource === 'number') {
                resourceId = String(resource);
            }
            else if (resource instanceof ResourceApi) {
                resourceId = resource.id; // guaranteed to always have an ID. hmmm
            }
            else {
                console.warn('unknown resource type: ' + resource);
            }
            if (resourceId) {
                resourceIds.push(resourceId);
            }
        }
        this.mutate({
            standardProps: {
                resourceIds,
            },
        });
    };

    registerResourceSourceDef({
        ignoreRange: true,
        parseMeta(refined) {
            if (Array.isArray(refined.resources)) {
                return refined.resources;
            }
            return null;
        },
        fetch(arg, successCallback) {
            successCallback({
                rawResources: arg.resourceSource.meta,
            });
        },
    });

    registerResourceSourceDef({
        parseMeta(refined) {
            if (typeof refined.resources === 'function') {
                return refined.resources;
            }
            return null;
        },
        fetch(arg, successCallback, errorCallback) {
            const dateEnv = arg.context.dateEnv;
            const func = arg.resourceSource.meta;
            const publicArg = arg.range ? {
                start: dateEnv.toDate(arg.range.start),
                end: dateEnv.toDate(arg.range.end),
                startStr: dateEnv.formatIso(arg.range.start),
                endStr: dateEnv.formatIso(arg.range.end),
                timeZone: dateEnv.timeZone,
            } : {};
            internal$1.unpromisify(func.bind(null, publicArg), (rawResources) => successCallback({ rawResources }), errorCallback);
        },
    });

    registerResourceSourceDef({
        parseMeta(refined) {
            if (refined.url) {
                return {
                    url: refined.url,
                    method: (refined.method || 'GET').toUpperCase(),
                    extraParams: refined.extraParams,
                };
            }
            return null;
        },
        fetch(arg, successCallback, errorCallback) {
            const meta = arg.resourceSource.meta;
            const requestParams = buildRequestParams(meta, arg.range, arg.context);
            internal$1.requestJson(meta.method, meta.url, requestParams).then(([rawResources, response]) => {
                successCallback({ rawResources, response });
            }, errorCallback);
        },
    });
    // TODO: somehow consolidate with event json feed
    function buildRequestParams(meta, range, context) {
        let { dateEnv, options } = context;
        let startParam;
        let endParam;
        let timeZoneParam;
        let customRequestParams;
        let params = {};
        if (range) {
            startParam = meta.startParam;
            if (startParam == null) {
                startParam = options.startParam;
            }
            endParam = meta.endParam;
            if (endParam == null) {
                endParam = options.endParam;
            }
            timeZoneParam = meta.timeZoneParam;
            if (timeZoneParam == null) {
                timeZoneParam = options.timeZoneParam;
            }
            params[startParam] = dateEnv.formatIso(range.start);
            params[endParam] = dateEnv.formatIso(range.end);
            if (dateEnv.timeZone !== 'local') {
                params[timeZoneParam] = dateEnv.timeZone;
            }
        }
        // retrieve any outbound GET/POST data from the options
        if (typeof meta.extraParams === 'function') {
            // supplied as a function that returns a key/value object
            customRequestParams = meta.extraParams();
        }
        else {
            // probably supplied as a straight key/value object
            customRequestParams = meta.extraParams || {};
        }
        Object.assign(params, customRequestParams);
        return params;
    }

    var plugin = core.createPlugin({
        name: '@fullcalendar/resource',
        premiumReleaseDate: '2024-07-12',
        deps: [premiumCommonPlugin__default["default"]],
        reducers: [reduceResources],
        isLoadingFuncs: [
            (state) => state.resourceSource && state.resourceSource.isFetching,
        ],
        eventRefiners: EVENT_REFINERS,
        eventDefMemberAdders: [generateEventDefResourceMembers],
        isDraggableTransformers: [transformIsDraggable],
        eventDragMutationMassagers: [massageEventDragMutation],
        eventDefMutationAppliers: [applyEventDefMutation],
        dateSelectionTransformers: [transformDateSelectionJoin],
        datePointTransforms: [transformDatePoint],
        dateSpanTransforms: [transformDateSpan],
        viewPropsTransformers: [ResourceDataAdder, ResourceEventConfigAdder],
        isPropsValid: isPropsValidWithResources,
        externalDefTransforms: [transformExternalDef],
        eventDropTransformers: [transformEventDrop],
        optionChangeHandlers,
        optionRefiners: OPTION_REFINERS,
        listenerRefiners: LISTENER_REFINERS,
        propSetHandlers: { resourceStore: handleResourceStore },
    });

    function refineRenderProps$1(input) {
        return {
            resource: new ResourceApi(input.context, input.resource),
        };
    }

    // TODO: not used for Spreadsheet. START USING. difficult because of col-specific rendering props
    class ResourceLabelContainer extends internal$1.BaseComponent {
        constructor() {
            super(...arguments);
            this.refineRenderProps = internal$1.memoizeObjArg(refineRenderProps);
        }
        render() {
            const { props } = this;
            return (preact.createElement(internal$1.ViewContextType.Consumer, null, (context) => {
                let { options } = context;
                let renderProps = this.refineRenderProps({
                    resource: props.resource,
                    date: props.date,
                    context,
                });
                return (preact.createElement(internal$1.ContentContainer, Object.assign({}, props, { elAttrs: Object.assign(Object.assign({}, props.elAttrs), { 'data-resource-id': props.resource.id, 'data-date': props.date ? internal$1.formatDayString(props.date) : undefined }), renderProps: renderProps, generatorName: "resourceLabelContent", customGenerator: options.resourceLabelContent, defaultGenerator: renderInnerContent, classNameGenerator: options.resourceLabelClassNames, didMount: options.resourceLabelDidMount, willUnmount: options.resourceLabelWillUnmount })));
            }));
        }
    }
    function renderInnerContent(props) {
        return props.resource.title || props.resource.id;
    }
    function refineRenderProps(input) {
        return {
            resource: new ResourceApi(input.context, input.resource),
            date: input.date ? input.context.dateEnv.toDate(input.date) : null,
            view: input.context.viewApi,
        };
    }

    class ResourceCell extends internal$1.BaseComponent {
        render() {
            let { props } = this;
            return (preact.createElement(ResourceLabelContainer, { elTag: "th", elClasses: ['fc-col-header-cell', 'fc-resource'], elAttrs: {
                    role: 'columnheader',
                    colSpan: props.colSpan,
                }, resource: props.resource, date: props.date }, (InnerContent) => (preact.createElement("div", { className: "fc-scrollgrid-sync-inner" },
                preact.createElement(InnerContent, { elTag: "span", elClasses: [
                        'fc-col-header-cell-cushion',
                        props.isSticky && 'fc-sticky',
                    ] })))));
        }
    }

    class ResourceDayHeader extends internal$1.BaseComponent {
        constructor() {
            super(...arguments);
            this.buildDateFormat = internal$1.memoize(buildDateFormat);
        }
        render() {
            let { props, context } = this;
            let dateFormat = this.buildDateFormat(context.options.dayHeaderFormat, props.datesRepDistinctDays, props.dates.length);
            return (preact.createElement(internal$1.NowTimer, { unit: "day" }, (nowDate, todayRange) => {
                if (props.dates.length === 1) {
                    return this.renderResourceRow(props.resources, props.dates[0]);
                }
                if (context.options.datesAboveResources) {
                    return this.renderDayAndResourceRows(props.dates, dateFormat, todayRange, props.resources);
                }
                return this.renderResourceAndDayRows(props.resources, props.dates, dateFormat, todayRange);
            }));
        }
        renderResourceRow(resources, date) {
            let resourceCells = resources.map((resource) => (preact.createElement(ResourceCell, { key: resource.id, resource: resource, colSpan: 1, date: date })));
            return this.buildTr(resourceCells, 'resources');
        }
        renderDayAndResourceRows(dates, dateFormat, todayRange, resources) {
            let dateCells = [];
            let resourceCells = [];
            for (let date of dates) {
                dateCells.push(this.renderDateCell(date, dateFormat, todayRange, resources.length, null, true));
                for (let resource of resources) {
                    resourceCells.push(preact.createElement(ResourceCell, { key: resource.id + ':' + date.toISOString(), resource: resource, colSpan: 1, date: date }));
                }
            }
            return (preact.createElement(preact.Fragment, null,
                this.buildTr(dateCells, 'day'),
                this.buildTr(resourceCells, 'resources')));
        }
        renderResourceAndDayRows(resources, dates, dateFormat, todayRange) {
            let resourceCells = [];
            let dateCells = [];
            for (let resource of resources) {
                resourceCells.push(preact.createElement(ResourceCell, { key: resource.id, resource: resource, colSpan: dates.length, isSticky: true }));
                for (let date of dates) {
                    dateCells.push(this.renderDateCell(date, dateFormat, todayRange, 1, resource));
                }
            }
            return (preact.createElement(preact.Fragment, null,
                this.buildTr(resourceCells, 'resources'),
                this.buildTr(dateCells, 'day')));
        }
        // a cell with date text. might have a resource associated with it
        renderDateCell(date, dateFormat, todayRange, colSpan, resource, isSticky) {
            let { props } = this;
            let keyPostfix = resource ? `:${resource.id}` : '';
            let extraRenderProps = resource ? { resource: new ResourceApi(this.context, resource) } : {};
            let extraDataAttrs = resource ? { 'data-resource-id': resource.id } : {};
            return props.datesRepDistinctDays ? (preact.createElement(internal$1.TableDateCell, { key: date.toISOString() + keyPostfix, date: date, dateProfile: props.dateProfile, todayRange: todayRange, colCnt: props.dates.length * props.resources.length, dayHeaderFormat: dateFormat, colSpan: colSpan, isSticky: isSticky, extraRenderProps: extraRenderProps, extraDataAttrs: extraDataAttrs })) : (preact.createElement(internal$1.TableDowCell // we can't leverage the pure-componentness becausae the extra* props are new every time :(
            , { key: date.getUTCDay() + keyPostfix, dow: date.getUTCDay(), dayHeaderFormat: dateFormat, colSpan: colSpan, isSticky: isSticky, extraRenderProps: extraRenderProps, extraDataAttrs: extraDataAttrs }));
        }
        buildTr(cells, key) {
            let { renderIntro } = this.props;
            if (!cells.length) {
                cells = [preact.createElement("td", { key: 0 }, "\u00A0")];
            }
            return (preact.createElement("tr", { key: key, role: "row" },
                renderIntro && renderIntro(key),
                cells));
        }
    }
    function buildDateFormat(dayHeaderFormat, datesRepDistinctDays, dayCnt) {
        return dayHeaderFormat || internal$1.computeFallbackHeaderFormat(datesRepDistinctDays, dayCnt);
    }

    class ResourceIndex {
        constructor(resources) {
            let indicesById = {};
            let ids = [];
            for (let i = 0; i < resources.length; i += 1) {
                let id = resources[i].id;
                ids.push(id);
                indicesById[id] = i;
            }
            this.ids = ids;
            this.indicesById = indicesById;
            this.length = resources.length;
        }
    }

    class AbstractResourceDayTableModel {
        constructor(dayTableModel, resources, context) {
            this.dayTableModel = dayTableModel;
            this.resources = resources;
            this.context = context;
            this.resourceIndex = new ResourceIndex(resources);
            this.rowCnt = dayTableModel.rowCnt;
            this.colCnt = dayTableModel.colCnt * resources.length;
            this.cells = this.buildCells();
        }
        buildCells() {
            let { rowCnt, dayTableModel, resources } = this;
            let rows = [];
            for (let row = 0; row < rowCnt; row += 1) {
                let rowCells = [];
                for (let dateCol = 0; dateCol < dayTableModel.colCnt; dateCol += 1) {
                    for (let resourceCol = 0; resourceCol < resources.length; resourceCol += 1) {
                        let resource = resources[resourceCol];
                        let extraRenderProps = { resource: new ResourceApi(this.context, resource) };
                        let extraDataAttrs = { 'data-resource-id': resource.id };
                        let extraClassNames = ['fc-resource'];
                        let extraDateSpan = { resourceId: resource.id };
                        let date = dayTableModel.cells[row][dateCol].date;
                        rowCells[this.computeCol(dateCol, resourceCol)] = {
                            key: resource.id + ':' + date.toISOString(),
                            date,
                            extraRenderProps,
                            extraDataAttrs,
                            extraClassNames,
                            extraDateSpan,
                        };
                    }
                }
                rows.push(rowCells);
            }
            return rows;
        }
    }

    /*
    resources over dates
    */
    class ResourceDayTableModel extends AbstractResourceDayTableModel {
        computeCol(dateI, resourceI) {
            return resourceI * this.dayTableModel.colCnt + dateI;
        }
        /*
        all date ranges are intact
        */
        computeColRanges(dateStartI, dateEndI, resourceI) {
            return [
                {
                    firstCol: this.computeCol(dateStartI, resourceI),
                    lastCol: this.computeCol(dateEndI, resourceI),
                    isStart: true,
                    isEnd: true,
                },
            ];
        }
    }

    /*
    dates over resources
    */
    class DayResourceTableModel extends AbstractResourceDayTableModel {
        computeCol(dateI, resourceI) {
            return dateI * this.resources.length + resourceI;
        }
        /*
        every single day is broken up
        */
        computeColRanges(dateStartI, dateEndI, resourceI) {
            let segs = [];
            for (let i = dateStartI; i <= dateEndI; i += 1) {
                let col = this.computeCol(i, resourceI);
                segs.push({
                    firstCol: col,
                    lastCol: col,
                    isStart: i === dateStartI,
                    isEnd: i === dateEndI,
                });
            }
            return segs;
        }
    }

    const NO_SEGS = []; // for memoizing
    class VResourceJoiner {
        constructor() {
            this.joinDateSelection = internal$1.memoize(this.joinSegs);
            this.joinBusinessHours = internal$1.memoize(this.joinSegs);
            this.joinFgEvents = internal$1.memoize(this.joinSegs);
            this.joinBgEvents = internal$1.memoize(this.joinSegs);
            this.joinEventDrags = internal$1.memoize(this.joinInteractions);
            this.joinEventResizes = internal$1.memoize(this.joinInteractions);
        }
        /*
        propSets also has a '' key for things with no resource
        */
        joinProps(propSets, resourceDayTable) {
            let dateSelectionSets = [];
            let businessHoursSets = [];
            let fgEventSets = [];
            let bgEventSets = [];
            let eventDrags = [];
            let eventResizes = [];
            let eventSelection = '';
            let keys = resourceDayTable.resourceIndex.ids.concat(['']); // add in the all-resource key
            for (let key of keys) {
                let props = propSets[key];
                dateSelectionSets.push(props.dateSelectionSegs);
                businessHoursSets.push(key ? props.businessHourSegs : NO_SEGS); // don't include redundant all-resource businesshours
                fgEventSets.push(key ? props.fgEventSegs : NO_SEGS); // don't include fg all-resource segs
                bgEventSets.push(props.bgEventSegs);
                eventDrags.push(props.eventDrag);
                eventResizes.push(props.eventResize);
                eventSelection = eventSelection || props.eventSelection;
            }
            return {
                dateSelectionSegs: this.joinDateSelection(resourceDayTable, ...dateSelectionSets),
                businessHourSegs: this.joinBusinessHours(resourceDayTable, ...businessHoursSets),
                fgEventSegs: this.joinFgEvents(resourceDayTable, ...fgEventSets),
                bgEventSegs: this.joinBgEvents(resourceDayTable, ...bgEventSets),
                eventDrag: this.joinEventDrags(resourceDayTable, ...eventDrags),
                eventResize: this.joinEventResizes(resourceDayTable, ...eventResizes),
                eventSelection,
            };
        }
        joinSegs(resourceDayTable, ...segGroups) {
            let resourceCnt = resourceDayTable.resources.length;
            let transformedSegs = [];
            for (let i = 0; i < resourceCnt; i += 1) {
                for (let seg of segGroups[i]) {
                    transformedSegs.push(...this.transformSeg(seg, resourceDayTable, i));
                }
                for (let seg of segGroups[resourceCnt]) { // one beyond. the all-resource
                    transformedSegs.push(...this.transformSeg(seg, resourceDayTable, i));
                }
            }
            return transformedSegs;
        }
        /*
        for expanding non-resource segs to all resources.
        only for public use.
        no memoizing.
        */
        expandSegs(resourceDayTable, segs) {
            let resourceCnt = resourceDayTable.resources.length;
            let transformedSegs = [];
            for (let i = 0; i < resourceCnt; i += 1) {
                for (let seg of segs) {
                    transformedSegs.push(...this.transformSeg(seg, resourceDayTable, i));
                }
            }
            return transformedSegs;
        }
        joinInteractions(resourceDayTable, ...interactions) {
            let resourceCnt = resourceDayTable.resources.length;
            let affectedInstances = {};
            let transformedSegs = [];
            let anyInteractions = false;
            let isEvent = false;
            for (let i = 0; i < resourceCnt; i += 1) {
                let interaction = interactions[i];
                if (interaction) {
                    anyInteractions = true;
                    for (let seg of interaction.segs) {
                        transformedSegs.push(...this.transformSeg(seg, resourceDayTable, i));
                    }
                    Object.assign(affectedInstances, interaction.affectedInstances);
                    isEvent = isEvent || interaction.isEvent;
                }
                if (interactions[resourceCnt]) { // one beyond. the all-resource
                    for (let seg of interactions[resourceCnt].segs) {
                        transformedSegs.push(...this.transformSeg(seg, resourceDayTable, i));
                    }
                }
            }
            if (anyInteractions) {
                return {
                    affectedInstances,
                    segs: transformedSegs,
                    isEvent,
                };
            }
            return null;
        }
    }

    /*
    TODO: just use ResourceHash somehow? could then use the generic ResourceSplitter
    */
    class VResourceSplitter extends internal$1.Splitter {
        getKeyInfo(props) {
            let { resourceDayTableModel } = props;
            let hash = internal$1.mapHash(resourceDayTableModel.resourceIndex.indicesById, (i) => resourceDayTableModel.resources[i]); // :(
            hash[''] = {};
            return hash;
        }
        getKeysForDateSpan(dateSpan) {
            return [dateSpan.resourceId || ''];
        }
        getKeysForEventDef(eventDef) {
            let resourceIds = eventDef.resourceIds;
            if (!resourceIds.length) {
                return [''];
            }
            return resourceIds;
        }
    }

    /*
    doesn't accept grouping
    */
    function flattenResources(resourceStore, orderSpecs) {
        return buildRowNodes(resourceStore, [], orderSpecs, false, {}, true)
            .map((node) => node.resource);
    }
    function buildRowNodes(resourceStore, groupSpecs, orderSpecs, isVGrouping, expansions, expansionDefault) {
        let complexNodes = buildHierarchy(resourceStore, isVGrouping ? -1 : 1, groupSpecs, orderSpecs);
        let flatNodes = [];
        flattenNodes(complexNodes, flatNodes, isVGrouping, [], 0, expansions, expansionDefault);
        return flatNodes;
    }
    function flattenNodes(complexNodes, res, isVGrouping, rowSpans, depth, expansions, expansionDefault) {
        for (let i = 0; i < complexNodes.length; i += 1) {
            let complexNode = complexNodes[i];
            let group = complexNode.group;
            if (group) {
                if (isVGrouping) {
                    let firstRowIndex = res.length;
                    let rowSpanIndex = rowSpans.length;
                    flattenNodes(complexNode.children, res, isVGrouping, rowSpans.concat(0), depth, expansions, expansionDefault);
                    if (firstRowIndex < res.length) {
                        let firstRow = res[firstRowIndex];
                        let firstRowSpans = firstRow.rowSpans = firstRow.rowSpans.slice();
                        firstRowSpans[rowSpanIndex] = res.length - firstRowIndex;
                    }
                }
                else {
                    let id = group.spec.field + ':' + group.value;
                    let isExpanded = expansions[id] != null ? expansions[id] : expansionDefault;
                    res.push({ id, group, isExpanded });
                    if (isExpanded) {
                        flattenNodes(complexNode.children, res, isVGrouping, rowSpans, depth + 1, expansions, expansionDefault);
                    }
                }
            }
            else if (complexNode.resource) {
                let id = complexNode.resource.id;
                let isExpanded = expansions[id] != null ? expansions[id] : expansionDefault;
                res.push({
                    id,
                    rowSpans,
                    depth,
                    isExpanded,
                    hasChildren: Boolean(complexNode.children.length),
                    resource: complexNode.resource,
                    resourceFields: complexNode.resourceFields,
                });
                if (isExpanded) {
                    flattenNodes(complexNode.children, res, isVGrouping, rowSpans, depth + 1, expansions, expansionDefault);
                }
            }
        }
    }
    function buildHierarchy(resourceStore, maxDepth, groupSpecs, orderSpecs) {
        let resourceNodes = buildResourceNodes(resourceStore, orderSpecs);
        let builtNodes = [];
        for (let resourceId in resourceNodes) {
            let resourceNode = resourceNodes[resourceId];
            if (!resourceNode.resource.parentId) {
                insertResourceNode(resourceNode, builtNodes, groupSpecs, 0, maxDepth, orderSpecs);
            }
        }
        return builtNodes;
    }
    function buildResourceNodes(resourceStore, orderSpecs) {
        let nodeHash = {};
        for (let resourceId in resourceStore) {
            let resource = resourceStore[resourceId];
            nodeHash[resourceId] = {
                resource,
                resourceFields: buildResourceFields(resource),
                children: [],
            };
        }
        for (let resourceId in resourceStore) {
            let resource = resourceStore[resourceId];
            if (resource.parentId) {
                let parentNode = nodeHash[resource.parentId];
                if (parentNode) {
                    insertResourceNodeInSiblings(nodeHash[resourceId], parentNode.children, orderSpecs);
                }
            }
        }
        return nodeHash;
    }
    function insertResourceNode(resourceNode, nodes, groupSpecs, depth, maxDepth, orderSpecs) {
        if (groupSpecs.length && (maxDepth === -1 || depth <= maxDepth)) {
            let groupNode = ensureGroupNodes(resourceNode, nodes, groupSpecs[0]);
            insertResourceNode(resourceNode, groupNode.children, groupSpecs.slice(1), depth + 1, maxDepth, orderSpecs);
        }
        else {
            insertResourceNodeInSiblings(resourceNode, nodes, orderSpecs);
        }
    }
    function ensureGroupNodes(resourceNode, nodes, groupSpec) {
        let groupValue = resourceNode.resourceFields[groupSpec.field];
        let groupNode;
        let newGroupIndex;
        // find an existing group that matches, or determine the position for a new group
        if (groupSpec.order) {
            for (newGroupIndex = 0; newGroupIndex < nodes.length; newGroupIndex += 1) {
                let node = nodes[newGroupIndex];
                if (node.group) {
                    let cmp = internal$1.flexibleCompare(groupValue, node.group.value) * groupSpec.order;
                    if (cmp === 0) {
                        groupNode = node;
                        break;
                    }
                    else if (cmp < 0) {
                        break;
                    }
                }
            }
        }
        else { // the groups are unordered
            for (newGroupIndex = 0; newGroupIndex < nodes.length; newGroupIndex += 1) {
                let node = nodes[newGroupIndex];
                if (node.group && groupValue === node.group.value) {
                    groupNode = node;
                    break;
                }
            }
        }
        if (!groupNode) {
            groupNode = {
                group: {
                    value: groupValue,
                    spec: groupSpec,
                },
                children: [],
            };
            nodes.splice(newGroupIndex, 0, groupNode);
        }
        return groupNode;
    }
    function insertResourceNodeInSiblings(resourceNode, siblings, orderSpecs) {
        let i;
        for (i = 0; i < siblings.length; i += 1) {
            let cmp = internal$1.compareByFieldSpecs(siblings[i].resourceFields, resourceNode.resourceFields, orderSpecs); // TODO: pass in ResourceApi?
            if (cmp > 0) { // went 1 past. insert at i
                break;
            }
        }
        siblings.splice(i, 0, resourceNode);
    }
    function buildResourceFields(resource) {
        let obj = Object.assign(Object.assign(Object.assign({}, resource.extendedProps), resource.ui), resource);
        delete obj.ui;
        delete obj.extendedProps;
        return obj;
    }
    function isGroupsEqual(group0, group1) {
        return group0.spec === group1.spec && group0.value === group1.value;
    }

    var internal = {
        __proto__: null,
        refineRenderProps: refineRenderProps$1,
        DEFAULT_RESOURCE_ORDER: DEFAULT_RESOURCE_ORDER,
        ResourceDayHeader: ResourceDayHeader,
        AbstractResourceDayTableModel: AbstractResourceDayTableModel,
        ResourceDayTableModel: ResourceDayTableModel,
        DayResourceTableModel: DayResourceTableModel,
        VResourceJoiner: VResourceJoiner,
        VResourceSplitter: VResourceSplitter,
        getPublicId: getPublicId,
        flattenResources: flattenResources,
        isGroupsEqual: isGroupsEqual,
        buildRowNodes: buildRowNodes,
        buildResourceFields: buildResourceFields,
        ResourceSplitter: ResourceSplitter,
        ResourceLabelContainer: ResourceLabelContainer
    };

    core.globalPlugins.push(plugin);

    exports.Internal = internal;
    exports.ResourceApi = ResourceApi;
    exports["default"] = plugin;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({}, FullCalendar, FullCalendar.PremiumCommon, FullCalendar.Internal, FullCalendar.Preact);
