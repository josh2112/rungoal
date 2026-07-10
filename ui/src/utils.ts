import { Temporal } from "temporal-polyfill";

import { DurationFormat } from '@formatjs/intl-durationformat';

export const currentLocale = new Intl.DateTimeFormat().resolvedOptions().locale;

export const parseUtcDateTime = (str: string): Temporal.ZonedDateTime => Temporal.Instant.from(str).toZonedDateTimeISO("UTC");

export const durationFormatter = new DurationFormat("en", {
    style: "digital",
    hours: "2-digit",
    minutes: "2-digit",
    seconds: "2-digit"
});

export function formatDec(num: number, maxDecimals: number): string {
    return num.toLocaleString('en-US', {
        maximumFractionDigits: maxDecimals,
        useGrouping: false
    });
}

const DistanceUnitData = {
    meters: {
        abbreviation: "m",
        toBase: 1,
    },
    millimeters: {
        abbreviation: "mm",
        toBase: 0.001,
    },
    kilometers: {
        abbreviation: "km",
        toBase: 1000,
    },
    miles: {
        abbreviation: "mi",
        toBase: 1609.344,
    },
    feet: {
        abbreviation: "ft",
        toBase: 0.3048
    }
} as const;

export type DistanceUnit = keyof typeof DistanceUnitData;

export function distanceConvert(val: number, from: DistanceUnit, to: DistanceUnit) {
    return val * DistanceUnitData[from].toBase / DistanceUnitData[to].toBase;
}

export function distanceAbbr(unit: DistanceUnit) {
    return DistanceUnitData[unit].abbreviation;
}