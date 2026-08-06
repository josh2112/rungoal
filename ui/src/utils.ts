import { Temporal } from "temporal-polyfill";

export const { locale: currentLocale, timeZone: currentTimeZone } = new Intl.DateTimeFormat().resolvedOptions();

export const parseUtcDateTime = (str: string): Temporal.ZonedDateTime =>
    Temporal.Instant.from(str).toZonedDateTimeISO("UTC").withTimeZone(currentTimeZone);

export const durationFormatter = (duration: Temporal.Duration) => {
    const paddedSeconds = String(duration.seconds).padStart(2, "0");

    if (duration.hours == 0) {
        return `${duration.minutes}:${paddedSeconds}`;
    } else {
        `${duration.hours}:${String(duration.seconds).padStart(2, "0")}:${paddedSeconds}`;
    }
};

export function formatDec(num: number, maxDecimals: number): string {
    return num.toLocaleString("en-US", {
        maximumFractionDigits: maxDecimals,
        useGrouping: false,
    });
}

const DistanceUnitData = {
    meters: {
        abbreviation: "m",
        fromBase: (v: number) => v,
        toBase: (v: number) => v,
    },
    millimeters: {
        abbreviation: "mm",
        fromBase: (v: number) => v * 1000,
        toBase: (v: number) => v * 0.001,
    },
    kilometers: {
        abbreviation: "km",
        fromBase: (v: number) => v * 0.001,
        toBase: (v: number) => v * 1000,
    },
    miles: {
        abbreviation: "mi",
        fromBase: (v: number) => v * 0.000621371192,
        toBase: (v: number) => v * 1609.344,
    },
    feet: {
        abbreviation: "ft",
        fromBase: (v: number) => v * 3.280839895,
        toBase: (v: number) => v * 0.3048,
    },
} as const;

export type DistanceUnit = keyof typeof DistanceUnitData;

export function distanceConvert(val: number, from: DistanceUnit, to: DistanceUnit) {
    return DistanceUnitData[to].fromBase(DistanceUnitData[from].toBase(val));
}

export function distanceAbbr(unit: DistanceUnit) {
    return DistanceUnitData[unit].abbreviation;
}

const TemperatureUnitData = {
    celsius: {
        abbreviation: "°C",
        fromBase: (v: number) => v,
        toBase: (v: number) => v,
    },
    fahrenheit: {
        abbreviation: "°F",
        fromBase: (v: number) => v * 1.8 + 32,
        toBase: (v: number) => (v - 32) / 1.8,
    },
};

export type TemperatureUnit = keyof typeof TemperatureUnitData;

export function temperatureConvert(val: number, from: TemperatureUnit, to: TemperatureUnit) {
    return TemperatureUnitData[to].fromBase(TemperatureUnitData[from].toBase(val));
}

export function temperatureAbbr(unit: TemperatureUnit) {
    return TemperatureUnitData[unit].abbreviation;
}
