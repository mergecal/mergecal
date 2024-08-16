/*!
FullCalendar Resource Day Grid Plugin v6.1.15
Docs & License: https://fullcalendar.io/docs/resource-daygrid-view
(c) 2024 Adam Shaw
*/
FullCalendar.ResourceDayGrid = (function (exports, core, premiumCommonPlugin, resourcePlugin, dayGridPlugin, internal$2, preact, internal$3, internal$1) {
    'use strict';

    function _interopDefault (e) { return e && e.__esModule ? e : { 'default': e }; }

    var premiumCommonPlugin__default = /*#__PURE__*/_interopDefault(premiumCommonPlugin);
    var resourcePlugin__default = /*#__PURE__*/_interopDefault(resourcePlugin);
    var dayGridPlugin__default = /*#__PURE__*/_interopDefault(dayGridPlugin);

    class ResourceDayTableJoiner extends internal$1.VResourceJoiner {
        transformSeg(seg, resourceDayTableModel, resourceI) {
            let colRanges = resourceDayTableModel.computeColRanges(seg.firstCol, seg.lastCol, resourceI);
            return colRanges.map((colRange) => (Object.assign(Object.assign(Object.assign({}, seg), colRange), { isStart: seg.isStart && colRange.isStart, isEnd: seg.isEnd && colRange.isEnd })));
        }
    }

    class ResourceDayTable extends internal$2.DateComponent {
        constructor() {
            super(...arguments);
            this.splitter = new internal$1.VResourceSplitter();
            this.slicers = {};
            this.joiner = new ResourceDayTableJoiner();
            this.tableRef = preact.createRef();
            this.isHitComboAllowed = (hit0, hit1) => {
                let allowAcrossResources = this.props.resourceDayTableModel.dayTableModel.colCnt === 1;
                return allowAcrossResources || hit0.dateSpan.resourceId === hit1.dateSpan.resourceId;
            };
        }
        render() {
            let { props, context } = this;
            let { resourceDayTableModel, nextDayThreshold, dateProfile } = props;
            let splitProps = this.splitter.splitProps(props);
            this.slicers = internal$2.mapHash(splitProps, (split, resourceId) => this.slicers[resourceId] || new internal$3.DayTableSlicer());
            let slicedProps = internal$2.mapHash(this.slicers, (slicer, resourceId) => slicer.sliceProps(splitProps[resourceId], dateProfile, nextDayThreshold, context, resourceDayTableModel.dayTableModel));
            return (preact.createElement(internal$3.Table, Object.assign({ forPrint: props.forPrint, ref: this.tableRef }, this.joiner.joinProps(slicedProps, resourceDayTableModel), { cells: resourceDayTableModel.cells, dateProfile: dateProfile, colGroupNode: props.colGroupNode, tableMinWidth: props.tableMinWidth, renderRowIntro: props.renderRowIntro, dayMaxEvents: props.dayMaxEvents, dayMaxEventRows: props.dayMaxEventRows, showWeekNumbers: props.showWeekNumbers, expandRows: props.expandRows, headerAlignElRef: props.headerAlignElRef, clientWidth: props.clientWidth, clientHeight: props.clientHeight, isHitComboAllowed: this.isHitComboAllowed })));
        }
    }

    class ResourceDayTableView extends internal$3.TableView {
        constructor() {
            super(...arguments);
            this.flattenResources = internal$2.memoize(internal$1.flattenResources);
            this.buildResourceDayTableModel = internal$2.memoize(buildResourceDayTableModel);
            this.headerRef = preact.createRef();
            this.tableRef = preact.createRef();
            // can't override any lifecycle methods from parent
        }
        render() {
            let { props, context } = this;
            let { options } = context;
            let resourceOrderSpecs = options.resourceOrder || internal$1.DEFAULT_RESOURCE_ORDER;
            let resources = this.flattenResources(props.resourceStore, resourceOrderSpecs);
            let resourceDayTableModel = this.buildResourceDayTableModel(props.dateProfile, context.dateProfileGenerator, resources, options.datesAboveResources, context);
            let headerContent = options.dayHeaders && (preact.createElement(internal$1.ResourceDayHeader, { ref: this.headerRef, resources: resources, dateProfile: props.dateProfile, dates: resourceDayTableModel.dayTableModel.headerDates, datesRepDistinctDays: true }));
            let bodyContent = (contentArg) => (preact.createElement(ResourceDayTable, { ref: this.tableRef, dateProfile: props.dateProfile, resourceDayTableModel: resourceDayTableModel, businessHours: props.businessHours, eventStore: props.eventStore, eventUiBases: props.eventUiBases, dateSelection: props.dateSelection, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, nextDayThreshold: options.nextDayThreshold, tableMinWidth: contentArg.tableMinWidth, colGroupNode: contentArg.tableColGroupNode, dayMaxEvents: options.dayMaxEvents, dayMaxEventRows: options.dayMaxEventRows, showWeekNumbers: options.weekNumbers, expandRows: !props.isHeightAuto, headerAlignElRef: this.headerElRef, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, forPrint: props.forPrint }));
            return options.dayMinWidth
                ? this.renderHScrollLayout(headerContent, bodyContent, resourceDayTableModel.colCnt, options.dayMinWidth)
                : this.renderSimpleLayout(headerContent, bodyContent);
        }
    }
    function buildResourceDayTableModel(dateProfile, dateProfileGenerator, resources, datesAboveResources, context) {
        let dayTable = internal$3.buildDayTableModel(dateProfile, dateProfileGenerator);
        return datesAboveResources ?
            new internal$1.DayResourceTableModel(dayTable, resources, context) :
            new internal$1.ResourceDayTableModel(dayTable, resources, context);
    }

    var plugin = core.createPlugin({
        name: '@fullcalendar/resource-daygrid',
        premiumReleaseDate: '2024-07-12',
        deps: [
            premiumCommonPlugin__default["default"],
            resourcePlugin__default["default"],
            dayGridPlugin__default["default"],
        ],
        initialView: 'resourceDayGridDay',
        views: {
            resourceDayGrid: {
                type: 'dayGrid',
                component: ResourceDayTableView,
                needsResourceData: true,
            },
            resourceDayGridDay: {
                type: 'resourceDayGrid',
                duration: { days: 1 },
            },
            resourceDayGridWeek: {
                type: 'resourceDayGrid',
                duration: { weeks: 1 },
            },
            resourceDayGridMonth: {
                type: 'resourceDayGrid',
                duration: { months: 1 },
                fixedWeekCount: true,
            },
        },
    });

    var internal = {
        __proto__: null,
        ResourceDayTableView: ResourceDayTableView,
        ResourceDayTable: ResourceDayTable
    };

    core.globalPlugins.push(plugin);

    exports.Internal = internal;
    exports["default"] = plugin;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({}, FullCalendar, FullCalendar.PremiumCommon, FullCalendar.Resource, FullCalendar.DayGrid, FullCalendar.Internal, FullCalendar.Preact, FullCalendar.DayGrid.Internal, FullCalendar.Resource.Internal);
