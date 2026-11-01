import type { PartName, SensorName } from './api'

// Sound is an optional stretch Sensor (#11): pages show it only when a Sleep Session has its Readings, and no part scores it.
export const SENSORS: { name: SensorName; label: string; unit: string; part?: PartName; optional?: true }[] = [
  { name: 'heart_rate', label: 'Heart rate', unit: 'bpm', part: 'heart_rate' },
  { name: 'temperature', label: 'Temperature', unit: '°C', part: 'environment' },
  { name: 'humidity', label: 'Humidity', unit: '%', part: 'environment' },
  { name: 'motion', label: 'Motion', unit: '/30 s', part: 'restlessness' },
  { name: 'sound', label: 'Sound', unit: 'dB', optional: true },
]

export const sensorsIn = (rows: { sensor: SensorName }[]) => SENSORS.filter((s) => !s.optional || rows.some((r) => r.sensor === s.name))

export const PART_NAMES: PartName[] = ['duration', 'restlessness', 'heart_rate', 'environment']
export const PART_LABELS: Record<PartName, string> = {
  duration: 'Duration',
  restlessness: 'Restlessness',
  heart_rate: 'Heart rate',
  environment: 'Environment',
}

// The API speaks UTC; the Sleeper reads local time.
export const clock = (iso: string | number) =>
  new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
export const day = (iso: string) => new Date(iso).toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' })
export const duration = (ms: number) => {
  const m = Math.round(ms / 60_000)
  return `${Math.floor(m / 60)} h ${m % 60} min`
}
export const between = (from: string, to: string) => duration(Date.parse(to) - Date.parse(from))
