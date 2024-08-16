/*!
FullCalendar Resource Time Grid Plugin v6.1.15
Docs & License: https://fullcalendar.io/docs/vertical-resource-view
(c) 2024 Adam Shaw
*/
FullCalendar.ResourceTimeGrid = (function (exports, core, premiumCommonPlugin, resourcePlugin, timeGridPlugin, internal$2, preact, internal$3, internal$1, internal$4) {
    'use strict';

    function _interopDefault (e) { return e && e.__esModule ? e : { 'default': e }; }

    var premiumCommonPlugin__default = /*#__PURE__*/_interopDefault(premiumCommonPlugin);
    var resourcePlugin__default = /*#__PURE__*/_interopDefault(resourcePlugin);
    var timeGridPlugin__default = /*#__PURE__*/_interopDefault(timeGridPlugin);

    class ResourceDayTimeColsJoiner extends internal$1.VResourceJoiner {
        transformSeg(seg, resourceDayTable, resourceI) {
            return [
                Object.assign(Object.assign({}, seg), { col: resourceDayTable.computeCol(seg.col, resourceI) }),
            ];
        }
    }

    class ResourceDayTimeCols extends internal$2.DateComponent {
        constructor() {
            super(...arguments);
            this.buildDayRanges = internal$2.memoize(internal$3.buildDayRanges);
            this.splitter = new internal$1.VResourceSplitter();
            this.slicers = {};
            this.joiner = new ResourceDayTimeColsJoiner();
            this.timeColsRef = preact.createRef();
            this.isHitComboAllowed = (hit0, hit1) => {
                let allowAcrossResources = this.dayRanges.length === 1;
                return allowAcrossResources || hit0.dateSpan.resourceId === hit1.dateSpan.resourceId;
            };
        }
        render() {
            let { props, context } = this;
            let { dateEnv, options } = context;
            let { dateProfile, resourceDayTableModel } = props;
            let dayRanges = this.dayRanges = this.buildDayRanges(resourceDayTableModel.dayTableModel, dateProfile, dateEnv);
            let splitProps = this.splitter.splitProps(props);
            this.slicers = internal$2.mapHash(splitProps, (split, resourceId) => this.slicers[resourceId] || new internal$3.DayTimeColsSlicer());
            let slicedProps = internal$2.mapHash(this.slicers, (slicer, resourceId) => slicer.sliceProps(splitProps[resourceId], dateProfile, null, context, dayRanges));
            return ( // TODO: would move this further down hierarchy, but sliceNowDate needs it
            preact.createElement(internal$2.NowTimer, { unit: options.nowIndicator ? 'minute' : 'day' }, (nowDate, todayRange) => (preact.createElement(internal$3.TimeCols, Object.assign({ ref: this.timeColsRef }, this.joiner.joinProps(slicedProps, resourceDayTableModel), { dateProfile: dateProfile, axis: props.axis, slotDuration: props.slotDuration, slatMetas: props.slatMetas, cells: resourceDayTableModel.cells[0], tableColGroupNode: props.tableColGroupNode, tableMinWidth: props.tableMinWidth, clientWidth: props.clientWidth, clientHeight: props.clientHeight, expandRows: props.expandRows, nowDate: nowDate, nowIndicatorSegs: options.nowIndicator && this.buildNowIndicatorSegs(nowDate), todayRange: todayRange, onScrollTopRequest: props.onScrollTopRequest, forPrint: props.forPrint, onSlatCoords: props.onSlatCoords, isHitComboAllowed: this.isHitComboAllowed })))));
        }
        buildNowIndicatorSegs(date) {
            let nonResourceSegs = this.slicers[''].sliceNowDate(date, this.props.dateProfile, this.context.options.nextDayThreshold, this.context, this.dayRanges);
            return this.joiner.expandSegs(this.props.resourceDayTableModel, nonResourceSegs);
        }
    }

    class ResourceDayTimeColsView extends internal$3.TimeColsView {
        constructor() {
            super(...arguments);
            this.flattenResources = internal$2.memoize(internal$1.flattenResources);
            this.buildResourceTimeColsModel = internal$2.memoize(buildResourceTimeColsModel);
            this.buildSlatMetas = internal$2.memoize(internal$3.buildSlatMetas);
        }
        render() {
            let { props, context } = this;
            let { options, dateEnv } = context;
            let { dateProfile } = props;
            let splitProps = this.allDaySplitter.splitProps(props);
            let resourceOrderSpecs = options.resourceOrder || internal$1.DEFAULT_RESOURCE_ORDER;
            let resources = this.flattenResources(props.resourceStore, resourceOrderSpecs);
            let resourceDayTableModel = this.buildResourceTimeColsModel(dateProfile, context.dateProfileGenerator, resources, options.datesAboveResources, context);
            let slatMetas = this.buildSlatMetas(dateProfile.slotMinTime, dateProfile.slotMaxTime, options.slotLabelInterval, options.slotDuration, dateEnv);
            let { dayMinWidth } = options;
            let hasAttachedAxis = !dayMinWidth;
            let hasDetachedAxis = dayMinWidth;
            let headerContent = options.dayHeaders && (preact.createElement(internal$1.ResourceDayHeader, { resources: resources, dates: resourceDayTableModel.dayTableModel.headerDates, dateProfile: dateProfile, datesRepDistinctDays: true, renderIntro: hasAttachedAxis ? this.renderHeadAxis : null }));
            let allDayContent = (options.allDaySlot !== false) && ((contentArg) => (preact.createElement(internal$4.ResourceDayTable, Object.assign({}, splitProps.allDay, { dateProfile: dateProfile, resourceDayTableModel: resourceDayTableModel, nextDayThreshold: options.nextDayThreshold, tableMinWidth: contentArg.tableMinWidth, colGroupNode: contentArg.tableColGroupNode, renderRowIntro: hasAttachedAxis ? this.renderTableRowAxis : null, showWeekNumbers: false, expandRows: false, headerAlignElRef: this.headerElRef, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, forPrint: props.forPrint }, this.getAllDayMaxEventProps()))));
            let timeGridContent = (contentArg) => (preact.createElement(ResourceDayTimeCols, Object.assign({}, splitProps.timed, { dateProfile: dateProfile, axis: hasAttachedAxis, slotDuration: options.slotDuration, slatMetas: slatMetas, resourceDayTableModel: resourceDayTableModel, tableColGroupNode: contentArg.tableColGroupNode, tableMinWidth: contentArg.tableMinWidth, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, onSlatCoords: this.handleSlatCoords, expandRows: contentArg.expandRows, forPrint: props.forPrint, onScrollTopRequest: this.handleScrollTopRequest })));
            return hasDetachedAxis
                ? this.renderHScrollLayout(headerContent, allDayContent, timeGridContent, resourceDayTableModel.colCnt, dayMinWidth, slatMetas, this.state.slatCoords)
                : this.renderSimpleLayout(headerContent, allDayContent, timeGridContent);
        }
    }
    function buildResourceTimeColsModel(dateProfile, dateProfileGenerator, resources, datesAboveResources, context) {
        let dayTable = internal$3.buildTimeColsModel(dateProfile, dateProfileGenerator);
        return datesAboveResources ?
            new internal$1.DayResourceTableModel(dayTable, resources, context) :
            new internal$1.ResourceDayTableModel(dayTable, resources, context);
    }

    var plugin = core.createPlugin({
        name: '@fullcalendar/resource-timegrid',
        premiumReleaseDate: '2024-07-12',
        deps: [
            premiumCommonPlugin__default["default"],
            resourcePlugin__default["default"],
            timeGridPlugin__default["default"],
        ],
        initialView: 'resourceTimeGridDay',
        views: {
            resourceTimeGrid: {
                type: 'timeGrid',
                component: ResourceDayTimeColsView,
                needsResourceData: true,
            },
            resourceTimeGridDay: {
                type: 'resourceTimeGrid',
                duration: { days: 1 },
            },
            resourceTimeGridWeek: {
                type: 'resourceTimeGrid',
                duration: { weeks: 1 },
            },
        },
    });

    var internal = {
        __proto__: null,
        ResourceDayTimeColsView: ResourceDayTimeColsView,
        ResourceDayTimeCols: ResourceDayTimeCols
    };

    core.globalPlugins.push(plugin);

    exports.Internal = internal;
    exports["default"] = plugin;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({}, FullCalendar, FullCalendar.PremiumCommon, FullCalendar.Resource, FullCalendar.TimeGrid, FullCalendar.Internal, FullCalendar.Preact, FullCalendar.TimeGrid.Internal, FullCalendar.Resource.Internal, FullCalendar.ResourceDayGrid.Internal);
